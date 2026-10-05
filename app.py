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
    呼叫，所以它的定義必須放在呼叫它的程式碼「之前」（檔案裡由上到下的順序）。

===================================================================
2026-08-28 修改（十二）：健康檢查頁面加上型號快取狀態 + 修正啟動卡死
===================================================================
  - / 健康檢查頁面加上 model_options_cache 區塊（updated_at、兩份選項數量、
    module_options_available、last_error），不用翻 log 就能直接看出型號快取
    是否正常刷新、卡在哪一步。
  - refresh_model_options_cache() 補上 last_error 記錄，讀取失敗時把明確的
    錯誤原因存進快取，透過健康檢查頁面就看得到，不用猜。
  - 新增 POST /api/refresh-model-options，可以手動觸發型號快取重新整理，
    不用等排程、也不用重新部署。
  - 修正啟動時卡死的問題：原本伺服器啟動時會「同時」開兩個背景執行緒
    （一個刷 DATA_CACHE、一個刷 MODEL_OPTIONS_CACHE），結果兩個執行緒
    同時做「第一次」Airtable 呼叫，疑似又踩到本檔案先前就記錄過的
    「多執行緒同時第一次呼叫 requests 會卡死」的坑，導致兩份快取都卡住
    完全跑不完。改成合併成一個背景執行緒，兩份快取「依序」刷新（先案件池，
    再型號清單），不要同時搶。之後排程觸發時因為 import 已經熱過了，
    各自獨立的排程工作就沒有這個風險。

===================================================================
2026-08-30 修改（十三）：修正背景初始化在 gunicorn master process 裡跑，
                        worker 完全看不到快取結果的重大問題
===================================================================
  - 發現健康檢查頁面 / 顯示的 pid 跟 log 裡 refresh_cache 完成時印出的 pid
    對不起來（例如健康檢查頁面顯示 pid=63，但 log 裡完成的是 pid=40）。
    對照 gunicorn 開機 log：40 是 master process，63 才是真正處理 HTTP
    請求的 worker process。
  - 根本原因：原本 threading.Thread(target=_startup_refresh_all).start()
    跟 scheduler.start() 都寫在模組最外層（import 時就執行），而 gunicorn
    是先在 master process import 一次 app.py（這時背景執行緒就在 master
    裡啟動、跑完），然後才 fork 出 worker。Unix fork() 的規則是「只有呼叫
    fork 的那個執行緒會延續到子行程，其他背景執行緒不會」，所以 worker
    自己的 DATA_CACHE / MODEL_OPTIONS_CACHE 永遠停留在 fork 那一刻的空白
    狀態，不管 master 那邊背景執行緒或排程再怎麼刷新都沒用（worker 才是
    真正回應前端請求的行程，前端永遠看到空/舊資料）。
  - 修正方式：把 threading.Thread(...).start() 跟 scheduler.start() 從模組
    最外層拿掉，改成定義但不呼叫；實際啟動移到同目錄新增的
    gunicorn.conf.py 的 post_fork(server, worker) hook 裡呼叫。
    post_fork 保證是在 fork 完成、worker process 自己的記憶體空間裡執行，
    背景執行緒跟排程就會真的在 worker 裡跑、worker 自己的快取也才會被更新。
  - 這個檔案本身 `python app.py` 直接執行（本機開發模式，不透過 gunicorn）
    時不會有 fork 這個步驟，所以額外保留 `if __name__ == "__main__"` 區塊
    自己呼叫一次啟動邏輯，確保本機開發體驗不受影響。
