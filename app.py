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

===================================================================
2026-08-25 修改：refresh_cache 過期自動重置防呆
===================================================================
  - 之前發生過 refreshing 卡在 True、但完全沒有對應 log 的情況（懷疑是背景執行緒
    被中斷但沒machine執行到 finally，或 process 被砍時機太巧）。
  - 加上 refreshing_started_at 時間戳記：如果偵測到上一輪已經「開始」超過
    STALE_REFRESH_SECONDS 秒還沒結束，視為異常卡死，強制放行讓新的一輪開始，
    不再需要手動重啟服務。
  - 同時在每一行 log 加上時間相關資訊，方便之後排查卡在哪個時間點。

===================================================================
2026-08-27 修改：註記清單新增「未使用料件」類型
===================================================================
  - 前端「異常案件」在案件已出貨的狀態下按「撤案」時，會詢問是否把這筆案件的
    模組/逆變器規格記到「未使用料件」清單，也開放使用者手動新增料件；
    這裡把 create_note() 的允許類型清單、以及 get_app_data() 組裝 notes 時
    判斷的類型清單，都加上「未使用料件」，兩處要同時改，不然會出現「寫得進去、
    但讀不出來」的不一致情況。

===================================================================
2026-08-27 修改（二）：補齊 upsert_case_status() 的欄位白名單
===================================================================
  - 發現撤案原因/撤案日期、屋主聯絡資訊、植筋日期這幾個前端後來新增的欄位，
    從來沒有被加進 upsert_case_status() 的 field_map，導致前端送出的資料
    在後端就被過濾掉、根本沒送到 Airtable，但 API 仍回傳成功，造成「畫面上
    看起來寫入成功，重新整理後又消失」的假象。這裡把 field_map 跟
    get_app_data() 的讀取端都補齊，兩邊要同時改，道理跟上面「未使用料件」
    那次一樣。

===================================================================
2026-08-27 修改（三）：未使用料件加上出貨日期 + 新增「料件使用」清單
===================================================================
  - 註記清單新增「料件使用」類型，記錄「哪筆未使用料件被挪去哪個案場用掉了」。
  - create_note() 新增可選的 ship_date 欄位（寫入 Airtable「出貨日期」欄），
    目前只有「未使用料件」會帶這個值，用來記錄該料件原本是哪天出貨的。
  - 新增 PATCH /api/app-data/note/<record_id>，讓前端可以修改既有註記的內容
    （用於「未使用料件」被部分使用後更新剩餘數量說明，不用整筆刪除重建）。

===================================================================
2026-08-27 修改（四）：里程碑記錄缺失時自動新增
===================================================================
  - 發現有些案件（通常是舊案件、或人工建立時漏掉）在「進度管理」表裡缺少
    「大料出貨時間」「進場屋主預約」或「掛表」這幾筆里程碑記錄，導致前端完全
    無法排定日期（因為沒有 milestone_record_id 可以寫入）。
  - 新增 ensure_milestone_record()：/api/schedule、/api/entry-date、
    /api/hang-meter-date 這三支 API 現在都接受 milestone_record_id 留空，
    只要有帶 case_record_id，缺記錄時就會自動在「進度管理」表新增一筆對應種類
    的記錄並連結回案件，再繼續寫入日期，使用者不會再卡住。

===================================================================
2026-08-27 修改（五）：異常案件新增「待取得函文再進場」
===================================================================
  - 「異常案件」現在可以額外標記案件是卡在等某份函文（免雜／細部協商／
    台電購售契約）才能進場，存在 APP資料 表的「等待函文種類」欄位
    （waiting_doc_type）。
  - 新增 /api/milestone-status：即時查詢單一案件、單一種類里程碑在 Airtable
    「進度管理」表的完成狀態（不用等整批快取），前端在異常案件列表用這支 API
    顯示函文目前實際進度，讓使用者不用自己回 Airtable 對照。

===================================================================
2026-08-27 修改（六）：函文取得後自動排除異常 + 觸發依據改用函文日期
===================================================================
  - 新增「等待函文取得日期」欄位（waiting_doc_date）。前端偵測到函文已取得時，
    會自動清空 issue_note/issue_date（等同「已排除異常」），並把取得日期存進
    waiting_doc_date，但保留 waiting_doc_type，讓案件回到「待安排出貨&植筋」
    清單時，「觸發依據」欄位可以顯示這份函文的日期，而不是原本的同意備案日期。

===================================================================
2026-08-27 修改（七）：未使用料件可以事後修改案號／內容／出貨日期
===================================================================
  - update_note() 從只能改 content，擴充成 content/case_text/ship_date
    三個欄位都可以選擇性更新，用於「未使用料件」清單補填漏掉的出貨日期、
    或修正打錯的內容/案號，不用整筆刪除重建。

===================================================================
2026-08-27 修改（八）：/api/app-data 支援跳過歷史紀錄，給高頻率背景同步用
===================================================================
  - 前端要做多人協作的背景自動同步（每幾秒偷偷檢查一次有沒有其他人改過資料），
    但 get_app_data() 裡「歷史紀錄」那段，每一筆已封存案件都要額外查 1-2 次
    Airtable，案件一多會很慢，高頻率輪詢下更會逼近甚至超過 Airtable 每秒 5 次
    請求的限制。加上 include_archived=false 這個參數後，前端可以讓「案件狀態／
    註記」這種輕量、變動頻繁的部分用高頻率同步，「歷史紀錄」這種本來就不太會
    臨時變動的部分用低頻率同步，兩者互不拖累。

===================================================================
2026-08-28 修改（九）：直接在網站補填模組/逆變器規格，不用回 Airtable
===================================================================
  - 新增 /api/inverter-options：回傳「採購-逆變器」表現有的型號選項
    （record_id + 名稱）。逆變器在案件表上是連結欄位，前端不能自己打型號名稱，
    必須從這裡的選項裡選，才能正確連結。
  - 新增 /api/case-spec：把使用者在網站上填的模組型號/數量、逆變器型號/數量
    寫回 Airtable「專案細節」表，寫入成功後觸發一次 refresh_cache，讓「⚠ 尚未
    填寫規格」的案件補填完立刻反映在案件池快取裡。

===================================================================
2026-08-28 修改（十）：模組型號也改成選單 + 型號管理功能
===================================================================
  - 「模組型號」是 Airtable 的 Single select（固定選項）欄位，新增
    /api/module-options（GET 讀取現有選項、POST 新增選項），用 Airtable
    的 Meta API（schema.bases:read / schema.bases:write）讀寫這個欄位的
    選項清單，不是一般的資料讀寫 API，需要 Token 額外開這兩個 schema 權限，
    沒開的話會回傳明確的錯誤訊息，前端要能優雅降級（退回文字輸入），不能整個卡死。
  - 新增 POST /api/inverter-options：在「採購-逆變器」表新增一筆新記錄，
    對應前端「新增逆變器型號」的管理功能。

