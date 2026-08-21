"""
EPC 出貨／進場排程 後端 API
=============================
跟 line-pdf-collector 一樣的架構：Flask + Render 部署，Airtable 金鑰只存在伺服器的
環境變數裡，前端網頁只呼叫這支程式提供的 API，不會碰到 Airtable 金鑰。

===================================================================
資料結構說明（實際查證過的真實結構，不是憑空設計）
===================================================================
「[電廠] 案場管理」Base 裡有兩張關鍵表：

1. 專案細節（案件主表）：一個案件一筆記錄，案號／廠商／地址／同意備案／掛表日期都在這；
   還有一個「進度管理」連結欄位，連到該案件在「進度管理」表裡的 18 筆里程碑記錄。
2. 進度管理（里程碑表）：**整張表是全公司所有案件、所有歷史紀錄**，一個案件對應 18 筆
   （工程合約簽約、併聯審查、同意備案…大料出貨時間、進場屋主預約…），
   各自有「預估日期」「實際日期」欄位。這張表可能非常大（全公司歷年案件 × 18）。

出貨、進場的排定，寫的就是「進度管理」表裡對應那一筆的「實際日期」：
  - 出貨 → 「大料出貨時間」那一筆（模組＋變流器視為同一個出貨事件，寫同一天）
  - 進場 → 「進場屋主預約」那一筆

===================================================================
效能設計（重要！之前踩過的坑）
===================================================================
❌ 錯誤做法：對整張「進度管理」表做 filterByFormula 找「種類=大料出貨時間」，
   因為這張表是全公司歷史資料，符合的筆數可能是幾千筆，分頁抓取要跑非常久
   （實測會卡超過 20 分鐘沒有回應，等同卡死）。

✅ 正確做法：
   1. 先用「專案細節」表的篩選條件（進行中 / 廠商 / 同意備案 / 掛表日期）鎖定
      一小批相關案件（通常幾十到一兩百筆）。
   2. 從這批案件的「進度管理」連結欄位，直接拿到每個案件對應的 18 筆里程碑
      record ID（不用查表，這些 ID 就在案件自己的欄位裡）。
   3. 把這些 ID 收集起來，用 OR(RECORD_ID()='...', ...) 分批只查「這些 ID
      裡種類是大料出貨時間或進場屋主預約」的記錄，不用管全表其他幾千筆。

===================================================================
資料更新架構（排程快取，不即時查詢）
===================================================================
  - 伺服器背景排程，每天 00:00／06:00／12:00／18:00（台北時間）整批查一次，
    存在記憶體的 DATA_CACHE。
  - 前端呼叫 /api/pending-cases、/api/entry-cases 直接讀 DATA_CACHE，秒開。
  - 使用者「排定日期」寫入成功後，立刻觸發一次重新整理。
  - 伺服器剛啟動時會立刻背景跑一次。
"""

import os
import time
import threading
import requests
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

app = Flask(__name__)
CORS(app)

# ===================================================================
# CONFIG
# ===================================================================

AIRTABLE_TOKEN = os.environ.get("AIRTABLE_TOKEN")
BASE_ID = "appj1wnO3WnRtIEvg"  # [電廠] 案場管理

# ---- 專案細節（案件主表） ----
CASE_TABLE_ID = "tblf6BPFcanBjHbaJ"
FIELD_CASE_NO = "fldt8vJbC6JtULwS6"
FIELD_ALIAS = "fldU5syY0OnJTS4ej"
FIELD_VENDOR = "fldgSgF77Yphcexx5"
FIELD_ADDRESS = "fldSox2FNoZwdZ0hh"
FIELD_AGREE_DATE = "fldfZlnPNHYaKy20o"
FIELD_MODULE_MODEL = "fldhZHcdwFYpZAol2"
FIELD_MODULE_QTY = "fldUSsNYyCZnO4zZv"
FIELD_INVERTER = "fldJInen90VWm95ut"
FIELD_INVERTER_QTY = "fld1h9cneDIQWnYrN"
FIELD_CLOSE_STATUS = "fldrnWIhxkZzJ7Got"
FIELD_HANG_METER_DATE = "fldNS6vTbnDtmQG0X"
FIELD_MS_LINK_ON_CASE = "fldEs9vLzY416tTHo"  # 「進度管理」連結欄位（在專案細節表上）

VENDOR_NAMES = ["三創", "尚展", "曙光"]