"""

import os
import io
import json
import time
import uuid
import secrets
import threading
import netrc  # noqa: F401  # 見下方說明：必須在多執行緒啟動前先 import 一次，避免 requests 內部
              # 的 get_netrc_auth() 在多執行緒同時第一次 import 這個模組時卡死（曾造成
              # gunicorn worker 因 WORKER TIMEOUT 被砍掉，且完全沒有任何錯誤 log）。
import requests
from datetime import datetime, timedelta, timezone
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

# 2026-08-31 新增 8 間廠商（宇陽達、聚曜、澄品、大昇、展亦、凰太竹、國欽、振庭）。
# 這份清單直接決定 compute_case_pool() 查詢 Airtable 時的篩選條件——不在這份
# 清單裡的廠商，案件從一開始就不會被抓進案件池，之後不管前端怎麼篩選都看不到，
# 所以新增廠商一定要先加進這裡。
VENDOR_NAMES = ["三創", "尚展", "曙光", "光鼎", "宇陽達", "聚曜", "澄品", "大昇", "展亦", "凰太竹", "國欽", "振庭"]

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
# 2026-08-31 新增：「掛表安排」頁籤要用來判斷「是不是真的可以安排掛表」的
# 兩個函文種類——完工不代表就能掛表，還要等這兩份文件都確認取得才行。
MILESTONE_TYPE_DETAIL_NEGO = "細部協商"
MILESTONE_TYPE_TAIPOWER_CONTRACT = "台電購售契約"

# 「異常案件」裡「待取得函文再進場」功能可選的函文種類，對應「進度管理」表裡
# 實際存在的里程碑「種類」名稱。如果 Airtable 那邊的實際命名跟這裡不同
# （尤其「台電契約」，Airtable 裡可能叫「台電購售契約」），要一併修改這裡。
DOCUMENT_MILESTONE_TYPES = ["免雜", "細部協商", "台電購售契約"]

# 2026-08-30 新增：「筆記本」功能（/api/case-lookup）要一次查詢的函文／審查
# 進度種類。跟上面 DOCUMENT_MILESTONE_TYPES 分開列一份，因為「待取得函文」
# 功能跟「筆記本快速查詢」用途不同、選項範圍也不完全一樣（筆記本多了「併聯審查」
# 跟「同意備案」）：
#   - 同意備案：其實案件表（專案細節）上就有 lookup 欄位（FIELD_AGREE_DATE），
#     但這裡為了讓 /api/case-lookup 回傳格式統一（案件基本資料 + 一份完整的
#     里程碑字典），還是一併從「進度管理」表查一次里程碑的實際日期，跟其他
#     幾種一樣處理，不用另外寫特殊分支。
NOTEBOOK_MILESTONE_TYPES = ["併聯審查", "同意備案", "細部協商", "台電購售契約", "免雜"]

CASE_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{CASE_TABLE_ID}"
MILESTONE_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{MILESTONE_TABLE_ID}"
INVERTER_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{INVERTER_TABLE_ID}"

# 2026-10-01 新增：「進度管理」表裡每筆里程碑記錄回連到「專案細節」的連結欄位
# （FIELD_MS_CASE_LINK）在公式裡直接引用時，Airtable 會用連結表的主欄位（也就是
# 專案細節表的「案號」，因為 CASE_TABLE_ID 的 primaryFieldId 正好是「案號」）當
# 顯示值。「專案名稱」這個公式欄位的內容就是 {FIELD_MS_CASE_LINK}，等於直接查到
# 這筆里程碑記錄屬於哪個案號，不用另外再查一次「專案細節」表比對 record id。
FIELD_MS_PROJECT_NAME = "fldn4GXmErzbm3FhU"
FIELD_MS_SUBMIT_DATE = "fldY0PpJgNXOEqwL8"  # 送件時間（跟 FIELD_MS_ACTUAL_DATE「完成日期」分開的欄位）

# ---- 場勘安排（2026-10-01 新增，資料來自另一個 Airtable base「工務組」）----
# 這是獨立於 appj1wnO3WnRtIEvg（[電廠] 案場管理）之外的另一個 base，工務組用來
# 追蹤案場從「拿到案件」到「完工」的各個現場階段（場勘／平配圖／設計討論／丈量…），
# 跟 EPC 出貨排程這邊原本接的 base 沒有關聯，只能用「案號」文字比對。
# 必須確認 AIRTABLE_TOKEN 這組 PAT 有把這個 base 加進授權範圍，不然查詢會收到
# 403 NOT_AUTHORIZED（跟本來那個 base 是各自獨立的權限設定）。
SURVEY_BASE_ID = "appijmWI4f4lukYF7"  # 工務組（跟陽光管理主控台原本的 base 不同）
SURVEY_TABLE_ID = "tbl9NIA83ZXUoozlT"  # Table 1
SURVEY_FIELD_ALIAS = "fldp2lLjWhBd0OVPz"  # 案場別名
SURVEY_FIELD_CASE_NO = "flda1hW5uEDeEsWTL"  # 案號
SURVEY_FIELD_ADDRESS = "fldClOEBKjeRGebbR"  # 地址
SURVEY_FIELD_VENDOR = "fldEiuYPdqOjlIG36"  # 責任EPC
SURVEY_FIELD_SALES = "fldAKCKzWyhrXDMY2"  # 責任業務1
SURVEY_FIELD_PROVIDED_DATE = "fldmhn7FUE8eoxKiW"  # 案件提供日（確定由哪間 EPC 承接的日期）
SURVEY_FIELD_PLANNED_DATE = "fldmmvw9v099ebhSv"  # 預計場勘日
SURVEY_FIELD_ACTUAL_DATE = "fldvgJUT55WLX4EiW"  # 實際場勘日
# 2026-10-01 新增（透過 Airtable MCP 建立）：勾選後，隔天的自動回填排程會跳過
# 這筆案件，不會把預計場勘日當成實際場勘日寫回去。使用者確認日期本身的調整
# 直接改「預計場勘日」就好（自動回填本來就只處理「日期已過」的案件，改成未來
# 日期自然就不會被處理到），只有「有異常但先不改日期」這種情況才需要這個獨立
# 的勾選欄位。
SURVEY_FIELD_EXCEPTION = "fldPzjPSpLdpUMJCg"  # 場勘異常
SURVEY_FIELD_PROGRESS = "fldmJt64Oy2ama2zS"  # 進度（singleSelect，Fail 代表已經撤案/結束，要排除）
SURVEY_API_URL = f"https://api.airtable.com/v0/{SURVEY_BASE_ID}/{SURVEY_TABLE_ID}"

# 2026-10-01 新增：「場勘安排」清單還要排除業務自治區 Google 試算表裡已經標記
# 「取消」的案件（使用者反饋：有些等了幾百天的紅字案件，其實早就撤案了，只是
# 工務組那個 base 沒有同步更新）。
#
# 原本想用 Google 服務帳戶讓後端主動去拉這份試算表，但公司 Workspace 網域政策
# 把「外部帳號存取」整個鎖死了——服務帳戶被共用雲端硬碟的網域限制擋下來，
# 改走 Apps Script 網頁應用程式也一樣，「誰可以存取」被組織政策鎖死只能選
# 「網域內使用者」，這支後端沒有 sunnyfounder.com 的 Google 身分，打不進去。
#
# 改成反過來：試算表那邊用 Apps Script 的「時間觸發器」，定期主動把資料
# UrlFetchApp.fetch() 推來這支 API，不是後端去拉。這個方向完全不受「誰可以
# 存取網頁應用程式」那個網域限制影響（那個設定只管「誰可以打進 Apps Script」，
# 不管「Apps Script 自己要打去哪裡」）。拿一組雙方說好的 SECRET（Render 環境
# 變數 BIZ_SHEET_SYNC_KEY）當簡單驗證，避免這支公開端點被亂打。
CANCELLED_CASE_CACHE = {"case_nos": set(), "updated_at": None}
BIZ_SHEET_SYNC_KEY = os.environ.get("BIZ_SHEET_SYNC_KEY")

# 2026-10-01 新增：同一份 Apps Script 推送，順便帶「A01資訊」分頁裡 A 欄
# ＝「已公證」的案件（案號＋施作廠商）。這些案件已經公證、PM 會需要先排
# 掛表/植筋/放樣/場勘時段，但業務流程上通常要再晚一點才會建進 Airtable
# 的「專案細節」表——不能等建檔才能排時段。只給「廠商時段協調」的案號
# 模糊搜尋用（/api/case-search），不影響其他地方的案件查詢；沒有
# record_id（因為根本沒有 Airtable 記錄），別名/業務欄位自然留空。
CERTIFIED_CASE_CACHE = {"cases": [], "updated_at": None}

# 2026-10-01 新增：屋主聯絡資訊（姓名/電話），來源是 A01資訊 K 欄連結指到的
# Drive 案場資料夾裡「契約」子資料夾裡的租賃合約書文件最後一頁「甲方」區塊。
# Apps Script 那邊先把解析結果快取寫回 A01資訊 表格的兩個新欄位（避免每次
# 推送都要重新打開文件解析，案件一多會太慢/超過 Apps Script 單次執行時間
# 限制），pushCancelledCases() 之後只是單純讀那兩欄、跟其他欄位一起推送
# 過來。涵蓋「所有」案件（不限於已公證／不限於還沒建進 Airtable），所以
# 用案號當 key 的獨立快取，不是 CERTIFIED_CASE_CACHE 的一部分。
OWNER_CONTACT_CACHE = {}  # {案號: {"name": ..., "phone": ...}}

# ---- 廠商時段協調（2026-10-01 新增）----
# 廠商會開放幾個日期讓我們安排現場作業（掛表／植筋／放樣／場勘），業務各自去
# 幫自己的案子卡時段，同一個廠商同一天不能有兩筆預約時間重疊（同一組工班）。
# 這張表跟其他案件 Airtable 表不太一樣，不是「一案一列」，而是「一筆時段一列」，
# 所以獨立開一張新表，不跟 APP資料 混在一起。
# 資料量不大（一次大概就是幾個廠商、幾天、幾個案子），不用像 pending/entry/
# completed 或場勘安排那樣做背景快取，直接即時查 Airtable 就好。
SLOT_TABLE_ID = "tbl4paq7aP2itEOk0"
FIELD_SLOT_TITLE = "fld4zSws0QYIpgiZE"       # 標題（後端自動產生，純顯示用）
FIELD_SLOT_KIND = "flds9FOlX6Z4vS2YS"        # 記錄類型：開放時段／已預約
FIELD_SLOT_VENDOR = "fldx0GNtq5juS4itt"      # 廠商
FIELD_SLOT_DATE = "fldmCEruO814y2TZY"        # 日期
FIELD_SLOT_START = "fldpHOWg6uebcs8Xe"       # 開始時間（"HH:MM" 字串，只有已預約會填）
FIELD_SLOT_END = "fldu0ZxMUnMtxy09d"         # 結束時間（同上）
FIELD_SLOT_CASE_NO = "fldbeFm5WoQG5J6Xn"     # 案號（只有已預約會填）
FIELD_SLOT_ALIAS = "fldqBDfAcb0r7pAPB"       # 案場別名（只有已預約會填）
FIELD_SLOT_TYPE = "fldxwQTU9dB1aDPqX"        # 項目類型(多選)：掛表／植筋／放樣／場勘，可複選
# 2026-10-01：原本 fldXYG2HPHWYI1NVk 是 singleSelect，使用者反饋常常要
# 「放樣跟植筋一起」用同一個時段，改成 multipleSelects 新欄位
# （fldxwQTU9dB1aDPqX，Airtable API 不能直接把既有欄位從 singleSelect
# 轉成 multipleSelects，只能建新欄位），舊欄位保留不刪，只是沒人寫/讀了。
FIELD_SLOT_REGISTRANT = "fldgzpUmVlN51Abf6"  # 登記人
FIELD_SLOT_NOTE = "fld0l1iExfCns0iNa"        # 備註
FIELD_SLOT_OWNER_NAME = "fld3ljzB0bpzQzaXL"  # 屋主姓名，2026-10-01 新增
FIELD_SLOT_OWNER_PHONE = "fldT1YrJY2Rp8L33S"  # 屋主電話，2026-10-01 新增
SLOT_KIND_WINDOW = "開放時段"
SLOT_KIND_BOOKING = "已預約"
SLOT_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{SLOT_TABLE_ID}"

# ---- 廠商時段任務（2026-10-01 新增，「廠商時段協調」的延伸）----
# PM 幫某個案子建一個「待業務安排」的任務（廠商提供候選日期，業務點免登入
# 連結、自己跟屋主喬好時間後進去完成預約），避免 PM 自己要一筆一筆去問每個
# 業務的時間、再手動登記。Token 就是這個連結的通行碼（/book.html?token=xxx），
# 沒有帳號密碼，知道連結就能用，所以 token 本身要夠長、夠隨機。
TASK_TABLE_ID = "tblgNebQ0zj2Sg2Cy"
FIELD_TASK_TITLE = "fldU4lK1ioIwC37El"
FIELD_TASK_VENDOR = "fldUuLlcmoPYH6D2v"
FIELD_TASK_CASE_NO = "fldBWRBOQAnLrOAQx"
FIELD_TASK_ALIAS = "fld415LlbNJEXLSXd"
FIELD_TASK_TYPE = "fldD0ZRPJ30k3efgy"        # 項目類型(多選)，同上改成 multipleSelects
FIELD_TASK_CANDIDATE_DATES = "fldtlJv4YEt2tH6nD"  # 逗號分隔 YYYY-MM-DD 字串
FIELD_TASK_ASSIGNEE = "fldsNoYvammA9I5E3"
FIELD_TASK_STATUS = "fldX4K5SBqwNtw6wm"
FIELD_TASK_TOKEN = "fldF8tofB4Ohsmmzj"
FIELD_TASK_BOOKING_ID = "fldjI1Lofz85R0qlA"
FIELD_TASK_CREATOR = "fldhlpfrSacYaGFsH"
FIELD_TASK_NOTE = "fldgyScZS4sEU85L3"
FIELD_TASK_DURATION_MIN = "fldzMaYBiILXmbHCd"  # 預估時長(分鐘)，2026-10-01 新增
FIELD_TASK_OWNER_NAME = "fldva2m9OpEuNfmf9"  # 屋主姓名(預設)，2026-10-01 新增
FIELD_TASK_OWNER_PHONE = "fldNqj1zYCkDjFIFf"  # 屋主電話(預設)，2026-10-01 新增
# 2026-10-04：「原預約時間屋主不行，業務提供其他時間 → 窗口跟廠商確認後選一個
# → 回傳業務確認」的協調流程。狀態欄位（待業務安排/已完成）是 singleSelect、
# Airtable API 沒辦法加選項，所以另開「協調階段」欄位：空白＝一般流程，
# 待窗口確認＝業務已回傳備選時段，待業務確認＝窗口已選定、等業務按確認。
FIELD_TASK_STAGE = "fldfh9eWwvx5Tii1s"
FIELD_TASK_ALT_SLOTS = "fldS0AR77PexwZJZa"      # 備選時段 JSON：[{date,start_time,end_time},...]
FIELD_TASK_CHOSEN_SLOT = "fldlqEl82wwwiq9tM"    # 窗口選定時段 JSON：{date,start_time,end_time}
FIELD_TASK_REP_NOTE = "fldAy7F6ibcZpbwTY"       # 業務回覆備註
FIELD_TASK_DEADLINE = "fldcNCOuBjyy4lT0E"       # 回覆期限（dateTime，台北時間），2026-10-04 新增
TASK_STAGE_WAIT_PM = "待窗口確認"
TASK_STAGE_WAIT_REP = "待業務確認"
# 2026-10-05：業務 LINE 綁定表（姓名 → LINE userId），供回覆期限提醒個別推播
LINE_BIND_TABLE_ID = "tblkTLFeRSvqsVpBi"
FIELD_BIND_NAME = "fldqJBVB9IYxnyWDR"
FIELD_BIND_UID = "fld21MqIEDGkcJtl8"
FIELD_BIND_DISPLAY = "fld5ebY8BPab9BotD"
FIELD_BIND_SCHEDULER = "fldP46k7RInwCYXQV"  # 安排人員（checkbox）
LINE_BIND_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{LINE_BIND_TABLE_ID}"
FIELD_TASK_REMINDED = "fldEYiVCaYVUORS9F"  # 已提醒（checkbox）
TASK_STATUS_PENDING = "待業務安排"
TASK_STATUS_DONE = "已完成"
TASK_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{TASK_TABLE_ID}"


def _parse_hhmm(s):
    h, m = (s or "").strip().split(":")
    return int(h) * 60 + int(m)


def _slots_overlap(start_a, end_a, start_b, end_b):
    """時間區間是否重疊（半開區間，10:00-11:00 跟 11:00-12:00 算不重疊，
    銜接得剛剛好）。輸入格式驗證（HH:MM、開始早於結束）由呼叫端先做好。"""
    return _parse_hhmm(start_a) < _parse_hhmm(end_b) and _parse_hhmm(start_b) < _parse_hhmm(end_a)


def _normalize_type_list(raw):
    """項目類型 2026-10-01 改成可複選（掛表/植筋/放樣/場勘可以同時選，例如
    「放樣+植筋」一起跑一趟），前端一律送陣列，但這裡也接受舊格式的單一
    字串（容錯，不然舊快取的前端頁面送過來會整個壞掉）。"""
    if isinstance(raw, str):
        raw = [raw] if raw.strip() else []
    return [t.strip() for t in (raw or []) if isinstance(t, str) and t.strip()]


@app.route("/api/vendor-slots")
def list_vendor_slots():
    """「廠商時段協調」頁用：回傳所有「開放時段」跟「已預約」記錄（資料量小，
    不分頁、不做日期範圍篩選，前端自己依日期分組顯示）。"""
    try:
        fields = [
            FIELD_SLOT_KIND, FIELD_SLOT_VENDOR, FIELD_SLOT_DATE, FIELD_SLOT_START,
            FIELD_SLOT_END, FIELD_SLOT_CASE_NO, FIELD_SLOT_ALIAS, FIELD_SLOT_TYPE,
            FIELD_SLOT_REGISTRANT, FIELD_SLOT_NOTE,
        ]
        records = airtable_get_all(SLOT_API_URL, "TRUE()", fields)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    windows, bookings = [], []
    for r in records:
        f = r["fields"]
        item = {
            "record_id": r["id"],
            "vendor": f.get(FIELD_SLOT_VENDOR),
            "date": f.get(FIELD_SLOT_DATE),
        }
        if f.get(FIELD_SLOT_KIND) == SLOT_KIND_BOOKING:
            item.update({
                "start_time": f.get(FIELD_SLOT_START),
                "end_time": f.get(FIELD_SLOT_END),
                "case": f.get(FIELD_SLOT_CASE_NO, ""),
                "alias": f.get(FIELD_SLOT_ALIAS, ""),
                "type": f.get(FIELD_SLOT_TYPE) or [],
                "registrant": f.get(FIELD_SLOT_REGISTRANT, ""),
                "note": f.get(FIELD_SLOT_NOTE, ""),
            })
            bookings.append(item)
        else:
            item["note"] = f.get(FIELD_SLOT_NOTE, "")
            windows.append(item)
    windows.sort(key=lambda w: (w.get("date") or "", w.get("vendor") or ""))
    bookings.sort(key=lambda b: (b.get("date") or "", b.get("start_time") or ""))
    return jsonify({"windows": windows, "bookings": bookings})


@app.route("/api/vendor-slots/windows", methods=["POST"])
def create_vendor_slot_windows():
    """開放時段：一次可以傳多個日期（同一個廠商一口氣開放禮拜一二四這種情境）。
    body: {vendor, dates: ["2026-10-06", "2026-10-07", ...], note}"""
    body = request.get_json(force=True)
    vendor = (body.get("vendor") or "").strip()
    dates = body.get("dates") or []
    note = (body.get("note") or "").strip()
    if not vendor or not dates:
        return jsonify({"error": "缺少 vendor 或 dates"}), 400
    try:
        for d in dates:
            fields = {
                FIELD_SLOT_TITLE: f"{vendor} {d} 開放時段",
                FIELD_SLOT_KIND: SLOT_KIND_WINDOW,
                FIELD_SLOT_VENDOR: vendor,
                FIELD_SLOT_DATE: d,
            }
            if note:
                fields[FIELD_SLOT_NOTE] = note
            resp = requests.post(SLOT_API_URL, headers=airtable_headers(), json={"fields": fields}, timeout=20)
            if resp.status_code >= 400:
                return jsonify({"error": "Airtable 寫入失敗", "detail": resp.text}), 502
        return jsonify({"ok": True, "count": len(dates)})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


def _find_slot_conflict(vendor, date, start_time, end_time):
    """同廠商同日期的既有「已預約」有沒有跟這段時間重疊。有的話回傳衝突那筆的
    資訊 dict，沒有回傳 None；查詢失敗直接丟例外給呼叫端處理。"""
    escaped_vendor = vendor.replace("'", "\\'")
    formula = (
        f"AND({{{FIELD_SLOT_KIND}}}='{SLOT_KIND_BOOKING}',"
        f"{{{FIELD_SLOT_VENDOR}}}='{escaped_vendor}',"
        f"IS_SAME({{{FIELD_SLOT_DATE}}},'{date}','day'))"
    )
    existing = airtable_get_all(
        SLOT_API_URL, formula,
        [FIELD_SLOT_START, FIELD_SLOT_END, FIELD_SLOT_CASE_NO, FIELD_SLOT_ALIAS, FIELD_SLOT_TYPE, FIELD_SLOT_REGISTRANT],
    )
    for r in existing:
        ef = r["fields"]
        es, ee = ef.get(FIELD_SLOT_START), ef.get(FIELD_SLOT_END)
        if not es or not ee:
            continue
        if _slots_overlap(start_time, end_time, es, ee):
            return {
                "case": ef.get(FIELD_SLOT_CASE_NO, ""),
                "alias": ef.get(FIELD_SLOT_ALIAS, ""),
                "type": ef.get(FIELD_SLOT_TYPE) or [],
                "start_time": es,
                "end_time": ee,
                "registrant": ef.get(FIELD_SLOT_REGISTRANT, ""),
            }
    return None


def _book_vendor_slot(vendor, date, start_time, end_time, case_no, alias, slot_type, registrant, note,
                       owner_name=None, owner_phone=None):
    """實際建立一筆「已預約」記錄的共用邏輯：驗證格式、查同廠商同日期的既有預約
    有沒有時間重疊、寫入 Airtable。被兩個地方呼叫：
      1. POST /api/vendor-slots/bookings（PM/業務在主控台裡直接預約）
      2. POST /api/vendor-slots/tasks/<token>/book（業務透過免登入連結自助預約）
    兩邊共用同一套衝突偵測，不要各自重寫一份（容易兩邊邏輯兜不起來）。
    回傳 (record_dict, None) 表示成功；(None, (body_dict, status_code)) 表示失敗，
    呼叫端直接 return jsonify(body), status 就好。"""
    vendor = (vendor or "").strip()
    date = (date or "").strip()
    start_time = (start_time or "").strip()
    end_time = (end_time or "").strip()
    case_no = (case_no or "").strip()
    slot_type = _normalize_type_list(slot_type)
    registrant = (registrant or "").strip()
    if not all([vendor, date, start_time, end_time, case_no, registrant]) or not slot_type:
        return None, ({"error": "缺少必填欄位（廠商/日期/開始時間/結束時間/案號/項目類型/登記人）"}, 400)
    try:
        _parse_hhmm(start_time)
        _parse_hhmm(end_time)
    except Exception:
        return None, ({"error": "時間格式錯誤，要是 HH:MM（例如 10:00）"}, 400)
    if _parse_hhmm(start_time) >= _parse_hhmm(end_time):
        return None, ({"error": "開始時間要早於結束時間"}, 400)

    try:
        conflict = _find_slot_conflict(vendor, date, start_time, end_time)
    except Exception as e:
        return None, ({"error": "查詢既有預約失敗", "detail": str(e)}, 502)
    if conflict:
        return None, ({"error": "這個時段已經被佔用了", "conflict": conflict}, 409)

    try:
        fields = {
            FIELD_SLOT_TITLE: f"{vendor} {date} {start_time}-{end_time} {'/'.join(slot_type)}",
            FIELD_SLOT_KIND: SLOT_KIND_BOOKING,
            FIELD_SLOT_VENDOR: vendor,
            FIELD_SLOT_DATE: date,
            FIELD_SLOT_START: start_time,
            FIELD_SLOT_END: end_time,
            FIELD_SLOT_CASE_NO: case_no,
            FIELD_SLOT_ALIAS: (alias or "").strip(),
            FIELD_SLOT_TYPE: slot_type,
            FIELD_SLOT_REGISTRANT: registrant,
            FIELD_SLOT_NOTE: (note or "").strip(),
        }
        if owner_name:
            fields[FIELD_SLOT_OWNER_NAME] = owner_name.strip()
        if owner_phone:
            fields[FIELD_SLOT_OWNER_PHONE] = owner_phone.strip()
        resp = requests.post(SLOT_API_URL, headers=airtable_headers(), json={"fields": fields}, timeout=20)
        if resp.status_code >= 400:
            return None, ({"error": "Airtable 寫入失敗", "detail": resp.text}, 502)
        record = resp.json()
    except Exception as e:
        return None, ({"error": str(e)}, 502)
    # 預約成功後，把日期同步寫進對應的「預計日期」欄位（失敗不影響預約本身）
    try:
        _sync_booking_to_case_dates(case_no, slot_type, date)
    except Exception as e:
        print(f"[_book_vendor_slot] 同步預計日期失敗（不影響預約）：{e}", flush=True)
    return record, None


def _sync_booking_to_case_dates(case_no, slot_type, date):
    """2026-10-05：時段預約完成後，自動把預約日期寫進主控台原本的「預計日期」欄位，
    PM 不用再手動多一步：
      掛表 → 預計掛表日期（APP資料「案件狀態」列）
      植筋 → 植筋日期（同上）
      場勘 → 預計場勘日（場勘 base）
      進場 → 「進場屋主預約」里程碑的實際日期（跟「案件進場安排」排定進場日期同一個地方）
    放樣目前沒有對應欄位（常跟場勘/植筋同一趟，勾多選就會跟著那個項目寫），不處理。
    同一筆預約有多個項目就各自寫。日期直接覆蓋原有的預計日期（預約＝PM 確認過的安排）。"""
    types = set(slot_type or [])
    patch = {}
    if "掛表" in types:
        patch["預計掛表日期"] = date
    if "植筋" in types:
        patch["植筋日期"] = date
    if patch or "進場" in types:
        escaped = case_no.replace("\\", "\\\\").replace("'", "\\'")
        recs = airtable_get_all(CASE_API_URL, f"{{{FIELD_CASE_NO}}}='{escaped}'", [FIELD_CASE_NO])
        if not recs:
            print(f"[_sync_booking_to_case_dates] 找不到案號 {case_no}，略過掛表/植筋日期同步", flush=True)
        else:
            case_record_id = recs[0]["id"]
            if "進場" in types:
                ms_id = ensure_milestone_record(case_record_id, MILESTONE_TYPE_ENTRY)
                resp = requests.patch(f"{MILESTONE_API_URL}/{ms_id}", headers=airtable_headers(),
                                      json={"fields": {FIELD_MS_ACTUAL_DATE: date}}, timeout=20)
                if resp.status_code >= 400:
                    raise Exception(resp.text)
                threading.Thread(target=refresh_cache, daemon=True).start()
            if patch:
                existing = app_data_find_case_row(case_record_id)
                if existing:
                    app_data_update(existing["id"], patch)
                else:
                    app_data_create({"類型": "案件狀態", "案件RecordID": case_record_id, "案號": case_no, **patch})
            if "預計掛表日期" in patch:
                threading.Thread(
                    target=sync_ops_case_on_meter_planned,
                    args=(case_record_id, case_no, date),
                    daemon=True,
                ).start()
    if "場勘" in types:
        escaped = case_no.replace("\\", "\\\\").replace("'", "\\'")
        recs = airtable_get_all(SURVEY_API_URL, f"{{{SURVEY_FIELD_CASE_NO}}}='{escaped}'", [SURVEY_FIELD_CASE_NO])
        if recs:
            rid = recs[0]["id"]
            resp = requests.patch(f"{SURVEY_API_URL}/{rid}", headers=airtable_headers(),
                                  json={"fields": {SURVEY_FIELD_PLANNED_DATE: date}}, timeout=20)
            if resp.status_code >= 400:
                raise Exception(resp.text)
            for c in SURVEY_CACHE["cases"]:
                if c["record_id"] == rid:
                    c["planned_date"] = date
                    break


@app.route("/api/vendor-slots/bookings", methods=["POST"])
def create_vendor_slot_booking():
    """預約時段：寫入前先查同廠商、同日期的既有「已預約」記錄，時間重疊就擋下來
    （回傳 409 跟衝突到的那筆資料），不讓兩個業務卡到同一段時間。
    body: {vendor, date, start_time, end_time, case, alias, type, registrant, note}
    start_time/end_time 格式 "HH:MM"（24 小時制）。實際邏輯見 _book_vendor_slot()。"""
    body = request.get_json(force=True)
    record, err = _book_vendor_slot(
        body.get("vendor"), body.get("date"), body.get("start_time"), body.get("end_time"),
        body.get("case"), body.get("alias"), body.get("type"), body.get("registrant"), body.get("note"),
    )
    if err:
        err_body, status = err
        return jsonify(err_body), status
    return jsonify({"ok": True, "record": record})


@app.route("/api/vendor-slots/<record_id>", methods=["DELETE"])
def delete_vendor_slot(record_id):
    """刪掉一筆開放時段或已預約記錄（登記錯誤時用）。"""
    try:
        resp = requests.delete(f"{SLOT_API_URL}/{record_id}", headers=airtable_headers(), timeout=20)
        if resp.status_code >= 400:
            return jsonify({"error": "Airtable 刪除失敗", "detail": resp.text}), 502
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


def _task_fields():
    return [
        FIELD_TASK_VENDOR, FIELD_TASK_CASE_NO, FIELD_TASK_ALIAS, FIELD_TASK_TYPE,
        FIELD_TASK_CANDIDATE_DATES, FIELD_TASK_ASSIGNEE, FIELD_TASK_STATUS,
        FIELD_TASK_TOKEN, FIELD_TASK_BOOKING_ID, FIELD_TASK_CREATOR, FIELD_TASK_NOTE,
        FIELD_TASK_DURATION_MIN, FIELD_TASK_OWNER_NAME, FIELD_TASK_OWNER_PHONE,
        FIELD_TASK_STAGE, FIELD_TASK_ALT_SLOTS, FIELD_TASK_CHOSEN_SLOT, FIELD_TASK_REP_NOTE,
        FIELD_TASK_DEADLINE,
    ]


def _normalize_deadline(raw):
    """前端送來的回覆期限（ISO 8601，例如 2026-10-04T18:00:00+08:00）驗證後原樣回傳；
    空值/格式不對回 None（＝不設期限）。"""
    s = str(raw or "").strip()
    if not s:
        return None
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None
    return s


def _json_or_default(raw, default):
    try:
        v = json.loads(raw) if raw else default
        return v if isinstance(v, type(default)) else default
    except Exception:
        return default


def _task_to_dict(r):
    f = r["fields"]
    dates_raw = f.get(FIELD_TASK_CANDIDATE_DATES, "") or ""
    return {
        "record_id": r["id"],
        "vendor": f.get(FIELD_TASK_VENDOR),
        "case": f.get(FIELD_TASK_CASE_NO, ""),
        "alias": f.get(FIELD_TASK_ALIAS, ""),
        "type": f.get(FIELD_TASK_TYPE) or [],
        "candidate_dates": [d.strip() for d in dates_raw.split(",") if d.strip()],
        "assignee": f.get(FIELD_TASK_ASSIGNEE, ""),
        "status": f.get(FIELD_TASK_STATUS, TASK_STATUS_PENDING),
        "token": f.get(FIELD_TASK_TOKEN, ""),
        "booking_id": f.get(FIELD_TASK_BOOKING_ID, ""),
        "creator": f.get(FIELD_TASK_CREATOR, ""),
        "note": f.get(FIELD_TASK_NOTE, ""),
        "duration_min": f.get(FIELD_TASK_DURATION_MIN),
        "owner_name": f.get(FIELD_TASK_OWNER_NAME, ""),
        "owner_phone": f.get(FIELD_TASK_OWNER_PHONE, ""),
        "stage": f.get(FIELD_TASK_STAGE) or "",
        "alt_slots": _json_or_default(f.get(FIELD_TASK_ALT_SLOTS), []),
        "chosen_slot": _json_or_default(f.get(FIELD_TASK_CHOSEN_SLOT), {}) or None,
        "rep_note": f.get(FIELD_TASK_REP_NOTE, ""),
        "deadline": f.get(FIELD_TASK_DEADLINE) or "",
    }


@app.route("/api/vendor-slots/tasks")
def list_vendor_slot_tasks():
    """主控台用：列出所有「待業務安排」任務（不分狀態，前端自己分組顯示）。"""
    try:
        records = airtable_get_all(TASK_API_URL, "TRUE()", _task_fields())
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    tasks = [_task_to_dict(r) for r in records]
    tasks.sort(key=lambda t: (t.get("status") == TASK_STATUS_DONE, t.get("vendor") or ""))
    return jsonify({"tasks": tasks})


@app.route("/api/vendor-slots/tasks", methods=["POST"])
def create_vendor_slot_task():
    """PM 建立一個待業務安排的任務。body: {vendor, case, alias, type, candidate_dates: [...],
    assignee, creator, note, duration_min}。產生一組隨機 token，回傳連結路徑
    /book.html?token=xxx 讓前端組出完整網址、產生要貼給業務的訊息文字。
    duration_min（選填，正整數）：PM 給的預估作業時長（分鐘），不管是直接
    勾「交由業務安排」填的時長，還是從完整預估時間 start/end 換算出來的，
    統一存成這一個欄位——book.html 自助預約頁看到這個值，就能讓業務只選
    開始時間、結束時間自動帶（仍可手動改），沒有這個值就維持原本兩個時間
    都要自己選的舊版行為（相容舊任務）。"""
    body = request.get_json(force=True)
    vendor = (body.get("vendor") or "").strip()
    case_no = (body.get("case") or "").strip()
    slot_type = _normalize_type_list(body.get("type"))
    candidate_dates = [d.strip() for d in (body.get("candidate_dates") or []) if d.strip()]
    if not vendor or not case_no or not slot_type or not candidate_dates:
        return jsonify({"error": "缺少必填欄位（廠商/案號/項目類型/候選日期至少一天）"}), 400
    duration_min = body.get("duration_min")
    try:
        duration_min = int(duration_min) if duration_min else None
        if duration_min is not None and duration_min <= 0:
            duration_min = None
    except (TypeError, ValueError):
        duration_min = None
    token = secrets.token_urlsafe(16)
    try:
        fields = {
            FIELD_TASK_TITLE: f"{vendor} {case_no} {'/'.join(slot_type)} 待業務安排",
            FIELD_TASK_VENDOR: vendor,
            FIELD_TASK_CASE_NO: case_no,
            FIELD_TASK_ALIAS: (body.get("alias") or "").strip(),
            FIELD_TASK_TYPE: slot_type,
            FIELD_TASK_CANDIDATE_DATES: ",".join(candidate_dates),
            FIELD_TASK_ASSIGNEE: (body.get("assignee") or "").strip(),
            FIELD_TASK_STATUS: TASK_STATUS_PENDING,
            FIELD_TASK_TOKEN: token,
            FIELD_TASK_CREATOR: (body.get("creator") or "").strip(),
            FIELD_TASK_NOTE: (body.get("note") or "").strip(),
        }
        if duration_min is not None:
            fields[FIELD_TASK_DURATION_MIN] = duration_min
        deadline = _normalize_deadline(body.get("deadline"))
        if deadline:
            fields[FIELD_TASK_DEADLINE] = deadline
        owner_name = (body.get("owner_name") or "").strip()
        owner_phone = (body.get("owner_phone") or "").strip()
        if owner_name:
            fields[FIELD_TASK_OWNER_NAME] = owner_name
        if owner_phone:
            fields[FIELD_TASK_OWNER_PHONE] = owner_phone
        resp = requests.post(TASK_API_URL, headers=airtable_headers(), json={"fields": fields}, timeout=20)
        if resp.status_code >= 400:
            return jsonify({"error": "Airtable 寫入失敗", "detail": resp.text}), 502
        return jsonify({"ok": True, "token": token, "path": f"/book.html?token={token}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/vendor-slots/tasks/<record_id>", methods=["DELETE"])
def delete_vendor_slot_task(record_id):
    """刪掉一個任務（連結會立刻失效）。"""
    try:
        resp = requests.delete(f"{TASK_API_URL}/{record_id}", headers=airtable_headers(), timeout=20)
        if resp.status_code >= 400:
            return jsonify({"error": "Airtable 刪除失敗", "detail": resp.text}), 502
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


def _find_line_binding_record(name):
    escaped = (name or "").strip().replace("\\", "\\\\").replace("'", "\\'")
    recs = airtable_get_all(LINE_BIND_API_URL, f"{{{FIELD_BIND_NAME}}}='{escaped}'", [FIELD_BIND_NAME, FIELD_BIND_UID])
    return recs[0] if recs else None


def _get_line_binding(name):
    rec = _find_line_binding_record(name)
    return (rec["fields"].get(FIELD_BIND_UID) if rec else None) or None


def _find_task_by_token(token):
    escaped = (token or "").replace("'", "\\'")
    formula = f"{{{FIELD_TASK_TOKEN}}}='{escaped}'"
    records = airtable_get_all(TASK_API_URL, formula, _task_fields())
    return records[0] if records else None


@app.route("/api/vendor-slots/public-task/<token>")
def get_vendor_slot_task_by_token(token):
    """給 book.html（業務自助預約頁，不用登入）用：用 token 查任務內容。這支 API
    本身沒有登入驗證——「知道連結」就是通行碼，所以 token 一定要夠長夠隨機
    （secrets.token_urlsafe(16)，產生時就決定了，這裡不用再額外加密碼）。
    如果任務已經完成，額外把對應那筆「已預約」記錄的日期/時間/登記人撈出來
    放進 booked，book.html 才能顯示「已經安排在幾點」，不用只顯示「已完成」
    四個字。撈不到（例如那筆記錄被手動刪了）也不報錯，booked 就是 null，
    前端會顯示「請直接聯絡窗口確認」。"""
    try:
        r = _find_task_by_token(token)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    if not r:
        return jsonify({"error": "找不到這個連結對應的任務，可能已經被刪除"}), 404
    task = _task_to_dict(r)
    if task["status"] == TASK_STATUS_DONE and task["booking_id"]:
        try:
            resp = requests.get(
                f"{SLOT_API_URL}/{task['booking_id']}", headers=airtable_headers(),
                params={"returnFieldsByFieldId": "true"}, timeout=15,
            )
            if resp.status_code < 400:
                bf = resp.json().get("fields", {})
                task["booked"] = {
                    "date": bf.get(FIELD_SLOT_DATE),
                    "start_time": bf.get(FIELD_SLOT_START),
                    "end_time": bf.get(FIELD_SLOT_END),
                    "registrant": bf.get(FIELD_SLOT_REGISTRANT),
                }
        except Exception:
            pass
    elif task["status"] != TASK_STATUS_DONE and task["vendor"] and task["candidate_dates"]:
        # 2026-10-03：book.html 要在選時間的下拉裡直接把「這個廠商那天已經被
        # 預約」的時段灰掉不能選，不要等送出才報衝突。這裡只回日期＋起訖時間
        # （不帶案號/登記人，這支 API 沒有登入、知道連結就能看，不要順便把別人
        # 的案子資訊也公開出去）。撈失敗不影響頁面，busy_slots 就是空陣列，
        # 照舊靠送出時後端的衝突檢查擋。
        task["busy_slots"] = []
        try:
            escaped_vendor = task["vendor"].replace("'", "\\'")
            # 2026-10-04：業務「提供其他時間」可以選候選日期以外的任何一天，所以不再只
            # 撈候選日期，改撈這個廠商昨天以後的所有預約（量小）。
            formula = (
                f"AND({{{FIELD_SLOT_KIND}}}='{SLOT_KIND_BOOKING}',"
                f"{{{FIELD_SLOT_VENDOR}}}='{escaped_vendor}',"
                f"IS_AFTER({{{FIELD_SLOT_DATE}}},DATEADD(TODAY(),-1,'days')))"
            )
            busy_records = airtable_get_all(
                SLOT_API_URL, formula, [FIELD_SLOT_DATE, FIELD_SLOT_START, FIELD_SLOT_END],
            )
            for br in busy_records:
                bf = br["fields"]
                if bf.get(FIELD_SLOT_DATE) and bf.get(FIELD_SLOT_START) and bf.get(FIELD_SLOT_END):
                    task["busy_slots"].append({
                        "date": bf[FIELD_SLOT_DATE],
                        "start_time": bf[FIELD_SLOT_START],
                        "end_time": bf[FIELD_SLOT_END],
                    })
        except Exception as e:
            print(f"[get_vendor_slot_task_by_token] 撈已預約時段失敗（不影響頁面）：{e}", flush=True)
    liff_id = os.environ.get("LIFF_ID", "").strip()
    line_bound = False
    if liff_id and task["assignee"]:
        try:
            line_bound = bool(_get_line_binding(task["assignee"]))
        except Exception:
            pass
    return jsonify({"task": task, "liff_id": liff_id, "line_bound": line_bound,
                    "add_friend_url": os.environ.get("LINE_ADD_FRIEND_URL", "").strip()})


@app.route("/api/vendor-slots/public-task/<token>/bind-line", methods=["POST"])
def bind_line_for_task(token):
    """業務在 book.html 按「綁定 LINE 提醒」後呼叫。前端用 LIFF 取得的 access token 傳來，
    這裡自己拿去問 LINE（/v2/profile）取得真正的 userId，不信任前端直接傳的 userId，
    避免有人亂填別人的 userId。userId 存進「業務LINE綁定」表（以任務的「指派給」名字為鍵），
    之後同一位業務的任務都直接推給他，不用再綁。"""
    body = request.get_json(force=True) or {}
    access_token = (body.get("access_token") or "").strip()
    if not access_token:
        return jsonify({"error": "缺少 LINE 登入資訊"}), 400
    try:
        r = _find_task_by_token(token)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    if not r:
        return jsonify({"error": "找不到這個連結對應的任務"}), 404
    name = (r["fields"].get(FIELD_TASK_ASSIGNEE) or "").strip()
    if not name:
        return jsonify({"error": "這個任務沒有指派業務姓名，無法綁定，請聯絡窗口"}), 400
    try:
        prof = requests.get(
            "https://api.line.me/v2/profile",
            headers={"Authorization": f"Bearer {access_token}"}, timeout=15,
        )
        if prof.status_code >= 400:
            return jsonify({"error": "LINE 驗證失敗，請重新開啟連結再試一次"}), 400
        pj = prof.json()
        user_id, display = pj.get("userId", ""), pj.get("displayName", "")
        if not user_id:
            return jsonify({"error": "LINE 驗證失敗"}), 400
        existing = _find_line_binding_record(name)
        fields = {FIELD_BIND_NAME: name, FIELD_BIND_UID: user_id, FIELD_BIND_DISPLAY: display}
        if existing:
            resp = requests.patch(f"{LINE_BIND_API_URL}/{existing['id']}", headers=airtable_headers(),
                                  json={"fields": fields}, timeout=20)
        else:
            resp = requests.post(LINE_BIND_API_URL, headers=airtable_headers(),
                                 json={"fields": fields}, timeout=20)
        if resp.status_code >= 400:
            return jsonify({"error": "寫入失敗", "detail": resp.text}), 502
        return jsonify({"ok": True, "display_name": display})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/vendor-slots/public-task/<token>/book", methods=["POST"])
def book_vendor_slot_task(token):
    """業務在 book.html 選好日期/時間、按下「完成預約」時呼叫。
    body: {date, start_time, end_time, registrant, note, owner_name, owner_phone}
    date 必須是這個任務候選日期之一；案號/別名/廠商/項目類型都從任務本身帶，
    業務不用也不能重新輸入（避免手滑打錯案號）。owner_name/owner_phone 是
    book.html「屋主聯絡資訊」區塊的值（業務可能勾「同公證書資訊」直接帶
    任務上的預設值，也可能手動改過，以業務實際送出的為準）。成功後把任務
    狀態改成「已完成」，這個連結之後只能看、不能再預約一次（但可以讓 PM
    自己刪掉任務重開一個）。"""
    try:
        r = _find_task_by_token(token)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    if not r:
        return jsonify({"error": "找不到這個連結對應的任務，可能已經被刪除"}), 404
    task = _task_to_dict(r)
    if task["status"] == TASK_STATUS_DONE:
        return jsonify({"error": "這個任務已經完成預約了，如果要改時間請聯絡窗口處理"}), 409

    body = request.get_json(force=True)
    date = (body.get("date") or "").strip()
    if date not in task["candidate_dates"]:
        return jsonify({"error": "日期不在候選範圍內，請從提供的候選日期裡選一個"}), 400

    record, err = _book_vendor_slot(
        task["vendor"], date, body.get("start_time"), body.get("end_time"),
        task["case"], task["alias"], task["type"], body.get("registrant"), body.get("note"),
        owner_name=body.get("owner_name"), owner_phone=body.get("owner_phone"),
    )
    if err:
        err_body, status = err
        return jsonify(err_body), status

    try:
        requests.patch(
            f"{TASK_API_URL}/{r['id']}", headers=airtable_headers(),
            json={"fields": {FIELD_TASK_STATUS: TASK_STATUS_DONE, FIELD_TASK_BOOKING_ID: record["id"],
                             FIELD_TASK_STAGE: None}},
            timeout=20,
        )
    except Exception as e:
        # 預約本身已經成功寫入了，這裡只是回頭標記任務完成，失敗也不該讓使用者
        # 以為預約失敗——只印 log，前端照樣顯示預約成功。PM 之後重新整理主控台
        # 時如果發現任務狀態沒更新，手動刪掉任務即可，不影響已經卡好的時段。
        print(f"[book_vendor_slot_task] 更新任務狀態失敗（預約本身已成功）：{e}", flush=True)

    _notify_scheduler_async(
        task["creator"],
        f"✅ {task['assignee'] or body.get('registrant') or '業務'} 已完成安排\n"
        f"{task['case']} {task['alias']}\n{'、'.join(task['type'])}｜{date} {body.get('start_time')}-{body.get('end_time')}",
    )
    return jsonify({"ok": True, "record": record})


# ---- 2026-10-04：「原時間屋主不行，業務提供其他時間」協調流程 ----
# 業務在 book.html 勾「原預約時間屋主無法配合」→ 填幾組其他日期＋時間（propose）
# → 窗口（PM）在主控台跟廠商確認後，從裡面選一個（choose）→ 業務打開同一條連結看到
# 選定的時間、按確認（confirm）才真的建立預約（這時才做衝突檢查＋鎖時段）。
# 窗口如果全部都被廠商打槍，可以退回（reset）請業務重新提供。
def _normalize_slot(s):
    """把前端送來的一組 {date,start_time,end_time} 驗證＋正規化；格式不對回 None。"""
    try:
        date = str(s.get("date") or "").strip()
        datetime.strptime(date, "%Y-%m-%d")
        st = _parse_hhmm(str(s.get("start_time") or ""))
        et = _parse_hhmm(str(s.get("end_time") or ""))
    except Exception:
        return None
    if st >= et:
        return None
    return {"date": date, "start_time": f"{st // 60:02d}:{st % 60:02d}", "end_time": f"{et // 60:02d}:{et % 60:02d}"}


def _patch_task(record_id, fields):
    resp = requests.patch(f"{TASK_API_URL}/{record_id}", headers=airtable_headers(), json={"fields": fields}, timeout=20)
    if resp.status_code >= 400:
        raise RuntimeError(resp.text)
    return resp.json()


def _get_task_by_record_id(record_id):
    resp = requests.get(
        f"{TASK_API_URL}/{record_id}", headers=airtable_headers(),
        params={"returnFieldsByFieldId": "true"}, timeout=15,
    )
    if resp.status_code >= 400:
        return None
    return resp.json()


@app.route("/api/vendor-slots/public-task/<token>/propose", methods=["POST"])
def propose_vendor_slot_alternatives(token):
    """業務回傳「屋主可以配合的其他時間」。body: {slots: [{date,start_time,end_time}, ...],
    note, owner_name, owner_phone}。可重複呼叫（窗口退回後業務重新提供，或業務想修改）。"""
    try:
        r = _find_task_by_token(token)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    if not r:
        return jsonify({"error": "找不到這個連結對應的任務，可能已經被刪除"}), 404
    task = _task_to_dict(r)
    if task["status"] == TASK_STATUS_DONE:
        return jsonify({"error": "這個任務已經完成預約了"}), 409
    body = request.get_json(force=True)
    slots, seen = [], set()
    for s in (body.get("slots") or []):
        ns = _normalize_slot(s if isinstance(s, dict) else {})
        if not ns:
            return jsonify({"error": "備選時段格式不對（每一組都要有日期、開始時間、結束時間，且開始要早於結束）"}), 400
        key = (ns["date"], ns["start_time"], ns["end_time"])
        if key not in seen:
            seen.add(key)
            slots.append(ns)
    if not slots:
        return jsonify({"error": "請至少填一組屋主可以配合的日期與時間"}), 400
    if len(slots) > 10:
        return jsonify({"error": "備選時段最多 10 組"}), 400
    fields = {
        FIELD_TASK_STAGE: TASK_STAGE_WAIT_PM,
        FIELD_TASK_ALT_SLOTS: json.dumps(slots, ensure_ascii=False),
        FIELD_TASK_CHOSEN_SLOT: "",
        FIELD_TASK_REP_NOTE: (body.get("note") or "").strip(),
    }
    if (body.get("owner_name") or "").strip():
        fields[FIELD_TASK_OWNER_NAME] = body["owner_name"].strip()
    if (body.get("owner_phone") or "").strip():
        fields[FIELD_TASK_OWNER_PHONE] = body["owner_phone"].strip()
    try:
        _patch_task(r["id"], fields)
    except Exception as e:
        return jsonify({"error": "Airtable 寫入失敗", "detail": str(e)}), 502
    _notify_scheduler_async(
        task["creator"],
        f"📝 {task['assignee'] or '業務'} 回傳了屋主可配合的其他時間（{len(slots)} 組）\n"
        f"{task['case']} {task['alias']}\n{'、'.join(task['type'])}\n"
        "請到主控台「廠商時段協調」跟廠商確認後，選一個時間。",
    )
    return jsonify({"ok": True, "slots": slots})


@app.route("/api/vendor-slots/tasks/<record_id>/choose", methods=["POST"])
def choose_vendor_slot_alternative(record_id):
    """窗口（PM）從業務回傳的備選時段裡選定一個。body: {index}。選的當下先檢查一次
    衝突（廠商那天那段已經被別案占用就直接告訴 PM），真正鎖時段是業務按確認那一刻。"""
    rec = _get_task_by_record_id(record_id)
    if not rec:
        return jsonify({"error": "找不到這個任務"}), 404
    task = _task_to_dict(rec)
    if task["status"] == TASK_STATUS_DONE or task["stage"] not in (TASK_STAGE_WAIT_PM, TASK_STAGE_WAIT_REP):
        return jsonify({"error": "這個任務目前沒有待選擇的備選時段"}), 409
    body = request.get_json(force=True)
    try:
        slot = task["alt_slots"][int(body.get("index"))]
    except Exception:
        return jsonify({"error": "選的備選時段不存在"}), 400
    try:
        conflict = _find_slot_conflict(task["vendor"], slot["date"], slot["start_time"], slot["end_time"])
    except Exception as e:
        return jsonify({"error": "查詢既有預約失敗", "detail": str(e)}), 502
    if conflict:
        return jsonify({"error": "這個時段已經被佔用了", "conflict": conflict}), 409
    try:
        _patch_task(record_id, {
            FIELD_TASK_CHOSEN_SLOT: json.dumps(slot, ensure_ascii=False),
            FIELD_TASK_STAGE: TASK_STAGE_WAIT_REP,
        })
    except Exception as e:
        return jsonify({"error": "Airtable 寫入失敗", "detail": str(e)}), 502
    return jsonify({"ok": True, "chosen_slot": slot})


@app.route("/api/vendor-slots/tasks/<record_id>/deadline", methods=["POST"])
def set_vendor_slot_task_deadline(record_id):
    """調整（或取消）回覆期限。body: {deadline: ISO 字串 | null}。"""
    body = request.get_json(force=True)
    raw = body.get("deadline")
    deadline = _normalize_deadline(raw)
    if raw and not deadline:
        return jsonify({"error": "期限格式不對"}), 400
    try:
        # 期限改了就重新武裝提醒（已提醒打勾清掉）
        _patch_task(record_id, {FIELD_TASK_DEADLINE: deadline, FIELD_TASK_REMINDED: False})
    except Exception as e:
        return jsonify({"error": "Airtable 寫入失敗", "detail": str(e)}), 502
    return jsonify({"ok": True, "deadline": deadline or ""})


@app.route("/api/vendor-slots/tasks/<record_id>/reset", methods=["POST"])
def reset_vendor_slot_alternatives(record_id):
    """窗口退回：備選時段廠商都不行，清掉備選/選定，回到一般「待業務安排」，請業務重新提供。"""
    try:
        _patch_task(record_id, {FIELD_TASK_STAGE: None, FIELD_TASK_ALT_SLOTS: "", FIELD_TASK_CHOSEN_SLOT: ""})
    except Exception as e:
        return jsonify({"error": "Airtable 寫入失敗", "detail": str(e)}), 502
    return jsonify({"ok": True})


@app.route("/api/vendor-slots/public-task/<token>/confirm", methods=["POST"])
def confirm_vendor_slot_chosen(token):
    """業務確認窗口選定的那個時間沒問題。body: {registrant, note, owner_name, owner_phone}。
    這時才真的建立預約（跟一般預約共用 _book_vendor_slot 的衝突檢查）、任務標成已完成。"""
    try:
        r = _find_task_by_token(token)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    if not r:
        return jsonify({"error": "找不到這個連結對應的任務，可能已經被刪除"}), 404
    task = _task_to_dict(r)
    if task["status"] == TASK_STATUS_DONE:
        return jsonify({"error": "這個任務已經完成預約了"}), 409
    chosen = task["chosen_slot"]
    if task["stage"] != TASK_STAGE_WAIT_REP or not chosen:
        return jsonify({"error": "窗口還沒有選定時間，目前不能確認"}), 409
    body = request.get_json(force=True)
    record, err = _book_vendor_slot(
        task["vendor"], chosen["date"], chosen["start_time"], chosen["end_time"],
        task["case"], task["alias"], task["type"],
        (body.get("registrant") or task["assignee"] or "").strip(), body.get("note"),
        owner_name=body.get("owner_name"), owner_phone=body.get("owner_phone"),
    )
    if err:
        err_body, status = err
        return jsonify(err_body), status
    try:
        _patch_task(r["id"], {FIELD_TASK_STATUS: TASK_STATUS_DONE, FIELD_TASK_BOOKING_ID: record["id"], FIELD_TASK_STAGE: None})
    except Exception as e:
        print(f"[confirm_vendor_slot_chosen] 更新任務狀態失敗（預約本身已成功）：{e}", flush=True)
    _notify_scheduler_async(
        task["creator"],
        f"✅ {task['assignee'] or '業務'} 已確認時間，安排完成\n"
        f"{task['case']} {task['alias']}\n{'、'.join(task['type'])}｜{chosen['date']} {chosen['start_time']}-{chosen['end_time']}",
    )
    return jsonify({"ok": True, "record": record})


@app.route("/api/site-survey-cancelled-sync", methods=["POST"])
def site_survey_cancelled_sync():
    """業務自治區 Google 試算表的 Apps Script 時間觸發器呼叫這支，把「取消案件」
    「A01資訊」兩個頁籤裡 A 欄＝「取消」的案號（D 欄）整批推過來，存進
    CANCELLED_CASE_CACHE，_compute_survey_cases() 算「場勘安排」清單時直接讀
    這份快取（不會每次都重新驗證 SECRET 以外的事，單純信任推進來的內容，呼叫
    頻率跟內容正確性由試算表那邊的腳本負責）。
    2026-10-01 同一支端點擴充：body 可以再帶一組 certified_cases（A01資訊
    分頁裡 A 欄＝「已公證」的案號＋別名＋施作廠商＋業務），存進
    CERTIFIED_CASE_CACHE，給 /api/case-search 用——這些案件已經公證但通常
    還沒建進 Airtable 的「專案細節」表，PM 卻已經要開始排時段了。
    2026-10-01 同日再擴充：body 可以再帶一組 owner_contacts（A01資訊表格
    裡快取好的屋主姓名/電話，來源是 K 欄連結的 Drive 合約文件，解析過程
    在 Apps Script 那邊做，這裡單純接收結果），存進 OWNER_CONTACT_CACHE，
    涵蓋所有案件（不限於已公證／不限於還沒建進 Airtable），PM 建立「指派
    給業務」任務時查到就會預先帶入屋主姓名/電話。
    body: {key, cancelled_case_numbers: [案號, ...],
           certified_cases: [{case, alias, vendor, sales_person}, ...],
           owner_contacts: [{case, name, phone}, ...]}"""
    body = request.get_json(force=True)
    if not BIZ_SHEET_SYNC_KEY or body.get("key") != BIZ_SHEET_SYNC_KEY:
        return jsonify({"error": "unauthorized"}), 401
    case_nos = body.get("cancelled_case_numbers") or []
    CANCELLED_CASE_CACHE["case_nos"] = {c for c in case_nos if c}
    CANCELLED_CASE_CACHE["updated_at"] = datetime.now().isoformat()
    certified = body.get("certified_cases") or []
    CERTIFIED_CASE_CACHE["cases"] = [
        {
            "case": (c.get("case") or "").strip(),
            "alias": (c.get("alias") or "").strip(),
            "vendor": (c.get("vendor") or "").strip(),
            "sales_person": (c.get("sales_person") or "").strip(),
        }
        for c in certified if isinstance(c, dict) and (c.get("case") or "").strip()
    ]
    CERTIFIED_CASE_CACHE["updated_at"] = datetime.now().isoformat()
    owner_contacts = body.get("owner_contacts") or []
    new_owner_cache = {}
    for c in owner_contacts:
        if not isinstance(c, dict):
            continue
        case_no = (c.get("case") or "").strip()
        name = (c.get("name") or "").strip()
        phone = (c.get("phone") or "").strip()
        if case_no and (name or phone):
            new_owner_cache[case_no] = {"name": name, "phone": phone}
    OWNER_CONTACT_CACHE.clear()
    OWNER_CONTACT_CACHE.update(new_owner_cache)
    print(
        f"[site_survey_cancelled_sync] 收到 {len(CANCELLED_CASE_CACHE['case_nos'])} 筆取消案號、"
        f"{len(CERTIFIED_CASE_CACHE['cases'])} 筆已公證案件、{len(OWNER_CONTACT_CACHE)} 筆屋主聯絡資訊",
        flush=True,
    )
    return jsonify({
        "ok": True,
        "count": len(CANCELLED_CASE_CACHE["case_nos"]),
        "certified_count": len(CERTIFIED_CASE_CACHE["cases"]),
        "owner_contact_count": len(OWNER_CONTACT_CACHE),
    })


@app.route("/api/owner-contact")
def get_owner_contact():
    """給前端選定案號後查屋主姓名/電話用（見 OWNER_CONTACT_CACHE 說明）。
    query params: case（完整案號，需完全相符）"""
    case_no = (request.args.get("case") or "").strip()
    if not case_no:
        return jsonify({"found": False})
    info = OWNER_CONTACT_CACHE.get(case_no)
    if not info:
        return jsonify({"found": False})
    return jsonify({"found": True, "name": info.get("name", ""), "phone": info.get("phone", "")})


# ---- APP資料（前端狀態同步用，跨裝置/跨使用者共用；取代原本的 localStorage）----
# 這張表是 2026-08-25 新增的，用來存放「已完工」「掛表安排」「異常案件」「變流器出貨日期」
# 「註記清單」這幾個原本只存在瀏覽器本機的狀態，改成寫回 Airtable，讓不同電腦、不同同事
# 都能看到同一份資料。這張表用「欄位名稱」而不是欄位 ID 存取（跟其他表不同），單純是因為
# 這張表是全新建立的，直接用名稱比較好維護，不用另外去 Airtable 查每個欄位的 ID。
APP_DATA_TABLE_ID = "tblafnN1qFDoLgTx1"
APP_DATA_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{APP_DATA_TABLE_ID}"

# 註記清單允許的「類型」。2026-08-27 新增「未使用料件」，2026-08-30 新增「電話紀錄」
# （給前端「筆記本」功能的線上紀錄用）——
# create_note() 的驗證跟 get_app_data() 組裝 notes 的判斷都要用這份同一份清單，
# 避免兩邊各自寫一次、改一邊忘了改另一邊。
NOTE_TYPES = ("併聯取得時備貨", "其他狀況備住", "未使用料件", "料件使用", "電話紀錄")

# 2026-08-30 新增：模組／逆變器型號「隱藏清單」，也存在 APP資料 表，用獨立的
# 類型「隱藏型號」跟上面 NOTE_TYPES 那些區分開（不會出現在前端「註記清單」裡）。
# 這是「軟隱藏」——完全不動 Airtable「專案細節」的 Single Select 選項、也不刪除
# 「採購-逆變器」表的任何記錄，只是讓 refresh_model_options_cache() 在組出最終
# 選項清單前，把使用者標記過的型號從清單中濾掉。這樣舊案件不管以前用的是哪個
# 型號都完全不受影響，之後想恢復顯示也只要把隱藏記錄刪掉即可，是可逆的操作。
# 借用 APP資料 表既有欄位存這筆記錄：
#   案號或別名 → 存 "module" 或 "inverter"，代表這筆隱藏的是哪一種型號
#   內容       → 模組型號：直接存型號名稱；
#                逆變器型號：因為要比對的是 record_id，但畫面上要顯示名稱給使用者看，
#                所以存成 "record_id::名稱" 這種組合格式，用的時候用 "::" 切開。
HIDDEN_MODEL_TYPE = "隱藏型號"

# ===================================================================
# 維運驗收（維運團隊現場驗收，2026-09-08 新增）
# ===================================================================
# 這張表跟「廠商資料」表都是全新建立，一律用欄位 ID 存取（跟「專案細節」
# 「進度管理」等舊表一致的慣例），欄位 ID 直接來自建表當下 Airtable 回傳的結果。
OPS_TABLE_ID = "tbl0qVhhjkwj200RP"
OPS_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{OPS_TABLE_ID}"

OPS_FIELD_CASE_NAME = "fld9egTx0mfs94wIr"          # 案場名稱（primary field）
OPS_FIELD_CASE_NO = "fldocN9NDjgCymWkz"            # 案號
OPS_FIELD_CASE_LINK = "fld500oePwtRY9JpP"          # 關聯案件（連結到 專案細節）
OPS_FIELD_VENDOR = "fld8xjiEsIaYj2fIf"             # 廠商（簡稱，快照）
OPS_FIELD_VENDOR_FULLNAME = "fldK2kuu5Vdx3DXrr"    # 系統商單位全名
OPS_FIELD_OWNER_COMPANY = "fldQ1LwFOK82xBr5K"      # 業主單位
OPS_FIELD_PLANNED_METER_DATE = "fldpqZvxSWPANgN51"  # 預計掛表日期
OPS_FIELD_CHECKLIST_JSON = "flda5pq5f33TcSs38"     # 檢查項目JSON
OPS_FIELD_OTHER_ISSUES = "fldZycOWm4ZrzmnGA"       # 其他缺失
OPS_FIELD_RESULT = "flduHCx5T9wNwvIif"             # 驗收結果（multipleSelects）
OPS_FIELD_EQUIPMENT_JSON = "fldkbi9CSbI9NayFC"     # 設備清單JSON
OPS_FIELD_OWNER_SIGNER_NAME = "fld1qIuXxhh7Cdy5L"  # 業主代表姓名
OPS_FIELD_OWNER_SIGNATURE = "fldYjfMYVHkwKCe9C"    # 業主簽名（attachment）
OPS_FIELD_OWNER_SIGN_DATE = "fldPGEZtKYZcmRkJP"    # 業主簽名日期
OPS_FIELD_VENDOR_SIGNER_NAME = "fldLI1dfYyoUkhNM8"  # 系統商代表姓名
OPS_FIELD_VENDOR_SIGNATURE = "fldkfJUSFsBUSzp9W"   # 系統商簽名（attachment）
OPS_FIELD_VENDOR_SIGN_DATE = "fldVCZ61YlZXpWO9F"   # 系統商簽名日期
OPS_FIELD_STATUS = "fldRGN4AsqexXxLDn"             # 狀態（singleSelect）
OPS_FIELD_PDF = "fldHYRHed1WT48pBy"                # PDF檔案（attachment）

OPS_STATUS_PENDING = "待填寫"
OPS_STATUS_DONE = "已完成驗收"
OPS_STATUS_PDF = "已產生PDF"

# ---- 廠商資料（廠商簡稱 -> 公司全名 對照表，2026-09-08 新增）----
VENDOR_INFO_TABLE_ID = "tblAbT7VocQUIj3zW"
VENDOR_INFO_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{VENDOR_INFO_TABLE_ID}"
VENDOR_INFO_FIELD_SHORT = "fldStStiYvwNdzVnj"   # 廠商簡稱
VENDOR_INFO_FIELD_FULL = "fld2wpGkRKBSzS29D"    # 公司全名

DEFAULT_OWNER_COMPANY = "綠點能創股份有限公司"

# 驗收單「太陽光電系統完工驗收細項表」預設 8 大類 44 小項，對照紙本驗收單。
# 每次幫案件新建一筆「維運驗收」記錄時，用這份樣板產生初始的「檢查項目JSON」，
# 現場人員在手機上針對每一項勾選「正常/異常」，異常的話可以填備註、勾選是否
# 現場修復。之後如果驗收單項目有調整，只要改這裡一份，不用同時改前端。
DEFAULT_CHECKLIST_TEMPLATE = [
    {"category": "變流器", "items": [
        "變流器輸出是否正常", "變流器線路溫度是否異常", "變流器安裝是否確實",
        "變流器進線標示是否正確", "變流器接地是否確實（O型端子）", "變流器鎖固是否確實",
        "變流器是否有遮陽措施", "變流器位置現場是否按審迄圖施工",
    ]},
    {"category": "交流箱與內部接線", "items": [
        "交流接線箱溫度是否異常", "交流開關是否正常", "交流配電箱內配線是否整齊",
        "交流配電箱標示是否正確", "交流配電箱是否確實接地（O型端子）",
        "交流配電箱線材規格、開關規格是否符合審迄圖", "交流配電箱現場是否按審迄圖施工",
    ]},
    {"category": "直流箱與內部接線", "items": [
        "直流箱內部溫度是否異常", "直流箱內配線是否整齊", "直流箱標示是否正確",
        "直流箱是否確實接地（O型端子）", "直流箱線路、保險絲、突波吸收器 是否正常",
        "模組串列開路電壓是否異常", "直流箱內線路絕緣是否異常",
        "直流箱內線材規格、開關規格、突波吸收器、保險絲規格是否符合審迄圖",
        "直流箱位置現場是否按審迄圖施工",
    ]},
    {"category": "監控箱", "items": [
        "監控電源插座是否完成", "監控與逆變器之通訊線路是否完成", "監控接地是否完成",
    ]},
    {"category": "支架結構", "items": [
        "支架鎖固是否確實", "支架是否按結構計算書施工", "支架防鏽是否確實",
        "支架是否確實接地", "支架規格材質否符合出廠證明與工程合約",
        "螺絲、壓塊 規格材質否符合承攬明細", "棚架型系統之水泥墩、平鋪型系統之角座 是否完整",
        "棚架型系統之水泥墩、平鋪型系統之角座 防水完整",
    ]},
    {"category": "模組", "items": [
        "模組鎖固是否確實", "模組線路固定是否確實", "模組溫度是否異常",
        "模組線路溫度是否異常", "模組接地是否確實（O型端子）", "模組是否破損",
        "模組表面是否有髒污異物(不含動物排泄物與沙塵)", "模組排佈現場是否按審迄圖施工",
    ]},
    {"category": "其他", "items": [
        "線槽是否固定確實", "線槽出口是否填補確實", "管材材質是否符合審迄圖",
        "箱體（直流箱、交流箱、監控箱）材質規格是否符合承攬明細",
    ]},
    {"category": "系統其他", "items": [
        "約定事項是否確實執行（例：水塔移動、結構補強）", "系統是否無（直接/潛在）遮陰",
        "施作標的物是否有因施工所造成之損壞",
    ]},
]

# 設備清單除了模組/變流器可以從案件既有規格自動帶出之外，其餘 5 項固定先給
# 空白列，讓現場人員手動填寫（見交接需求：模組/逆變器自動帶入，其餘手動輸入）。
DEFAULT_EQUIPMENT_EXTRA_NAMES = ["箱體", "電表", "監控", "分享器", "支架"]


def build_default_checklist():
    """展開 DEFAULT_CHECKLIST_TEMPLATE，補上流水編號（對照紙本 1.1、1.2...），
    回傳給新建的「維運驗收」記錄當作「檢查項目JSON」初始內容。"""
    checklist = []
    for cat_index, cat in enumerate(DEFAULT_CHECKLIST_TEMPLATE, start=1):
        for item_index, item_text in enumerate(cat["items"], start=1):
            checklist.append({
                "no": f"{cat_index}.{item_index}",
                "category": cat["category"],
                "item": item_text,
                "result": None,       # "正常" / "異常" / None(未填)
                "note": "",
                "onsite_fix": False,
            })
    return checklist


def ops_get_all(filter_formula=None, field_ids=None):
    return airtable_get_all(OPS_API_URL, filter_formula, field_ids) if field_ids else \
        airtable_get_all(OPS_API_URL, filter_formula, [])


def get_vendor_fullname(vendor_short_name):
    """用廠商簡稱查「廠商資料」表拿公司全名；查不到就直接回傳簡稱本身，
    不會讓呼叫端因為漏填全名而整支壞掉。"""
    if not vendor_short_name:
        return vendor_short_name
    escaped = vendor_short_name.replace("'", "\\'")
    formula = f"{{{VENDOR_INFO_FIELD_SHORT}}}='{escaped}'"
    try:
        records = airtable_get_all(VENDOR_INFO_API_URL, formula, [VENDOR_INFO_FIELD_FULL])
        if records:
            return records[0]["fields"].get(VENDOR_INFO_FIELD_FULL) or vendor_short_name
    except Exception as e:
        print(f"[get_vendor_fullname] 查詢廠商全名失敗（不影響主要流程）：{e}", flush=True)
    return vendor_short_name


def fetch_case_basic_info(case_record_id):
    """輕量版的案件基本資料查詢，只拿維運驗收單需要的欄位（案號、別名、廠商、
    模組、逆變器），不像 fetch_case_snapshot_for_archive 那樣還要多查一輪
    里程碑資料——這裡用不到出貨/進場/掛表日期，沒必要多花那些查詢時間。"""
    try:
        resp = requests.get(
            f"{CASE_API_URL}/{case_record_id}",
            headers=airtable_headers(),
            params={"returnFieldsByFieldId": "true"},
            timeout=15,
        )
        if resp.status_code >= 400:
            return None
        f = resp.json().get("fields", {})
    except Exception:
        return None

    module = format_module(f)
    inverter_ids = f.get(FIELD_INVERTER) or []
    inverter_name_map = resolve_inverter_names(inverter_ids)
    inverter = format_inverter(f, inverter_name_map)

    return {
        "case_no": f.get(FIELD_CASE_NO, ""),
        "alias": f.get(FIELD_ALIAS, ""),
        "vendor": f.get(FIELD_VENDOR, ""),
        "address": f.get(FIELD_ADDRESS, ""),
        "module": module,
        "inverter": inverter,
    }


def build_default_equipment_list(case_info):
    """組出設備清單JSON 的初始內容：模組/變流器從案件既有規格帶出（唯讀性質，
    但允許現場人員之後覆寫），其餘 5 項給空白列讓現場人員手動輸入。"""
    equipment = []
    if case_info and case_info.get("module"):
        equipment.append({"name": "模組", "brand": "", "model": case_info["module"], "qty": "", "unit": "片", "note": ""})
    else:
        equipment.append({"name": "模組", "brand": "", "model": "", "qty": "", "unit": "片", "note": ""})
    if case_info and case_info.get("inverter"):
        equipment.append({"name": "變流器", "brand": "", "model": case_info["inverter"], "qty": "", "unit": "台", "note": ""})
    else:
        equipment.append({"name": "變流器", "brand": "", "model": "", "qty": "", "unit": "台", "note": ""})
    for name in DEFAULT_EQUIPMENT_EXTRA_NAMES:
        equipment.append({"name": name, "brand": "", "model": "", "qty": "", "unit": "", "note": ""})
    return equipment


def ops_find_by_case(case_record_id):
    """找這個案件目前在「維運驗收」表裡對應的那一筆記錄（如果有的話）。"""
    escaped = case_record_id.replace("'", "\\'")
    formula = f"FIND('{escaped}', ARRAYJOIN({{{OPS_FIELD_CASE_LINK}}}))"
    records = airtable_get_all(OPS_API_URL, formula, [OPS_FIELD_CASE_NAME])
    return records[0] if records else None


def sync_ops_case_on_meter_planned(case_record_id, case_no, meter_planned_date):
    """「掛表安排」頁設定/修改「預計掛表日期」時呼叫：確保這個案件在「維運驗收」
    表裡有一筆對應記錄，讓維運團隊模組能看到這個案場。已經存在就只更新日期
    （不動使用者已經填寫的檢查項目/簽名等內容），第一次才建立完整的初始資料
    （含 44 項檢查清單樣板、設備清單、廠商全名查詢）。
    任何失敗都只印 log、不拋出例外，不能因為這個同步動作失敗就讓「掛表安排」
    頁原本的「設定預計掛表日期」功能連帶掛掉。"""
    try:
        existing = ops_find_by_case(case_record_id)
        if existing:
            resp = requests.patch(
                f"{OPS_API_URL}/{existing['id']}",
                headers=airtable_headers(),
                json={"fields": {OPS_FIELD_PLANNED_METER_DATE: meter_planned_date}},
                timeout=20,
            )
            if resp.status_code >= 400:
                print(f"[sync_ops_case] 更新既有維運驗收記錄失敗：{resp.text}", flush=True)
            return

        case_info = fetch_case_basic_info(case_record_id) or {}
        vendor_short = case_info.get("vendor", "")
        vendor_full = get_vendor_fullname(vendor_short)
        case_name = case_info.get("alias") or case_no or ""
        checklist = build_default_checklist()
        equipment = build_default_equipment_list(case_info)

        create_fields = {
            OPS_FIELD_CASE_NAME: case_name,
            OPS_FIELD_CASE_NO: case_no,
            OPS_FIELD_CASE_LINK: [case_record_id],
            OPS_FIELD_VENDOR: vendor_short,
            OPS_FIELD_VENDOR_FULLNAME: vendor_full,
            OPS_FIELD_OWNER_COMPANY: DEFAULT_OWNER_COMPANY,
            OPS_FIELD_PLANNED_METER_DATE: meter_planned_date,
            OPS_FIELD_CHECKLIST_JSON: json.dumps(checklist, ensure_ascii=False),
            OPS_FIELD_EQUIPMENT_JSON: json.dumps(equipment, ensure_ascii=False),
            OPS_FIELD_STATUS: OPS_STATUS_PENDING,
        }
        resp = requests.post(
            OPS_API_URL, headers=airtable_headers(),
            json={"fields": create_fields}, timeout=20,
        )
        if resp.status_code >= 400:
            print(f"[sync_ops_case] 建立維運驗收記錄失敗：{resp.text}", flush=True)
    except Exception as e:
        print(f"[sync_ops_case] 同步維運驗收記錄失敗（不影響掛表安排主要流程）：{e}", flush=True)


def upload_attachment_to_ops_record(ops_record_id, field_id, base64_data, filename, content_type="image/png"):
    """把一張 base64 圖片（簽名畫布 canvas.toDataURL() 產生的內容）上傳成
    Airtable 附件欄位。Airtable 附件上傳走的是另一個 domain（content.airtable.com），
    跟平常讀寫記錄資料的 api.airtable.com 不是同一個 API，欄位/記錄都要先存在，
    上傳成功後那個欄位會多一筆附件（不會覆蓋原本已有的附件，是用「新增」的方式）。"""
    url = f"https://content.airtable.com/v0/{BASE_ID}/{ops_record_id}/{field_id}/uploadAttachment"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}"},
        json={"contentType": content_type, "filename": filename, "file": base64_data},
        timeout=30,
    )
    if resp.status_code >= 400:
        raise Exception(resp.text)
    return resp.json()


def _pdf_checkbox_flowable(checked, size=7):
    """畫一個真正的方框 checkbox（不依賴字型有沒有 ☐☑ 這種符號的字），
    用 reportlab 的 Flowable 直接畫矩形＋打勾時畫一個 X，任何電腦、任何
    PDF 閱讀器開起來都長一樣，不會有字型缺字/兩種符號長得一樣分不出來的問題。"""
    from reportlab.platypus import Flowable

    class _CheckBox(Flowable):
        def __init__(self, checked, size):
            super().__init__()
            self.checked = checked
            self.width = size
            self.height = size

        def draw(self):
            c = self.canv
            s = self.width
            c.setLineWidth(0.8)
            c.rect(0.5, 0.5, s - 1, s - 1)
            if self.checked:
                c.line(1.6, 1.6, s - 1.6, s - 1.6)
                c.line(1.6, s - 1.6, s - 1.6, 1.6)

    return _CheckBox(checked, size)


def _pdf_checkbox_with_label(checked, label, font_name, font_size, cb_size=7, label_width=26):
    """checkbox + 文字標籤（例如「☐正常」）組成一個小 flowable，用一個
    無邊框的內嵌 mini table 讓 checkbox 跟文字對齊在同一行。"""
    from reportlab.platypus import Table as _MiniTable, TableStyle as _MiniStyle
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import Paragraph

    style = ParagraphStyle("cb_label", fontName=font_name, fontSize=font_size, leading=font_size + 2)
    t = _MiniTable(
        [[_pdf_checkbox_flowable(checked, cb_size), Paragraph(label, style)]],
        colWidths=[cb_size + 3, label_width],
    )
    t.setStyle(_MiniStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _pdf_fetch_image_flowable(url, max_width, max_height):
    """從一個網址（通常是 Airtable 附件網址）下載圖片，包成 reportlab 的
    Image flowable，並依比例縮放到不超過 max_width x max_height。
    下載失敗時回傳 None，呼叫端要能優雅處理（顯示空白而不是整份 PDF 產生失敗）。"""
    from reportlab.platypus import Image as RLImage
    from PIL import Image as PILImage

    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        buf = io.BytesIO(resp.content)
        with PILImage.open(buf) as im:
            w, h = im.size
        buf.seek(0)
        scale = min(max_width / w, max_height / h, 1.0)
        return RLImage(buf, width=w * scale, height=h * scale)
    except Exception as e:
        print(f"[build_acceptance_pdf] 下載簽名圖片失敗（{url}）：{e}", flush=True)
        return None


def build_acceptance_pdf(data):
    """把一筆「維運驗收」記錄的內容排版成跟公司紙本「太陽光電系統完工驗收
    細項表」一模一樣的格式：
      案場名稱／表頭 → 編號｜子項｜檢查項目｜正常☐｜異常☐｜備註｜現場修復☐
      （同一大類的「編號」「子項」直向合併儲存格）→ 其他缺失／驗收結果
      （3 個 checkbox）→ 業主/系統商單位 → 雙方代表簽名（含簽名圖片）／
      簽名日期 → 設備清單（含流水編號）。
    回傳 PDF 檔案的 bytes。checkbox 一律用向量繪製（見 _pdf_checkbox_flowable），
    不依賴字型是否有方框符號的字。中文用 reportlab 內建 CID 字型
    STSong-Light，不需要額外字型檔。"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    font_name = "STSong-Light"

    styles = {
        "title": ParagraphStyle("title", fontName=font_name, fontSize=15, leading=19, alignment=1),
        "h": ParagraphStyle("h", fontName=font_name, fontSize=9.5, leading=13),
        "h_bold": ParagraphStyle("h_bold", fontName=font_name, fontSize=9.5, leading=13),
        "cell": ParagraphStyle("cell", fontName=font_name, fontSize=8, leading=11),
        "cat": ParagraphStyle("cat", fontName=font_name, fontSize=8, leading=11, alignment=1),
        "small": ParagraphStyle("small", fontName=font_name, fontSize=8, leading=11),
    }

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=10 * mm, bottomMargin=10 * mm, leftMargin=10 * mm, rightMargin=10 * mm,
    )
    story = []
    case_label = data.get("case_name") or data.get("case_no") or ""

    # ---- 表頭：案場名稱｜案場值｜大標題 ----
    header_tbl = Table(
        [[Paragraph("案場名稱", styles["h_bold"]), Paragraph(case_label, styles["h"]),
          Paragraph("太陽光電系統完工驗收細項表", styles["title"])]],
        colWidths=[22 * mm, 48 * mm, 117 * mm],
    )
    header_tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.8, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.8, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (0, 0), colors.whitesmoke),
    ]))
    story.append(header_tbl)

    # ---- 44 項檢查清單表格：編號｜子項｜檢查項目｜正常｜異常｜備註｜現場修復 ----
    col_widths = [9 * mm, 23 * mm, 62 * mm, 22 * mm, 22 * mm, 32 * mm, 17 * mm]
    header_row = ["編號", "子項", "檢查項目", "業主確認", "", "備註", "現場修復"]
    rows = [[Paragraph(t, styles["cell"]) if t else "" for t in header_row]]
    span_cmds = []
    prev_cat_no = None
    cat_start_row = 1

    for item in data.get("checklist", []):
        cat_no = (item.get("no") or "").split(".")[0]
        result = item.get("result") or ""
        row_index = len(rows)
        if cat_no != prev_cat_no:
            if prev_cat_no is not None and row_index - 1 > cat_start_row:
                span_cmds.append(("SPAN", (0, cat_start_row), (0, row_index - 1)))
                span_cmds.append(("SPAN", (1, cat_start_row), (1, row_index - 1)))
            prev_cat_no = cat_no
            cat_start_row = row_index
        rows.append([
            Paragraph(cat_no, styles["cat"]),
            Paragraph(item.get("category", ""), styles["cat"]),
            Paragraph(item.get("item", ""), styles["cell"]),
            _pdf_checkbox_with_label(result == "正常", "正常", font_name, 8),
            _pdf_checkbox_with_label(result == "異常", "異常", font_name, 8),
            Paragraph(item.get("note") or "", styles["cell"]),
            _pdf_checkbox_flowable(bool(item.get("onsite_fix")), size=8),
        ])
    # 收尾：最後一個分類也要補上合併
    last_row = len(rows) - 1
    if last_row > cat_start_row:
        span_cmds.append(("SPAN", (0, cat_start_row), (0, last_row)))
        span_cmds.append(("SPAN", (1, cat_start_row), (1, last_row)))

    checklist_tbl = Table(rows, colWidths=col_widths, repeatRows=1)
    checklist_style = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("SPAN", (3, 0), (4, 0)),  # 表頭「業主確認」橫跨 正常/異常 兩欄
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (1, -1), "CENTER"),
        ("ALIGN", (3, 0), (4, -1), "CENTER"),
        ("ALIGN", (6, 0), (6, -1), "CENTER"),
    ] + span_cmds
    checklist_tbl.setStyle(TableStyle(checklist_style))
    story.append(checklist_tbl)

    # ---- 其他缺失 / 驗收結果（3 個 checkbox） ----
    result_choices = data.get("result") or []
    result_row_content = Table(
        [[
            _pdf_checkbox_with_label("合格" in result_choices, "合格", font_name, 8, label_width=22),
            _pdf_checkbox_with_label("照片複驗" in result_choices, "照片複驗", font_name, 8, label_width=32),
            _pdf_checkbox_with_label("現場複驗" in result_choices, "現場複驗", font_name, 8, label_width=32),
        ]],
        colWidths=[30, 42, 42],
    )
    result_row_content.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))
    other_tbl = Table([
        [Paragraph("其他缺失", styles["cell"]), Paragraph(data.get("other_issues") or "", styles["cell"])],
        [Paragraph("驗收結果", styles["cell"]), result_row_content],
    ], colWidths=[22 * mm, 165 * mm])
    other_tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
    ]))
    story.append(other_tbl)
    story.append(Spacer(1, 5 * mm))

    # ---- 業主/系統商單位 → 代表簽名（含簽名圖片）→ 簽名日期 ----
    owner_sig = _pdf_fetch_image_flowable(data.get("owner_signature_url"), 50 * mm, 16 * mm) \
        if data.get("owner_signature_url") else ""
    vendor_sig = _pdf_fetch_image_flowable(data.get("vendor_signature_url"), 50 * mm, 16 * mm) \
        if data.get("vendor_signature_url") else ""

    def sign_row_cell(label, content):
        t = Table([[Paragraph(label, styles["small"]), content or ""]], colWidths=[24 * mm, 60 * mm])
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        return t

    sign_tbl = Table([
        [Paragraph(f"業主單位 : {data.get('owner_company') or ''}", styles["h"]),
         Paragraph(f"系統商單位 : {data.get('vendor_fullname') or ''}", styles["h"])],
        [sign_row_cell("業主代表簽名 :", owner_sig), sign_row_cell("系統商代表簽名 :", vendor_sig)],
        [Paragraph(f"簽名日期 : {data.get('owner_sign_date') or ''}", styles["small"]),
         Paragraph(f"簽名日期 : {data.get('vendor_sign_date') or ''}", styles["small"])],
    ], colWidths=[93.5 * mm, 93.5 * mm])
    sign_tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(sign_tbl)
    story.append(Spacer(1, 5 * mm))

    # ---- 設備清單（含流水編號） ----
    story.append(Paragraph(f"設備清單　案場名稱 : {case_label}", styles["h"]))
    story.append(Spacer(1, 2 * mm))
    eq_rows = [[Paragraph(t, styles["cell"]) for t in ["", "設備名稱", "品牌", "型號", "數量", "單位", "備註"]]]
    for i, eq in enumerate(data.get("equipment", []), start=1):
        eq_rows.append([
            Paragraph(str(i), styles["cell"]),
            Paragraph(str(eq.get("name") or ""), styles["cell"]),
            Paragraph(str(eq.get("brand") or ""), styles["cell"]),
            Paragraph(str(eq.get("model") or ""), styles["cell"]),
            Paragraph(str(eq.get("qty") or ""), styles["cell"]),
            Paragraph(str(eq.get("unit") or ""), styles["cell"]),
            Paragraph(str(eq.get("note") or ""), styles["cell"]),
        ])
    eq_tbl = Table(eq_rows, colWidths=[8 * mm, 26 * mm, 26 * mm, 50 * mm, 16 * mm, 16 * mm, 45 * mm], repeatRows=1)
    eq_tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
    ]))
    story.append(eq_tbl)

    doc.build(story)
    return buf.getvalue()