===================================================================
2026-08-28 修改（十一）：模組／逆變器型號選項改成記憶體快取
===================================================================
  - 原本 /api/inverter-options、/api/module-options 這兩支 API 每次被呼叫
    都直接即時打 Airtable（逆變器要撈整張表；模組型號要打較慢的 Meta API 查
    欄位結構），前端開「填寫規格」視窗時兩支疊在一起，實測要 20 秒以上。
  - 新增 MODEL_OPTIONS_CACHE + refresh_model_options_cache()，做法比照
    DATA_CACHE：伺服器啟動時背景跑一次、之後跟著 DATA_CACHE 同樣的
    00:00／06:00／12:00／18:00 排程更新（錯開 5 分鐘避免跟主要那份快取
    同時打 Airtable）。GET 這兩支 API 現在直接讀記憶體，秒回；新增型號
    （POST）成功後另外觸發一次立即刷新，讓新選項馬上可以選到，不用等下一輪。
  - 注意：_find_field_schema() 這個輔助函式被 refresh_model_options_cache()
    在啟動階段的背景執行緒呼叫，所以它的定義必須放在啟動該執行緒的程式碼「之前」
    （檔案裡由上到下的順序），不能放在後面才定義，不然背景執行緒可能會搶在
    主執行緒還沒執行到那個 def 之前就先呼叫，導致 NameError。