# ---- 採購-逆變器 ----
INVERTER_TABLE_ID = "tbl7l7OM63jo3pxDN"
INVERTER_MODEL_FIELD = "fldBkhuYPlr2w8hrH"

# ---- 進度管理（里程碑表） ----
MILESTONE_TABLE_ID = "tblxeiUluMFOBI2ci"
FIELD_MS_CASE_LINK = "fldome7Uo2fuK2Ucp"
FIELD_MS_TYPE = "fldTr1O1foeVmDbnm"
FIELD_MS_ACTUAL_DATE = "fldWuXRAVhfZJcjXj"
FIELD_MS_EST_DATE = "fldA9MK2ATP7GrLJC"

MILESTONE_TYPE_SHIP = "大料出貨時間"
MILESTONE_TYPE_ENTRY = "進場屋主預約"

CASE_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{CASE_TABLE_ID}"
MILESTONE_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{MILESTONE_TABLE_ID}"
INVERTER_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{INVERTER_TABLE_ID}"


def airtable_headers():
    return {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json",
    }


def airtable_get_all(api_url, filter_formula, fields):
    """處理 Airtable 分頁，把符合條件的所有記錄抓完（加上安全上限，避免萬一公式寫錯
    導致無止盡分頁）。用 returnFieldsByFieldId=true 讓回傳的 fields 用欄位 ID 當 key。"""
    records = []
    params = {
        "filterByFormula": filter_formula,
        "fields[]": fields,
        "pageSize": 100,
        "returnFieldsByFieldId": "true",
    }
    offset = None
    max_pages = 200  # 安全上限：最多 20,000 筆，正常情況遠遠用不到，純粹防呆避免真的卡死
    page = 0
    while True:
        if offset:
            params["offset"] = offset
        resp = requests.get(api_url, headers=airtable_headers(), params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        records.extend(data.get("records", []))
        offset = data.get("offset")
        page += 1
        if not offset or page >= max_pages:
            break
    return records


def format_module(fields):
    model = fields.get(FIELD_MODULE_MODEL)
    if not model:
        return None
    qty = fields.get(FIELD_MODULE_QTY)
    if isinstance(qty, (int, float)):
        qty = int(qty) if float(qty).is_integer() else qty
        return f"{model} ×{qty}"
    return model


def resolve_inverter_names(record_ids):
    """只查真正用到的那幾筆逆變器記錄的型號，不整表撈。"""
    ids = [rid for rid in record_ids if rid]
    if not ids:
        return {}
    name_map = {}
    batch_size = 80
    ids_list = list(set(ids))
    for i in range(0, len(ids_list), batch_size):
        batch = ids_list[i:i + batch_size]
        formula = "OR(" + ",".join(f"RECORD_ID()='{rid}'" for rid in batch) + ")"
        records = airtable_get_all(INVERTER_API_URL, formula, [INVERTER_MODEL_FIELD])
        for r in records:
            name_map[r["id"]] = r["fields"].get(INVERTER_MODEL_FIELD, r["id"])
    return name_map


def format_inverter(fields, name_map):
    ids = fields.get(FIELD_INVERTER) or []
    qtys = fields.get(FIELD_INVERTER_QTY) or []
    if not ids:
        return None
    parts = []
    for i, rid in enumerate(ids):
        name = name_map.get(rid, rid)
        q = qtys[i] if i < len(qtys) else None
        parts.append(f"{name} ×{q}" if q is not None else name)
    return "、".join(parts)


def fetch_milestones_for_case_pool(case_records):
    """收集這批案件（bounded，通常幾十到一兩百筆）在「進度管理」表裡的連結 record ID，
    分批只查『種類是大料出貨時間或進場屋主預約』的那幾筆——不用管全表其他幾千筆歷史資料。
    回傳 (ship_map, entry_map)，key 都是案件的 record_id。"""
    all_ms_ids = set()
    for r in case_records:
        all_ms_ids.update(r["fields"].get(FIELD_MS_LINK_ON_CASE) or [])

    ship_map, entry_map = {}, {}
    if not all_ms_ids:
        return ship_map, entry_map

    type_formula = f"OR({{{FIELD_MS_TYPE}}}='{MILESTONE_TYPE_SHIP}',{{{FIELD_MS_TYPE}}}='{MILESTONE_TYPE_ENTRY}')"
    ids_list = list(all_ms_ids)
    batch_size = 80  # Airtable formula/URL 長度有限，分批查
    for i in range(0, len(ids_list), batch_size):
        batch = ids_list[i:i + batch_size]
        id_formula = "OR(" + ",".join(f"RECORD_ID()='{mid}'" for mid in batch) + ")"
        formula = f"AND({id_formula},{type_formula})"
        records = airtable_get_all(
            MILESTONE_API_URL, formula,
            [FIELD_MS_CASE_LINK, FIELD_MS_TYPE, FIELD_MS_ACTUAL_DATE, FIELD_MS_EST_DATE],
        )
        for r in records:
            f = r["fields"]
            ms_type = f.get(FIELD_MS_TYPE)
            entry = {
                "milestone_record_id": r["id"],
                "actual_date": f.get(FIELD_MS_ACTUAL_DATE),
                "est_date": f.get(FIELD_MS_EST_DATE),
            }
            for cid in (f.get(FIELD_MS_CASE_LINK) or []):
                if ms_type == MILESTONE_TYPE_SHIP:
                    ship_map[cid] = entry
                elif ms_type == MILESTONE_TYPE_ENTRY:
                    entry_map[cid] = entry
    return ship_map, entry_map


def compute_case_pool():
    """抓一次基礎案件池：進行中 + 同意備案已填 + 掛表日期空 + 三創/尚展/曙光。
    這批案件同時涵蓋『待安排出貨』跟『已出貨待進場』兩種狀態（因為兩者都還沒掛表），
    後面再依「大料出貨時間」「進場屋主預約」是否已填分流，不用分兩次查案件表。"""
    vendor_formula = "OR(" + ",".join(f"{{{FIELD_VENDOR}}}='{v}'" for v in VENDOR_NAMES) + ")"
    formula = (
        f"AND("
        f"{{{FIELD_CLOSE_STATUS}}}='進行中',"
        f"NOT({{{FIELD_AGREE_DATE}}}=''),"
        f"{{{FIELD_HANG_METER_DATE}}}='',"
        f"{vendor_formula}"
        f")"
    )
    fields = [FIELD_CASE_NO, FIELD_ALIAS, FIELD_VENDOR, FIELD_ADDRESS, FIELD_AGREE_DATE,
              FIELD_MODULE_MODEL, FIELD_MODULE_QTY, FIELD_INVERTER, FIELD_INVERTER_QTY,
              FIELD_MS_LINK_ON_CASE]
    return airtable_get_all(CASE_API_URL, formula, fields)


def compute_pending_and_entry():
    """一次算出「待安排出貨案件」跟「案件進場安排」兩份清單。"""
    case_records = compute_case_pool()
    ship_map, entry_map = fetch_milestones_for_case_pool(case_records)

    all_inverter_ids = set()
    for r in case_records:
        all_inverter_ids.update(r["fields"].get(FIELD_INVERTER) or [])
    inverter_name_map = resolve_inverter_names(all_inverter_ids)

    pending, entry = [], []
    for r in case_records:
        f = r["fields"]
        ship_info = ship_map.get(r["id"])
        entry_info = entry_map.get(r["id"])
        module = format_module(f)
        inverter = format_inverter(f, inverter_name_map)

        base = {
            "record_id": r["id"],
            "case": f.get(FIELD_CASE_NO, ""),
            "alias": f.get(FIELD_ALIAS, ""),
            "vendor": f.get(FIELD_VENDOR, ""),
            "address": f.get(FIELD_ADDRESS, ""),
            "module": module,
            "inverter": inverter,
        }

        if not (ship_info and ship_info.get("actual_date")):
            # 還沒出貨 → 待安排出貨案件
            agree = f.get(FIELD_AGREE_DATE)
            pending.append({
                **base,
                "ship_milestone_record_id": ship_info["milestone_record_id"] if ship_info else None,
                "agree_date": agree[0] if isinstance(agree, list) and agree else agree,
            })
        elif not (entry_info and entry_info.get("actual_date")):
            # 已出貨，還沒進場 → 案件進場安排
            entry.append({
                **base,
                "ship_milestone_record_id": ship_info["milestone_record_id"],
                "entry_milestone_record_id": entry_info["milestone_record_id"] if entry_info else None,
                "ship_date": ship_info.get("actual_date"),
            })
        # else：已進場，兩份清單都不列（之後排程日曆功能會用到）

    return pending, entry


# ===================================================================
# 記憶體快取 + 背景排程
# ===================================================================

DATA_CACHE = {"pending": [], "entry": [], "updated_at": None, "refreshing": False, "last_error": None}
_cache_lock = threading.Lock()


def refresh_cache():
    with _cache_lock:
        if DATA_CACHE["refreshing"]:
            return
        DATA_CACHE["refreshing"] = True
    try:
        pending, entry = compute_pending_and_entry()
        DATA_CACHE["pending"] = pending
        DATA_CACHE["entry"] = entry
        DATA_CACHE["updated_at"] = datetime.now().isoformat()
        DATA_CACHE["last_error"] = None
        print(f"[refresh_cache] 完成，pending={len(pending)} entry={len(entry)}", flush=True)
    except Exception as e:
        DATA_CACHE["last_error"] = str(e)
        print(f"[refresh_cache] 失敗：{e}", flush=True)
    finally:
        DATA_CACHE["refreshing"] = False


scheduler = BackgroundScheduler(timezone="Asia/Taipei")
scheduler.add_job(refresh_cache, CronTrigger(hour="0,6,12,18", minute=0))
scheduler.start()

threading.Thread(target=refresh_cache, daemon=True).start()


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@app.route("/api/pending-cases")
def pending_cases():
    return jsonify({
        "count": len(DATA_CACHE["pending"]),
        "cases": DATA_CACHE["pending"],
        "updated_at": DATA_CACHE["updated_at"],
        "refreshing": DATA_CACHE["refreshing"],
        "last_error": DATA_CACHE["last_error"],
    })


@app.route("/api/entry-cases")
def entry_cases():
    return jsonify({
        "count": len(DATA_CACHE["entry"]),
        "cases": DATA_CACHE["entry"],
        "updated_at": DATA_CACHE["updated_at"],
        "refreshing": DATA_CACHE["refreshing"],
        "last_error": DATA_CACHE["last_error"],
    })


@app.route("/api/refresh", methods=["POST"])
def manual_refresh():
    threading.Thread(target=refresh_cache, daemon=True).start()
    return jsonify({"ok": True, "message": "已在背景開始重新整理"})


@app.route("/api/schedule", methods=["POST"])
def schedule_shipment():
    """排定（或重新排定）出貨時間，寫進「進度管理」表「大料出貨時間」那筆的實際日期。
    body: {milestone_record_id, ship_date}"""
    body = request.get_json(force=True)
    milestone_record_id = body.get("milestone_record_id")
    ship_date = body.get("ship_date")

    if not milestone_record_id or not ship_date:
        return jsonify({"error": "缺少 milestone_record_id 或 ship_date"}), 400

    resp = requests.patch(
        f"{MILESTONE_API_URL}/{milestone_record_id}",
        headers=airtable_headers(),
        json={"fields": {FIELD_MS_ACTUAL_DATE: ship_date}},
        timeout=20,
    )
    if resp.status_code >= 400:
        return jsonify({"error": "Airtable 寫入失敗", "detail": resp.text}), 502
    threading.Thread(target=refresh_cache, daemon=True).start()
    return jsonify({"ok": True, "record": resp.json()})


@app.route("/api/entry-date", methods=["POST"])
def schedule_entry():
    """排定進場日期，寫進「進度管理」表「進場屋主預約」那筆的實際日期。
    body: {milestone_record_id, entry_date}"""
    body = request.get_json(force=True)
    milestone_record_id = body.get("milestone_record_id")
    entry_date = body.get("entry_date")

    if not milestone_record_id or not entry_date:
        return jsonify({"error": "缺少 milestone_record_id 或 entry_date"}), 400

    resp = requests.patch(
        f"{MILESTONE_API_URL}/{milestone_record_id}",
        headers=airtable_headers(),
        json={"fields": {FIELD_MS_ACTUAL_DATE: entry_date}},
        timeout=20,
    )
    if resp.status_code >= 400:
        return jsonify({"error": "Airtable 寫入失敗", "detail": resp.text}), 502
    threading.Thread(target=refresh_cache, daemon=True).start()
    return jsonify({"ok": True, "record": resp.json()})


@app.route("/")
def health():
    return jsonify({
        "status": "ok",
        "service": "epc-backend",
        "cache_updated_at": DATA_CACHE["updated_at"],
        "refreshing": DATA_CACHE["refreshing"],
        "last_error": DATA_CACHE["last_error"],
        "pending_count": len(DATA_CACHE["pending"]),
        "entry_count": len(DATA_CACHE["entry"]),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