def get_hidden_models():
    """讀取目前所有被隱藏的模組／逆變器型號。
    回傳 (hidden_module_names: set, hidden_inverter_ids: set, hidden_list: list)，
    hidden_list 是給 /api/hidden-models 這支 API 直接組裝回傳用的原始清單
    （含 app_record_id，才能讓前端顯示「恢復」按鈕）。"""
    formula = f"{{類型}}='{HIDDEN_MODEL_TYPE}'"
    recs = app_data_get_all(formula)
    hidden_module_names = set()
    hidden_inverter_ids = set()
    hidden_list = []
    for r in recs:
        f = r["fields"]
        category = f.get("案號或別名")
        value = f.get("內容") or ""
        hidden_list.append({"app_record_id": r["id"], "category": category, "value": value})
        if category == "module":
            hidden_module_names.add(value)
        elif category == "inverter":
            # 逆變器存的是 "record_id::名稱"，比對時只需要 record_id 那一段
            hidden_inverter_ids.add(value.split("::", 1)[0])
    return hidden_module_names, hidden_inverter_ids, hidden_list


def airtable_headers():
    return {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type": "application/json",
    }


def airtable_get_all(api_url, filter_formula, fields):
    """處理 Airtable 分頁，把符合條件的所有記錄抓完（加上安全上限，避免萬一公式寫錯
    導致無止盡分頁）。用 returnFieldsByFieldId=true 讓回傳的 fields 用欄位 ID 當 key。

    2026-08-31 修正：單筆請求的 timeout 從 30 秒拉長到 60 秒。廠商清單擴增到
    12 間、里程碑查詢又多比對了細部協商／台電購售契約兩種類型後，實測發現偶爾
    會遇到單一批次查詢真的需要超過 30 秒才有回應，導致 requests 主動判定逾時、
    整個 refresh_cache() 失敗（連帶讓這一輪所有新資料都不會寫入快取，畫面看起來
    像是「改的東西沒生效」，其實是這一輪整批失敗、沿用了更早、程式碼改版之前
    的舊快取）。拉長逾時上限給 Airtable 更多時間回應，減少誤判逾時的機率。"""
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
        resp = requests.get(api_url, headers=airtable_headers(), params=params, timeout=60)
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
        resp = requests.get(APP_DATA_API_URL, headers=airtable_headers(), params=params, timeout=60)
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
    """2026-09-01 修正：原本用 resp.raise_for_status() 拋出例外，訊息只有
    「422 Client Error: ...」這種通用文字，看不到 Airtable 真正回傳的錯誤內容
    （例如是哪個欄位、什麼原因被拒絕）。改成失敗時直接把 resp.text（Airtable
    原始回應內容）當作例外訊息拋出，這樣 create_note() 等呼叫端的
    except Exception as e 抓到的 str(e) 就會是真正有用的錯誤細節，不用再靠
    使用者一步步用瀏覽器開發者工具去對照猜測。"""
    resp = requests.post(APP_DATA_API_URL, headers=airtable_headers(), json={"fields": fields}, timeout=20)
    if resp.status_code >= 400:
        raise Exception(resp.text)
    return resp.json()