"""

import os
import time
import uuid
import threading
import netrc  # noqa: F401  # 見下方說明：必須在多執行緒啟動前先 import 一次，避免 requests 內部
              # 的 get_netrc_auth() 在多執行緒同時第一次 import 這個模組時卡死（曾造成
              # gunicorn worker 因 WORKER TIMEOUT 被砍掉，且完全沒有任何錯誤 log）。
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

VENDOR_NAMES = ["三創", "尚展", "曙光", "光鼎"]

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
MILESTONE_TYPE_METER = "掛表"

# 「異常案件」裡「待取得函文再進場」功能可選的函文種類，對應「進度管理」表裡
# 實際存在的里程碑「種類」名稱。如果 Airtable 那邊的實際命名跟這裡不同
# （尤其「台電契約」，Airtable 裡可能叫「台電購售契約」），要一併修改這裡。
DOCUMENT_MILESTONE_TYPES = ["免雜", "細部協商", "台電購售契約"]

CASE_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{CASE_TABLE_ID}"
MILESTONE_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{MILESTONE_TABLE_ID}"
INVERTER_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{INVERTER_TABLE_ID}"

# ---- APP資料（前端狀態同步用，跨裝置/跨使用者共用；取代原本的 localStorage）----
# 這張表是 2026-08-25 新增的，用來存放「已完工」「掛表安排」「異常案件」「變流器出貨日期」
# 「註記清單」這幾個原本只存在瀏覽器本機的狀態，改成寫回 Airtable，讓不同電腦、不同同事
# 都能看到同一份資料。這張表用「欄位名稱」而不是欄位 ID 存取（跟其他表不同），單純是因為
# 這張表是全新建立的，直接用名稱比較好維護，不用另外去 Airtable 查每個欄位的 ID。
APP_DATA_TABLE_ID = "tblafnN1qFDoLgTx1"
APP_DATA_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{APP_DATA_TABLE_ID}"

# 註記清單允許的「類型」。2026-08-27 新增「未使用料件」——
# create_note() 的驗證跟 get_app_data() 組裝 notes 的判斷都要用這份同一份清單，
# 避免兩邊各自寫一次、改一邊忘了改另一邊。
NOTE_TYPES = ("併聯取得時備貨", "其他狀況備住", "未使用料件", "料件使用")


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


# ===================================================================
# APP資料表 輔助函式（用欄位名稱，不是欄位 ID）
# ===================================================================

def app_data_get_all(filter_formula=None):
    records = []
    params = {"pageSize": 100}
    if filter_formula:
        params["filterByFormula"] = filter_formula
    offset = None
    while True:
        if offset:
            params["offset"] = offset
        resp = requests.get(APP_DATA_API_URL, headers=airtable_headers(), params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break
    return records


def app_data_find_case_row(case_record_id):
    """找這個案件在 APP資料 表裡「類型=案件狀態」的那一列（如果有的話）。"""
    escaped = case_record_id.replace("'", "\\'")
    formula = f"AND({{案件RecordID}}='{escaped}',{{類型}}='案件狀態')"
    recs = app_data_get_all(formula)
    return recs[0] if recs else None


def app_data_create(fields):
    resp = requests.post(APP_DATA_API_URL, headers=airtable_headers(), json={"fields": fields}, timeout=20)
    resp.raise_for_status()
    return resp.json()


def app_data_update(record_id, fields):
    resp = requests.patch(f"{APP_DATA_API_URL}/{record_id}", headers=airtable_headers(),
                           json={"fields": fields}, timeout=20)
    resp.raise_for_status()
    return resp.json()


def app_data_delete(record_id):
    resp = requests.delete(f"{APP_DATA_API_URL}/{record_id}", headers=airtable_headers(), timeout=20)
    resp.raise_for_status()
    return resp.json()


def _find_field_schema(table_id, field_id):
    """透過 Airtable Meta API 找到指定欄位目前的完整定義（含 Single select 的選項清單）。
    這支 API 需要 Token 有 schema.bases:read 這個範圍的權限，跟平常讀寫資料的權限不同，
    如果權限不夠，Airtable 會回傳 403，呼叫端要處理這種情況並提示使用者去檢查 Token 設定。"""
    resp = requests.get(
        f"https://api.airtable.com/v0/meta/bases/{BASE_ID}/tables",
        headers=airtable_headers(),
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    for table in data.get("tables", []):
        if table.get("id") != table_id:
            continue
        for field in table.get("fields", []):
            if field.get("id") == field_id:
                return field
    return None


def ensure_milestone_record(case_record_id, milestone_type):
    """如果案件在「進度管理」表裡缺少指定種類的里程碑記錄（例如舊案件建立時
    範本還沒有這個種類、或人工建立時漏掉了），就自動新增一筆，種類設為
    milestone_type，並連結回這個案件。Airtable 的雙向連結欄位會自動把這筆
    新記錄同步反向連結回案件表的「進度管理」欄位，不需要另外更新案件表。
    回傳新記錄的 record_id；失敗會拋出例外，由呼叫端處理。"""
    resp = requests.post(
        MILESTONE_API_URL,
        headers=airtable_headers(),
        json={"fields": {FIELD_MS_TYPE: milestone_type, FIELD_MS_CASE_LINK: [case_record_id]}},
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def fetch_case_snapshot_for_archive(case_record_id):
    """針對已經離開排程池的案件（掛表已確認完成），直接用 record_id 查案件本身跟相關里程碑，
    補齊「歷史紀錄」要顯示的資料。查不到就回傳 None（可能案件被刪除，或 record_id 有誤）。"""
    try:
        resp = requests.get(f"{CASE_API_URL}/{case_record_id}", headers=airtable_headers(), timeout=15)
        if resp.status_code >= 400:
            return None
        f = resp.json().get("fields", {})
    except Exception:
        return None

    module = format_module(f)
    inverter_ids = f.get(FIELD_INVERTER) or []
    inverter_name_map = resolve_inverter_names(inverter_ids)
    inverter = format_inverter(f, inverter_name_map)

    ms_ids = f.get(FIELD_MS_LINK_ON_CASE) or []
    ship_date = entry_date = meter_date = None
    if ms_ids:
        id_formula = "OR(" + ",".join(f"RECORD_ID()='{mid}'" for mid in ms_ids) + ")"
        type_formula = (
            f"OR({{{FIELD_MS_TYPE}}}='{MILESTONE_TYPE_SHIP}',"
            f"{{{FIELD_MS_TYPE}}}='{MILESTONE_TYPE_ENTRY}',"
            f"{{{FIELD_MS_TYPE}}}='{MILESTONE_TYPE_METER}')"
        )
        formula = f"AND({id_formula},{type_formula})"
        records = airtable_get_all(
            MILESTONE_API_URL, formula,
            [FIELD_MS_TYPE, FIELD_MS_ACTUAL_DATE],
        )
        for r in records:
            mf = r["fields"]
            mtype = mf.get(FIELD_MS_TYPE)
            date = mf.get(FIELD_MS_ACTUAL_DATE)
            if mtype == MILESTONE_TYPE_SHIP:
                ship_date = date
            elif mtype == MILESTONE_TYPE_ENTRY:
                entry_date = date
            elif mtype == MILESTONE_TYPE_METER:
                meter_date = date

    return {
        "case": f.get(FIELD_CASE_NO, ""),
        "alias": f.get(FIELD_ALIAS, ""),
        "vendor": f.get(FIELD_VENDOR, ""),
        "address": f.get(FIELD_ADDRESS, ""),
        "module": module,
        "inverter": inverter,
        "ship_date": ship_date,
        "entry_date": entry_date,
        "meter_date": meter_date,
    }


def format_module(fields):
    model = fields.get(FIELD_MODULE_MODEL)
    if not model:
        return None
    qty = fields.get(FIELD_MODULE_QTY)
    if isinstance(qty, (int, float)):
        # Airtable 這個欄位背後常常是公式/rollup 算出來的，可能回傳像 25.999999999999996
        # 這種浮點數誤差值，不會完全等於整數，因此不能只用 is_integer() 判斷；
        # 改成「跟最接近的整數相差在極小誤差內」就視為整數。
        rounded = round(qty)
        qty = rounded if abs(qty - rounded) < 1e-6 else qty
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
    total_batches = (len(ids_list) + batch_size - 1) // batch_size
    print(f"[步驟3] 共 {len(ids_list)} 個逆變器 ID，分 {total_batches} 批查詢…", flush=True)
    for i in range(0, len(ids_list), batch_size):
        batch_no = i // batch_size + 1
        batch = ids_list[i:i + batch_size]
        formula = "OR(" + ",".join(f"RECORD_ID()='{rid}'" for rid in batch) + ")"
        records = airtable_get_all(INVERTER_API_URL, formula, [INVERTER_MODEL_FIELD])
        print(f"[步驟3] 第 {batch_no}/{total_batches} 批完成，取得 {len(records)} 筆", flush=True)
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
        if isinstance(q, (int, float)):
            rounded = round(q)
            q = rounded if abs(q - rounded) < 1e-6 else q
        parts.append(f"{name} ×{q}" if q is not None else name)
    return "、".join(parts)


def fetch_milestones_for_case_pool(case_records):
    """收集這批案件（bounded，通常幾十到一兩百筆）在「進度管理」表裡的連結 record ID，
    分批只查『種類是大料出貨時間、進場屋主預約、或掛表』的那幾筆——不用管全表其他幾千筆歷史資料。
    回傳 (ship_map, entry_map, meter_map)，key 都是案件的 record_id。

    「掛表日期」是寫在這裡（里程碑記錄），不是案件表（專案細節）上那個同名欄位——
    案件表上的「掛表日期」欄位是唯讀的 lookup/rollup，直接寫入會失敗；
    案件表原本用來篩選案件池的 {FIELD_HANG_METER_DATE}='' 條件，等這裡的里程碑
    實際日期寫入後，Airtable 端會自動連動更新，下次 refresh_cache 案件就會自然
    從排程池消失，不用另外處理。"""
    all_ms_ids = set()
    for r in case_records:
        all_ms_ids.update(r["fields"].get(FIELD_MS_LINK_ON_CASE) or [])

    ship_map, entry_map, meter_map = {}, {}, {}
    if not all_ms_ids:
        print("[步驟2] 這批案件沒有任何『進度管理』連結 ID，略過", flush=True)
        return ship_map, entry_map, meter_map

    type_formula = (
        f"OR({{{FIELD_MS_TYPE}}}='{MILESTONE_TYPE_SHIP}',"
        f"{{{FIELD_MS_TYPE}}}='{MILESTONE_TYPE_ENTRY}',"
        f"{{{FIELD_MS_TYPE}}}='{MILESTONE_TYPE_METER}')"
    )
    ids_list = list(all_ms_ids)
    batch_size = 80  # Airtable formula/URL 長度有限，分批查
    total_batches = (len(ids_list) + batch_size - 1) // batch_size
    print(f"[步驟2] 共 {len(ids_list)} 個里程碑 ID，分 {total_batches} 批查詢…", flush=True)
    for i in range(0, len(ids_list), batch_size):
        batch_no = i // batch_size + 1
        batch = ids_list[i:i + batch_size]
        id_formula = "OR(" + ",".join(f"RECORD_ID()='{mid}'" for mid in batch) + ")"
        formula = f"AND({id_formula},{type_formula})"
        print(f"[步驟2] 查詢第 {batch_no}/{total_batches} 批…", flush=True)
        records = airtable_get_all(
            MILESTONE_API_URL, formula,
            [FIELD_MS_CASE_LINK, FIELD_MS_TYPE, FIELD_MS_ACTUAL_DATE, FIELD_MS_EST_DATE],
        )
        print(f"[步驟2] 第 {batch_no}/{total_batches} 批完成，取得 {len(records)} 筆", flush=True)
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
                elif ms_type == MILESTONE_TYPE_METER:
                    meter_map[cid] = entry
    print(f"[步驟2] 全部完成，ship_map={len(ship_map)} entry_map={len(entry_map)} "
          f"meter_map={len(meter_map)}", flush=True)
    return ship_map, entry_map, meter_map


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
    print("[步驟1] 開始查詢案件池…", flush=True)
    records = airtable_get_all(CASE_API_URL, formula, fields)
    print(f"[步驟1] 完成，案件池共 {len(records)} 筆", flush=True)
    return records


def compute_pending_and_entry():
    """一次算出「待安排出貨案件」「案件進場安排」「已進場」三份清單。
    「已進場」是模組出貨+進場日期都已填寫的案件；是否要在前端標記為「完工」
    純粹是前端本機自己記錄的狀態，不會回寫 Airtable，所以這份清單一律回傳
    給前端，由前端自己決定要不要繼續顯示在「案件進場安排」或移到「歷史紀錄」。"""
    case_records = compute_case_pool()
    ship_map, entry_map, meter_map = fetch_milestones_for_case_pool(case_records)

    all_inverter_ids = set()
    for r in case_records:
        all_inverter_ids.update(r["fields"].get(FIELD_INVERTER) or [])
    inverter_name_map = resolve_inverter_names(all_inverter_ids)
    print("[步驟4] 開始整理清單…", flush=True)

    pending, entry, completed = [], [], []
    for r in case_records:
        f = r["fields"]
        ship_info = ship_map.get(r["id"])
        entry_info = entry_map.get(r["id"])
        meter_info = meter_map.get(r["id"])
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
        else:
            # 出貨+進場都已完成 → 已進場（前端自行決定何時標記「完工」/「掛表」）
            completed.append({
                **base,
                "ship_date": ship_info.get("actual_date"),
                "entry_date": entry_info.get("actual_date"),
                "meter_milestone_record_id": meter_info["milestone_record_id"] if meter_info else None,
            })

    return pending, entry, completed


# ===================================================================
# 記憶體快取 + 背景排程
# ===================================================================

DATA_CACHE = {
    "pending": [],
    "entry": [],
    "completed": [],  # 出貨+進場都已完成，前端自行決定是否標記「完工」移入歷史紀錄
    "updated_at": None,
    "refreshing": False,
    "refreshing_started_at": None,   # 這一輪 refresh 是什麼時候開始的（datetime）
    "refreshing_run_id": None,       # 這一輪 refresh 的獨立編號，方便對照 log 追蹤
    "last_error": None,
}
_cache_lock = threading.Lock()

# 如果 refreshing=True 但已經超過這個秒數還沒結束，視為異常卡死，
# 下一次呼叫 refresh_cache() 時強制重置、重新開始，不用再手動重啟服務。
# 2026-08-25：正常一輪大約 10~30 秒會跑完，實測發現偶爾會出現不同 worker
# process 之間狀態不同步的情況（懷疑跟 Render 平台的 worker 生命週期/健康檢查機制有關，
# 不是單純的程式邏輯問題），因此把門檻從 5 分鐘縮短到 1 分鐘，讓系統能更快自動恢復，
# 把使用者最長等待時間壓在可接受範圍內。
STALE_REFRESH_SECONDS = 60


def refresh_cache():
    run_id = uuid.uuid4().hex[:8]  # 每一輪獨立編號，方便從 log 精準追蹤同一輪的開始/完成/重置
    pid = os.getpid()
    tid = threading.get_ident()
    now = datetime.now()
    tag = f"[refresh_cache #{run_id} pid={pid} tid={tid}]"

    with _cache_lock:
        if DATA_CACHE["refreshing"]:
            started = DATA_CACHE.get("refreshing_started_at")
            owner = DATA_CACHE.get("refreshing_run_id")
            age = (now - started).total_seconds() if started else None
            if age is not None and age < STALE_REFRESH_SECONDS:
                print(f"{tag} 已有其他更新在進行中（run_id={owner}，開始於 "
                      f"{started.isoformat()}，已過 {age:.0f} 秒），略過本次觸發", flush=True)
                return
            print(f"{tag} 偵測到上一輪（run_id={owner}）疑似卡死（開始於 "
                  f"{started.isoformat() if started else '未知'}，已過 "
                  f"{age:.0f} 秒，超過 {STALE_REFRESH_SECONDS} 秒門檻），強制重新開始", flush=True)
        DATA_CACHE["refreshing"] = True
        DATA_CACHE["refreshing_started_at"] = now
        DATA_CACHE["refreshing_run_id"] = run_id

    print(f"{tag} 開始…（{now.isoformat()}）", flush=True)
    try:
        pending, entry, completed = compute_pending_and_entry()
        DATA_CACHE["pending"] = pending
        DATA_CACHE["entry"] = entry
        DATA_CACHE["completed"] = completed
        DATA_CACHE["updated_at"] = datetime.now().isoformat()
        DATA_CACHE["last_error"] = None
        elapsed = (datetime.now() - now).total_seconds()
        print(f"{tag} 完成，pending={len(pending)} entry={len(entry)} completed={len(completed)}，"
              f"耗時 {elapsed:.1f} 秒", flush=True)
    except Exception as e:
        DATA_CACHE["last_error"] = str(e)
        print(f"{tag} 失敗：{e}", flush=True)
    finally:
        with _cache_lock:
            # 只有「這一輪自己」才可以清除 refreshing 狀態，避免萬一之後有更複雜的併發情境時，
            # 不小心清掉別輪剛設定好的狀態（目前設計下理論上不會發生，但這樣寫更保險）。
            if DATA_CACHE.get("refreshing_run_id") == run_id:
                DATA_CACHE["refreshing"] = False
                DATA_CACHE["refreshing_started_at"] = None
                DATA_CACHE["refreshing_run_id"] = None
                print(f"{tag} 已重置 refreshing=False", flush=True)
            else:
                print(f"{tag} 結束，但目前 refreshing_run_id 已經是 "
                      f"{DATA_CACHE.get('refreshing_run_id')}（不是自己），不重置，"
                      f"這是異常情況，需要留意", flush=True)


# ===================================================================
# requests 套件暖機（重要！）
# ===================================================================
# 曾經發生過背景執行緒卡在第一次呼叫 requests.get()/patch() 就永遠不動、
# 連我們自己設定的 timeout 都不會觸發、也不會拋出任何例外的情況（懷疑是
# requests/urllib3 底層某些模組——例如 netrc、ssl、certifi、字元編碼判斷
# 模組等——在多執行緒同時「第一次」import 時發生死結）。
# 解法：在這裡、程式還是單一執行緒、背景排程跟其他執行緒都還沒啟動之前，
# 先真的發一次 HTTPS 請求出去（就算失敗也沒關係，重點是強迫底層所有
# 這些模組把 import 走過一輪、放進 sys.modules 快取），這樣之後不管多少
# 執行緒同時打 requests.*，都不會再搶著做「第一次 import」而卡死。
try:
    print("[startup] 暖機中：預先發送一次 HTTPS 請求，避免多執行緒 import 死結…", flush=True)
    requests.get("https://api.airtable.com/", timeout=10)
    print("[startup] 暖機完成", flush=True)
except Exception as e:
    # 暖機請求失敗完全沒關係（例如網路還沒完全就緒），重點只是讓 import 跑過一輪
    print(f"[startup] 暖機請求本身失敗（沒關係，目的已達成）：{e}", flush=True)


# ===================================================================
# 模組／逆變器型號選項快取
# ===================================================================
# 「填寫規格」視窗要用的兩份選項清單（模組型號、逆變器型號），原本是每次開視窗
# 都直接打 Airtable（逆變器要撈整張表，模組型號要打比較慢的 Meta API 查欄位結構），
# 疊在一起單次要 20 秒以上。改成跟 DATA_CACHE 一樣的記憶體快取模式：背景排程
# 定期刷新，前端請求直接讀記憶體，秒回；新增型號成功後額外觸發一次立即刷新，
# 讓新選項馬上出現，不用等下一輪排程。
MODEL_OPTIONS_CACHE = {
    "inverter_options": [],
    "module_options": [],
    "module_options_available": True,
    "updated_at": None,
    "last_error": None,  # 記錄最近一次刷新時任何一邊失敗的錯誤訊息，方便從 / 健康檢查頁面直接看到原因
}
_model_cache_lock = threading.Lock()


def refresh_model_options_cache():
    tag = "[refresh_model_options_cache]"
    print(f"{tag} 開始…", flush=True)
    errors = []

    try:
        records = airtable_get_all(INVERTER_API_URL, "TRUE()", [INVERTER_MODEL_FIELD])
        inverter_options = [
            {"record_id": r["id"], "name": r["fields"].get(INVERTER_MODEL_FIELD, r["id"])}
            for r in records
        ]
        inverter_options.sort(key=lambda o: o["name"] or "")
    except Exception as e:
        msg = f"逆變器選項讀取失敗：{e}"
        print(f"{tag} {msg}（沿用舊快取）", flush=True)
        errors.append(msg)
        inverter_options = MODEL_OPTIONS_CACHE.get("inverter_options") or []

    module_options_available = True
    try:
        field = _find_field_schema(CASE_TABLE_ID, FIELD_MODULE_MODEL)
        if field and field.get("type") == "singleSelect":
            choices = field.get("options", {}).get("choices", [])
            module_options = [c.get("name") for c in choices if c.get("name")]
        elif field:
            module_options_available = False
            module_options = []
            errors.append(f"「模組型號」欄位目前是 {field.get('type')} 類型，不是固定選項欄位")
        else:
            module_options_available = False
            module_options = []
            errors.append("在 Airtable 找不到「模組型號」這個欄位（FIELD_MODULE_MODEL 設定可能不對）")
    except Exception as e:
        msg = f"模組型號選項讀取失敗：{e}（可能是 Token 缺 schema.bases:read 權限）"
        print(f"{tag} {msg}", flush=True)
        errors.append(msg)
        module_options_available = False
        module_options = MODEL_OPTIONS_CACHE.get("module_options") or []

    with _model_cache_lock:
        MODEL_OPTIONS_CACHE["inverter_options"] = inverter_options
        MODEL_OPTIONS_CACHE["module_options"] = module_options
        MODEL_OPTIONS_CACHE["module_options_available"] = module_options_available
        MODEL_OPTIONS_CACHE["updated_at"] = datetime.now().isoformat()
        MODEL_OPTIONS_CACHE["last_error"] = " ／ ".join(errors) if errors else None
    print(f"{tag} 完成，inverter_options={len(inverter_options)} "
          f"module_options={len(module_options)} available={module_options_available}", flush=True)


scheduler = BackgroundScheduler(timezone="Asia/Taipei")
scheduler.add_job(refresh_cache, CronTrigger(hour="0,6,12,18", minute=0))
scheduler.add_job(refresh_model_options_cache, CronTrigger(hour="0,6,12,18", minute=5))
scheduler.start()

threading.Thread(target=refresh_cache, daemon=True).start()
threading.Thread(target=refresh_model_options_cache, daemon=True).start()


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
        "refreshing_started_at": (
            DATA_CACHE["refreshing_started_at"].isoformat()
            if DATA_CACHE["refreshing_started_at"] else None
        ),
        "refreshing_run_id": DATA_CACHE.get("refreshing_run_id"),
        "last_error": DATA_CACHE["last_error"],
    })


@app.route("/api/entry-cases")
def entry_cases():
    return jsonify({
        "count": len(DATA_CACHE["entry"]),
        "cases": DATA_CACHE["entry"],
        "updated_at": DATA_CACHE["updated_at"],
        "refreshing": DATA_CACHE["refreshing"],
        "refreshing_started_at": (
            DATA_CACHE["refreshing_started_at"].isoformat()
            if DATA_CACHE["refreshing_started_at"] else None
        ),
        "refreshing_run_id": DATA_CACHE.get("refreshing_run_id"),
        "last_error": DATA_CACHE["last_error"],
    })


@app.route("/api/completed-cases")
def completed_cases():
    """出貨+進場都已完成的案件；是否標記「完工」移入歷史紀錄純粹是前端本機
    自己的狀態，這裡一律回傳全部已進場案件，由前端自行過濾顯示。"""
    return jsonify({
        "count": len(DATA_CACHE["completed"]),
        "cases": DATA_CACHE["completed"],
        "updated_at": DATA_CACHE["updated_at"],
        "refreshing": DATA_CACHE["refreshing"],
        "refreshing_started_at": (
            DATA_CACHE["refreshing_started_at"].isoformat()
            if DATA_CACHE["refreshing_started_at"] else None
        ),
        "refreshing_run_id": DATA_CACHE.get("refreshing_run_id"),
        "last_error": DATA_CACHE["last_error"],
    })


@app.route("/api/refresh", methods=["POST"])
def manual_refresh():
    threading.Thread(target=refresh_cache, daemon=True).start()
    return jsonify({"ok": True, "message": "已在背景開始重新整理"})


@app.route("/api/refresh-model-options", methods=["POST"])
def manual_refresh_model_options():
    """手動觸發一次模組／逆變器型號選項快取的重新整理，不用等排程、也不用重新部署。
    刷新完的結果（含錯誤訊息，如果有的話）可以到 / 健康檢查頁面的 model_options_cache
    裡看到。"""
    threading.Thread(target=refresh_model_options_cache, daemon=True).start()
    return jsonify({"ok": True, "message": "已在背景開始重新整理型號選項，完成後可到 / 健康檢查頁面查看結果"})


@app.route("/api/schedule", methods=["POST"])
def schedule_shipment():
    """排定（或重新排定）出貨時間，寫進「進度管理」表「大料出貨時間」那筆的實際日期。
    body: {milestone_record_id, case_record_id, ship_date}
    milestone_record_id 可以留空——如果案件在 Airtable「進度管理」表裡缺少這筆
    「大料出貨時間」里程碑記錄（例如舊案件建立時模板漏掉了），會自動幫這個案件
    新增一筆再寫入，但這種情況下就必須帶 case_record_id 才能知道要連結到哪個案件。"""
    body = request.get_json(force=True)
    milestone_record_id = body.get("milestone_record_id")
    case_record_id = body.get("case_record_id")
    ship_date = body.get("ship_date")

    if not ship_date:
        return jsonify({"error": "缺少 ship_date"}), 400
    if not milestone_record_id:
        if not case_record_id:
            return jsonify({"error": "缺少 milestone_record_id 或 case_record_id"}), 400
        try:
            milestone_record_id = ensure_milestone_record(case_record_id, MILESTONE_TYPE_SHIP)
            print(f"[schedule_shipment] 案件 {case_record_id} 缺少「大料出貨時間」里程碑，"
                  f"已自動新增：{milestone_record_id}", flush=True)
        except Exception as e:
            return jsonify({"error": "自動新增「大料出貨時間」里程碑記錄失敗", "detail": str(e)}), 502

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
    body: {milestone_record_id, case_record_id, entry_date}
    milestone_record_id 留空時，邏輯同 /api/schedule：自動新增缺少的里程碑記錄。"""
    body = request.get_json(force=True)
    milestone_record_id = body.get("milestone_record_id")
    case_record_id = body.get("case_record_id")
    entry_date = body.get("entry_date")

    if not entry_date:
        return jsonify({"error": "缺少 entry_date"}), 400
    if not milestone_record_id:
        if not case_record_id:
            return jsonify({"error": "缺少 milestone_record_id 或 case_record_id"}), 400
        try:
            milestone_record_id = ensure_milestone_record(case_record_id, MILESTONE_TYPE_ENTRY)
            print(f"[schedule_entry] 案件 {case_record_id} 缺少「進場屋主預約」里程碑，"
                  f"已自動新增：{milestone_record_id}", flush=True)
        except Exception as e:
            return jsonify({"error": "自動新增「進場屋主預約」里程碑記錄失敗", "detail": str(e)}), 502

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


