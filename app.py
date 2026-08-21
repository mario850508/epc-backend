"""
EPC 出貨／進場排程 後端 API
=============================
跟 line-pdf-collector 一樣的架構：Flask + Render 部署，Airtable 金鑰只存在伺服器的
環境變數裡，前端網頁只呼叫這支程式提供的 API，不會碰到 Airtable 金鑰。

===================================================================
資料結構說明（實際查證過的真實結構，不是憑空設計）
===================================================================
「[電廠] 案場管理」Base 裡有兩張關鍵表：

1. 專案細節（案件主表）：一個案件一筆記錄，案號／廠商／地址／同意備案／掛表日期都在這。
2. 進度管理（里程碑表）：**一個案件對應 18 筆記錄**，每筆代表一個里程碑階段
   （工程合約簽約、併聯審查、同意備案…大料出貨時間、進場屋主預約…），
   每筆都有「預估日期」「實際日期」欄位。

也就是說「模組／變流器出貨」跟「進場」在 Airtable 裡本來就有對應的里程碑，
不需要另外新增欄位：
  - 出貨 → 進度管理表裡「種類 = 大料出貨時間」那一筆的「實際日期」
  - 進場 → 進度管理表裡「種類 = 進場屋主預約」那一筆的「實際日期」
（大料出貨時間視為模組＋變流器同一個出貨事件，寫同一個日期。）

狀態設計（不額外存資料庫，直接反映 Airtable 欄位）：
  待安排出貨案件 = 同意備案有值 且 掛表日期空 且「大料出貨時間」實際日期空
  案件進場安排   = 「大料出貨時間」實際日期有值 且「進場屋主預約」實際日期空
  已完成         = 「進場屋主預約」實際日期有值

===================================================================
資料更新架構（V2：排程快取，不再即時查詢）
===================================================================
直接即時查 Airtable 太慢（案件量一多，一次要 30 秒～1 分多鐘），改成：
  - 伺服器背景排程，每天 00:00 / 06:00 / 12:00 / 18:00（台北時間）自動整批查詢一次，
    結果存在記憶體裡的 DATA_CACHE。
  - 前端呼叫 /api/pending-cases、/api/entry-cases 時，直接回傳 DATA_CACHE 裡的內容，
    不會去查 Airtable，幾乎是秒開。
  - 使用者按「排定日期」「排定進場日期」寫入成功後，會立刻觸發一次 refresh_cache()，
    讓清單馬上反映最新狀態（這個當下會等幾秒，因為要重新整批查詢，但平常瀏覽時是秒開）。
  - 伺服器剛啟動時（第一次部署、或 Render 重啟）會立刻背景跑一次，不用等到下個整點。
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
CORS(app)  # 讓網頁前端（不同網域）可以呼叫這支 API

# ===================================================================
# CONFIG
# ===================================================================

AIRTABLE_TOKEN = os.environ.get("AIRTABLE_TOKEN")  # 部署到 Render 時用環境變數設定，不要寫死在程式碼裡
BASE_ID = "appj1wnO3WnRtIEvg"  # [電廠] 案場管理

# ---- 專案細節（案件主表） ----
CASE_TABLE_ID = "tblf6BPFcanBjHbaJ"
FIELD_CASE_NO = "fldt8vJbC6JtULwS6"       # 案號
FIELD_ALIAS = "fldU5syY0OnJTS4ej"         # 別名
FIELD_VENDOR = "fldgSgF77Yphcexx5"        # 施作廠商
FIELD_ADDRESS = "fldSox2FNoZwdZ0hh"       # 地址
FIELD_AGREE_DATE = "fldfZlnPNHYaKy20o"    # 同意備案（lookup，唯讀）
FIELD_MODULE_MODEL = "fldhZHcdwFYpZAol2"  # 模組型號
FIELD_MODULE_QTY = "fldUSsNYyCZnO4zZv"    # 電廠模組片數
FIELD_INVERTER = "fldJInen90VWm95ut"      # 採購-逆變器（linked records，回傳的是記錄代碼，要另外查表轉型號）
FIELD_INVERTER_QTY = "fld1h9cneDIQWnYrN"  # 逆變器數量（lookup）
FIELD_CLOSE_STATUS = "fldrnWIhxkZzJ7Got"  # 專案結案狀態
FIELD_HANG_METER_DATE = "fldNS6vTbnDtmQG0X"  # 掛表日期（lookup，唯讀）

VENDOR_NAMES = ["三創", "尚展", "曙光"]  # 先以這三間廠商測試

# ---- 採購-逆變器（連結欄位指到這張表，要用記錄 ID 反查型號） ----
INVERTER_TABLE_ID = "tbl7l7OM63jo3pxDN"
INVERTER_MODEL_FIELD = "fldBkhuYPlr2w8hrH"  # 型號

# ---- 進度管理（里程碑表） ----
MILESTONE_TABLE_ID = "tblxeiUluMFOBI2ci"
FIELD_MS_CASE_LINK = "fldome7Uo2fuK2Ucp"   # 專案（連回專案細節的 linked records）
FIELD_MS_TYPE = "fldTr1O1foeVmDbnm"        # 種類（single select）
FIELD_MS_ACTUAL_DATE = "fldWuXRAVhfZJcjXj"  # 實際日期
FIELD_MS_EST_DATE = "fldA9MK2ATP7GrLJC"     # 預估日期

MILESTONE_TYPE_SHIP = "大料出貨時間"   # 對應「模組／變流器出貨」
MILESTONE_TYPE_ENTRY = "進場屋主預約"  # 對應「進場」

CASE_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{CASE_TABLE_ID}"
MILESTONE_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{MILESTONE_TABLE_ID}"
INVERTER_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{INVERTER_TABLE_ID}"


def airtable_headers():
    return {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json",
    }


def airtable_get_all(api_url, filter_formula, fields):
    """處理 Airtable 分頁，把符合條件的所有記錄抓完。
    加上 returnFieldsByFieldId=true，讓回傳的 fields 物件用「欄位 ID」當 key
    （不加的話 Airtable 預設用「欄位名稱」當 key，會跟程式裡用 ID 讀取的邏輯對不起來）。"""
    records = []
    params = {
        "filterByFormula": filter_formula,
        "fields[]": fields,
        "pageSize": 100,
        "returnFieldsByFieldId": "true",
    }
    offset = None
    while True:
        if offset:
            params["offset"] = offset
        resp = requests.get(api_url, headers=airtable_headers(), params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return records


def get_milestone_map(milestone_type):
    """回傳 {案件record_id: {milestone_record_id, actual_date, est_date}}。"""
    formula = f"{{{FIELD_MS_TYPE}}}='{milestone_type}'"
    records = airtable_get_all(
        MILESTONE_API_URL, formula,
        [FIELD_MS_CASE_LINK, FIELD_MS_ACTUAL_DATE, FIELD_MS_EST_DATE],
    )
    result = {}
    for r in records:
        f = r["fields"]
        case_ids = f.get(FIELD_MS_CASE_LINK) or []
        for cid in case_ids:
            result[cid] = {
                "milestone_record_id": r["id"],
                "actual_date": f.get(FIELD_MS_ACTUAL_DATE),
                "est_date": f.get(FIELD_MS_EST_DATE),
            }
    return result


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
    """只查真正用到的那幾筆逆變器記錄的型號，不要整張表撈（那張表可能有上千筆）。"""
    ids = [rid for rid in record_ids if rid]
    if not ids:
        return {}
    formula = "OR(" + ",".join(f"RECORD_ID()='{rid}'" for rid in ids) + ")"
    records = airtable_get_all(INVERTER_API_URL, formula, [INVERTER_MODEL_FIELD])
    return {r["id"]: r["fields"].get(INVERTER_MODEL_FIELD, r["id"]) for r in records}


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


# ===================================================================
# 整批查詢邏輯（背景排程 / 手動刷新都呼叫這兩支）
# ===================================================================

def compute_pending_cases():
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
              FIELD_MODULE_MODEL, FIELD_MODULE_QTY, FIELD_INVERTER, FIELD_INVERTER_QTY]
    case_records = airtable_get_all(CASE_API_URL, formula, fields)

    ship_map = get_milestone_map(MILESTONE_TYPE_SHIP)

    all_inverter_ids = set()
    for r in case_records:
        all_inverter_ids.update(r["fields"].get(FIELD_INVERTER) or [])
    inverter_name_map = resolve_inverter_names(all_inverter_ids)

    result = []
    for r in case_records:
        ship_info = ship_map.get(r["id"])
        if ship_info and ship_info.get("actual_date"):
            continue  # 已經排過出貨了，不屬於「待安排」

        f = r["fields"]
        agree = f.get(FIELD_AGREE_DATE)
        result.append({
            "record_id": r["id"],
            "ship_milestone_record_id": ship_info["milestone_record_id"] if ship_info else None,
            "case": f.get(FIELD_CASE_NO, ""),
            "alias": f.get(FIELD_ALIAS, ""),
            "vendor": f.get(FIELD_VENDOR, ""),
            "address": f.get(FIELD_ADDRESS, ""),
            "agree_date": agree[0] if isinstance(agree, list) and agree else agree,
            "module": format_module(f),
            "inverter": format_inverter(f, inverter_name_map),
        })
    return result, ship_map  # ship_map 給 compute_entry_cases 重複使用，不用再查一次


def compute_entry_cases(ship_map=None):
    if ship_map is None:
        ship_map = get_milestone_map(MILESTONE_TYPE_SHIP)
    entry_map = get_milestone_map(MILESTONE_TYPE_ENTRY)

    shipped_case_ids = [
        cid for cid, info in ship_map.items()
        if info.get("actual_date") and not (entry_map.get(cid) or {}).get("actual_date")
    ]
    if not shipped_case_ids:
        return []

    fields = [FIELD_CASE_NO, FIELD_ALIAS, FIELD_VENDOR, FIELD_ADDRESS,
              FIELD_MODULE_MODEL, FIELD_MODULE_QTY, FIELD_INVERTER, FIELD_INVERTER_QTY]
    formula = "OR(" + ",".join(f"RECORD_ID()='{cid}'" for cid in shipped_case_ids) + ")"
    case_records = airtable_get_all(CASE_API_URL, formula, fields)

    all_inverter_ids = set()
    for r in case_records:
        all_inverter_ids.update(r["fields"].get(FIELD_INVERTER) or [])
    inverter_name_map = resolve_inverter_names(all_inverter_ids)

    result = []
    for r in case_records:
        f = r["fields"]
        ship_info = ship_map.get(r["id"], {})
        entry_info = entry_map.get(r["id"], {})
        result.append({
            "record_id": r["id"],
            "ship_milestone_record_id": ship_info.get("milestone_record_id"),
            "entry_milestone_record_id": entry_info.get("milestone_record_id"),
            "case": f.get(FIELD_CASE_NO, ""),
            "alias": f.get(FIELD_ALIAS, ""),
            "vendor": f.get(FIELD_VENDOR, ""),
            "address": f.get(FIELD_ADDRESS, ""),
            "module": format_module(f),
            "inverter": format_inverter(f, inverter_name_map),
            "ship_date": ship_info.get("actual_date"),
        })
    return result


# ===================================================================
# 記憶體快取 + 背景排程
# ===================================================================

DATA_CACHE = {"pending": [], "entry": [], "updated_at": None, "refreshing": False}
_cache_lock = threading.Lock()


def refresh_cache():
    """整批重新查詢一次 Airtable，更新 DATA_CACHE。定時排程跟「排定日期後」都會呼叫這支。"""
    with _cache_lock:
        if DATA_CACHE["refreshing"]:
            return  # 已經有一份在跑了，不要重複跑
        DATA_CACHE["refreshing"] = True
    try:
        pending, ship_map = compute_pending_cases()
        entry = compute_entry_cases(ship_map)
        DATA_CACHE["pending"] = pending
        DATA_CACHE["entry"] = entry
        DATA_CACHE["updated_at"] = datetime.now().isoformat()
        print(f"[refresh_cache] 完成，pending={len(pending)} entry={len(entry)}")
    except Exception as e:
        print(f"[refresh_cache] 失敗：{e}")
    finally:
        DATA_CACHE["refreshing"] = False


scheduler = BackgroundScheduler(timezone="Asia/Taipei")
scheduler.add_job(refresh_cache, CronTrigger(hour="0,6,12,18", minute=0))
scheduler.start()

# 伺服器一啟動就在背景跑一次，不用等到下個整點才有資料
threading.Thread(target=refresh_cache, daemon=True).start()


@app.route("/api/pending-cases")
def pending_cases():
    """待安排出貨案件 —— 直接回傳快取內容，不即時查 Airtable。"""
    return jsonify({
        "count": len(DATA_CACHE["pending"]),
        "cases": DATA_CACHE["pending"],
        "updated_at": DATA_CACHE["updated_at"],
    })


@app.route("/api/entry-cases")
def entry_cases():
    """案件進場安排 —— 直接回傳快取內容，不即時查 Airtable。"""
    return jsonify({
        "count": len(DATA_CACHE["entry"]),
        "cases": DATA_CACHE["entry"],
        "updated_at": DATA_CACHE["updated_at"],
    })


@app.route("/api/refresh", methods=["POST"])
def manual_refresh():
    """手動觸發一次重新整理（排定日期成功後會自動呼叫；也保留給以後有需要時手動呼叫）。"""
    threading.Thread(target=refresh_cache, daemon=True).start()
    return jsonify({"ok": True, "message": "已在背景開始重新整理"})


@app.route("/api/schedule", methods=["POST"])
def schedule_shipment():
    """排定（或重新排定）出貨時間，寫進「進度管理」表「大料出貨時間」那筆的實際日期。
    body: {milestone_record_id, ship_date}
    （模組／變流器視為同一個出貨事件，寫同一個日期；milestone_record_id 從
    /api/pending-cases 或 /api/entry-cases 回傳的 ship_milestone_record_id 取得）"""
    body = request.get_json(force=True)
    milestone_record_id = body.get("milestone_record_id")
    ship_date = body.get("ship_date")  # "YYYY-MM-DD"

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
    refresh_cache()  # 寫入成功後立刻整批重整一次，讓清單馬上反映最新狀態
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
    refresh_cache()
    return jsonify({"ok": True, "record": resp.json()})


@app.route("/")
def health():
    return jsonify({
        "status": "ok",
        "service": "epc-backend",
        "cache_updated_at": DATA_CACHE["updated_at"],
        "pending_count": len(DATA_CACHE["pending"]),
        "entry_count": len(DATA_CACHE["entry"]),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