def app_data_update(record_id, fields):
    resp = requests.patch(f"{APP_DATA_API_URL}/{record_id}", headers=airtable_headers(),
                           json={"fields": fields}, timeout=20)
    if resp.status_code >= 400:
        raise Exception(resp.text)
    return resp.json()


def app_data_delete(record_id):
    resp = requests.delete(f"{APP_DATA_API_URL}/{record_id}", headers=airtable_headers(), timeout=20)
    if resp.status_code >= 400:
        raise Exception(resp.text)
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


def _find_field_id_by_name(table_id, field_name):
    """透過 Airtable Meta API，用欄位「名稱」找到對應的欄位 ID（跟 _find_field_schema
    用 ID 找欄位剛好相反）。2026-08-30 新增，給「筆記本」功能查詢「業務」欄位用——
    因為當時不確定這個欄位實際的 field ID，用名稱動態查找可以省去手動去 Airtable
    後台翻找 ID 的步驟；如果 Airtable 上這個欄位不叫這個名字，會找不到、回傳 None，
    呼叫端要能優雅處理（顯示「未設定」而不是整支 API 壞掉）。"""
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
            if field.get("name") == field_name:
                return field.get("id")
    return None


# 2026-08-30 新增：「業務」（負責業務員）欄位的 ID，給「筆記本」功能
# （/api/case-lookup）顯示案件基本資料用。因為一開始不確定這個欄位實際的
# field ID，改成「用名稱動態查一次、記在記憶體快取」的做法——第一次呼叫
# /api/case-lookup 時，會去 Airtable Meta API 找「專案細節」表裡名稱剛好叫
# 「業務」的欄位，找到後把 ID 存起來，之後就不用每次都重新查。如果 Airtable
# 上這個欄位的實際名稱不是「業務」兩個字（例如叫「承辦業務」「業務員」等），
# 這裡會找不到、sales_person 會一律回傳 None，前端會顯示「尚未設定業務欄位」
# 提示，不會讓整支 API 掛掉——之後只要把下面 SALES_FIELD_NAME 改成正確的
# 欄位名稱，或直接把 SALES_FIELD_ID_CACHE["id"] 换成正確的 field ID 常數即可。
SALES_FIELD_NAME = "綠點業務"
SALES_FIELD_ID_CACHE = {"id": None, "resolved": False}