@app.route("/api/hang-meter-date", methods=["POST"])
def schedule_hang_meter():
    """排定掛表日期，寫進「進度管理」表「掛表」那筆的實際日期——注意這是里程碑
    記錄（跟大料出貨時間、進場屋主預約的寫法一樣），不是案件表（專案細節）上那個
    同名欄位（那個是唯讀的 lookup/rollup，直接寫入會失敗）。
    寫入後，案件表上的「掛表日期」lookup 欄位會被 Airtable 自動連動更新，
    下次 refresh_cache 時案件就會自然從整個排程池（pending/entry/completed）消失
    ——這是既有 compute_case_pool() 篩選條件本來就有的行為，不用額外處理。
    同時，如果有帶 case_record_id，會一併把 APP資料 表裡這筆案件狀態標記為
    「掛表日期已確認」，讓前端知道要把這筆案件移入歷史紀錄。
    body: {case_record_id, milestone_record_id, hang_meter_date}
    milestone_record_id 留空時，邏輯同 /api/schedule：自動新增缺少的里程碑記錄
    （這種情況下 case_record_id 是必填，本來就必填，不受影響）。"""
    body = request.get_json(force=True)
    case_record_id = body.get("case_record_id")
    milestone_record_id = body.get("milestone_record_id")
    hang_meter_date = body.get("hang_meter_date")

    if not hang_meter_date:
        return jsonify({"error": "缺少 hang_meter_date"}), 400
    if not milestone_record_id:
        if not case_record_id:
            return jsonify({"error": "缺少 milestone_record_id 或 case_record_id"}), 400
        try:
            milestone_record_id = ensure_milestone_record(case_record_id, MILESTONE_TYPE_METER)
            print(f"[schedule_hang_meter] 案件 {case_record_id} 缺少「掛表」里程碑，"
                  f"已自動新增：{milestone_record_id}", flush=True)
        except Exception as e:
            return jsonify({"error": "自動新增「掛表」里程碑記錄失敗", "detail": str(e)}), 502

    resp = requests.patch(
        f"{MILESTONE_API_URL}/{milestone_record_id}",
        headers=airtable_headers(),
        json={"fields": {FIELD_MS_ACTUAL_DATE: hang_meter_date}},
        timeout=20,
    )
    if resp.status_code >= 400:
        return jsonify({"error": "Airtable 寫入失敗", "detail": resp.text}), 502

    if case_record_id:
        try:
            existing = app_data_find_case_row(case_record_id)
            if existing:
                app_data_update(existing["id"], {"掛表日期已確認": True})
        except Exception as e:
            print(f"[schedule_hang_meter] 更新 APP資料 掛表確認狀態失敗（不影響主要寫入）：{e}", flush=True)

    threading.Thread(target=refresh_cache, daemon=True).start()
    return jsonify({"ok": True, "record": resp.json()})


@app.route("/api/inverter-options")
def inverter_options():
    """回傳「採購-逆變器」表所有型號選項（record_id + 名稱），給前端做逆變器選單用。
    逆變器欄位在案件表上是連結欄位，前端不能自己亂打型號名稱，必須從這裡回傳的
    現有選項裡選，才能正確連結到 Airtable 的記錄。直接讀記憶體快取（見
    MODEL_OPTIONS_CACHE / refresh_model_options_cache），不用每次都重新查
    Airtable，秒回。"""
    return jsonify({"options": MODEL_OPTIONS_CACHE.get("inverter_options") or []})


@app.route("/api/inverter-options", methods=["POST"])
def create_inverter_option():
    """在「採購-逆變器」表新增一筆新型號記錄，讓「填寫規格」選單裡可以選到。
    寫入成功後立刻在背景刷新一次選項快取，讓新型號馬上出現，不用等下一輪排程。
    body: {name}"""
    body = request.get_json(force=True)
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "缺少 name"}), 400
    try:
        resp = requests.post(
            INVERTER_API_URL,
            headers=airtable_headers(),
            json={"fields": {INVERTER_MODEL_FIELD: name}},
            timeout=20,
        )
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        return jsonify({"error": "Airtable 寫入失敗", "detail": str(e)}), 502
    threading.Thread(target=refresh_model_options_cache, daemon=True).start()
    return jsonify({"ok": True, "record_id": result["id"], "name": name})