def get_sales_field_id():
    if not SALES_FIELD_ID_CACHE["resolved"]:
        try:
            SALES_FIELD_ID_CACHE["id"] = _find_field_id_by_name(CASE_TABLE_ID, SALES_FIELD_NAME)
            if SALES_FIELD_ID_CACHE["id"] is None:
                print(f"[get_sales_field_id] 在「專案細節」表找不到名稱是「{SALES_FIELD_NAME}」的欄位，"
                      f"「業務」資訊將無法顯示，需要確認 Airtable 實際欄位名稱", flush=True)
        except Exception as e:
            print(f"[get_sales_field_id] 查詢「業務」欄位 ID 失敗：{e}", flush=True)
        SALES_FIELD_ID_CACHE["resolved"] = True
    return SALES_FIELD_ID_CACHE["id"]


# 2026-08-31 新增：「採購-逆變器」表裡的「專案」欄位 ID——這個欄位把每一筆
# 逆變器記錄（一筆＝一顆實體逆變器）連結回「專案細節」表的案件。發現案件表上
# 「逆變器數量」是 rollup（加總所有連結到這個案件的逆變器記錄），不是能直接
# 填數字的欄位；要讓某個案件「有 2 顆 CPSPV6600ETL1」，正確做法是讓 2 筆
# 型號＝CPSPV6600ETL1 的獨立記錄，把各自的「專案」欄位連到這個案件（原本
# 使用者是透過另一個 Airtable Extension，選好案件、型號、數量後，由那支
# script 自動建立對應筆數的新記錄）。這裡比照 SALES_FIELD_ID_CACHE 的做法，
# 用名稱「專案」動態查一次 ID、記在記憶體快取，避免要手動去 Airtable 後台
# 翻找確切的 field ID。
INVERTER_PROJECT_FIELD_NAME = "專案"
INVERTER_PROJECT_FIELD_ID_CACHE = {"id": None, "resolved": False}


def get_inverter_project_field_id():
    if not INVERTER_PROJECT_FIELD_ID_CACHE["resolved"]:
        try:
            INVERTER_PROJECT_FIELD_ID_CACHE["id"] = _find_field_id_by_name(
                INVERTER_TABLE_ID, INVERTER_PROJECT_FIELD_NAME
            )
            if INVERTER_PROJECT_FIELD_ID_CACHE["id"] is None:
                print(f"[get_inverter_project_field_id] 在「採購-逆變器」表找不到名稱是"
                      f"「{INVERTER_PROJECT_FIELD_NAME}」的欄位，新增逆變器數量功能將無法使用，"
                      f"需要確認 Airtable 實際欄位名稱", flush=True)
        except Exception as e:
            print(f"[get_inverter_project_field_id] 查詢「專案」欄位 ID 失敗：{e}", flush=True)
        INVERTER_PROJECT_FIELD_ID_CACHE["resolved"] = True
    return INVERTER_PROJECT_FIELD_ID_CACHE["id"]


# 2026-08-31 追加修正：案件上的「逆變器數量」rollup 實測是加總每一筆連結記錄
# 自己的「數量」欄位（不是單純算連結了幾筆），所以新建立的逆變器記錄如果沒有
# 順便把它自己的「數量」欄位設成 1，這筆記錄雖然連結上了，但因為自己的數量是
# 空值，rollup 加總時不會被計入，案件上顯示的逆變器數量就不會增加——這就是
# 「型號存進去了、但數量沒變」的原因。跟「專案」欄位一樣，用名稱動態查一次 ID。
INVERTER_UNIT_QTY_FIELD_NAME = "數量"
INVERTER_UNIT_QTY_FIELD_ID_CACHE = {"id": None, "resolved": False}


def get_inverter_unit_qty_field_id():
    if not INVERTER_UNIT_QTY_FIELD_ID_CACHE["resolved"]:
        try:
            INVERTER_UNIT_QTY_FIELD_ID_CACHE["id"] = _find_field_id_by_name(
                INVERTER_TABLE_ID, INVERTER_UNIT_QTY_FIELD_NAME
            )
            if INVERTER_UNIT_QTY_FIELD_ID_CACHE["id"] is None:
                print(f"[get_inverter_unit_qty_field_id] 在「採購-逆變器」表找不到名稱是"
                      f"「{INVERTER_UNIT_QTY_FIELD_NAME}」的欄位，新建立的逆變器記錄將不會"
                      f"帶入數量，案件上的逆變器數量 rollup 可能不會正確增加，"
                      f"需要確認 Airtable 實際欄位名稱", flush=True)
        except Exception as e:
            print(f"[get_inverter_unit_qty_field_id] 查詢「數量」欄位 ID 失敗：{e}", flush=True)
        INVERTER_UNIT_QTY_FIELD_ID_CACHE["resolved"] = True
    return INVERTER_UNIT_QTY_FIELD_ID_CACHE["id"]


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
    補齊「歷史紀錄」要顯示的資料。查不到就回傳 None（可能案件被刪除，或 record_id 有誤）。

    2026-08-31 修正：這裡原本呼叫單筆記錄的 GET API 時沒有加
    returnFieldsByFieldId=true，導致回傳的 fields 是用「欄位名稱」當 key，
    但下面全部用欄位 ID（FIELD_CASE_NO 等常數）去讀，兩邊對不起來，實際上
    一直讀不到值（f.get(FIELD_CASE_NO) 會是 None）。這裡補上這個參數，
    修正後歷史紀錄的欄位才會正確顯示；本檔案其他地方的 airtable_get_all()
    批次查詢因為本來就有加這個參數，不受影響。"""
    try:
        resp = requests.get(
            f"{CASE_API_URL}/{case_record_id}",
            headers=airtable_headers(),
            params={"returnFieldsByFieldId": "true"},
            timeout=15,
        )
        if resp.status_code >= 400:
            return None
        f = resp.json().get("fields", {})
    except Exception:
        return None

    module = format_module(f)
    inverter_ids = f.get(FIELD_INVERTER) or []
    inverter_name_map = resolve_inverter_names(inverter_ids)
    inverter = format_inverter(f, inverter_name_map)
    sales_field_id = get_sales_field_id()
    sales_person = f.get(sales_field_id) if sales_field_id else None

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
        "sales_person": sales_person,
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
        # 2026-08-31 新增：廠商清單擴增到 12 間後案件量變多，批次數也跟著變多，
        # 這裡刻意加一個小間隔（Airtable 官方限制每秒 5 次請求，沒有間隔的話
        # 案件量一大很容易連續撞到這個限制被拒絕）。0.25 秒等於每秒最多 4 次，
        # 留一點安全餘裕。
        if batch_no < total_batches:
            time.sleep(0.25)
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
    分批只查『種類是大料出貨時間、進場屋主預約、掛表、細部協商、或台電購售契約』
    的那幾筆——不用管全表其他幾千筆歷史資料。
    回傳 (ship_map, entry_map, meter_map, detail_nego_map, contract_map)，
    key 都是案件的 record_id。

    「掛表日期」是寫在這裡（里程碑記錄），不是案件表（專案細節）上那個同名欄位——
    案件表上的「掛表日期」欄位是唯讀的 lookup/rollup，直接寫入會失敗；
    案件表原本用來篩選案件池的 {FIELD_HANG_METER_DATE}='' 條件，等這裡的里程碑
    實際日期寫入後，Airtable 端會自動連動更新，下次 refresh_cache 案件就會自然
    從排程池消失，不用另外處理。

    2026-08-31 新增細部協商／台電購售契約：因為要查的還是同一批 case_records
    連結到的里程碑 ID（all_ms_ids 本來就是不分種類、整批抓來的），這裡只是在
    type_formula 裡多比對兩種種類，不會多打任何一次 Airtable API，完全不影響
    批次數量／速度。用途是給「掛表安排」頁籤判斷案件「完工了，但這兩份函文
    是不是都已經取得」，還沒取得的話要先歸類到「待函文取得」，不能直接排掛表。"""
    all_ms_ids = set()
    for r in case_records:
        all_ms_ids.update(r["fields"].get(FIELD_MS_LINK_ON_CASE) or [])

    ship_map, entry_map, meter_map = {}, {}, {}
    detail_nego_map, contract_map = {}, {}
    if not all_ms_ids:
        print("[步驟2] 這批案件沒有任何『進度管理』連結 ID，略過", flush=True)
        return ship_map, entry_map, meter_map, detail_nego_map, contract_map

    type_formula = (
        f"OR({{{FIELD_MS_TYPE}}}='{MILESTONE_TYPE_SHIP}',"
        f"{{{FIELD_MS_TYPE}}}='{MILESTONE_TYPE_ENTRY}',"
        f"{{{FIELD_MS_TYPE}}}='{MILESTONE_TYPE_METER}',"
        f"{{{FIELD_MS_TYPE}}}='{MILESTONE_TYPE_DETAIL_NEGO}',"
        f"{{{FIELD_MS_TYPE}}}='{MILESTONE_TYPE_TAIPOWER_CONTRACT}')"
    )
    ids_list = list(all_ms_ids)
    # 2026-08-31 調整：從 80 縮小到 50。廠商清單擴增、比對的種類也從 3 種
    # 增加到 5 種後，同樣 80 筆一批可能會比對出更多符合的里程碑記錄、回傳的
    # 資料量變大，單次查詢時間也跟著變長，更容易撞到 Airtable 端或
    # requests 這邊的逾時。批次縮小可以讓每次查詢更快完成，代價是批次數變多，
    # 但配合前面已經加的批次間隔（0.25 秒），總時間增加有限，換來的是更穩定
    # 不容易逾時。
    batch_size = 50  # Airtable formula/URL 長度有限，分批查
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
                elif ms_type == MILESTONE_TYPE_DETAIL_NEGO:
                    detail_nego_map[cid] = entry
                elif ms_type == MILESTONE_TYPE_TAIPOWER_CONTRACT:
                    contract_map[cid] = entry
        # 2026-08-31 新增：理由同 resolve_inverter_names() 那邊的說明——廠商清單
        # 擴增後批次數變多，加一點間隔避免連續撞到 Airtable 每秒 5 次請求的限制。
        if batch_no < total_batches:
            time.sleep(0.25)
    print(f"[步驟2] 全部完成，ship_map={len(ship_map)} entry_map={len(entry_map)} "
          f"meter_map={len(meter_map)} detail_nego_map={len(detail_nego_map)} "
          f"contract_map={len(contract_map)}", flush=True)
    return ship_map, entry_map, meter_map, detail_nego_map, contract_map