@app.route("/api/module-options")
def module_options():
    """回傳「專案細節」表「模組型號」欄位目前的選項清單（假設是 Single select 固定
    選項欄位）。直接讀記憶體快取，不用每次都重新打 Airtable Meta API（那支比較慢）。
    如果快取顯示這個欄位不可用（例如 Token 沒有 schema.bases:read 權限、或欄位其實
    不是 Single select），回傳空選項清單，前端要能優雅退回文字輸入框。"""
    available = MODEL_OPTIONS_CACHE.get("module_options_available", True)
    if not available:
        return jsonify({"error": "模組型號選項目前無法使用（可能是 Token 缺 schema.bases:read 權限，"
                                  "或欄位不是固定選項類型），請改用文字輸入",
                         "options": []}), 200
    return jsonify({"options": MODEL_OPTIONS_CACHE.get("module_options") or []})


@app.route("/api/module-options", methods=["POST"])
def create_module_option():
    """幫「模組型號」這個 Single select 欄位新增一個選項。需要 Token 有
    schema.bases:write 權限。寫入成功後立刻在背景刷新一次選項快取。
    body: {name}"""
    body = request.get_json(force=True)
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "缺少 name"}), 400
    try:
        field = _find_field_schema(CASE_TABLE_ID, FIELD_MODULE_MODEL)
        if not field:
            return jsonify({"error": "在 Airtable 找不到「模組型號」這個欄位"}), 404
        if field.get("type") != "singleSelect":
            return jsonify({"error": "「模組型號」欄位不是固定選項欄位，不需要（也無法）新增選項"}), 400
        choices = field.get("options", {}).get("choices", [])
        if any(c.get("name") == name for c in choices):
            return jsonify({"ok": True, "message": "這個選項已經存在"})
        new_choices = choices + [{"name": name}]
        resp = requests.patch(
            f"https://api.airtable.com/v0/meta/bases/{BASE_ID}/tables/{CASE_TABLE_ID}/fields/{FIELD_MODULE_MODEL}",
            headers=airtable_headers(),
            json={"options": {"choices": new_choices}},
            timeout=20,
        )
        resp.raise_for_status()
    except Exception as e:
        return jsonify({"error": "新增選項失敗，Token 可能沒有 schema.bases:write 權限",
                         "detail": str(e)}), 502
    threading.Thread(target=refresh_model_options_cache, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/case-spec", methods=["POST"])
def update_case_spec():
    """直接在網站上補填/修改案件的模組、逆變器規格，寫回 Airtable「專案細節」表，
    不用再回 Airtable 手動填。模組型號是純文字欄位，可以自由輸入；逆變器是連結欄位，
    body 裡要帶 /api/inverter-options 回傳的 record_id，不能只給名稱。
    body: {case_record_id, module_model, module_qty, inverters: [{record_id, qty}, ...]}
    module_model/module_qty/inverters 都是選填，只會更新有帶到的欄位；
    inverters 給空陣列代表清空逆變器（連同數量欄位一起清空）。"""
    body = request.get_json(force=True)
    case_record_id = body.get("case_record_id")
    if not case_record_id:
        return jsonify({"error": "缺少 case_record_id"}), 400

    fields = {}
    if "module_model" in body:
        fields[FIELD_MODULE_MODEL] = (body.get("module_model") or "").strip() or None
    if "module_qty" in body:
        fields[FIELD_MODULE_QTY] = body.get("module_qty")
    if "inverters" in body:
        inverters = body.get("inverters") or []
        fields[FIELD_INVERTER] = [inv["record_id"] for inv in inverters if inv.get("record_id")]
        fields[FIELD_INVERTER_QTY] = [inv.get("qty") for inv in inverters if inv.get("record_id")]

    if not fields:
        return jsonify({"error": "沒有帶任何要更新的欄位"}), 400

    resp = requests.patch(
        f"{CASE_API_URL}/{case_record_id}",
        headers=airtable_headers(),
        json={"fields": fields},
        timeout=20,
    )
    if resp.status_code >= 400:
        return jsonify({"error": "Airtable 寫入失敗", "detail": resp.text}), 502
    threading.Thread(target=refresh_cache, daemon=True).start()
    return jsonify({"ok": True, "record": resp.json()})


@app.route("/api/milestone-status")
def milestone_status():
    """查詢單一案件、單一種類里程碑目前在 Airtable「進度管理」表的完成狀態
    （有沒有實際日期）。用於「異常案件」裡「待取得函文再進場」這個功能，
    即時反映 Airtable 最新進度，不用等整批快取更新，因為只有少數案件會用到，
    不需要跟 pending/entry/completed 那樣整批處理。
    query params: case_record_id, type（type 必須是 DOCUMENT_MILESTONE_TYPES 其中之一）"""
    case_record_id = request.args.get("case_record_id")
    milestone_type = request.args.get("type")
    if not case_record_id or not milestone_type:
        return jsonify({"error": "缺少 case_record_id 或 type"}), 400
    if milestone_type not in DOCUMENT_MILESTONE_TYPES:
        return jsonify({"error": f"type 必須是以下其中之一：{'、'.join(DOCUMENT_MILESTONE_TYPES)}"}), 400
    try:
        resp = requests.get(f"{CASE_API_URL}/{case_record_id}", headers=airtable_headers(), timeout=15)
        if resp.status_code >= 400:
            return jsonify({"error": "Airtable 找不到這筆案件"}), 404
        f = resp.json().get("fields", {})
        ms_ids = f.get(FIELD_MS_LINK_ON_CASE) or []
        if not ms_ids:
            return jsonify({"completed": False, "actual_date": None, "found_milestone": False})
        id_formula = "OR(" + ",".join(f"RECORD_ID()='{mid}'" for mid in ms_ids) + ")"
        formula = f"AND({id_formula},{{{FIELD_MS_TYPE}}}='{milestone_type}')"
        records = airtable_get_all(MILESTONE_API_URL, formula, [FIELD_MS_TYPE, FIELD_MS_ACTUAL_DATE])
        if not records:
            return jsonify({"completed": False, "actual_date": None, "found_milestone": False})
        actual_date = records[0]["fields"].get(FIELD_MS_ACTUAL_DATE)
        return jsonify({"completed": bool(actual_date), "actual_date": actual_date, "found_milestone": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


# ===================================================================
# APP資料 相關 API（已完工／掛表安排／異常案件／變流器日期／註記清單，跨裝置共用）
# ===================================================================

@app.route("/api/app-data")
def get_app_data():
    """回傳 APP資料 表所有列，前端用來重建已完工/掛表安排/異常案件/變流器日期/註記清單
    這幾個原本存在本機瀏覽器的狀態。對於「掛表日期已確認」的案件（已經離開排程池，
    查不到即時資料了），額外去 Airtable 抓一次案件本身跟里程碑的完整資料，
    補齊歷史紀錄要顯示的欄位。
    query param: include_archived=false 可以跳過歷史紀錄這段（每筆都要額外查 1-2 次
    Airtable，案件一多會拖慢速度、甚至撞到 Airtable 每秒 5 次請求的限制）；
    前端做高頻率背景同步時應該帶這個參數，只有真的要看歷史紀錄或低頻率全量刷新時
    才不帶（或帶 true）。"""
    include_archived = request.args.get("include_archived", "true").lower() != "false"
    try:
        rows = app_data_get_all()
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    case_status = []
    notes = []
    for r in rows:
        f = r["fields"]
        t = f.get("類型")
        if t == "案件狀態":
            case_status.append({
                "app_record_id": r["id"],
                "case_record_id": f.get("案件RecordID"),
                "case_no": f.get("案號"),
                "completed_date": f.get("完工日期"),
                "meter_planned_date": f.get("預計掛表日期"),
                "meter_confirmed": bool(f.get("掛表日期已確認")),
                "issue_note": f.get("異常狀況"),
                "issue_date": f.get("異常記錄日期"),
                "inverter_ship_date": f.get("變流器出貨日期"),
                "withdrawn_note": f.get("撤案原因"),
                "withdrawn_date": f.get("撤案日期"),
                "owner_contact_name": f.get("屋主聯絡人"),
                "owner_contact_phone": f.get("屋主聯絡電話"),
                "owner_contact_note": f.get("屋主備註"),
                "rebar_planned_date": f.get("植筋日期"),
                "rebar_with_entry": bool(f.get("植筋跟進場一起")),
                "waiting_doc_type": f.get("等待函文種類"),
                "waiting_doc_date": f.get("等待函文取得日期"),
            })
        elif t in NOTE_TYPES:
            notes.append({
                "app_record_id": r["id"],
                "type": t,
                "case_text": f.get("案號或別名"),
                "content": f.get("內容"),
                "date": f.get("記錄日期"),
                "ship_date": f.get("出貨日期"),
            })

    archived = None
    if include_archived:
        archived = []
        for cs in case_status:
            if not cs["meter_confirmed"] or not cs["case_record_id"]:
                continue
            snap = fetch_case_snapshot_for_archive(cs["case_record_id"])
            if snap:
                archived.append({**cs, **snap})

    result = {"case_status": case_status, "notes": notes}
    if archived is not None:
        result["archived"] = archived
    return jsonify(result)


@app.route("/api/app-data/case-status", methods=["POST"])
def upsert_case_status():
    """新增或更新一筆「案件狀態」列（已完工/掛表安排/異常案件/變流器日期共用同一列）。
    body: {case_record_id, case_no, fields: {...僅放要更新的欄位...}}
    fields 可包含：completed_date, meter_planned_date, meter_confirmed,
    issue_note, issue_date, inverter_ship_date（value 給 None 代表清空該欄位）"""
    body = request.get_json(force=True)
    case_record_id = body.get("case_record_id")
    case_no = body.get("case_no", "")
    patch = body.get("fields", {}) or {}
    if not case_record_id:
        return jsonify({"error": "缺少 case_record_id"}), 400

    field_map = {
        "completed_date": "完工日期",
        "meter_planned_date": "預計掛表日期",
        "meter_confirmed": "掛表日期已確認",
        "issue_note": "異常狀況",
        "issue_date": "異常記錄日期",
        "inverter_ship_date": "變流器出貨日期",
        "withdrawn_note": "撤案原因",
        "withdrawn_date": "撤案日期",
        "owner_contact_name": "屋主聯絡人",
        "owner_contact_phone": "屋主聯絡電話",
        "owner_contact_note": "屋主備註",
        "rebar_planned_date": "植筋日期",
        "rebar_with_entry": "植筋跟進場一起",
        "waiting_doc_type": "等待函文種類",
        "waiting_doc_date": "等待函文取得日期",
    }
    airtable_fields = {field_map[k]: v for k, v in patch.items() if k in field_map}

    try:
        existing = app_data_find_case_row(case_record_id)
        if existing:
            result = app_data_update(existing["id"], airtable_fields)
        else:
            create_fields = {"類型": "案件狀態", "案件RecordID": case_record_id, "案號": case_no, **airtable_fields}
            result = app_data_create(create_fields)
    except Exception as e:
        return jsonify({"error": "Airtable 寫入失敗", "detail": str(e)}), 502
    return jsonify({"ok": True, "record": result})


@app.route("/api/app-data/case-status/clear", methods=["POST"])
def clear_case_status():
    """整筆刪除某案件在 APP資料 表裡的「案件狀態」列（用於「移回案件進場安排」）。
    body: {case_record_id}"""
    body = request.get_json(force=True)
    case_record_id = body.get("case_record_id")
    if not case_record_id:
        return jsonify({"error": "缺少 case_record_id"}), 400
    try:
        existing = app_data_find_case_row(case_record_id)
        if existing:
            app_data_delete(existing["id"])
    except Exception as e:
        return jsonify({"error": "Airtable 刪除失敗", "detail": str(e)}), 502
    return jsonify({"ok": True})


@app.route("/api/app-data/note", methods=["POST"])
def create_note():
    """新增一筆註記清單項目（併聯取得時備貨／其他狀況備住／未使用料件／料件使用）。
    body: {type, case_text, content, ship_date}
    ship_date 是選填欄位，目前只有「未使用料件」會用到（記錄這批料件原本的出貨日期）。"""
    body = request.get_json(force=True)
    note_type = body.get("type")
    case_text = (body.get("case_text") or "").strip()
    content = (body.get("content") or "").strip()
    ship_date = (body.get("ship_date") or "").strip()
    if note_type not in NOTE_TYPES:
        return jsonify({"error": f"type 必須是以下其中之一：{'、'.join(NOTE_TYPES)}"}), 400
    if not case_text or not content:
        return jsonify({"error": "缺少 case_text 或 content"}), 400
    try:
        fields = {
            "類型": note_type,
            "案號或別名": case_text,
            "內容": content,
            "記錄日期": datetime.now().strftime("%Y-%m-%d"),
        }
        if ship_date:
            fields["出貨日期"] = ship_date
        result = app_data_create(fields)
    except Exception as e:
        return jsonify({"error": "Airtable 寫入失敗", "detail": str(e)}), 502
    return jsonify({"ok": True, "record": result})


@app.route("/api/app-data/<record_id>", methods=["DELETE"])
def delete_app_data_row(record_id):
    """刪除 APP資料 表裡的任一列（刪除註記清單項目用）。"""
    try:
        app_data_delete(record_id)
    except Exception as e:
        return jsonify({"error": "Airtable 刪除失敗", "detail": str(e)}), 502
    return jsonify({"ok": True})


@app.route("/api/app-data/note/<record_id>", methods=["PATCH"])
def update_note(record_id):
    """修改一筆註記清單項目（例如「未使用料件」被部分使用後更新剩餘數量說明，
    或事後補填出貨日期、修正案號）。body 裡的欄位都是選填，只會更新有帶到的欄位：
    body: {content, case_text, ship_date}
    ship_date 給空字串代表清空該欄位（例如填錯了要清掉重填）。"""
    body = request.get_json(force=True)
    fields = {}
    if "content" in body:
        content = (body.get("content") or "").strip()
        if not content:
            return jsonify({"error": "content 不能是空字串"}), 400
        fields["內容"] = content
    if "case_text" in body:
        case_text = (body.get("case_text") or "").strip()
        if not case_text:
            return jsonify({"error": "case_text 不能是空字串"}), 400
        fields["案號或別名"] = case_text
    if "ship_date" in body:
        fields["出貨日期"] = body.get("ship_date") or None
    if not fields:
        return jsonify({"error": "沒有帶任何要更新的欄位"}), 400
    try:
        result = app_data_update(record_id, fields)
    except Exception as e:
        return jsonify({"error": "Airtable 寫入失敗", "detail": str(e)}), 502
    return jsonify({"ok": True, "record": result})


@app.route("/")
def health():
    return jsonify({
        "status": "ok",
        "service": "epc-backend",
        "pid": os.getpid(),
        "cache_updated_at": DATA_CACHE["updated_at"],
        "refreshing": DATA_CACHE["refreshing"],
        "refreshing_started_at": (
            DATA_CACHE["refreshing_started_at"].isoformat()
            if DATA_CACHE["refreshing_started_at"] else None
        ),
        "refreshing_run_id": DATA_CACHE.get("refreshing_run_id"),
        "last_error": DATA_CACHE["last_error"],
        "pending_count": len(DATA_CACHE["pending"]),
        "entry_count": len(DATA_CACHE["entry"]),
        "completed_count": len(DATA_CACHE["completed"]),
        "model_options_cache": {
            "updated_at": MODEL_OPTIONS_CACHE.get("updated_at"),
            "inverter_options_count": len(MODEL_OPTIONS_CACHE.get("inverter_options") or []),
            "module_options_count": len(MODEL_OPTIONS_CACHE.get("module_options") or []),
            "module_options_available": MODEL_OPTIONS_CACHE.get("module_options_available"),
            "last_error": MODEL_OPTIONS_CACHE.get("last_error"),
        },
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