def compute_case_pool():
    """抓一次基礎案件池：進行中 + 同意備案已填 + 掛表日期空 + VENDOR_NAMES 清單裡的廠商。
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
    sales_field_id = get_sales_field_id()
    if sales_field_id:
        fields.append(sales_field_id)
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
    ship_map, entry_map, meter_map, detail_nego_map, contract_map = fetch_milestones_for_case_pool(case_records)

    all_inverter_ids = set()
    for r in case_records:
        all_inverter_ids.update(r["fields"].get(FIELD_INVERTER) or [])
    inverter_name_map = resolve_inverter_names(all_inverter_ids)
    sales_field_id = get_sales_field_id()
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
            "sales_person": f.get(sales_field_id) if sales_field_id else None,
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
            detail_nego_info = detail_nego_map.get(r["id"])
            contract_info = contract_map.get(r["id"])
            completed.append({
                **base,
                "ship_date": ship_info.get("actual_date"),
                "entry_date": entry_info.get("actual_date"),
                "meter_milestone_record_id": meter_info["milestone_record_id"] if meter_info else None,
                # 2026-08-31 新增：給「掛表安排」頁籤判斷「細部協商」「台電購售契約」
                # 這兩份函文是不是都已經取得（都有 actual_date 才算取得）。
                "detail_nego_date": detail_nego_info.get("actual_date") if detail_nego_info else None,
                "contract_date": contract_info.get("actual_date") if contract_info else None,
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
# 2026-08-31 調整：廠商清單從 4 間擴增到 12 間後，案件池變大，單輪刷新
# 需要的時間也會跟著變長（更多案件 → 更多里程碑批次查詢 → 更多 Airtable API
# 呼叫）。門檻拉長到 3 分鐘，避免案件量變多之後，正常但比較久的一輪刷新被
# 誤判成「卡死」而被強制中斷重跑；這個數字仍然安全地小於 gunicorn.conf.py
# 裡 worker 的 --timeout 300 秒設定，不會反過來造成 worker 被砍。
STALE_REFRESH_SECONDS = 180


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
#
# 注意：這段暖機請求留在模組最外層執行沒關係（不涉及背景執行緒/排程），
# gunicorn master process 在 import 時會跑一次、worker fork 之後 import
# 快取已經熱過，不會重複造成問題；即使重複執行也只是多發一次 HTTP 請求，
# 沒有副作用。
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
        # 2026-08-30 新增：「採購-逆變器」表裡存在同名重複記錄（同一型號被建立成
        # 好幾筆獨立的 Airtable 記錄），下拉選單如果整表照列，使用者會看到同一個
        # 型號名稱重複出現好幾次，選哪一筆都分不清楚差異在哪。這裡依名稱去重，
        # 同名只保留第一筆（用哪一筆的 record_id 不影響顯示名稱，寫入時只要
        # record_id 對應得到一筆有效記錄即可）。這只影響「下拉選單顯示」，
        # 不會刪除 Airtable 裡任何重複的原始記錄，既有案件連結的舊 record_id
        # 也完全不受影響。
        seen_names = set()
        deduped_inverter_options = []
        for o in inverter_options:
            if o["name"] in seen_names:
                continue
            seen_names.add(o["name"])
            deduped_inverter_options.append(o)
        inverter_options = deduped_inverter_options
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

    # 2026-08-30 新增：套用隱藏清單，把使用者標記過不想再看到的型號從最終結果濾掉。
    # 這一步刻意放在快取真正寫入之前的最後一步，且失敗時只印 log、不影響其他部分
    # （沿用未過濾的結果），避免因為這個新功能本身的問題連累原本已經在跑的型號快取。
    try:
        hidden_module_names, hidden_inverter_ids, _ = get_hidden_models()
        if hidden_module_names:
            module_options = [m for m in module_options if m not in hidden_module_names]
        if hidden_inverter_ids:
            inverter_options = [o for o in inverter_options if o["record_id"] not in hidden_inverter_ids]
    except Exception as e:
        print(f"{tag} 讀取隱藏型號清單失敗（沿用未過濾的完整清單）：{e}", flush=True)

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
# 注意（2026-08-30 修改十三）：這裡刻意不呼叫 scheduler.start()。
# 實際啟動移到 gunicorn.conf.py 的 post_fork() hook 裡呼叫，確保排程是在
# 真正處理請求的 worker process 裡執行，而不是 gunicorn 的 master process
# （master 裡執行的話，worker 自己的 DATA_CACHE/MODEL_OPTIONS_CACHE 永遠
# 不會被更新，因為兩者是 fork() 之後各自獨立的記憶體空間）。
# 詳細原因見檔案最上方「2026-08-30 修改（十三）」的說明。


def _startup_refresh_all():
    """伺服器啟動時的背景初始化，兩份快取「依序」做，不要同時開兩個執行緒。
    這個專案先前就踩過「多執行緒同時第一次呼叫 requests」會卡死的坑（見上面
    2026-08-28 修改十一的說明跟暖機那段），一次只讓一個背景執行緒去做「第一次」
    網路呼叫比較保險；等之後排程真的觸發時，import 早就熱過了，兩個排程工作
    各自獨立執行就沒有這個風險，不需要也一起依序做。

    注意（2026-08-30 修改十三）：這個函式本身「定義」在這裡沒問題，但「呼叫」
    這個函式的地方，已經從模組最外層移到 gunicorn.conf.py 的 post_fork() hook
    裡（正式部署走 gunicorn 時），以及本檔案最下方 __main__ 區塊（本機開發
    直接 `python app.py` 執行時），確保一定是在真正服務請求的 process 裡執行。"""
    refresh_cache()
    refresh_model_options_cache()
    refresh_survey_cache()


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


@app.route("/api/hidden-models")
def get_hidden_models_api():
    """回傳目前所有被隱藏的型號，給「管理型號清單」視窗顯示「已隱藏」清單、
    讓使用者可以選擇恢復。逆變器型號存的原始格式是 "record_id::名稱"，這裡
    直接拆好只回傳給前端顯示用的名稱，不用前端自己處理格式。"""
    try:
        _, _, hidden_list = get_hidden_models()
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    result = []
    for h in hidden_list:
        if h["category"] == "inverter":
            parts = h["value"].split("::", 1)
            name = parts[1] if len(parts) > 1 else parts[0]
        else:
            name = h["value"]
        result.append({"app_record_id": h["app_record_id"], "category": h["category"], "name": name})
    return jsonify({"hidden": result})


@app.route("/api/hidden-models", methods=["POST"])
def add_hidden_model():
    """把一個模組或逆變器型號加入隱藏清單（軟隱藏，不動 Airtable 原始資料）。
    body: {category: "module" | "inverter", value: string}
    module 的 value 直接是型號名稱；inverter 的 value 必須是 "record_id::名稱"
    這種組合格式（前端呼叫時要自己組好），因為實際比對用的是 record_id，
    名稱只是存起來給畫面顯示用。寫入成功後立刻在背景刷新一次型號快取，
    讓隱藏立刻生效，不用等下一輪排程。"""
    body = request.get_json(force=True)
    category = body.get("category")
    value = (body.get("value") or "").strip()
    if category not in ("module", "inverter"):
        return jsonify({"error": "category 必須是 module 或 inverter"}), 400
    if not value:
        return jsonify({"error": "缺少 value"}), 400
    try:
        app_data_create({
            "類型": HIDDEN_MODEL_TYPE,
            "案號或別名": category,
            "內容": value,
            "記錄日期": datetime.now().strftime("%Y-%m-%d"),
        })
    except Exception as e:
        return jsonify({"error": "Airtable 寫入失敗", "detail": str(e)}), 502
    threading.Thread(target=refresh_model_options_cache, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/hidden-models/<record_id>", methods=["DELETE"])
def remove_hidden_model(record_id):
    """把一筆隱藏記錄刪掉，等於「恢復顯示」這個型號。刪除成功後立刻在背景
    刷新一次型號快取，讓恢復立刻生效。"""
    try:
        app_data_delete(record_id)
    except Exception as e:
        return jsonify({"error": "Airtable 刪除失敗", "detail": str(e)}), 502
    threading.Thread(target=refresh_model_options_cache, daemon=True).start()
    return jsonify({"ok": True})


def _fetch_case_current_inverter_ids(case_record_id):
    """讀取這個案件目前實際連結的逆變器 record_id 清單（直接查案件本身的
    FIELD_INVERTER 欄位，不是查快取），給 sync_inverter_units_for_case() 用來
    比對「這個型號目前已經連了幾筆」。"""
    resp = requests.get(
        f"{CASE_API_URL}/{case_record_id}",
        headers=airtable_headers(),
        params={"returnFieldsByFieldId": "true"},
        timeout=15,
    )
    resp.raise_for_status()
    f = resp.json().get("fields", {})
    return f.get(FIELD_INVERTER) or []


def sync_inverter_units_for_case(case_record_id, desired):
    """把案件的逆變器連結，同步成使用者想要的「型號＋數量」組合。

    背景：案件上的「逆變器數量」是 rollup（加總所有連結到這個案件的逆變器記錄），
    不是能直接填數字的欄位；「採購-逆變器」表裡一筆記錄＝一顆實體逆變器（數量
    固定是 1）。要讓案件「有 2 顆 CPSPV6600ETL1」，正確做法是讓 2 筆型號＝
    CPSPV6600ETL1 的獨立記錄，把「專案」欄位連到這個案件——這裡就是在做這件事：
    比對案件目前已經連結的逆變器記錄（依型號分組），數量不夠的型號就自動新增
    對應筆數的新記錄補齊，數量給的比現有的少（或整個型號被拿掉不要了）則不去
    刪除那些實體記錄本身，只是不再把它們連回這個案件（案件的逆變器數量 rollup
    因此會自動跟著減少）。

    desired: [{"name": 型號名稱, "qty": 想要的總數量}, ...]
    回傳最終應該連到這個案件的完整 record_id 清單（給呼叫端拿去 PATCH 案件的
    FIELD_INVERTER 用）。"""
    existing_ids = _fetch_case_current_inverter_ids(case_record_id)
    existing_name_map = resolve_inverter_names(existing_ids) if existing_ids else {}
    # 依型號把「目前已連結」的 record_id 分組，方便逐一比對夠不夠
    existing_by_name = {}
    for rid in existing_ids:
        name = existing_name_map.get(rid, rid)
        existing_by_name.setdefault(name, []).append(rid)

    project_field_id = get_inverter_project_field_id()
    unit_qty_field_id = get_inverter_unit_qty_field_id()
    final_ids = []
    for item in desired:
        name = (item.get("name") or "").strip()
        qty = item.get("qty")
        if not name or not qty or qty < 1:
            continue
        pool = existing_by_name.get(name, [])
        keep = pool[:qty]
        final_ids.extend(keep)
        shortfall = qty - len(keep)
        for _ in range(shortfall):
            create_fields = {INVERTER_MODEL_FIELD: name}
            if project_field_id:
                create_fields[project_field_id] = [case_record_id]
            if unit_qty_field_id:
                # 案件上的「逆變器數量」是加總每一筆連結記錄自己的「數量」欄位，
                # 不是單純算連結了幾筆，所以新記錄一定要把自己的數量設成 1，
                # 不然雖然連結上了，但因為自己的數量是空值，rollup 不會計入，
                # 案件上看到的逆變器數量就不會增加。
                create_fields[unit_qty_field_id] = 1
            resp = requests.post(
                INVERTER_API_URL,
                headers=airtable_headers(),
                json={"fields": create_fields},
                timeout=20,
            )
            resp.raise_for_status()
            final_ids.append(resp.json()["id"])
    return final_ids


@app.route("/api/case-spec", methods=["POST"])
def update_case_spec():
    """直接在網站上補填/修改案件的模組、逆變器規格，寫回 Airtable「專案細節」表，
    不用再回 Airtable 手動填。模組型號是純文字欄位，可以自由輸入。
    body: {case_record_id, module_model, inverters: [{name, qty}, ...]}
    module_model/inverters 都是選填，只會更新有帶到的欄位；
    inverters 給空陣列代表清空所有逆變器連結。

    2026-08-31 修正：body 裡即使帶了 module_qty，也不會真的寫進 Airtable。
    實測發現 FIELD_MODULE_QTY 對應的「電廠模組片數」欄位在 Airtable 裡其實是
    計算欄位（公式／rollup 算出來的，依系統容量換算），外部一律不能寫入，
    Airtable 會直接拒絕整筆 PATCH（連同一起送的模組型號也會跟著存不進去，
    因為 Airtable 的欄位更新是整包成功或整包失敗）。這裡完全不送這個欄位，
    只更新真正能改的「模組型號」。

    2026-08-31 追加修正：逆變器的處理方式整個改掉了。原本以為 FIELD_INVERTER_QTY
    （「逆變器數量」）可以直接寫入一個數字，但實測它也是計算欄位（rollup，加總
    所有連結到這個案件的逆變器記錄）——「數量」的來源其實是「連結了幾筆逆變器
    記錄」，不是一個獨立可填的數字。所以 inverters 現在改成 {name, qty} 的格式
    （型號名稱＋想要的總數量），實際處理交給 sync_inverter_units_for_case()：
    比對案件目前已連結幾筆該型號、不夠的話自動新增對應筆數的新記錄補齊，這樣
    案件上的逆變器數量 rollup 才會自動變成使用者想要的數字。"""
    body = request.get_json(force=True)
    case_record_id = body.get("case_record_id")
    if not case_record_id:
        return jsonify({"error": "缺少 case_record_id"}), 400

    fields = {}
    if "module_model" in body:
        fields[FIELD_MODULE_MODEL] = (body.get("module_model") or "").strip() or None
    # module_qty 刻意不處理：對應的 Airtable 欄位是計算欄位，寫入必定被拒絕，
    # 詳見上方 2026-08-31 修正說明。

    if "inverters" in body:
        try:
            fields[FIELD_INVERTER] = sync_inverter_units_for_case(case_record_id, body.get("inverters") or [])
        except Exception as e:
            return jsonify({"error": "建立／比對逆變器記錄失敗", "detail": str(e)}), 502

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
    threading.Thread(target=refresh_model_options_cache, daemon=True).start()
    return jsonify({"ok": True, "record": resp.json()})


@app.route("/api/case-search")
def case_search():
    """給前端「筆記本」功能用：模糊搜尋案件，輸入案號、別名（案場常常把屋主姓名
    寫在別名裡）或地址的其中一段關鍵字，就能列出符合的候選案件，讓使用者從清單
    裡點選正確的那一筆，不用打完整、一字不差的案號。只回傳輕量欄位（案號／別名／
    廠商／地址）給清單顯示用，選定之後前端再呼叫 /api/case-lookup（帶
    case_record_id）查詢完整規格跟函文進度，這樣使用者一個字一個字打的時候，
    每次查詢都很輕量、不會卡頓。
    query params:
      - q（至少 1 個字，會同時比對案號／別名／地址，比對不分大小寫）
      - include_certified（選填，隨便給個值即可）：2026-10-01 新增，只有
        「廠商時段協調」的案號搜尋會帶這個參數——額外把業務自治區 A01資訊
        分頁裡 A 欄＝「已公證」、但還沒建進 Airtable 的案件也混進結果（見
        CERTIFIED_CASE_CACHE）。其他呼叫端（電話紀錄筆記本、案件進場安排
        手動新增）故意不帶這個參數，維持原本只查 Airtable 的行為，不要
        把還沒建檔的案件混進那些場景（record_id 是空的，那些地方的後續
        流程都假設一定有 record_id）。"""
    q = (request.args.get("q") or "").strip()
    include_certified = bool(request.args.get("include_certified"))
    if not q:
        return jsonify({"results": []})
    try:
        escaped = q.replace("'", "\\'").replace('"', '\\"')
        formula = (
            f"OR("
            f"FIND(LOWER('{escaped}'),LOWER({{{FIELD_CASE_NO}}}))>0,"
            f"FIND(LOWER('{escaped}'),LOWER({{{FIELD_ALIAS}}}))>0,"
            f"FIND(LOWER('{escaped}'),LOWER({{{FIELD_ADDRESS}}}))>0"
            f")"
        )
        resp = requests.get(
            CASE_API_URL,
            headers=airtable_headers(),
            params={
                "filterByFormula": formula,
                "fields[]": [FIELD_CASE_NO, FIELD_ALIAS, FIELD_VENDOR, FIELD_ADDRESS],
                "maxRecords": 8,  # 只是打字時的候選清單，不需要撈全部符合的筆數
                "returnFieldsByFieldId": "true",
            },
            timeout=15,
        )
        resp.raise_for_status()
        records = resp.json().get("records", [])
        results = []
        for r in records:
            f = r["fields"]
            results.append({
                "record_id": r["id"],
                "case": f.get(FIELD_CASE_NO, ""),
                "alias": f.get(FIELD_ALIAS, ""),
                "vendor": f.get(FIELD_VENDOR, ""),
                "address": f.get(FIELD_ADDRESS, ""),
            })
        if include_certified:
            seen_cases = {r["case"] for r in results}
            q_lower = q.lower()
            for c in CERTIFIED_CASE_CACHE.get("cases", []):
                case_no = c.get("case", "")
                if not case_no or case_no in seen_cases:
                    continue
                alias = c.get("alias") or ""
                vendor = c.get("vendor") or ""
                if q_lower in case_no.lower() or q_lower in vendor.lower() or q_lower in alias.lower():
                    results.append({
                        "record_id": "",
                        "case": case_no,
                        "alias": alias,
                        "vendor": vendor,
                        "address": "",
                        "sales_person": c.get("sales_person") or "",
                        "not_in_airtable": True,
                    })
            results = results[:8]
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/case-lookup")
def case_lookup():
    """給前端「筆記本」功能用：查詢單一案件的完整基本資料（案號／別名／廠商／
    地址／模組／逆變器／業務）跟關鍵進度日期（併聯審查／同意備案／細部協商／
    台電購售契約／免雜）。即時查 Airtable，不走整批快取（跟 /api/milestone-status
    一樣，只有使用者主動查詢時才會用到，不需要整批處理）。
    query params（擇一提供即可，優先用 case_record_id）：
      - case_record_id：使用者從 /api/case-search 的候選清單裡點選後，直接帶
        record_id 查，最準確也最快（不用另外打公式比對）。
      - case_no：完整案號，需完全相符（保留給還沒有 record_id 的呼叫端用，
        例如舊版前端或其他直接輸入完整案號的情境）。"""
    case_record_id = (request.args.get("case_record_id") or "").strip()
    case_no = (request.args.get("case_no") or "").strip()
    if not case_record_id and not case_no:
        return jsonify({"error": "缺少 case_record_id 或 case_no"}), 400
    try:
        sales_field_id = get_sales_field_id()

        if case_record_id:
            resp = requests.get(
                f"{CASE_API_URL}/{case_record_id}",
                headers=airtable_headers(),
                params={"returnFieldsByFieldId": "true"},
                timeout=15,
            )
            if resp.status_code >= 400:
                return jsonify({"found": False})
            f = resp.json().get("fields", {})
            record_id = case_record_id
        else:
            escaped = case_no.replace("'", "\\'")
            formula = f"{{{FIELD_CASE_NO}}}='{escaped}'"
            fields = [FIELD_CASE_NO, FIELD_ALIAS, FIELD_VENDOR, FIELD_ADDRESS,
                      FIELD_MODULE_MODEL, FIELD_MODULE_QTY, FIELD_INVERTER, FIELD_INVERTER_QTY,
                      FIELD_MS_LINK_ON_CASE]
            if sales_field_id:
                fields.append(sales_field_id)
            records = airtable_get_all(CASE_API_URL, formula, fields)
            if not records:
                return jsonify({"found": False})
            f = records[0]["fields"]
            record_id = records[0]["id"]

        module = format_module(f)
        inverter_ids = f.get(FIELD_INVERTER) or []
        inverter_name_map = resolve_inverter_names(inverter_ids)
        inverter = format_inverter(f, inverter_name_map)
        sales_person = f.get(sales_field_id) if sales_field_id else None

        ms_ids = f.get(FIELD_MS_LINK_ON_CASE) or []
        milestones = {t: None for t in NOTEBOOK_MILESTONE_TYPES}
        if ms_ids:
            id_formula = "OR(" + ",".join(f"RECORD_ID()='{mid}'" for mid in ms_ids) + ")"
            type_formula = "OR(" + ",".join(
                f"{{{FIELD_MS_TYPE}}}='{t}'" for t in NOTEBOOK_MILESTONE_TYPES
            ) + ")"
            ms_formula = f"AND({id_formula},{type_formula})"
            ms_records = airtable_get_all(MILESTONE_API_URL, ms_formula, [FIELD_MS_TYPE, FIELD_MS_ACTUAL_DATE])
            for mr in ms_records:
                mf = mr["fields"]
                mtype = mf.get(FIELD_MS_TYPE)
                if mtype in milestones:
                    milestones[mtype] = mf.get(FIELD_MS_ACTUAL_DATE)

        return jsonify({
            "found": True,
            "record_id": record_id,
            "case": f.get(FIELD_CASE_NO, ""),
            "alias": f.get(FIELD_ALIAS, ""),
            "vendor": f.get(FIELD_VENDOR, ""),
            "address": f.get(FIELD_ADDRESS, ""),
            "module": module,
            "inverter": inverter,
            "sales_person": sales_person,
            "sales_field_configured": sales_field_id is not None,
            "milestones": milestones,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 502


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
        # 2026-09-30 修正：這裡原本沒帶 returnFieldsByFieldId=true，但 FIELD_MS_LINK_ON_CASE
        # 是欄位 ID（fldEs9vLzY416tTHo）不是欄位名稱，導致 f.get(FIELD_MS_LINK_ON_CASE) 永遠
        # 抓不到值（Airtable 預設用欄位顯示名稱當 key），ms_ids 永遠是空陣列，這支 API 對任何
        # 案件、任何函文類型都會回傳 found_milestone:false，「異常案件」的「待取得函文」自動
        # 偵測功能實際上從來沒有真的生效過。加上這個參數後，讀 fields 才會用跟其他函式
        # （例如 case_lookup()）一致的欄位 ID 當 key。
        resp = requests.get(
            f"{CASE_API_URL}/{case_record_id}", headers=airtable_headers(),
            params={"returnFieldsByFieldId": "true"}, timeout=15,
        )
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


SURVEY_CACHE = {
    "cases": [],
    "excluded_count": 0,
    "updated_at": None,
    "refreshing": False,
    "refreshing_started_at": None,
    "refreshing_run_id": None,
    "last_error": None,
}
_survey_cache_lock = threading.Lock()


def _compute_survey_cases():
    """實際去兩個 Airtable base 查詢、算出「場勘安排」清單，是 refresh_survey_cache()
    真正做事的部分。拆成獨立函式方便測試，也讓 refresh_survey_cache() 專心處理
    快取狀態（跟 compute_pending_and_entry() / refresh_cache() 的分工方式一樣）。
    條件：
      1. 案件提供日有值（代表已經確定由哪間 EPC 承接這個案子）
      2. 實際場勘日空白（代表 EPC 還沒去場勘）
    這兩個條件單獨用，會混進一批很久以前、根本沒在用這個流程節點的舊案件
    （已經撤案/完工/走到後面階段，只是「實際場勘日」欄位本來就沒人回頭填過——
    2026-10-01 實測：單用這兩個條件有 69 筆，但有 22 筆「進度」其實已經是
    Fail／完成／送件進行中等等跟場勘無關的狀態）。使用者確認的排除規則：
      3. 這個案號在陽光管理主控台原本的 base（appj1wnO3WnRtIEvg）「進度管理」
         表裡，「併聯審查」這個里程碑如果已經有送件日期或取得日期，代表案件
         早就過了場勘階段，要排除（不管這邊的實際場勘日有沒有填）。
      4. 這個案號在業務自治區 Google 試算表「取消案件」或「A01資訊」頁籤裡，
         如果 A 欄已經標記「取消」，代表案件已經撤案，要排除——這是因為
         有些撤案案件工務組沒有回頭在 Table 1 更新狀態，只單用前三個條件
         會把這些早就撤案、但案件提供日停在很久以前的案件也列進來（使用者
         截圖回報：「等幾百天」的紅字案件其實都已經撤案）。這份清單是試算表
         那邊 Apps Script 定期主動推過來的（見 CANCELLED_CASE_CACHE／
         /api/site-survey-cancelled-sync），這裡直接讀快取，不是現查。
      5. Table 1 自己的「進度」欄位＝Fail 的也要排除（2026-10-01 使用者
         截圖回報：用上面 1~4 的規則後，畫面上還是有一些「進度」已經是
         Fail 的案件沒被擋到——這些是從頭到尾都沒進到併聯審查、也不在
         業務自治區撤案清單裡的案件，只能直接看 Table 1 自己的進度欄位）。
         直接寫進 Airtable filterByFormula，由 Airtable 端篩選掉，不用
         另外查。"""
    survey_fields = [
        SURVEY_FIELD_ALIAS, SURVEY_FIELD_CASE_NO, SURVEY_FIELD_ADDRESS,
        SURVEY_FIELD_VENDOR, SURVEY_FIELD_SALES, SURVEY_FIELD_PROVIDED_DATE,
        SURVEY_FIELD_PLANNED_DATE, SURVEY_FIELD_EXCEPTION,
    ]
    candidate_formula = (
        f"AND(NOT({{{SURVEY_FIELD_PROVIDED_DATE}}}=BLANK()),"
        f"{{{SURVEY_FIELD_ACTUAL_DATE}}}=BLANK(),"
        f"{{{SURVEY_FIELD_PROGRESS}}}!='Fail')"
    )
    candidates = airtable_get_all(SURVEY_API_URL, candidate_formula, survey_fields)
    if not candidates:
        return [], 0

    # 併聯審查「送件時間」或「完成日期」只要有一個有值，就代表已經過了場勘階段
    rejoin_formula = (
        f"AND({{{FIELD_MS_TYPE}}}='併聯審查',"
        f"OR(NOT({{{FIELD_MS_SUBMIT_DATE}}}=BLANK()),NOT({{{FIELD_MS_ACTUAL_DATE}}}=BLANK())))"
    )
    rejoin_records = airtable_get_all(MILESTONE_API_URL, rejoin_formula, [FIELD_MS_PROJECT_NAME])
    excluded_case_nos = {
        r["fields"].get(FIELD_MS_PROJECT_NAME)
        for r in rejoin_records
        if r["fields"].get(FIELD_MS_PROJECT_NAME)
    }

    # 不用現查，直接讀 Apps Script 推過來的快取（還沒收到過推送時就是空集合，
    # 等同「這輪不排除任何撤案案件」，不會讓這支函式整個失敗）。
    cancelled_case_nos = CANCELLED_CASE_CACHE["case_nos"]

    cases = []
    for r in candidates:
        f = r["fields"]
        case_no = f.get(SURVEY_FIELD_CASE_NO, "")
        if case_no and case_no in excluded_case_nos:
            continue
        if case_no and case_no in cancelled_case_nos:
            continue
        cases.append({
            "record_id": r["id"],
            "alias": f.get(SURVEY_FIELD_ALIAS, ""),
            "case": case_no,
            "address": f.get(SURVEY_FIELD_ADDRESS, ""),
            # singleSelect 欄位透過 REST API（不是 MCP 工具）查詢時，值直接就是
            # 選項文字本身，不是物件，不用再額外 .get("name")。
            "vendor": f.get(SURVEY_FIELD_VENDOR),
            "sales_person": f.get(SURVEY_FIELD_SALES),
            "provided_date": f.get(SURVEY_FIELD_PROVIDED_DATE),
            "planned_date": f.get(SURVEY_FIELD_PLANNED_DATE),
            "exception": bool(f.get(SURVEY_FIELD_EXCEPTION)),
        })
    cases.sort(key=lambda c: c.get("provided_date") or "")
    return cases, len(candidates) - len(cases)


def refresh_survey_cache():
    """2026-10-01 新增：原本 /api/site-survey-pending 是每次有人打開頁面就「現場」
    查兩個 Airtable base（一次候選案件查詢 + 一次要掃好幾百筆的併聯審查排除查詢），
    使用者反饋每次進頁面都要等～10 秒。改成跟 refresh_cache()（出貨/進場/已完工
    那份快取）一樣的「背景排程 + 記憶體快取」模式：這支函式才會真的去查 Airtable，
    API 本身只讀記憶體、瞬間回應。"""
    run_id = uuid.uuid4().hex[:8]
    now = datetime.now()
    tag = f"[refresh_survey_cache #{run_id}]"

    with _survey_cache_lock:
        if SURVEY_CACHE["refreshing"]:
            started = SURVEY_CACHE.get("refreshing_started_at")
            age = (now - started).total_seconds() if started else None
            if age is not None and age < STALE_REFRESH_SECONDS:
                print(f"{tag} 已有其他更新在進行中，略過本次觸發", flush=True)
                return
            print(f"{tag} 偵測到上一輪疑似卡死，強制重新開始", flush=True)
        SURVEY_CACHE["refreshing"] = True
        SURVEY_CACHE["refreshing_started_at"] = now
        SURVEY_CACHE["refreshing_run_id"] = run_id

    print(f"{tag} 開始…", flush=True)
    try:
        cases, excluded_count = _compute_survey_cases()
        SURVEY_CACHE["cases"] = cases
        SURVEY_CACHE["excluded_count"] = excluded_count
        SURVEY_CACHE["updated_at"] = datetime.now().isoformat()
        SURVEY_CACHE["last_error"] = None
        elapsed = (datetime.now() - now).total_seconds()
        print(f"{tag} 完成，cases={len(cases)} excluded={excluded_count}，耗時 {elapsed:.1f} 秒", flush=True)
    except Exception as e:
        SURVEY_CACHE["last_error"] = str(e)
        print(f"{tag} 失敗：{e}", flush=True)
    finally:
        with _survey_cache_lock:
            if SURVEY_CACHE.get("refreshing_run_id") == run_id:
                SURVEY_CACHE["refreshing"] = False
                SURVEY_CACHE["refreshing_started_at"] = None
                SURVEY_CACHE["refreshing_run_id"] = None


@app.route("/api/site-survey-pending")
def site_survey_pending():
    """「EPC 出貨／進場排程 → 場勘安排」頁用：列出需要安排場勘的案件。只讀記憶體
    快取（SURVEY_CACHE），瞬間回應——真正查 Airtable 的邏輯在 refresh_survey_cache()，
    由排程（每 20 分鐘，見 scheduler.add_job）跟手動重新整理（POST 這支 API 的
    /refresh）觸發，不會卡在這支 API 裡。"""
    if SURVEY_CACHE["updated_at"] is None and not SURVEY_CACHE["refreshing"] and not SURVEY_CACHE["last_error"]:
        # 伺服器剛啟動、_startup_refresh_all() 還沒跑到這份快取時，順手在背景觸發一次，
        # 不然要等到下一個 20 分鐘整點才有資料。
        threading.Thread(target=refresh_survey_cache, daemon=True).start()
    return jsonify({
        "cases": SURVEY_CACHE["cases"],
        "excluded_count": SURVEY_CACHE["excluded_count"],
        "updated_at": SURVEY_CACHE["updated_at"],
        "refreshing": SURVEY_CACHE["refreshing"],
        "last_error": SURVEY_CACHE["last_error"],
    })


@app.route("/api/site-survey-pending/refresh", methods=["POST"])
def refresh_site_survey_pending():
    """手動觸發「場勘安排」資料重新整理，背景執行、立刻回應（跟 /api/refresh 的
    手動更新按鈕是同一種模式），前端按「🔄 重新整理」時呼叫這支，再輪詢
    /api/site-survey-pending 的 updated_at 有沒有變化。"""
    threading.Thread(target=refresh_survey_cache, daemon=True).start()
    return jsonify({"ok": True, "message": "已在背景開始重新整理"})


@app.route("/api/site-survey-pending/<record_id>", methods=["POST"])
def update_site_survey_case(record_id):
    """「場勘安排」頁用：填寫/修改單一案件的「預計場勘日」，以及切換「場勘異常」
    勾選（勾選後隔天的自動回填排程會跳過這筆）。直接寫回另一個 Airtable base
    （SURVEY_BASE_ID）的 Table 1，不經過 APP資料 表——跟這頁其他表格不同，
    這份資料本來就不是陽光管理主控台原本那個 base 的案件，沒有案件 RecordID
    可以對應，record_id 這裡指的就是 SURVEY_BASE_ID 這個 base 裡的記錄 id。
    body: {planned_date: "YYYY-MM-DD" 或 null（選填）, exception: true/false（選填）}
    兩個都是選填，只會更新有帶的欄位。寫入成功後順手同步更新 SURVEY_CACHE 裡
    對應那一筆，這樣不用等下一輪排程，其他人下一次打開頁面就能看到最新值。"""
    body = request.get_json(force=True)
    fields = {}
    if "planned_date" in body:
        fields[SURVEY_FIELD_PLANNED_DATE] = body.get("planned_date") or None
    if "exception" in body:
        fields[SURVEY_FIELD_EXCEPTION] = bool(body.get("exception"))
    if not fields:
        return jsonify({"error": "缺少 planned_date 或 exception"}), 400
    try:
        resp = requests.patch(
            f"{SURVEY_API_URL}/{record_id}", headers=airtable_headers(),
            json={"fields": fields}, timeout=20,
        )
        if resp.status_code >= 400:
            return jsonify({"error": "Airtable 寫入失敗", "detail": resp.text}), 502
        for c in SURVEY_CACHE["cases"]:
            if c["record_id"] == record_id:
                if "planned_date" in body:
                    c["planned_date"] = body.get("planned_date") or None
                if "exception" in body:
                    c["exception"] = bool(body.get("exception"))
                break
        return jsonify({"ok": True, "record": resp.json()})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


def auto_fill_survey_actual_dates():
    """每天固定時間自動執行（排程見 scheduler.add_job）：「預計場勘日」已經是
    過去的日期、「實際場勘日」還空白、而且沒有勾選「場勘異常」的案件，視為
    「場勘當天如期完成、沒人回報異常」，自動把實際場勘日寫成預計場勘日。
    使用者確認的規則：日期有調整就直接改預計場勘日（本來就只處理「日期已過」
    的案件，改成未來日期自然不會被這裡處理到）；有異常但先不改日期的，要手動
    勾選「場勘異常」，這裡會跳過。失敗只印 log，不拋出例外——排程本身不能因為
    這個失敗就整個掛掉，之後排程換下一輪、或使用者手動在畫面上處理都還有
    機會補救。"""
    try:
        formula = (
            f"AND(NOT({{{SURVEY_FIELD_PLANNED_DATE}}}=BLANK()),"
            f"{{{SURVEY_FIELD_ACTUAL_DATE}}}=BLANK(),"
            f"{{{SURVEY_FIELD_PLANNED_DATE}}}<TODAY(),"
            f"NOT({{{SURVEY_FIELD_EXCEPTION}}}))"
        )
        records = airtable_get_all(
            SURVEY_API_URL, formula, [SURVEY_FIELD_CASE_NO, SURVEY_FIELD_PLANNED_DATE]
        )
    except Exception as e:
        print(f"[auto_fill_survey_actual_dates] 查詢失敗：{e}", flush=True)
        return
    ok_count, fail_count = 0, 0
    for r in records:
        planned = r["fields"].get(SURVEY_FIELD_PLANNED_DATE)
        if not planned:
            continue
        try:
            resp = requests.patch(
                f"{SURVEY_API_URL}/{r['id']}", headers=airtable_headers(),
                json={"fields": {SURVEY_FIELD_ACTUAL_DATE: planned}}, timeout=20,
            )
            if resp.status_code >= 400:
                fail_count += 1
                print(f"[auto_fill_survey_actual_dates] {r['id']} 寫入失敗：{resp.text}", flush=True)
            else:
                ok_count += 1
        except Exception as e:
            fail_count += 1
            print(f"[auto_fill_survey_actual_dates] {r['id']} 寫入例外：{e}", flush=True)
    print(f"[auto_fill_survey_actual_dates] 完成，成功 {ok_count} 筆、失敗 {fail_count} 筆", flush=True)


# 排到每天早上 7:30（Asia/Taipei，跟 scheduler 建立時設定的時區一致）執行。
# 這支函式定義在 scheduler 物件建立（第 1616 行附近）之後，所以沒有跟
# refresh_cache／refresh_model_options_cache 那兩個排程放在一起註冊，但
# add_job() 只是把工作登記進 scheduler 的 job store，呼叫的時間點不影響
# 排程本身何時真正執行（實際啟動是 gunicorn.conf.py 的 post_fork 裡呼叫
# scheduler.start()，那時候這裡一定已經執行完畢、job 已經登記好了）。
scheduler.add_job(auto_fill_survey_actual_dates, CronTrigger(hour=7, minute=30))
# 「場勘安排」快取每 20 分鐘重新整理一次（0,20,40 分），比出貨/進場那份快取
# （每 6 小時）頻繁，因為這份資料使用者會常態性打開查看、填寫預計場勘日；
# 但也不像出貨/進場那份有 6 秒一次的前端背景同步，避免兩個 base 一起查太頻繁。
scheduler.add_job(refresh_survey_cache, CronTrigger(minute="0,20,40"))


# ===================================================================
# LINE 回覆期限提醒（2026-10-05）
# 業務在「回覆期限」前 LINE_REMINDER_LEAD_MIN 分鐘（預設 60）還沒完成安排，
# 就用 LINE 官方帳號（Messaging API）推播到指定群組/個人。需在 Render 設定環境變數：
#   LINE_CHANNEL_ACCESS_TOKEN  官方帳號的 Channel access token（長期）
#   LINE_REMINDER_TARGET_ID    要推播的 groupId（C 開頭）或 userId（U 開頭）
#   DASHBOARD_BASE_URL         （選填）前端網址，例如 https://xxx.github.io/epc-dashboard，用來附業務填單連結
# 兩個必要變數沒設就整個功能休眠、不影響其他功能。
# 「已提醒」checkbox 欄位避免重複提醒（重新部署也不會重發）。
# ===================================================================
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def _line_config():
    return (
        os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip(),
        os.environ.get("LINE_REMINDER_TARGET_ID", "").strip(),
    )


def _line_push_text(text, to=None):
    token, default_target = _line_config()
    target = to or default_target
    if not token or not target:
        return False, "LINE 環境變數未設定"
    resp = requests.post(
        LINE_PUSH_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"to": target, "messages": [{"type": "text", "text": text}]},
        timeout=15,
    )
    if resp.status_code >= 400:
        return False, f"{resp.status_code} {resp.text}"
    return True, ""


def send_deadline_reminders():
    token, target = _line_config()
    if not token:
        return
    try:
        lead_min = int(os.environ.get("LINE_REMINDER_LEAD_MIN", "60"))
    except ValueError:
        lead_min = 60
    try:
        records = airtable_get_all(
            TASK_API_URL, "TRUE()", _task_fields() + [FIELD_TASK_REMINDED]
        )
    except Exception as e:
        print(f"[send_deadline_reminders] 讀取任務失敗：{e}", flush=True)
        return
    now = datetime.now(timezone.utc)
    base_url = os.environ.get("DASHBOARD_BASE_URL", "").strip().rstrip("/")
    for r in records:
        f = r["fields"]
        if f.get(FIELD_TASK_REMINDED):
            continue
        if f.get(FIELD_TASK_STATUS, TASK_STATUS_PENDING) != TASK_STATUS_PENDING:
            continue
        # 待窗口確認＝業務已經回傳備選時段，球在窗口手上，不用催業務
        if f.get(FIELD_TASK_STAGE) == TASK_STAGE_WAIT_PM:
            continue
        raw = f.get(FIELD_TASK_DEADLINE)
        if not raw:
            continue
        try:
            dl = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if dl.tzinfo is None:
                dl = dl.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        remain_min = (dl - now).total_seconds() / 60
        # 只提醒「剩餘時間已進入提醒區間、且還沒過期」的任務
        if remain_min > lead_min or remain_min < 0:
            continue
        local = dl.astimezone(timezone(timedelta(hours=8)))
        who = f.get(FIELD_TASK_ASSIGNEE) or "業務"
        case_no = f.get(FIELD_TASK_CASE_NO, "")
        alias = f.get(FIELD_TASK_ALIAS, "")
        types = "、".join(f.get(FIELD_TASK_TYPE) or [])
        lines = [
            f"⏰ {who} 您好，{case_no} {alias}".rstrip(),
            f"{types}時段還沒確認，回覆期限 {local.strftime('%H:%M')}，剩約 {max(1, round(remain_min))} 分鐘。",
        ]
        if f.get(FIELD_TASK_STAGE) == TASK_STAGE_WAIT_REP:
            lines.append("窗口已選好時段，請進表單按「確認」。")
        if base_url and f.get(FIELD_TASK_TOKEN):
            lines.append(f"{base_url}/book.html?token={f[FIELD_TASK_TOKEN]}")
        rep_uid = None
        if f.get(FIELD_TASK_ASSIGNEE):
            try:
                rep_uid = _get_line_binding(f[FIELD_TASK_ASSIGNEE])
            except Exception as e:
                print(f"[send_deadline_reminders] 查綁定失敗：{e}", flush=True)
        rep_ok = False
        if rep_uid:
            rep_ok, err = _line_push_text("\n".join(lines), to=rep_uid)
            if not rep_ok:
                print(f"[send_deadline_reminders] {case_no} 推播給業務失敗：{err}", flush=True)
        # 同時通知「安排人員」（建立任務的人）：期限快到、還沒安排完成＋目前狀態
        stage = f.get(FIELD_TASK_STAGE) or ""
        stage_text = {
            TASK_STAGE_WAIT_REP: "已選好時間，等業務按確認",
        }.get(stage, "業務還沒安排")
        creator = (f.get(FIELD_TASK_CREATOR) or "").strip()
        sched_ok = False
        if creator:
            sched_ok = _notify_scheduler(
                creator,
                f"⏰ 回覆期限 {local.strftime('%H:%M')} 快到了（剩約 {max(1, round(remain_min))} 分鐘）\n"
                f"{case_no} {alias}\n{types}｜指派：{who}\n目前狀態：{stage_text}",
            )
        ok = rep_ok or sched_ok
        if not ok:
            # 業務、安排人員都沒綁定（或推播失敗）→ 轉給預設對象，不要讓提醒默默消失
            if not target:
                continue
            lines.insert(0, f"（{who} 尚未綁定 LINE 或推播失敗，轉給你代為提醒）")
            ok, err = _line_push_text("\n".join(lines))
            if not ok:
                print(f"[send_deadline_reminders] {case_no} 推播失敗：{err}", flush=True)
                continue
        try:
            _patch_task(r["id"], {FIELD_TASK_REMINDED: True})
        except Exception as e:
            print(f"[send_deadline_reminders] {case_no} 標記已提醒失敗：{e}", flush=True)


scheduler.add_job(send_deadline_reminders, CronTrigger(minute="*/5"))


def _list_scheduler_names():
    recs = airtable_get_all(LINE_BIND_API_URL, f"{{{FIELD_BIND_SCHEDULER}}}=TRUE()", [FIELD_BIND_NAME])
    return sorted({(r["fields"].get(FIELD_BIND_NAME) or "").strip() for r in recs} - {""})


def _scheduler_summary(creator):
    """這位安排人員名下任務的目前狀況，附在每則通知後面。"""
    esc = creator.replace("\\", "\\\\").replace("'", "\\'")
    recs = airtable_get_all(TASK_API_URL, f"{{{FIELD_TASK_CREATOR}}}='{esc}'", [FIELD_TASK_STATUS, FIELD_TASK_STAGE])
    wait_rep = wait_pm = wait_confirm = done = 0
    for r in recs:
        f = r["fields"]
        if f.get(FIELD_TASK_STATUS) == TASK_STATUS_DONE:
            done += 1
        elif f.get(FIELD_TASK_STAGE) == TASK_STAGE_WAIT_PM:
            wait_pm += 1
        elif f.get(FIELD_TASK_STAGE) == TASK_STAGE_WAIT_REP:
            wait_confirm += 1
        else:
            wait_rep += 1
    return (
        f"📊 你名下的任務：待業務安排 {wait_rep}、待你選時間 {wait_pm}、"
        f"待業務確認 {wait_confirm}、已完成 {done}"
    )


def _notify_scheduler(creator, headline):
    """推播給安排人員（用名字對應「業務LINE綁定」表）。沒綁定回 False。"""
    creator = (creator or "").strip()
    token, _ = _line_config()
    if not token or not creator:
        return False
    try:
        uid = _get_line_binding(creator)
        if not uid:
            return False
        text = headline
        try:
            text += "\n\n" + _scheduler_summary(creator)
        except Exception as e:
            print(f"[_notify_scheduler] 組狀態摘要失敗：{e}", flush=True)
        ok, err = _line_push_text(text, to=uid)
        if not ok:
            print(f"[_notify_scheduler] 推播給 {creator} 失敗：{err}", flush=True)
        return ok
    except Exception as e:
        print(f"[_notify_scheduler] 例外：{e}", flush=True)
        return False


def _notify_scheduler_async(creator, headline):
    """在背景執行，不拖慢業務按「完成預約」的回應。"""
    threading.Thread(target=_notify_scheduler, args=(creator, headline), daemon=True).start()


@app.route("/api/line/liff-config")
def line_liff_config():
    return jsonify({
        "liff_id": os.environ.get("LIFF_ID", "").strip(),
        "add_friend_url": os.environ.get("LINE_ADD_FRIEND_URL", "").strip(),
    })


@app.route("/api/line/schedulers")
def line_schedulers():
    """已綁定 LINE 的安排人員名單（只回名字），給「指派給業務」視窗的安排人員下拉用。"""
    try:
        return jsonify({"names": _list_scheduler_names()})
    except Exception as e:
        return jsonify({"error": str(e), "names": []}), 502


@app.route("/api/line/bind-scheduler", methods=["POST"])
def line_bind_scheduler():
    """安排人員在 book.html?bind=scheduler 輸入自己的名字、用 LINE 登入後呼叫。
    跟業務綁定一樣用 access token 向 LINE 驗證 userId，寫進「業務LINE綁定」表並勾「安排人員」。
    body: {access_token, name}"""
    body = request.get_json(force=True) or {}
    access_token = (body.get("access_token") or "").strip()
    name = (body.get("name") or "").strip()
    if not access_token or not name:
        return jsonify({"error": "缺少名字或 LINE 登入資訊"}), 400
    try:
        prof = requests.get("https://api.line.me/v2/profile",
                            headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
        if prof.status_code >= 400:
            return jsonify({"error": "LINE 驗證失敗，請重新開啟連結再試一次"}), 400
        pj = prof.json()
        user_id, display = pj.get("userId", ""), pj.get("displayName", "")
        if not user_id:
            return jsonify({"error": "LINE 驗證失敗"}), 400
        fields = {FIELD_BIND_NAME: name, FIELD_BIND_UID: user_id, FIELD_BIND_DISPLAY: display,
                  FIELD_BIND_SCHEDULER: True}
        existing = _find_line_binding_record(name)
        if existing:
            resp = requests.patch(f"{LINE_BIND_API_URL}/{existing['id']}", headers=airtable_headers(),
                                  json={"fields": fields}, timeout=20)
        else:
            resp = requests.post(LINE_BIND_API_URL, headers=airtable_headers(),
                                 json={"fields": fields}, timeout=20)
        if resp.status_code >= 400:
            return jsonify({"error": "寫入失敗", "detail": resp.text}), 502
        return jsonify({"ok": True, "display_name": display, "name": name})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.route("/api/line/status")
def line_status():
    """只回報 LINE 提醒設定是否到位（不回傳 token / ID 內容）。"""
    token, target = _line_config()
    return jsonify({
        "token_set": bool(token),
        "target_set": bool(target),
        "target_kind": {"C": "group", "R": "room", "U": "user"}.get(target[:1], "unknown") if target else None,
    })


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
                # 2026-09-01 新增：讓「未使用料件」清單可以直接顯示廠商，不用每次
                # 都靠即時比對現有案件才能查到（撤案的案件之後可能查不到了）。
                # 讀取這個欄位失敗（Airtable 還沒新增「廠商」這個欄位）時，
                # f.get() 單純回傳 None，不會讓整支 API 掛掉。
                "vendor": f.get("廠商"),
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

    # 2026-09-08 新增：「掛表安排」頁設定/修改「預計掛表日期」時，同步讓這個
    # 案件出現在「維運團隊」模組。背景執行緒處理，不拖慢這支 API 原本的回應速度，
    # 失敗也不影響「設定預計掛表日期」這個主要動作本身有沒有成功。
    if "meter_planned_date" in patch and patch.get("meter_planned_date"):
        threading.Thread(
            target=sync_ops_case_on_meter_planned,
            args=(case_record_id, case_no, patch["meter_planned_date"]),
            daemon=True,
        ).start()

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
    """新增一筆註記清單項目（併聯取得時備貨／其他狀況備住／未使用料件／料件使用／電話紀錄）。
    body: {type, case_text, content, ship_date, vendor}
    ship_date 是選填欄位，目前只有「未使用料件」會用到（記錄這批料件原本的出貨日期）。
    vendor 也是選填（2026-09-01 新增），目前只有「未使用料件」會用到，記錄這批
    料件實際放在哪個廠商的倉庫，不用每次都靠案號去即時比對現有案件（案件如果
    後來被撤案、狀態變動，即時比對可能會找不到，直接存廠商文字比較穩定）。
    注意：這需要 Airtable「APP資料」表已經手動新增一個叫「廠商」的欄位，
    不然 Airtable 會直接回傳 UNKNOWN_FIELD_NAME 錯誤，導致整筆寫入失敗
    （不只「未使用料件」，其他類型如果不小心也帶了 vendor 一樣會失敗，所以
    前端只在新增「未使用料件」時才會帶這個欄位）。"""
    body = request.get_json(force=True)
    note_type = body.get("type")
    case_text = (body.get("case_text") or "").strip()
    content = (body.get("content") or "").strip()
    ship_date = (body.get("ship_date") or "").strip()
    vendor = (body.get("vendor") or "").strip()
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
        if vendor:
            fields["廠商"] = vendor
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
    body: {content, case_text, ship_date, vendor}
    ship_date 給空字串代表清空該欄位（例如填錯了要清掉重填）。
    vendor（2026-09-01 新增）同樣需要 Airtable「APP資料」表已有「廠商」欄位。"""
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
    if "vendor" in body:
        fields["廠商"] = body.get("vendor") or None
    if not fields:
        return jsonify({"error": "沒有帶任何要更新的欄位"}), 400
    try:
        result = app_data_update(record_id, fields)
    except Exception as e:
        return jsonify({"error": "Airtable 寫入失敗", "detail": str(e)}), 502
    return jsonify({"ok": True, "record": result})


# ===================================================================
# 維運團隊（維運驗收，2026-09-08 新增）
# ===================================================================

def _ops_record_to_dict(rec, full=False):
    """把「維運驗收」表一筆 Airtable record 轉成前端好用的格式，把兩個 JSON
    長文字欄位解析成陣列/物件；full=False 時只回傳清單頁需要的精簡欄位。"""
    f = rec["fields"]

    def parse_json(field_id, default):
        raw = f.get(field_id)
        if not raw:
            return default
        try:
            return json.loads(raw)
        except Exception:
            return default

    result = {
        "id": rec["id"],
        "case_name": f.get(OPS_FIELD_CASE_NAME, ""),
        "case_no": f.get(OPS_FIELD_CASE_NO, ""),
        "case_record_id": (f.get(OPS_FIELD_CASE_LINK) or [None])[0],
        "vendor": f.get(OPS_FIELD_VENDOR, ""),
        "vendor_fullname": f.get(OPS_FIELD_VENDOR_FULLNAME, ""),
        "owner_company": f.get(OPS_FIELD_OWNER_COMPANY, ""),
        "planned_meter_date": f.get(OPS_FIELD_PLANNED_METER_DATE),
        "result": f.get(OPS_FIELD_RESULT) or [],
        "status": f.get(OPS_FIELD_STATUS) or OPS_STATUS_PENDING,
    }
    if not full:
        return result

    owner_sig = f.get(OPS_FIELD_OWNER_SIGNATURE) or []
    vendor_sig = f.get(OPS_FIELD_VENDOR_SIGNATURE) or []
    pdf = f.get(OPS_FIELD_PDF) or []
    result.update({
        "checklist": parse_json(OPS_FIELD_CHECKLIST_JSON, []),
        "other_issues": f.get(OPS_FIELD_OTHER_ISSUES, ""),
        "equipment": parse_json(OPS_FIELD_EQUIPMENT_JSON, []),
        "owner_signer_name": f.get(OPS_FIELD_OWNER_SIGNER_NAME, ""),
        "owner_signature_url": owner_sig[-1]["url"] if owner_sig else None,
        "owner_sign_date": f.get(OPS_FIELD_OWNER_SIGN_DATE),
        "vendor_signer_name": f.get(OPS_FIELD_VENDOR_SIGNER_NAME, ""),
        "vendor_signature_url": vendor_sig[-1]["url"] if vendor_sig else None,
        "vendor_sign_date": f.get(OPS_FIELD_VENDOR_SIGN_DATE),
        "pdf_url": pdf[-1]["url"] if pdf else None,
    })
    return result


@app.route("/api/ops-cases")
def ops_cases():
    """維運團隊模組的案件清單。回傳所有「維運驗收」記錄的精簡資訊，前端可以
    自行依「狀態」分區（待填寫/已完成驗收/已產生PDF）。"""
    try:
        records = airtable_get_all(OPS_API_URL, None, [
            OPS_FIELD_CASE_NAME, OPS_FIELD_CASE_NO, OPS_FIELD_CASE_LINK,
            OPS_FIELD_VENDOR, OPS_FIELD_VENDOR_FULLNAME, OPS_FIELD_OWNER_COMPANY,
            OPS_FIELD_PLANNED_METER_DATE, OPS_FIELD_RESULT, OPS_FIELD_STATUS,
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    return jsonify({"cases": [_ops_record_to_dict(r) for r in records]})


@app.route("/api/ops-cases/manual", methods=["POST"])
def create_ops_case_manual():
    """手動新增一筆「維運驗收」記錄（給沒有走「掛表安排」自動同步流程的案件用，
    例如補登舊案件、或案號還沒建進「專案細節」表的特殊情況）。
    body: {case_record_id（選填，前端用 /api/case-search 選到候選案件時帶入，
    有帶的話會自動查案件既有的模組/逆變器/廠商資料覆蓋掉手動輸入的同名欄位）,
    case_no, case_name（案場名稱/別名）, vendor（廠商簡稱，選填）,
    planned_meter_date（選填）}。
    如果 case_record_id 已經有對應的維運驗收記錄，直接回傳既有那筆的 id，
    不會重複建立（避免跟「掛表安排」自動同步流程打架，出現同一案件兩筆記錄）。"""
    body = request.get_json(force=True)
    case_record_id = body.get("case_record_id")
    case_no = (body.get("case_no") or "").strip()
    case_name = (body.get("case_name") or "").strip()
    vendor_short = (body.get("vendor") or "").strip()
    planned_meter_date = body.get("planned_meter_date") or None

    if not case_no and not case_name:
        return jsonify({"error": "請至少填寫案號或案場名稱"}), 400

    if case_record_id:
        existing = ops_find_by_case(case_record_id)
        if existing:
            return jsonify({"ok": True, "id": existing["id"], "already_existed": True})

    case_info = fetch_case_basic_info(case_record_id) if case_record_id else None
    if case_info:
        vendor_short = case_info.get("vendor") or vendor_short
        case_name = case_info.get("alias") or case_name
        case_no = case_info.get("case_no") or case_no
    vendor_full = get_vendor_fullname(vendor_short) if vendor_short else ""

    checklist = build_default_checklist()
    equipment = build_default_equipment_list(case_info)

    create_fields = {
        OPS_FIELD_CASE_NAME: case_name or case_no,
        OPS_FIELD_CASE_NO: case_no,
        OPS_FIELD_VENDOR: vendor_short,
        OPS_FIELD_VENDOR_FULLNAME: vendor_full,
        OPS_FIELD_OWNER_COMPANY: DEFAULT_OWNER_COMPANY,
        OPS_FIELD_CHECKLIST_JSON: json.dumps(checklist, ensure_ascii=False),
        OPS_FIELD_EQUIPMENT_JSON: json.dumps(equipment, ensure_ascii=False),
        OPS_FIELD_STATUS: OPS_STATUS_PENDING,
    }
    if case_record_id:
        create_fields[OPS_FIELD_CASE_LINK] = [case_record_id]
    if planned_meter_date:
        create_fields[OPS_FIELD_PLANNED_METER_DATE] = planned_meter_date

    resp = requests.post(OPS_API_URL, headers=airtable_headers(), json={"fields": create_fields}, timeout=20)
    if resp.status_code >= 400:
        return jsonify({"error": "Airtable 寫入失敗", "detail": resp.text}), 502
    return jsonify({"ok": True, "id": resp.json()["id"]})


@app.route("/api/ops-acceptance/<record_id>", methods=["DELETE"])
def delete_ops_acceptance(record_id):
    """刪除一筆「維運驗收」記錄（例如手動誤觸新增、或重複記錄）。這是整筆刪除，
    前端要在按下之前先跳出確認提示，不能誤觸就刪掉。"""
    resp = requests.delete(f"{OPS_API_URL}/{record_id}", headers=airtable_headers(), timeout=20)
    if resp.status_code >= 400:
        return jsonify({"error": "Airtable 刪除失敗", "detail": resp.text}), 502
    return jsonify({"ok": True})


@app.route("/api/ops-acceptance/<record_id>")
def ops_acceptance_detail(record_id):
    """讀取單一案件的完整驗收單內容（給驗收表單頁用）。"""
    try:
        resp = requests.get(
            f"{OPS_API_URL}/{record_id}",
            headers=airtable_headers(),
            params={"returnFieldsByFieldId": "true"},
            timeout=20,
        )
        if resp.status_code >= 400:
            return jsonify({"error": "找不到這筆維運驗收記錄", "detail": resp.text}), 404
        rec = resp.json()
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    return jsonify(_ops_record_to_dict(rec, full=True))


@app.route("/api/ops-acceptance/<record_id>", methods=["POST"])
def save_ops_acceptance(record_id):
    """儲存驗收單內容（可以只存部分欄位，隨時可以按儲存，不用一次填完）。
    body 可包含：owner_company, vendor_fullname, checklist(陣列), other_issues,
    result(陣列), equipment(陣列), owner_signer_name, owner_sign_date,
    vendor_signer_name, vendor_sign_date, status,
    owner_signature_base64/owner_signature_filename（簽名圖片，可省略）,
    vendor_signature_base64/vendor_signature_filename（同上）。
    簽名圖片走 Airtable 附件上傳 API，跟其他欄位是分開兩次呼叫，其中一個
    失敗不影響另一個，最後統一回傳整體是否成功。"""
    body = request.get_json(force=True)
    fields = {}

    simple_field_map = {
        "owner_company": OPS_FIELD_OWNER_COMPANY,
        "vendor_fullname": OPS_FIELD_VENDOR_FULLNAME,
        "other_issues": OPS_FIELD_OTHER_ISSUES,
        "owner_signer_name": OPS_FIELD_OWNER_SIGNER_NAME,
        "owner_sign_date": OPS_FIELD_OWNER_SIGN_DATE,
        "vendor_signer_name": OPS_FIELD_VENDOR_SIGNER_NAME,
        "vendor_sign_date": OPS_FIELD_VENDOR_SIGN_DATE,
        "status": OPS_FIELD_STATUS,
    }
    for key, field_id in simple_field_map.items():
        if key in body:
            fields[field_id] = body[key]

    if "checklist" in body:
        fields[OPS_FIELD_CHECKLIST_JSON] = json.dumps(body["checklist"], ensure_ascii=False)
    if "equipment" in body:
        fields[OPS_FIELD_EQUIPMENT_JSON] = json.dumps(body["equipment"], ensure_ascii=False)
    if "result" in body:
        fields[OPS_FIELD_RESULT] = body["result"] or []

    if fields:
        resp = requests.patch(
            f"{OPS_API_URL}/{record_id}",
            headers=airtable_headers(),
            json={"fields": fields},
            timeout=20,
        )
        if resp.status_code >= 400:
            return jsonify({"error": "Airtable 寫入失敗", "detail": resp.text}), 502

    signature_errors = []
    if body.get("owner_signature_base64"):
        try:
            upload_attachment_to_ops_record(
                record_id, OPS_FIELD_OWNER_SIGNATURE,
                body["owner_signature_base64"],
                body.get("owner_signature_filename", "owner_signature.png"),
            )
        except Exception as e:
            signature_errors.append(f"業主簽名上傳失敗：{e}")
    if body.get("vendor_signature_base64"):
        try:
            upload_attachment_to_ops_record(
                record_id, OPS_FIELD_VENDOR_SIGNATURE,
                body["vendor_signature_base64"],
                body.get("vendor_signature_filename", "vendor_signature.png"),
            )
        except Exception as e:
            signature_errors.append(f"系統商簽名上傳失敗：{e}")

    if signature_errors:
        return jsonify({"ok": False, "errors": signature_errors}), 502
    return jsonify({"ok": True})


@app.route("/api/ops-acceptance/<record_id>/generate-pdf", methods=["POST"])
def generate_ops_pdf(record_id):
    """讀取這筆驗收單目前存好的資料，排版成跟紙本「太陽光電系統完工驗收細項表」
    一樣格式的 PDF，上傳回「維運驗收」表的 PDF檔案 欄位，並把狀態改成「已產生PDF」。
    回傳 Airtable 附件網址給前端顯示/下載連結（Airtable 附件網址有時效性，
    如果之後要長期保存連結，建議前端拿到網址後提示使用者另外下載存檔）。"""
    try:
        resp = requests.get(
            f"{OPS_API_URL}/{record_id}",
            headers=airtable_headers(),
            params={"returnFieldsByFieldId": "true"},
            timeout=20,
        )
        if resp.status_code >= 400:
            return jsonify({"error": "找不到這筆維運驗收記錄"}), 404
        data = _ops_record_to_dict(resp.json(), full=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    try:
        pdf_bytes = build_acceptance_pdf(data)
    except Exception as e:
        return jsonify({"error": "PDF 產生失敗", "detail": str(e)}), 500

    import base64
    b64 = base64.b64encode(pdf_bytes).decode("ascii")
    filename = f"{data['case_name'] or data['case_no'] or record_id}_驗收單.pdf"
    try:
        upload_resp = upload_attachment_to_ops_record(
            record_id, OPS_FIELD_PDF, b64, filename, content_type="application/pdf",
        )
    except Exception as e:
        return jsonify({"error": "PDF 上傳 Airtable 失敗", "detail": str(e)}), 502

    requests.patch(
        f"{OPS_API_URL}/{record_id}",
        headers=airtable_headers(),
        json={"fields": {OPS_FIELD_STATUS: OPS_STATUS_PDF}},
        timeout=20,
    )

    pdf_url = None
    attachments = upload_resp.get("fields", {}).get(OPS_FIELD_PDF, [])
    if attachments:
        pdf_url = attachments[-1].get("url")
    return jsonify({"ok": True, "pdf_url": pdf_url})


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
        "scheduler_running": scheduler.running,
    })


if __name__ == "__main__":
    # 本機開發模式（直接 `python app.py` 執行，不透過 gunicorn）：
    # 這裡沒有 fork()，所以要自己啟動背景初始化跟排程，行為才會跟正式環境一致。
    scheduler.start()
    threading.Thread(target=_startup_refresh_all, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
