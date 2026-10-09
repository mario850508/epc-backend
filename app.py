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
import re
import csv
import base64
import difflib
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
from flask import Flask, Response, jsonify, request
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
# 2026-10-08：「通知廠商」——PM 確認屋主資料後，用 LIFF shareTargetPicker 把卡片轉發到廠商群組
FIELD_SLOT_VENDOR_TOKEN = "fldny0M5w7oBVr14z"     # 廠商通知Token
FIELD_SLOT_PM_NOTE = "flddfOVk2OdqMElSm"          # 給廠商備註
FIELD_SLOT_VENDOR_NOTIFIED = "fldCC1k8KciTDtK61"  # 廠商通知時間（ISO 字串）
FIELD_SLOT_OWNER_PHONE = "fldT1YrJY2Rp8L33S"  # 屋主電話，2026-10-01 新增
SLOT_KIND_WINDOW = "開放時段"
SLOT_KIND_BOOKING = "已預約"
SLOT_KIND_CANCELLED = "已取消"   # 2026-10-08：取消的預約保留紀錄，但不再佔時段
FIELD_SLOT_CANCEL_REASON = "fld75wrXrUpPZUbzZ"   # 取消原因
FIELD_SLOT_CANCELLED_AT = "fldYfmiei6CcseaqB"    # 取消時間（ISO）
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
FIELD_TASK_EST_START = "fld71d3cCHY4hhzoN"  # 預估開始時間 HH:MM（PM 指派時填，填單頁當預設開始時間）
# 2026-10-07：屋主版預約連結（測試版）。跟業務版 token 分開，屋主版只回去識別化的資料。
FIELD_TASK_OWNER_TOKEN = "fldEAVpfdwAot2wmx"      # 屋主Token
FIELD_TASK_OWNER_WIN_START = "fldcshgkAyg8iA1mV"  # 屋主可選時段開始 HH:MM（預設 09:00）
FIELD_TASK_OWNER_WIN_END = "fldZM3kKE3GWpyvvK"    # 屋主可選時段結束 HH:MM（預設 17:00，作業要在這之前結束）
FIELD_TASK_OWNER_MODE = "fld7qN5jOoOyB0SY5"       # 屋主版已發出（由屋主自己填表；期限提醒改寫法）
TASK_STATUS_PENDING = "待業務安排"
TASK_STATUS_DONE = "已完成"
TASK_STATUS_CANCELLED = "已取消"   # 2026-10-08：窗口取消預約、且不重新約
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
            FIELD_SLOT_REGISTRANT, FIELD_SLOT_NOTE, FIELD_SLOT_OWNER_NAME, FIELD_SLOT_OWNER_PHONE,
            FIELD_SLOT_VENDOR_NOTIFIED, FIELD_SLOT_CANCEL_REASON, FIELD_SLOT_CANCELLED_AT,
        ]
        records = airtable_get_all(SLOT_API_URL, "TRUE()", fields)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    windows, bookings, cancelled = [], [], []
    for r in records:
        f = r["fields"]
        item = {
            "record_id": r["id"],
            "vendor": f.get(FIELD_SLOT_VENDOR),
            "date": f.get(FIELD_SLOT_DATE),
        }
        if f.get(FIELD_SLOT_KIND) == SLOT_KIND_CANCELLED:
            item.update({
                "start_time": f.get(FIELD_SLOT_START), "end_time": f.get(FIELD_SLOT_END),
                "case": f.get(FIELD_SLOT_CASE_NO, ""), "alias": f.get(FIELD_SLOT_ALIAS, ""),
                "type": f.get(FIELD_SLOT_TYPE) or [], "registrant": f.get(FIELD_SLOT_REGISTRANT, ""),
                "note": f.get(FIELD_SLOT_NOTE, ""), "owner_name": f.get(FIELD_SLOT_OWNER_NAME, ""),
                "owner_phone": f.get(FIELD_SLOT_OWNER_PHONE, ""), "cancelled": True,
                "cancel_reason": f.get(FIELD_SLOT_CANCEL_REASON, ""), "cancelled_at": f.get(FIELD_SLOT_CANCELLED_AT, ""),
            })
            cancelled.append(item)
        elif f.get(FIELD_SLOT_KIND) == SLOT_KIND_BOOKING:
            item.update({
                "start_time": f.get(FIELD_SLOT_START),
                "end_time": f.get(FIELD_SLOT_END),
                "case": f.get(FIELD_SLOT_CASE_NO, ""),
                "alias": f.get(FIELD_SLOT_ALIAS, ""),
                "type": f.get(FIELD_SLOT_TYPE) or [],
                "registrant": f.get(FIELD_SLOT_REGISTRANT, ""),
                "note": f.get(FIELD_SLOT_NOTE, ""),
                "owner_name": f.get(FIELD_SLOT_OWNER_NAME, ""),
                "owner_phone": f.get(FIELD_SLOT_OWNER_PHONE, ""),
                "vendor_notified_at": f.get(FIELD_SLOT_VENDOR_NOTIFIED, ""),
            })
            bookings.append(item)
        else:
            item["note"] = f.get(FIELD_SLOT_NOTE, "")
            windows.append(item)
    windows.sort(key=lambda w: (w.get("date") or "", w.get("vendor") or ""))
    bookings.sort(key=lambda b: (b.get("date") or "", b.get("start_time") or ""))
    cancelled.sort(key=lambda b: (b.get("date") or "", b.get("start_time") or ""))
    return jsonify({"windows": windows, "bookings": bookings, "cancelled": cancelled})


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


def _revert_case_dates(case_no, slot_type, date):
    """取消預約時，把當初自動寫回的預計日期清掉（只清「還是這一天」的，避免蓋掉之後手動改過的日期）。"""
    types = set(slot_type or [])
    if not case_no:
        return
    esc = case_no.replace("\\", "\\\\").replace("'", "\\'")
    if types & {"掛表", "植筋", "進場"}:
        recs = airtable_get_all(CASE_API_URL, f"{{{FIELD_CASE_NO}}}='{esc}'", [FIELD_CASE_NO])
        if recs:
            case_record_id = recs[0]["id"]
            existing = app_data_find_case_row(case_record_id)
            if existing:
                ef = existing.get("fields", {})
                patch = {}
                if "掛表" in types and ef.get("預計掛表日期") == date:
                    patch["預計掛表日期"] = None
                if "植筋" in types and ef.get("植筋日期") == date:
                    patch["植筋日期"] = None
                if patch:
                    app_data_update(existing["id"], patch)
            if "進場" in types:
                ms_id = ensure_milestone_record(case_record_id, MILESTONE_TYPE_ENTRY)
                ms = requests.get(f"{MILESTONE_API_URL}/{ms_id}", headers=airtable_headers(),
                                  params={"returnFieldsByFieldId": "true"}, timeout=20)
                if ms.status_code < 400 and ms.json().get("fields", {}).get(FIELD_MS_ACTUAL_DATE) == date:
                    requests.patch(f"{MILESTONE_API_URL}/{ms_id}", headers=airtable_headers(),
                                   json={"fields": {FIELD_MS_ACTUAL_DATE: None}}, timeout=20)
                    threading.Thread(target=refresh_cache, daemon=True).start()
    if "場勘" in types:
        recs = airtable_get_all(SURVEY_API_URL, f"{{{SURVEY_FIELD_CASE_NO}}}='{esc}'", [SURVEY_FIELD_CASE_NO, SURVEY_FIELD_PLANNED_DATE])
        if recs and recs[0]["fields"].get(SURVEY_FIELD_PLANNED_DATE) == date:
            rid = recs[0]["id"]
            requests.patch(f"{SURVEY_API_URL}/{rid}", headers=airtable_headers(),
                           json={"fields": {SURVEY_FIELD_PLANNED_DATE: None}}, timeout=20)
            for c in SURVEY_CACHE["cases"]:
                if c["record_id"] == rid:
                    c["planned_date"] = None
                    break


@app.route("/api/vendor-slots/<record_id>/cancel", methods=["POST"])
def cancel_vendor_slot_booking(record_id):
    """2026-10-08：窗口取消一筆預約（例如發現還不能進場）。
    - 預約改成「已取消」（保留紀錄，但不再佔廠商時段）
    - 當初自動寫回的預計日期清掉（還是這一天的才清）
    - 任務：reopen=true 退回「待業務安排」之後重新約；否則標「已取消」（業務／屋主連結都不能再約）
    - 通知業務（LINE 卡片附「複製給屋主的取消訊息」按鈕），API 也回傳這段訊息讓窗口自己轉傳
    body: {reason, reopen, notify}"""
    body = request.get_json(force=True) or {}
    reason = (body.get("reason") or "").strip()[:300]
    reopen = bool(body.get("reopen"))
    notify = body.get("notify", True) is not False
    rec = _get_booking(record_id)
    if not rec:
        return jsonify({"error": "找不到這筆預約"}), 404
    f = rec.get("fields", {})
    if f.get(FIELD_SLOT_KIND) != SLOT_KIND_BOOKING:
        return jsonify({"error": "這筆已經不是有效的預約（可能已經取消過）"}), 409
    case_no = f.get(FIELD_SLOT_CASE_NO, "")
    types = f.get(FIELD_SLOT_TYPE) or []
    date, start, end = f.get(FIELD_SLOT_DATE, ""), f.get(FIELD_SLOT_START, ""), f.get(FIELD_SLOT_END, "")
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    resp = requests.patch(f"{SLOT_API_URL}/{record_id}", headers=airtable_headers(), json={"fields": {
        FIELD_SLOT_KIND: SLOT_KIND_CANCELLED, FIELD_SLOT_CANCEL_REASON: reason, FIELD_SLOT_CANCELLED_AT: now,
    }}, timeout=20)
    if resp.status_code >= 400:
        return jsonify({"error": "Airtable 寫入失敗", "detail": resp.text}), 502
    try:
        _revert_case_dates(case_no, types, date)
    except Exception as e:
        print(f"[cancel_vendor_slot_booking] 清除預計日期失敗（預約已取消）：{e}", flush=True)
    task = None
    try:
        trs = airtable_get_all(TASK_API_URL, "{" + FIELD_TASK_BOOKING_ID + "}='" + record_id + "'", _task_fields())
        if trs:
            task = _task_to_dict(trs[0])
            if reopen:
                _patch_task(task["record_id"], {
                    FIELD_TASK_STATUS: TASK_STATUS_PENDING, FIELD_TASK_BOOKING_ID: "", FIELD_TASK_STAGE: None,
                    FIELD_TASK_ALT_SLOTS: "", FIELD_TASK_CHOSEN_SLOT: "", FIELD_TASK_REMINDED: False, FIELD_TASK_DEADLINE: None,
                })
            else:
                _patch_task(task["record_id"], {FIELD_TASK_STATUS: TASK_STATUS_CANCELLED})
    except Exception as e:
        print(f"[cancel_vendor_slot_booking] 更新任務失敗（預約已取消）：{e}", flush=True)
    notice = _cancel_notice(rec, task, reason, reopen)
    rep_ok = _push_to_name(notice["rep_name"], notice["rep_card"]) if (notify and notice["rep_name"]) else False
    sched_ok = _send_cancel_to_scheduler(notice, task)
    return jsonify({"ok": True, "owner_message": notice["msg"], "rep_name": notice["rep_name"], "rep_notified": rep_ok,
                    "scheduler_notified": sched_ok,
                    "vendor_was_notified": bool(f.get(FIELD_SLOT_VENDOR_NOTIFIED)), "reopened": reopen})


def _cancel_notice(rec, task, reason, reopen):
    """組取消通知：給屋主的訊息、給業務的卡片、給安排人員的卡片。"""
    f = rec.get("fields", {})
    case_no = f.get(FIELD_SLOT_CASE_NO, "")
    types = f.get(FIELD_SLOT_TYPE) or []
    date, start, end = f.get(FIELD_SLOT_DATE, ""), f.get(FIELD_SLOT_START, ""), f.get(FIELD_SLOT_END, "")
    registrant = (f.get(FIELD_SLOT_REGISTRANT) or "").strip()
    rep_name = (task and task.get("assignee")) or ("" if registrant.startswith("屋主") else registrant)
    owner_name = (f.get(FIELD_SLOT_OWNER_NAME) or "").strip()
    owner_phone = (f.get(FIELD_SLOT_OWNER_PHONE) or "").strip()
    items = "、".join(OWNER_TYPE_LABELS.get(t, t) for t in types)
    msg = (f"{owner_name or '屋主'} 您好，原本約在 {_wd_label(date)} {start}–{end} 的「{items}」，"
           f"因為{reason or '施工安排需要調整'}，這次行程先取消，造成您的不便很抱歉。"
           + ("我們會再跟您約新的時間。" if reopen else "後續安排會再跟您聯絡。")
           + ("\n—陽光伏特家 " + rep_name if rep_name else "\n—陽光伏特家"))
    dial = "".join(c for c in owner_phone if c.isdigit() or c == "+")
    buttons = [("📋 複製給屋主的取消訊息", {"clipboard": msg})]
    if len(dial) >= 8:
        buttons.append(("📞 撥號給屋主", "tel:" + dial))
    title = f"{case_no} {f.get(FIELD_SLOT_ALIAS, '')}".strip()
    rows = [("項目", "、".join(types)), ("廠商", f.get(FIELD_SLOT_VENDOR, "")),
            ("原訂時間", f"{_wd_label(date)} {start}-{end}"), ("屋主", _owner_str(owner_name, owner_phone)),
            ("取消原因", reason), ("後續", "會再重新約時間" if reopen else "")]
    rep_card = _card("❌ 預約已取消｜給業務", "#DC2626", title, subtitle=f"{rep_name} 您好" if rep_name else "",
                     rows=rows, note="請通知屋主這次行程取消：按下方「複製給屋主的取消訊息」貼給屋主，或直接打電話",
                     buttons=buttons)
    sched_card = _card("❌ 預約已取消｜給安排人員", "#DC2626", title, rows=[("業務", rep_name)] + rows,
                       note="如果業務沒通知到屋主，可以按下方按鈕複製取消訊息自己傳",
                       buttons=buttons + [("開啟主控台", _dash_url() + "/")])
    return {"msg": msg, "rep_name": rep_name, "rep_card": rep_card, "sched_card": sched_card}


def _send_cancel_to_scheduler(notice, task):
    """取消通知也發給安排人員（任務建立人）；沒有建立人（例如 PM 直接預約的）就發給預設對象（許家豪）。"""
    creator = ((task or {}).get("creator") or "").strip()
    try:
        if creator:
            return _push_to_name(creator, notice["sched_card"])
        ok, _ = _line_push_card(notice["sched_card"])
        return ok
    except Exception as e:
        print(f"[_send_cancel_to_scheduler] 推播失敗：{e}", flush=True)
        return False


@app.route("/api/vendor-slots/<record_id>/cancel-notice", methods=["POST"])
def resend_cancel_notice(record_id):
    """重新發送已取消預約的通知。body: {targets: ["scheduler", "rep"]}（預設只發安排人員）"""
    body = request.get_json(force=True) or {}
    targets = body.get("targets") or ["scheduler"]
    rec = _get_booking(record_id)
    if not rec:
        return jsonify({"error": "找不到這筆預約"}), 404
    f = rec.get("fields", {})
    if f.get(FIELD_SLOT_KIND) != SLOT_KIND_CANCELLED:
        return jsonify({"error": "這筆不是已取消的預約"}), 409
    task = None
    try:
        trs = airtable_get_all(TASK_API_URL, "{" + FIELD_TASK_BOOKING_ID + "}='" + record_id + "'", _task_fields())
        if trs:
            task = _task_to_dict(trs[0])
    except Exception:
        pass
    reopen = bool(task and task.get("status") == TASK_STATUS_PENDING)
    notice = _cancel_notice(rec, task, (f.get(FIELD_SLOT_CANCEL_REASON) or "").strip(), reopen)
    out = {"ok": True}
    if "scheduler" in targets:
        out["scheduler_notified"] = _send_cancel_to_scheduler(notice, task)
    if "rep" in targets and notice["rep_name"]:
        out["rep_notified"] = _push_to_name(notice["rep_name"], notice["rep_card"])
    return jsonify(out)


@app.route("/api/vendor-slots/<record_id>/detail")
def vendor_slot_booking_detail(record_id):
    """2026-10-05：主控台「查看填單」用——回傳業務當時送出的預約內容（時間、屋主資訊、備註、
    登記人、填單時間），並且如果這筆預約是從「指派給業務」任務來的，一併帶出任務資訊
    （指派對象、安排人員、回覆期限、屋主預設資料＝公證書資訊、業務曾經回傳的其他時間）。"""
    try:
        resp = requests.get(f"{SLOT_API_URL}/{record_id}", headers=airtable_headers(),
                            params={"returnFieldsByFieldId": "true"}, timeout=20)
        if resp.status_code >= 400:
            return jsonify({"error": "找不到這筆預約"}), 404
        rec = resp.json()
        f = rec.get("fields", {})
        out = {
            "booking": {
                "record_id": rec["id"],
                "created_at": rec.get("createdTime"),
                "vendor": f.get(FIELD_SLOT_VENDOR),
                "date": f.get(FIELD_SLOT_DATE),
                "start_time": f.get(FIELD_SLOT_START),
                "end_time": f.get(FIELD_SLOT_END),
                "case": f.get(FIELD_SLOT_CASE_NO, ""),
                "alias": f.get(FIELD_SLOT_ALIAS, ""),
                "type": f.get(FIELD_SLOT_TYPE) or [],
                "registrant": f.get(FIELD_SLOT_REGISTRANT, ""),
                "note": f.get(FIELD_SLOT_NOTE, ""),
                "owner_name": f.get(FIELD_SLOT_OWNER_NAME, ""),
                "owner_phone": f.get(FIELD_SLOT_OWNER_PHONE, ""),
            },
            "task": None,
        }
        escaped = rec["id"].replace("'", "\\'")
        trs = airtable_get_all(TASK_API_URL, f"{{{FIELD_TASK_BOOKING_ID}}}='{escaped}'", _task_fields())
        if trs:
            t = _task_to_dict(trs[0])
            out["task"] = {
                "assignee": t["assignee"], "creator": t["creator"], "deadline": t["deadline"],
                "candidate_dates": t["candidate_dates"], "duration_min": t["duration_min"],
                "owner_name": t["owner_name"], "owner_phone": t["owner_phone"],
                "alt_slots": t["alt_slots"], "rep_note": t["rep_note"], "note": t["note"],
                "created_at": trs[0].get("createdTime"),
            }
        return jsonify(out)
    except Exception as e:
        return jsonify({"error": str(e)}), 502


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
        FIELD_TASK_DEADLINE, FIELD_TASK_EST_START,
        FIELD_TASK_OWNER_TOKEN, FIELD_TASK_OWNER_WIN_START, FIELD_TASK_OWNER_WIN_END, FIELD_TASK_OWNER_MODE,
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
        "est_start": f.get(FIELD_TASK_EST_START) or "",
        "owner_token": f.get(FIELD_TASK_OWNER_TOKEN) or "",
        "owner_win_start": f.get(FIELD_TASK_OWNER_WIN_START) or "",
        "owner_win_end": f.get(FIELD_TASK_OWNER_WIN_END) or "",
        "owner_mode": bool(f.get(FIELD_TASK_OWNER_MODE)),
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
    owner_token = secrets.token_urlsafe(16)
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
            FIELD_TASK_OWNER_TOKEN: owner_token,
            FIELD_TASK_OWNER_WIN_START: _valid_hhmm(body.get("owner_win_start"), "09:00"),
            FIELD_TASK_OWNER_WIN_END: _valid_hhmm(body.get("owner_win_end"), "17:00"),
        }
        if duration_min is not None:
            fields[FIELD_TASK_DURATION_MIN] = duration_min
        deadline = _normalize_deadline(body.get("deadline"))
        if deadline:
            fields[FIELD_TASK_DEADLINE] = deadline
        est_start = (body.get("est_start") or "").strip()
        try:
            _parse_hhmm(est_start)
            fields[FIELD_TASK_EST_START] = est_start
        except Exception:
            pass
        owner_name = (body.get("owner_name") or "").strip()
        owner_phone = (body.get("owner_phone") or "").strip()
        if owner_name:
            fields[FIELD_TASK_OWNER_NAME] = owner_name
        if owner_phone:
            fields[FIELD_TASK_OWNER_PHONE] = owner_phone
        resp = requests.post(TASK_API_URL, headers=airtable_headers(), json={"fields": fields}, timeout=20)
        if resp.status_code >= 400:
            return jsonify({"error": "Airtable 寫入失敗", "detail": resp.text}), 502
        return jsonify({"ok": True, "token": token, "path": f"/book.html?token={token}",
                        "record_id": resp.json().get("id"), "owner_path": f"/owner.html?t={owner_token}"})
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


def _binding_name_candidates(name):
    """「林嘉偉(Mika)」這種寫法也要對得上只綁「Mika」或「林嘉偉」的人：依序試完整名字、括號內、括號外。"""
    import re
    name = (name or "").strip()
    out = [name] if name else []
    m = re.match(r"^(.*?)[(（]\s*(.+?)\s*[)）]\s*$", name)
    if m:
        for part in (m.group(2).strip(), m.group(1).strip()):
            if part and part not in out:
                out.append(part)
    return out


def _get_line_binding(name):
    for cand in _binding_name_candidates(name):
        rec = _find_line_binding_record(cand)
        uid = (rec["fields"].get(FIELD_BIND_UID) if rec else None) or None
        if uid:
            return uid
    return None


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
    if task["status"] == TASK_STATUS_CANCELLED:
        return jsonify({"error": "這個預約已經取消了，請聯絡窗口或您的業務"}), 409
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
        _card("✅ 業務已完成安排｜給安排人員", "#16A34A", f"{task['case']} {task['alias']}".strip(),
              rows=[("業務", task["assignee"] or body.get("registrant") or ""), ("項目", "、".join(task["type"])),
                    ("廠商", task["vendor"]), ("時間", f"{_wd_label(date)} {body.get('start_time')}-{body.get('end_time')}"),
                    ("屋主", _owner_str(body.get("owner_name"), body.get("owner_phone"))),
                    ("備註", (body.get("note") or "").strip())],
              button=("開啟主控台", _dash_url() + "/")),
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
    if task["status"] == TASK_STATUS_CANCELLED:
        return jsonify({"error": "這個預約已經取消了，請聯絡窗口或您的業務"}), 409
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
    slot_lines = "\n".join(
        f"{i + 1}. {sl['date'][5:].replace('-', '/')}（週{WEEKDAY_ZH[datetime.strptime(sl['date'], '%Y-%m-%d').weekday()]}）"
        f"{sl['start_time']}-{sl['end_time']}"
        for i, sl in enumerate(slots)
    )
    rep_note = (body.get("note") or "").strip()
    _notify_scheduler_async(
        task["creator"],
        _card("📝 業務回傳其他時間｜給安排人員", "#D97706", f"{task['case']} {task['alias']}".strip(),
              rows=[("業務", task["assignee"] or ""), ("項目", "、".join(task["type"])), ("廠商", task["vendor"]),
                    (f"可選時間（{len(slots)} 組）", slot_lines), ("業務備註", rep_note)],
              note="請跟廠商確認後，到主控台選一個時間",
              button=("開啟主控台", _dash_url() + "/")),
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
        slot = dict(task["alt_slots"][int(body.get("index"))])
    except Exception:
        return jsonify({"error": "選的備選時段不存在"}), 400
    # 2026-10-08：屋主版只給日期，窗口選的時候補開始時間（結束時間＝開始＋作業時長，也可直接帶 end_time）
    if body.get("start_time"):
        try:
            st = _parse_hhmm(body["start_time"])
            et = _parse_hhmm(body["end_time"]) if body.get("end_time") else st + _owner_duration(task)
        except Exception:
            return jsonify({"error": "時間格式不對，要像 09:00"}), 400
        if et <= st:
            return jsonify({"error": "結束時間要晚於開始時間"}), 400
        slot["start_time"], slot["end_time"] = f"{st // 60:02d}:{st % 60:02d}", f"{et // 60:02d}:{et % 60:02d}"
    if not slot.get("start_time") or not slot.get("end_time"):
        return jsonify({"error": "這個備選只有日期，請先填開始時間"}), 400
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
    if task["status"] == TASK_STATUS_CANCELLED:
        return jsonify({"error": "這個預約已經取消了，請聯絡窗口或您的業務"}), 409
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
        _card("✅ 業務已確認時間，安排完成｜給安排人員", "#16A34A", f"{task['case']} {task['alias']}".strip(),
              rows=[("業務", task["assignee"] or ""), ("項目", "、".join(task["type"])), ("廠商", task["vendor"]),
                    ("時間", f"{_wd_label(chosen['date'])} {chosen['start_time']}-{chosen['end_time']}"),
                    ("屋主", _owner_str(body.get("owner_name"), body.get("owner_phone"))),
                    ("備註", (body.get("note") or "").strip())],
              button=("開啟主控台", _dash_url() + "/")),
    )
    return jsonify({"ok": True, "record": record})


# ===================================================================
# 2026-10-07：屋主版預約（測試版）。業務把屋主版連結（owner.html?t=屋主Token）轉給屋主，
# 屋主自己選時間。跟業務版的差別：
#   - 只回去識別化資料：不給案號、別名、廠商名稱、地址、屋主預設姓名電話、回覆期限。
#   - 施工項目用白話（現場勘查／施工團隊進場安裝…）。
#   - 只能在 PM 設定的「屋主可選時段」內、每 30 分鐘選開始時間；結束時間由後端依作業時長算，屋主不能改。
#   - 屋主送出（預約／提供其他時間／確認）後，用 LINE 卡片同時通知業務跟安排人員。
# 業務版連結照常可用，誰先完成預約就算數。
# ===================================================================
OWNER_TYPE_LABELS = {
    "場勘": "現場勘查", "放樣": "施工前現場放樣（定位）", "植筋": "植筋（支架基座施工）",
    "進場": "施工團隊進場安裝", "掛表": "台電人員裝設電表（掛表）",
}
OWNER_TYPE_DEFAULT_MIN = {"掛表": 180, "植筋": 180, "放樣": 60, "場勘": 60, "進場": 240}


def _valid_hhmm(raw, default):
    v = (raw or "").strip() if isinstance(raw, str) else ""
    try:
        m = _parse_hhmm(v)
        return f"{m // 60:02d}:{m % 60:02d}"
    except Exception:
        return default


def _case_address(case_no):
    """案件地址：Airtable 案件表優先，沒有的話用場勘快取裡的地址。"""
    case_no = (case_no or "").strip()
    if not case_no:
        return ""
    try:
        esc = case_no.replace("'", chr(92) + "'")
        recs = airtable_get_all(CASE_API_URL, "{" + FIELD_CASE_NO + "}='" + esc + "'", [FIELD_CASE_NO, FIELD_ADDRESS])
        if recs and recs[0]["fields"].get(FIELD_ADDRESS):
            return " ".join(recs[0]["fields"][FIELD_ADDRESS].split())
    except Exception as e:
        print(f"[_case_address] 查地址失敗：{e}", flush=True)
    for c in SURVEY_CACHE.get("cases") or []:
        if c.get("case") == case_no and c.get("address"):
            return " ".join(c["address"].split())
    return ""


def _owner_find_task(otoken):
    otoken = (otoken or "").strip()
    if len(otoken) < 10:
        return None
    esc = otoken.replace("'", chr(92) + "'")
    recs = airtable_get_all(TASK_API_URL, "{" + FIELD_TASK_OWNER_TOKEN + "}='" + esc + "'", _task_fields())
    return recs[0] if recs else None


def _owner_duration(task):
    return task.get("duration_min") or sum(OWNER_TYPE_DEFAULT_MIN.get(t, 60) for t in task.get("type") or []) or 60


def _owner_window(task):
    return _valid_hhmm(task.get("owner_win_start"), "09:00"), _valid_hhmm(task.get("owner_win_end"), "17:00")


def _vendor_busy_slots(vendor):
    if not vendor:
        return []
    esc = vendor.replace("'", chr(92) + "'")
    formula = (f"AND({{{FIELD_SLOT_KIND}}}='{SLOT_KIND_BOOKING}',{{{FIELD_SLOT_VENDOR}}}='{esc}',"
               f"IS_AFTER({{{FIELD_SLOT_DATE}}},DATEADD(TODAY(),-1,'days')))")
    out = []
    for br in airtable_get_all(SLOT_API_URL, formula, [FIELD_SLOT_DATE, FIELD_SLOT_START, FIELD_SLOT_END]):
        bf = br["fields"]
        if bf.get(FIELD_SLOT_DATE) and bf.get(FIELD_SLOT_START) and bf.get(FIELD_SLOT_END):
            out.append({"date": bf[FIELD_SLOT_DATE], "start_time": bf[FIELD_SLOT_START], "end_time": bf[FIELD_SLOT_END]})
    return out


def _owner_slot_from_start(task, date, start):
    """依屋主選的日期＋開始時間算出完整時段，並檢查是否落在可選時段內。回 (slot, 錯誤訊息)。"""
    try:
        datetime.strptime(date or "", "%Y-%m-%d")
        st = _parse_hhmm(start or "")
    except Exception:
        return None, "日期或時間格式不正確"
    ws, we = _owner_window(task)
    et = st + _owner_duration(task)
    if st < _parse_hhmm(ws) or et > _parse_hhmm(we):
        return None, f"請選 {ws}–{we} 之間的時間"
    return {"date": date, "start_time": f"{st // 60:02d}:{st % 60:02d}", "end_time": f"{et // 60:02d}:{et % 60:02d}"}, None


def _owner_contact(body):
    name = (body.get("owner_name") or "").strip()[:30]
    phone = (body.get("owner_phone") or "").strip()[:30]
    if not name or sum(c.isdigit() for c in phone) < 8:
        return None, None, "請填寫您的姓名和聯絡電話"
    return name, phone, None


def _notify_owner_action(task, tag_scheduler, tag_rep, color, rows, note_rep=""):
    """屋主有動作時，通知安排人員（附任務狀態）和業務。"""
    title = f"{task['case']} {task['alias']}".strip()
    _notify_scheduler_async(task["creator"], _card(tag_scheduler, color, title, rows=rows,
                                                   button=("開啟主控台", _dash_url() + "/")))
    if task.get("assignee") and task["assignee"] != task.get("creator"):
        threading.Thread(target=_push_to_name, daemon=True, args=(
            task["assignee"], _card(tag_rep, color, title, rows=rows, note=note_rep))).start()


@app.route("/api/owner-booking/<otoken>")
def owner_booking_get(otoken):
    try:
        r = _owner_find_task(otoken)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    if not r:
        return jsonify({"error": "找不到這個預約連結，可能已經失效，請直接聯絡您的業務"}), 404
    task = _task_to_dict(r)
    ws, we = _owner_window(task)
    stage = task["stage"]
    if task["status"] == TASK_STATUS_CANCELLED:
        status = "cancelled"
    elif task["status"] == TASK_STATUS_DONE:
        status = "done"
    elif stage == TASK_STAGE_WAIT_PM:
        status = "wait_pm"
    elif stage == TASK_STAGE_WAIT_REP and task["chosen_slot"]:
        status = "wait_confirm"
    else:
        status = "open"
    out = {
        "items": [OWNER_TYPE_LABELS.get(t, t) for t in task["type"]],
        "candidate_dates": task["candidate_dates"],
        "duration_min": _owner_duration(task),
        "window_start": ws, "window_end": we,
        "rep_name": task["assignee"],
        # 2026-10-08：使用者要求顯示施工地址，讓屋主確認是自己的案子
        "address": _case_address(task["case"]),
        "status": status,
        "chosen_slot": task["chosen_slot"] if status == "wait_confirm" else None,
        "proposed": task["alt_slots"] if status == "wait_pm" else [],
        "busy_slots": [],
        "booked": None,
    }
    if status == "done" and task["booking_id"]:
        try:
            resp = requests.get(f"{SLOT_API_URL}/{task['booking_id']}", headers=airtable_headers(),
                                params={"returnFieldsByFieldId": "true"}, timeout=15)
            if resp.status_code < 400:
                bf = resp.json().get("fields", {})
                out["booked"] = {"date": bf.get(FIELD_SLOT_DATE), "start_time": bf.get(FIELD_SLOT_START),
                                 "end_time": bf.get(FIELD_SLOT_END)}
        except Exception:
            pass
    elif status != "done":
        try:
            out["busy_slots"] = _vendor_busy_slots(task["vendor"])
        except Exception as e:
            print(f"[owner_booking_get] 撈已預約時段失敗：{e}", flush=True)
    return jsonify(out)


@app.route("/api/owner-booking/<otoken>/book", methods=["POST"])
def owner_booking_book(otoken):
    try:
        r = _owner_find_task(otoken)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    if not r:
        return jsonify({"error": "找不到這個預約連結，請直接聯絡您的業務"}), 404
    task = _task_to_dict(r)
    if task["status"] == TASK_STATUS_CANCELLED:
        return jsonify({"error": "這個預約已經取消了，請聯絡窗口或您的業務"}), 409
    if task["status"] == TASK_STATUS_DONE:
        return jsonify({"error": "這個預約已經完成了，如需更改請聯絡您的業務"}), 409
    body = request.get_json(force=True) or {}
    date = (body.get("date") or "").strip()
    if date not in task["candidate_dates"]:
        return jsonify({"error": "請從頁面上的日期裡選一天"}), 400
    slot, err_msg = _owner_slot_from_start(task, date, body.get("start_time"))
    if err_msg:
        return jsonify({"error": err_msg}), 400
    name, phone, err_msg = _owner_contact(body)
    if err_msg:
        return jsonify({"error": err_msg}), 400
    note = (body.get("note") or "").strip()[:300]
    record, err = _book_vendor_slot(
        task["vendor"], date, slot["start_time"], slot["end_time"], task["case"], task["alias"], task["type"],
        f"屋主 {name}", note, owner_name=name, owner_phone=phone,
    )
    if err:
        err_body, status = err
        if status == 409:
            return jsonify({"error": "這個時間剛好被別人預約了，請換一個時間"}), 409
        return jsonify(err_body), status
    try:
        _patch_task(r["id"], {FIELD_TASK_STATUS: TASK_STATUS_DONE, FIELD_TASK_BOOKING_ID: record["id"], FIELD_TASK_STAGE: None})
    except Exception as e:
        print(f"[owner_booking_book] 更新任務狀態失敗（預約本身已成功）：{e}", flush=True)
    _notify_owner_action(
        task, "🏠 屋主已自行預約｜給安排人員", "🏠 屋主已自行預約｜給業務", "#16A34A",
        [("業務", task["assignee"]), ("項目", "、".join(task["type"])), ("廠商", task["vendor"]),
         ("時間", f"{_wd_label(date)} {slot['start_time']}-{slot['end_time']}"),
         ("屋主", _owner_str(name, phone)), ("屋主備註", note)],
        note_rep="屋主已經自己選好時間，前一天請記得再跟屋主確認",
    )
    return jsonify({"ok": True, "booked": slot})


@app.route("/api/owner-booking/<otoken>/propose", methods=["POST"])
def owner_booking_propose(otoken):
    try:
        r = _owner_find_task(otoken)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    if not r:
        return jsonify({"error": "找不到這個預約連結，請直接聯絡您的業務"}), 404
    task = _task_to_dict(r)
    if task["status"] == TASK_STATUS_CANCELLED:
        return jsonify({"error": "這個預約已經取消了，請聯絡窗口或您的業務"}), 409
    if task["status"] == TASK_STATUS_DONE:
        return jsonify({"error": "這個預約已經完成了，如需更改請聯絡您的業務"}), 409
    body = request.get_json(force=True) or {}
    name, phone, err_msg = _owner_contact(body)
    if err_msg:
        return jsonify({"error": err_msg}), 400
    slots, seen = [], set()
    # 2026-10-08：屋主只選「哪幾天方便」，不選時間；窗口跟廠商確認後選一天並決定時間
    for sl in (body.get("slots") or [])[:10]:
        if not isinstance(sl, dict):
            continue
        d = (sl.get("date") or "").strip()
        try:
            datetime.strptime(d, "%Y-%m-%d")
        except Exception:
            return jsonify({"error": "日期格式不正確"}), 400
        if d not in seen:
            seen.add(d)
            slots.append({"date": d, "start_time": "", "end_time": ""})
    slots.sort(key=lambda x: x["date"])
    if not slots:
        return jsonify({"error": "請至少選一天您方便的日期"}), 400
    note = (body.get("note") or "").strip()[:300]
    try:
        _patch_task(r["id"], {
            FIELD_TASK_STAGE: TASK_STAGE_WAIT_PM,
            FIELD_TASK_ALT_SLOTS: json.dumps(slots, ensure_ascii=False),
            FIELD_TASK_CHOSEN_SLOT: "",
            FIELD_TASK_REP_NOTE: f"（屋主 {name} {phone}）{note}".strip(),
        })
    except Exception as e:
        return jsonify({"error": "送出失敗，請稍後再試", "detail": str(e)}), 502
    slot_lines = "\n".join(f"{i + 1}. {_wd_label(sl['date'])}" for i, sl in enumerate(slots))
    _notify_owner_action(
        task, "🏠 屋主提供其他日期｜給安排人員", "🏠 屋主提供其他日期｜給業務", "#D97706",
        [("業務", task["assignee"]), ("項目", "、".join(task["type"])), ("廠商", task["vendor"]),
         (f"屋主方便的日期（{len(slots)} 天）", slot_lines), ("屋主", _owner_str(name, phone)), ("屋主備註", note)],
        note_rep="窗口跟廠商確認後會選一天並決定時間，屋主可以在同一個連結按確認",
    )
    return jsonify({"ok": True, "slots": slots})


@app.route("/api/owner-booking/<otoken>/confirm", methods=["POST"])
def owner_booking_confirm(otoken):
    try:
        r = _owner_find_task(otoken)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    if not r:
        return jsonify({"error": "找不到這個預約連結，請直接聯絡您的業務"}), 404
    task = _task_to_dict(r)
    if task["status"] == TASK_STATUS_CANCELLED:
        return jsonify({"error": "這個預約已經取消了，請聯絡窗口或您的業務"}), 409
    if task["status"] == TASK_STATUS_DONE:
        return jsonify({"error": "這個預約已經完成了"}), 409
    chosen = task["chosen_slot"]
    if task["stage"] != TASK_STAGE_WAIT_REP or not chosen:
        return jsonify({"error": "目前還沒有需要確認的時間"}), 409
    body = request.get_json(force=True) or {}
    name, phone, err_msg = _owner_contact(body)
    if err_msg:
        return jsonify({"error": err_msg}), 400
    note = (body.get("note") or "").strip()[:300]
    record, err = _book_vendor_slot(
        task["vendor"], chosen["date"], chosen["start_time"], chosen["end_time"], task["case"], task["alias"],
        task["type"], f"屋主 {name}", note, owner_name=name, owner_phone=phone,
    )
    if err:
        err_body, status = err
        if status == 409:
            return jsonify({"error": "這個時間剛好被別人預約了，請聯絡您的業務重新安排"}), 409
        return jsonify(err_body), status
    try:
        _patch_task(r["id"], {FIELD_TASK_STATUS: TASK_STATUS_DONE, FIELD_TASK_BOOKING_ID: record["id"], FIELD_TASK_STAGE: None})
    except Exception as e:
        print(f"[owner_booking_confirm] 更新任務狀態失敗（預約本身已成功）：{e}", flush=True)
    _notify_owner_action(
        task, "🏠 屋主已確認時間｜給安排人員", "🏠 屋主已確認時間｜給業務", "#16A34A",
        [("業務", task["assignee"]), ("項目", "、".join(task["type"])), ("廠商", task["vendor"]),
         ("時間", f"{_wd_label(chosen['date'])} {chosen['start_time']}-{chosen['end_time']}"),
         ("屋主", _owner_str(name, phone)), ("屋主備註", note)],
        note_rep="屋主已確認時間，前一天請記得再跟屋主確認",
    )
    return jsonify({"ok": True, "booked": chosen})


@app.route("/api/vendor-slots/tasks/<record_id>/owner-link", methods=["POST"])
def vendor_slot_task_owner_link(record_id):
    """主控台「複製屋主版訊息」用：取得（沒有就產生）屋主版連結，回傳組訊息需要的資料。
    舊任務沒有屋主 token／可選時段，第一次按的時候補上（預設 09:00–17:00）。"""
    rec = _get_task_by_record_id(record_id)
    if not rec:
        return jsonify({"error": "找不到這個任務"}), 404
    task = _task_to_dict(rec)
    patch = {}
    if not task["owner_token"]:
        task["owner_token"] = secrets.token_urlsafe(16)
        patch[FIELD_TASK_OWNER_TOKEN] = task["owner_token"]
    if not task["owner_win_start"] or not task["owner_win_end"]:
        ws, we = _owner_window(task)
        patch[FIELD_TASK_OWNER_WIN_START] = ws
        patch[FIELD_TASK_OWNER_WIN_END] = we
        task["owner_win_start"], task["owner_win_end"] = ws, we
    if not task.get("owner_mode"):
        patch[FIELD_TASK_OWNER_MODE] = True
    if patch:
        try:
            _patch_task(record_id, patch)
        except Exception as e:
            return jsonify({"error": "Airtable 寫入失敗", "detail": str(e)}), 502
    ws, we = _owner_window(task)
    return jsonify({
        "ok": True, "owner_path": f"/owner.html?t={task['owner_token']}",
        "items": [OWNER_TYPE_LABELS.get(t, t) for t in task["type"]],
        "candidate_dates": task["candidate_dates"], "duration_min": _owner_duration(task),
        "window_start": ws, "window_end": we, "assignee": task["assignee"], "status": task["status"],
        "assignee_bound": bool(task["assignee"] and _get_line_binding(task["assignee"])),
        "rep_bind_url": _rep_bind_url(task["assignee"]),
    })


# ===================================================================
# 2026-10-08：通知廠商。主控台「完成安排」每筆預約按「📤 通知廠商」→ PM 確認屋主聯絡資料
# （預設帶公證書/合約上的資料）→ 產生 LIFF 分享連結 → PM 用手機 LINE 開啟、用
# shareTargetPicker 選廠商群組，把卡片以 PM 本人身分傳進群組（機器人不需要在群組裡、
# 也不需要 groupId）。傳送完成後回寫「廠商通知時間」。
# 需要在 LINE Developers「陽光填單」channel 的 LIFF 頁打開 shareTargetPicker。
# ===================================================================
def _get_booking(record_id):
    resp = requests.get(f"{SLOT_API_URL}/{record_id}", headers=airtable_headers(),
                        params={"returnFieldsByFieldId": "true"}, timeout=20)
    return resp.json() if resp.status_code < 400 else None


def _vendor_notice_card(rec):
    from urllib.parse import quote
    f = rec.get("fields", {})
    case_no = f.get(FIELD_SLOT_CASE_NO, "")
    address = ""
    coords = None
    if case_no:
        try:
            esc = case_no.replace("'", chr(92) + "'")
            recs = airtable_get_all(CASE_API_URL, "{" + FIELD_CASE_NO + "}='" + esc + "'",
                                    [FIELD_CASE_NO, FIELD_ADDRESS, FIELD_PLANT_COORDS])
            if recs:
                address = " ".join((recs[0]["fields"].get(FIELD_ADDRESS) or "").split())
                coords = _parse_coords(recs[0]["fields"].get(FIELD_PLANT_COORDS))
        except Exception as e:
            print(f"[_vendor_notice_card] 查地址失敗：{e}", flush=True)
        # 座標以業務自治區為準（使用者指定），沒有才用 Airtable 案件表的電廠座標
        try:
            _ensure_biz_snapshots_loaded()
            biz = _parse_coords(BIZ_COORDS_CACHE.get(case_no))
            if biz:
                coords = biz
        except Exception as e:
            print(f"[_vendor_notice_card] 查業務自治區座標失敗：{e}", flush=True)
    rep_name = f.get(FIELD_SLOT_REGISTRANT, "")
    try:
        trs = airtable_get_all(TASK_API_URL, "{" + FIELD_TASK_BOOKING_ID + "}='" + rec["id"] + "'", [FIELD_TASK_ASSIGNEE])
        if trs and trs[0]["fields"].get(FIELD_TASK_ASSIGNEE):
            rep_name = trs[0]["fields"][FIELD_TASK_ASSIGNEE]
    except Exception:
        pass
    date = f.get(FIELD_SLOT_DATE, "")
    return _card(
        "📋 施工排程通知｜給廠商", "#2563EB", f"{case_no} {f.get(FIELD_SLOT_ALIAS, '')}".strip(),
        rows=[("廠商", f.get(FIELD_SLOT_VENDOR, "")), ("項目", "、".join(f.get(FIELD_SLOT_TYPE) or [])),
              ("時間", f"{_wd_label(date)} {f.get(FIELD_SLOT_START, '')}-{f.get(FIELD_SLOT_END, '')}"),
              ("地址", address), ("座標", coords or ""),
              ("屋主", _owner_str(f.get(FIELD_SLOT_OWNER_NAME), f.get(FIELD_SLOT_OWNER_PHONE))),
              ("業務", rep_name), ("現場備註", (f.get(FIELD_SLOT_NOTE) or "").strip()),
              ("陽光備註", (f.get(FIELD_SLOT_PM_NOTE) or "").strip())],
        buttons=_vendor_card_buttons(f, address, coords),
    )


# 2026-10-08：案件表「電廠座標」（業務標的，格式像「24.921159,121.071300」，偶爾有空白/tab）
FIELD_PLANT_COORDS = "fldrgbALndLShwtxd"


def _parse_coords(raw):
    """從座標文字抓出 (緯度, 經度)；格式不對或不在合理範圍就回 None（改用地址）。"""
    import re
    nums = re.findall(r"-?\d+(?:\.\d+)?", raw or "")
    if len(nums) < 2:
        return None
    sa, sb = nums[0], nums[1]
    a, b = float(sa), float(sb)
    if abs(a) > 90 and abs(b) <= 90:   # 經緯度填反
        a, b, sa, sb = b, a, sb, sa
    if not (-90 <= a <= 90 and -180 <= b <= 180) or (a == 0 and b == 0):
        return None
    return f"{sa},{sb}"


def _vendor_card_buttons(f, address, coords=None):
    """給廠商卡片的按鈕：撥號給屋主（tel:，手機會直接帶號碼到撥號畫面）、開啟地圖、複製屋主資料。
    地圖優先用電廠座標（比地址查詢準），沒有座標才用地址。"""
    from urllib.parse import quote
    name = (f.get(FIELD_SLOT_OWNER_NAME) or "").strip()
    phone = (f.get(FIELD_SLOT_OWNER_PHONE) or "").strip()
    dial = "".join(c for c in phone if c.isdigit() or c == "+")
    buttons = []
    if len(dial) >= 8:
        buttons.append(("📞 撥號給屋主", "tel:" + dial))
    if coords:
        buttons.append(("📍 開啟地圖（座標）", "https://www.google.com/maps/search/?api=1&query=" + quote(coords)))
    elif address:
        buttons.append(("📍 開啟地圖", "https://www.google.com/maps/search/?api=1&query=" + quote(address)))
    copy_lines = [x for x in [f"屋主：{_owner_str(name, phone)}" if (name or phone) else "",
                              f"地址：{address}" if address else "", f"座標：{coords}" if coords else ""] if x]
    if copy_lines:
        buttons.append(("📋 複製屋主資料", {"clipboard": "\n".join(copy_lines)}))
    return buttons


def _card_alt(card):
    return (card["tag"] + "：" + card["title"] + "｜" + "｜".join(f"{k}{v}" for k, v in (card.get("rows") or []) if v not in (None, "")))[:390]


@app.route("/api/vendor-slots/<record_id>/vendor-notice", methods=["POST"])
def vendor_slot_vendor_notice(record_id):
    """存屋主聯絡資料（＋給廠商備註），產生 LIFF 分享連結。body: {owner_name, owner_phone, pm_note}"""
    body = request.get_json(force=True) or {}
    rec = _get_booking(record_id)
    if not rec:
        return jsonify({"error": "找不到這筆預約"}), 404
    f = rec.get("fields", {})
    token = f.get(FIELD_SLOT_VENDOR_TOKEN) or secrets.token_urlsafe(16)
    patch = {
        FIELD_SLOT_OWNER_NAME: (body.get("owner_name") or "").strip()[:40],
        FIELD_SLOT_OWNER_PHONE: (body.get("owner_phone") or "").strip()[:40],
        FIELD_SLOT_PM_NOTE: (body.get("pm_note") or "").strip()[:500],
        FIELD_SLOT_VENDOR_TOKEN: token,
    }
    resp = requests.patch(f"{SLOT_API_URL}/{record_id}", headers=airtable_headers(), json={"fields": patch}, timeout=20)
    if resp.status_code >= 400:
        return jsonify({"error": "Airtable 寫入失敗", "detail": resp.text}), 502
    rec = _get_booking(record_id) or rec   # PATCH 的回傳用欄位名稱當 key，重新用欄位 ID 讀一次
    liff_id = os.environ.get("LIFF_ID", "").strip()
    return jsonify({
        "ok": True,
        "liff_url": f"https://liff.line.me/{liff_id}?vshare={token}" if liff_id else "",
        "plain_text": _card_plain_text(_vendor_notice_card(rec)),
    })


def _find_booking_by_vendor_token(token):
    token = (token or "").strip()
    if len(token) < 10:
        return None
    esc = token.replace("'", chr(92) + "'")
    recs = airtable_get_all(SLOT_API_URL, "{" + FIELD_SLOT_VENDOR_TOKEN + "}='" + esc + "'", [FIELD_SLOT_VENDOR_TOKEN])
    return _get_booking(recs[0]["id"]) if recs else None


@app.route("/api/vendor-share/<token>")
def vendor_share_get(token):
    try:
        rec = _find_booking_by_vendor_token(token)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    if not rec:
        return jsonify({"error": "找不到這則廠商通知，可能已失效，請回主控台重新產生"}), 404
    card = _vendor_notice_card(rec)
    return jsonify({"card": card, "flex": _card_to_flex(card), "alt": _card_alt(card),
                    "sent_at": rec.get("fields", {}).get(FIELD_SLOT_VENDOR_NOTIFIED, "")})


@app.route("/api/vendor-share/<token>/sent", methods=["POST"])
def vendor_share_sent(token):
    try:
        rec = _find_booking_by_vendor_token(token)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    if not rec:
        return jsonify({"error": "找不到這則廠商通知"}), 404
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%dT%H:%M:%S+08:00")
    resp = requests.patch(f"{SLOT_API_URL}/{rec['id']}", headers=airtable_headers(),
                          json={"fields": {FIELD_SLOT_VENDOR_NOTIFIED: now}}, timeout=20)
    if resp.status_code >= 400:
        return jsonify({"error": "寫入失敗", "detail": resp.text}), 502
    return jsonify({"ok": True, "sent_at": now})


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
    coords_in = body.get("plant_coords")
    if isinstance(coords_in, list):
        new_coords = {}
        for c in coords_in:
            if isinstance(c, dict) and (c.get("case") or "").strip() and (c.get("coords") or "").strip():
                new_coords[c["case"].strip()] = c["coords"].strip()
        BIZ_COORDS_CACHE.clear()
        BIZ_COORDS_CACHE.update(new_coords)
    threading.Thread(target=_persist_biz_snapshots, daemon=True).start()
    print(
        f"[site_survey_cancelled_sync] 收到 {len(CANCELLED_CASE_CACHE['case_nos'])} 筆取消案號、"
        f"{len(CERTIFIED_CASE_CACHE['cases'])} 筆已公證案件、{len(OWNER_CONTACT_CACHE)} 筆屋主聯絡資訊、"
        f"{len(BIZ_COORDS_CACHE)} 筆電廠座標",
        flush=True,
    )
    return jsonify({
        "ok": True,
        "count": len(CANCELLED_CASE_CACHE["case_nos"]),
        "certified_count": len(CERTIFIED_CASE_CACHE["cases"]),
        "owner_contact_count": len(OWNER_CONTACT_CACHE),
        "plant_coords_count": len(BIZ_COORDS_CACHE),
    })


# 2026-10-08：業務自治區推送的「電廠座標」（{案號: 座標文字}）。給廠商通知卡片的地圖按鈕用，
# 使用者指定以業務自治區為準（Airtable 案件表的電廠座標只當備援）。
# 記憶體快取在 Render 重啟後會清空，所以每次推送也存一份 JSON 快照到「系統狀態」表的「長值」，
# 快取是空的時候先從快照還原（公證書屋主資料 OWNER_CONTACT_CACHE 也一樣處理）。
BIZ_COORDS_CACHE = {}
STATE_FIELD_LONG = "fld4BuR3sfKTkDvsi"   # 系統狀態「長值」（multilineText）
_BIZ_SNAPSHOT_LOADED = {"done": False}


def _state_get_long(key):
    esc = key.replace("'", chr(92) + "'")
    recs = airtable_get_all(STATE_API_URL, "{" + STATE_FIELD_KEY + "}='" + esc + "'", [STATE_FIELD_KEY, STATE_FIELD_LONG])
    return (recs[0]["fields"].get(STATE_FIELD_LONG) or "") if recs else ""


def _state_set_long(key, text):
    esc = key.replace("'", chr(92) + "'")
    recs = airtable_get_all(STATE_API_URL, "{" + STATE_FIELD_KEY + "}='" + esc + "'", [STATE_FIELD_KEY])
    fields = {STATE_FIELD_KEY: key, STATE_FIELD_LONG: text, STATE_FIELD_VALUE: datetime.now().isoformat()}
    if recs:
        resp = requests.patch(f"{STATE_API_URL}/{recs[0]['id']}", headers=airtable_headers(), json={"fields": fields}, timeout=30)
    else:
        resp = requests.post(STATE_API_URL, headers=airtable_headers(), json={"fields": fields}, timeout=30)
    if resp.status_code >= 400:
        raise Exception(resp.text)


def _persist_biz_snapshots():
    try:
        if BIZ_COORDS_CACHE:
            _state_set_long("biz_plant_coords", json.dumps(BIZ_COORDS_CACHE, ensure_ascii=False))
        if OWNER_CONTACT_CACHE:
            _state_set_long("biz_owner_contacts", json.dumps(OWNER_CONTACT_CACHE, ensure_ascii=False))
    except Exception as e:
        print(f"[_persist_biz_snapshots] 存快照失敗：{e}", flush=True)


def _ensure_biz_snapshots_loaded():
    """快取是空的（剛重啟、Apps Script 還沒推送）時，從 Airtable 快照還原一次。"""
    if _BIZ_SNAPSHOT_LOADED["done"]:
        return
    _BIZ_SNAPSHOT_LOADED["done"] = True
    try:
        if not BIZ_COORDS_CACHE:
            raw = _state_get_long("biz_plant_coords")
            if raw:
                BIZ_COORDS_CACHE.update(json.loads(raw))
        if not OWNER_CONTACT_CACHE:
            raw = _state_get_long("biz_owner_contacts")
            if raw:
                OWNER_CONTACT_CACHE.update(json.loads(raw))
    except Exception as e:
        _BIZ_SNAPSHOT_LOADED["done"] = False
        print(f"[_ensure_biz_snapshots_loaded] 還原快照失敗：{e}", flush=True)


@app.route("/api/owner-contact")
def get_owner_contact():
    """給前端選定案號後查屋主姓名/電話用（見 OWNER_CONTACT_CACHE 說明）。
    query params: case（完整案號，需完全相符）"""
    case_no = (request.args.get("case") or "").strip()
    if not case_no:
        return jsonify({"found": False})
    _ensure_biz_snapshots_loaded()
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


# ---- 2026-10-07：LINE 通知改用 Flex Message「卡片」（上方色塊標示「這則是給誰的／什麼事」）----
# 色塊顏色：橘＝給業務的提醒、藍＝給安排人員、綠＝完成、琥珀＝需要處理、紫＝明天行程、青綠＝總覽。
# Flex 推播失敗（例如格式有問題）會自動退回純文字，不讓通知消失。
def _dash_url():
    return os.environ.get("DASHBOARD_BASE_URL", "https://epc-dashboard-ee5f.onrender.com").strip().rstrip("/")


def _wd_label(date_str):
    """'2026-10-08' → '10/08（週四）'"""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{d.strftime('%m/%d')}（週{WEEKDAY_ZH[d.weekday()]}）"
    except Exception:
        return date_str or ""


def _card(tag, color, title, subtitle="", rows=None, sections=None, note="", button=None, footer="", buttons=None):
    return {"tag": tag, "color": color, "title": title, "subtitle": subtitle, "rows": rows or [],
            "sections": sections or [], "note": note, "button": button, "footer": footer, "buttons": buttons or []}


def _card_to_flex(card):
    contents = [{"type": "text", "text": card["title"] or "（無標題）", "weight": "bold", "size": "lg", "wrap": True}]
    if card.get("subtitle"):
        contents.append({"type": "text", "text": card["subtitle"], "size": "sm", "color": "#6B7280", "wrap": True, "margin": "xs"})
    rows = [(k, v) for k, v in (card.get("rows") or []) if v not in (None, "")]
    if rows:
        contents.append({"type": "separator", "margin": "md"})
    for k, v in rows:
        contents.append({"type": "box", "layout": "baseline", "margin": "sm", "spacing": "sm", "contents": [
            {"type": "text", "text": str(k), "size": "sm", "color": "#6B7280", "flex": 2},
            {"type": "text", "text": str(v), "size": "sm", "color": "#1B2333", "wrap": True, "flex": 5},
        ]})
    for heading, lines in card.get("sections") or []:
        contents.append({"type": "text", "text": heading, "size": "sm", "weight": "bold", "color": card["color"], "margin": "lg"})
        for ln in lines:
            contents.append({"type": "text", "text": ln, "size": "sm", "wrap": True, "margin": "xs", "color": "#1B2333"})
    if card.get("note"):
        contents.append({"type": "text", "text": card["note"], "size": "sm", "wrap": True, "margin": "lg", "color": "#B45309", "weight": "bold"})
    bubble = {
        "type": "bubble", "size": "mega",
        "header": {"type": "box", "layout": "vertical", "backgroundColor": card["color"], "paddingAll": "12px",
                   "contents": [{"type": "text", "text": card["tag"], "color": "#FFFFFF", "weight": "bold", "size": "sm", "wrap": True}]},
        "body": {"type": "box", "layout": "vertical", "paddingAll": "14px", "contents": contents},
    }
    footer = []
    buttons = list(card.get("buttons") or [])
    if card.get("button"):
        buttons.insert(0, card["button"])
    for i, (label, target) in enumerate(buttons):
        if isinstance(target, dict) and "clipboard" in target:
            # LINE 卡片上的文字不能直接複製，用「複製」按鈕把內容放進剪貼簿
            action = {"type": "clipboard", "label": label, "clipboardText": target["clipboard"][:1000]}
        else:
            action = {"type": "uri", "label": label, "uri": target}
        btn = {"type": "button", "height": "sm", "action": action, "margin": "sm" if i else "none"}
        if i == 0:
            btn.update({"style": "primary", "color": card["color"]})
        else:
            btn.update({"style": "secondary"})
        footer.append(btn)
    if card.get("footer"):
        footer.append({"type": "text", "text": card["footer"], "size": "xs", "color": "#6B7280", "wrap": True, "margin": "md"})
    if footer:
        bubble["footer"] = {"type": "box", "layout": "vertical", "paddingAll": "12px", "contents": footer}
    return bubble


def _card_plain_text(card):
    lines = [card["tag"], card["title"]]
    if card.get("subtitle"):
        lines.append(card["subtitle"])
    lines += [f"{k}：{v}" for k, v in (card.get("rows") or []) if v not in (None, "")]
    for heading, sec in card.get("sections") or []:
        lines.append("\n" + heading)
        lines += sec
    if card.get("note"):
        lines.append("\n" + card["note"])
    if card.get("footer"):
        lines.append("\n" + card["footer"])
    return "\n".join(lines)


def _line_push_card(card, to=None):
    token, default_target = _line_config()
    target = to or default_target
    if not token or not target:
        return False, "LINE 環境變數未設定"
    alt = (card["tag"] + "：" + card["title"] + "｜" + "｜".join(f"{k}{v}" for k, v in (card.get("rows") or []) if v not in (None, "")))[:390]
    try:
        resp = requests.post(
            LINE_PUSH_URL,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"to": target, "messages": [{"type": "flex", "altText": alt, "contents": _card_to_flex(card)}]},
            timeout=15,
        )
        if resp.status_code < 400:
            return True, ""
        print(f"[_line_push_card] Flex 失敗，改用純文字：{resp.status_code} {resp.text[:200]}", flush=True)
    except Exception as e:
        print(f"[_line_push_card] Flex 例外，改用純文字：{e}", flush=True)
    return _line_push_text(_card_plain_text(card), to=to)


def _owner_str(name, phone):
    return " ".join(x for x in [(name or "").strip(), (phone or "").strip()] if x)


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
        vendor = f.get(FIELD_TASK_VENDOR) or ""
        title = f"{case_no} {alias}".strip()
        dl_text = f"{local.strftime('%H:%M')}（剩約 {max(1, round(remain_min))} 分鐘）"
        stage = f.get(FIELD_TASK_STAGE) or ""
        owner_mode = bool(f.get(FIELD_TASK_OWNER_MODE))
        if owner_mode:
            rep_note = ("窗口已選好時間，請提醒屋主打開連結按「確認」" if stage == TASK_STAGE_WAIT_REP
                        else "屋主還沒填預約表，請提醒屋主在期限前填好；也可以問好時間後自己按下面的按鈕幫屋主填")
        else:
            rep_note = "窗口已選好時段，請進表單按「確認」" if stage == TASK_STAGE_WAIT_REP else "還沒安排時間，請盡快回覆窗口"
        rep_card = _card(
            "⏰ 屋主還沒填預約表｜給業務" if owner_mode else "⏰ 回覆期限快到了｜給業務", "#F2790C", title, subtitle=f"{who} 您好",
            rows=[("項目", types), ("廠商", vendor), ("回覆期限", dl_text)],
            note=rep_note,
            button=("打開填單", f"{_dash_url()}/book.html?token={f[FIELD_TASK_TOKEN]}") if f.get(FIELD_TASK_TOKEN) else None,
        )
        rep_uid = None
        if f.get(FIELD_TASK_ASSIGNEE):
            try:
                rep_uid = _get_line_binding(f[FIELD_TASK_ASSIGNEE])
            except Exception as e:
                print(f"[send_deadline_reminders] 查綁定失敗：{e}", flush=True)
        rep_ok = False
        if rep_uid:
            rep_ok, err = _line_push_card(rep_card, to=rep_uid)
            if not rep_ok:
                print(f"[send_deadline_reminders] {case_no} 推播給業務失敗：{err}", flush=True)
        # 同時通知「安排人員」（建立任務的人）：期限快到、還沒安排完成＋目前狀態
        if owner_mode:
            stage_text = "已選好時間，等屋主按確認" if stage == TASK_STAGE_WAIT_REP else "屋主還沒填預約表"
        else:
            stage_text = {
                TASK_STAGE_WAIT_REP: "已選好時間，等業務按確認",
            }.get(stage, "業務還沒安排")
        creator = (f.get(FIELD_TASK_CREATOR) or "").strip()
        sched_ok = False
        if creator:
            sched_ok = _notify_scheduler(
                creator,
                _card("⏰ 屋主還沒填預約表｜給安排人員" if owner_mode else "⏰ 業務尚未回覆｜給安排人員", "#1E46C4", title,
                      rows=[("指派業務", who), ("項目", types), ("廠商", vendor), ("回覆期限", dl_text), ("目前狀態", stage_text)],
                      button=("開啟主控台", _dash_url() + "/")),
            )
        ok = rep_ok or sched_ok
        if not ok:
            # 業務、安排人員都沒綁定（或推播失敗）→ 轉給預設對象，不要讓提醒默默消失
            if not target:
                continue
            rep_card["tag"] = f"⏰ 回覆期限快到了｜轉給你代為提醒（{who} 尚未綁定 LINE）"
            ok, err = _line_push_card(rep_card)
            if not ok:
                print(f"[send_deadline_reminders] {case_no} 推播失敗：{err}", flush=True)
                continue
        try:
            _patch_task(r["id"], {FIELD_TASK_REMINDED: True})
        except Exception as e:
            print(f"[send_deadline_reminders] {case_no} 標記已提醒失敗：{e}", flush=True)


scheduler.add_job(send_deadline_reminders, CronTrigger(minute="*/5"), id="line_deadline", replace_existing=True,
                  misfire_grace_time=900, coalesce=True, max_instances=1)


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
    """推播給安排人員（用名字對應「業務LINE綁定」表）。headline 可以是卡片（_card）或純文字。
    沒綁定回 False。卡片會在底部附上「你名下的任務」狀態摘要。"""
    creator = (creator or "").strip()
    token, _ = _line_config()
    if not token or not creator:
        return False
    try:
        uid = _get_line_binding(creator)
        if not uid:
            return False
        try:
            summary = _scheduler_summary(creator)
        except Exception as e:
            summary = ""
            print(f"[_notify_scheduler] 組狀態摘要失敗：{e}", flush=True)
        if isinstance(headline, dict):
            card = dict(headline)
            card["footer"] = summary
            ok, err = _line_push_card(card, to=uid)
        else:
            ok, err = _line_push_text(headline + ("\n\n" + summary if summary else ""), to=uid)
        if not ok:
            print(f"[_notify_scheduler] 推播給 {creator} 失敗：{err}", flush=True)
        return ok
    except Exception as e:
        print(f"[_notify_scheduler] 例外：{e}", flush=True)
        return False


def _notify_scheduler_async(creator, headline):
    """在背景執行，不拖慢業務按「完成預約」的回應。"""
    threading.Thread(target=_notify_scheduler, args=(creator, headline), daemon=True).start()


def _owner_note_lines(owner_name, owner_phone, note):
    """通知訊息裡附上業務填的屋主資訊與備註（有填才顯示）。"""
    out = ""
    owner = " ".join(x for x in [(owner_name or "").strip(), (owner_phone or "").strip()] if x)
    if owner:
        out += f"\n屋主：{owner}"
    if (note or "").strip():
        out += f"\n備註：{note.strip()}"
    return out


FIELD_SLOT_DAY_REMINDED = "fldsDdEwnmxc68MR6"  # 已前日提醒（checkbox）
WEEKDAY_ZH = ["一", "二", "三", "四", "五", "六", "日"]


def _push_to_name(name, text):
    """用名字查「業務LINE綁定」表推播；沒綁定或失敗回 False。"""
    name = (name or "").strip()
    if not name:
        return False
    try:
        uid = _get_line_binding(name)
    except Exception as e:
        print(f"[_push_to_name] 查綁定失敗：{e}", flush=True)
        return False
    if not uid:
        return False
    ok, err = _line_push_card(text, to=uid) if isinstance(text, dict) else _line_push_text(text, to=uid)
    if not ok:
        print(f"[_push_to_name] 推播給 {name} 失敗：{err}", flush=True)
    return ok


DAY_BEFORE_STATE = {}  # 最近一次前日提醒排程的執行狀態（給 /api/line/status 看，方便排查）


def send_day_before_reminders():
    DAY_BEFORE_STATE.update({"at": datetime.now().isoformat(), "error": None, "found": None, "sent": 0})
    try:
        _send_day_before_reminders_impl()
    except Exception as e:
        DAY_BEFORE_STATE["error"] = repr(e)
        print(f"[send_day_before_reminders] 例外：{e!r}", flush=True)


def _send_day_before_reminders_impl():
    """2026-10-05：行程前一天中午 12:00（排程每 10 分鐘檢查 12:00–17:50，用「已前日提醒」
    勾選避免重複），LINE 提醒負責的業務跟安排人員：請業務跟屋主提醒明天的行程。
    「負責的業務」＝任務的指派對象（沒有任務、PM 直接預約的，用登記人）；
    「安排人員」＝任務的建立人。都沒綁定就轉給預設對象，不讓提醒默默消失。"""
    token, default_target = _line_config()
    if not token:
        return
    tw = timezone(timedelta(hours=8))
    tomorrow = datetime.now(tw) + timedelta(days=1)
    tmr = tomorrow.strftime("%Y-%m-%d")
    try:
        records = airtable_get_all(
            SLOT_API_URL,
            f"AND({{{FIELD_SLOT_KIND}}}='{SLOT_KIND_BOOKING}',IS_SAME({{{FIELD_SLOT_DATE}}},'{tmr}','day'))",
            [FIELD_SLOT_VENDOR, FIELD_SLOT_DATE, FIELD_SLOT_START, FIELD_SLOT_END, FIELD_SLOT_CASE_NO,
             FIELD_SLOT_ALIAS, FIELD_SLOT_TYPE, FIELD_SLOT_REGISTRANT, FIELD_SLOT_NOTE,
             FIELD_SLOT_OWNER_NAME, FIELD_SLOT_OWNER_PHONE, FIELD_SLOT_DAY_REMINDED],
        )
    except Exception as e:
        print(f"[send_day_before_reminders] 讀取預約失敗：{e}", flush=True)
        DAY_BEFORE_STATE["error"] = f"讀取預約失敗：{e}"
        return
    DAY_BEFORE_STATE["found"] = len(records)
    for r in records:
        f = r["fields"]
        if f.get(FIELD_SLOT_DAY_REMINDED):
            continue
        rep_name = (f.get(FIELD_SLOT_REGISTRANT) or "").strip()
        creator = ""
        try:
            trs = airtable_get_all(TASK_API_URL, f"{{{FIELD_TASK_BOOKING_ID}}}='{r['id']}'",
                                   [FIELD_TASK_ASSIGNEE, FIELD_TASK_CREATOR])
            if trs:
                rep_name = (trs[0]["fields"].get(FIELD_TASK_ASSIGNEE) or rep_name).strip()
                creator = (trs[0]["fields"].get(FIELD_TASK_CREATOR) or "").strip()
        except Exception as e:
            print(f"[send_day_before_reminders] 查任務失敗：{e}", flush=True)
        case_no = f.get(FIELD_SLOT_CASE_NO, "")
        alias = f.get(FIELD_SLOT_ALIAS, "")
        types = "、".join(f.get(FIELD_SLOT_TYPE) or [])
        title = f"{case_no} {alias}".strip()
        base_rows = [
            ("時間", f"明天 {_wd_label(tmr)} {f.get(FIELD_SLOT_START, '')}-{f.get(FIELD_SLOT_END, '')}"),
            ("項目", types), ("廠商", f.get(FIELD_SLOT_VENDOR, "")),
            ("屋主", _owner_str(f.get(FIELD_SLOT_OWNER_NAME), f.get(FIELD_SLOT_OWNER_PHONE))),
            ("備註", (f.get(FIELD_SLOT_NOTE) or "").strip()),
        ]
        rep_card = _card("📅 明天有行程｜給業務", "#7C3AED", title, subtitle=f"{rep_name} 您好" if rep_name else "",
                         rows=base_rows, note="請今天聯絡屋主，提醒明天的行程 🙏")
        rep_ok = _push_to_name(rep_name, rep_card)
        sched_ok = False
        if creator and creator != rep_name:
            sched_ok = _push_to_name(
                creator,
                _card("📅 明天有行程｜給安排人員", "#7C3AED", title, rows=[("業務", rep_name)] + base_rows,
                      note=(f"已通知業務 {rep_name}" if rep_ok else f"業務 {rep_name or '?'} 沒綁定 LINE，請你確認有提醒屋主"),
                      button=("開啟主控台", _dash_url() + "/")),
            )
        ok = rep_ok or sched_ok
        if not ok:
            if not default_target:
                continue
            ok, err = _line_push_card(
                _card("📅 明天有行程｜轉給你代為通知", "#7C3AED", title, rows=[("業務", rep_name)] + base_rows,
                      note="業務／安排人員都沒綁定 LINE")
            )
            if not ok:
                print(f"[send_day_before_reminders] {case_no} 推播失敗：{err}", flush=True)
                continue
        try:
            resp = requests.patch(f"{SLOT_API_URL}/{r['id']}", headers=airtable_headers(),
                                  json={"fields": {FIELD_SLOT_DAY_REMINDED: True}}, timeout=20)
            if resp.status_code >= 400:
                raise Exception(resp.text)
            DAY_BEFORE_STATE["sent"] = DAY_BEFORE_STATE.get("sent", 0) + 1
        except Exception as e:
            print(f"[send_day_before_reminders] {case_no} 標記已前日提醒失敗：{e}", flush=True)


scheduler.add_job(send_day_before_reminders, CronTrigger(hour="12-17", minute="*/10", timezone="Asia/Taipei"), id="line_day_before",
                  replace_existing=True, misfire_grace_time=900, coalesce=True, max_instances=1)


# ---- 2026-10-05：隔天行程總覽（給 PM 本人，不限業務填單的案件）----
# 每天 12:05 起（每 10 分鐘檢查到 17:55，成功發過就不重發），把「明天」所有行程整理成一則
# LINE 訊息傳給預設對象（LINE_REMINDER_TARGET_ID＝PM 本人）：時段預約（場勘/放樣/掛表/植筋/進場…）、
# 模組/逆變器出貨、進場、預計掛表日、植筋日、變流器出貨日、預計場勘日。
# 只列指定廠商（預設 三創/尚展/曙光，可用環境變數 LINE_DIGEST_VENDORS 改，逗號分隔）。
DIGEST_VENDORS = [v.strip() for v in os.environ.get("LINE_DIGEST_VENDORS", "三創,尚展,曙光").split(",") if v.strip()]
DIGEST_STATE = {}

# 「系統狀態」小型鍵值表：記錄隔天總覽最後一次發送的日期。不能只放在記憶體——Render 服務
# 閒置重啟後記憶體就清空，會讓同一天的總覽每小時重發一次（2026-10-07 發生過）。
STATE_TABLE_ID = "tblVreMXHonXqiLQ5"
STATE_FIELD_KEY = "fldrHYI14wJILHojA"
STATE_FIELD_VALUE = "fldFPRxqylDFdtWNg"
STATE_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{STATE_TABLE_ID}"


def _state_get(key):
    esc = key.replace("'", chr(92) + "'")
    recs = airtable_get_all(STATE_API_URL, "{" + STATE_FIELD_KEY + "}='" + esc + "'", [STATE_FIELD_KEY, STATE_FIELD_VALUE])
    return (recs[0]["fields"].get(STATE_FIELD_VALUE) or "") if recs else ""


def _state_set(key, value):
    esc = key.replace("'", chr(92) + "'")
    recs = airtable_get_all(STATE_API_URL, "{" + STATE_FIELD_KEY + "}='" + esc + "'", [STATE_FIELD_KEY])
    fields = {STATE_FIELD_KEY: key, STATE_FIELD_VALUE: value}
    if recs:
        resp = requests.patch(f"{STATE_API_URL}/{recs[0]['id']}", headers=airtable_headers(), json={"fields": fields}, timeout=20)
    else:
        resp = requests.post(STATE_API_URL, headers=airtable_headers(), json={"fields": fields}, timeout=20)
    if resp.status_code >= 400:
        raise Exception(resp.text)


def _collect_tomorrow_events(tmr):
    events, seen = [], set()   # seen：(案號, 項目) 避免「時段預約」跟「預計日期欄位」重複列
    # 1. 廠商時段預約（含 PM 自己直接預約的）
    recs = airtable_get_all(
        SLOT_API_URL,
        f"AND({{{FIELD_SLOT_KIND}}}='{SLOT_KIND_BOOKING}',IS_SAME({{{FIELD_SLOT_DATE}}},'{tmr}','day'))",
        [FIELD_SLOT_VENDOR, FIELD_SLOT_START, FIELD_SLOT_END, FIELD_SLOT_CASE_NO, FIELD_SLOT_ALIAS,
         FIELD_SLOT_TYPE, FIELD_SLOT_REGISTRANT],
    )
    for r in recs:
        f = r["fields"]
        types = f.get(FIELD_SLOT_TYPE) or []
        case_no = f.get(FIELD_SLOT_CASE_NO, "")
        for t in types:
            seen.add((case_no, t))
        events.append({
            "vendor": f.get(FIELD_SLOT_VENDOR) or "", "kind": "/".join(types),
            "time": f"{f.get(FIELD_SLOT_START, '')}-{f.get(FIELD_SLOT_END, '')}",
            "case": case_no, "alias": f.get(FIELD_SLOT_ALIAS, ""),
            "extra": f"業務：{f.get(FIELD_SLOT_REGISTRANT)}" if f.get(FIELD_SLOT_REGISTRANT) else "",
        })
    # 2. 出貨／進場（來自出貨進場排程快取）
    case_vendor = {}
    for lst in (DATA_CACHE.get("pending") or [], DATA_CACHE.get("entry") or [], DATA_CACHE.get("completed") or []):
        for c in lst:
            case_vendor[c.get("case")] = c.get("vendor") or ""
    for c in (DATA_CACHE.get("entry") or []) + (DATA_CACHE.get("completed") or []):
        if c.get("ship_date") == tmr and (c["case"], "出貨") not in seen:
            seen.add((c["case"], "出貨"))
            extra = "；".join(x for x in [f"模組 {c.get('module')}" if c.get("module") else "",
                                          f"變流器 {c.get('inverter')}" if c.get("inverter") else ""] if x)
            events.append({"vendor": c.get("vendor") or "", "kind": "出貨", "time": "", "case": c["case"],
                           "alias": c.get("alias", ""), "extra": extra})
    for c in DATA_CACHE.get("completed") or []:
        if c.get("entry_date") == tmr and (c["case"], "進場") not in seen:
            seen.add((c["case"], "進場"))
            events.append({"vendor": c.get("vendor") or "", "kind": "進場", "time": "", "case": c["case"],
                           "alias": c.get("alias", ""), "extra": ""})
    # 3. APP資料「案件狀態」裡手動填的日期
    for row in app_data_get_all("{類型}='案件狀態'"):
        f = row["fields"]
        case_no = f.get("案號", "")
        for field_name, kind in (("預計掛表日期", "掛表"), ("植筋日期", "植筋"), ("變流器出貨日期", "變流器出貨")):
            if f.get(field_name) == tmr and (case_no, kind) not in seen:
                seen.add((case_no, kind))
                events.append({"vendor": case_vendor.get(case_no, ""), "kind": kind, "time": "", "case": case_no,
                               "alias": "", "extra": ""})
    # 4. 預計場勘日（場勘 base）
    for c in SURVEY_CACHE.get("cases") or []:
        if c.get("planned_date") == tmr and (c.get("case"), "場勘") not in seen:
            seen.add((c.get("case"), "場勘"))
            events.append({"vendor": c.get("vendor") or "", "kind": "場勘", "time": "", "case": c.get("case", ""),
                           "alias": c.get("alias", ""), "extra": f"業務：{c['sales_person']}" if c.get("sales_person") else ""})
    # 廠商還不知道的（例如案件已不在出貨進場排程裡），直接去案件表用案號查
    missing = sorted({e["case"] for e in events if not e["vendor"] and e["case"]})
    for i in range(0, len(missing), 20):
        chunk = missing[i:i + 20]
        formula = "OR(" + ",".join("{" + FIELD_CASE_NO + "}='" + c.replace("'", chr(92) + "'") + "'" for c in chunk) + ")"
        try:
            vm = {r["fields"].get(FIELD_CASE_NO): (r["fields"].get(FIELD_VENDOR) or "")
                  for r in airtable_get_all(CASE_API_URL, formula, [FIELD_CASE_NO, FIELD_VENDOR])}
        except Exception as e:
            print(f"[_collect_tomorrow_events] 查廠商失敗：{e}", flush=True)
            continue
        for ev in events:
            if not ev["vendor"] and ev["case"] in vm:
                ev["vendor"] = vm[ev["case"]]
    return [e for e in events if (not e["vendor"]) or e["vendor"] in DIGEST_VENDORS]


def send_tomorrow_digest(force=False):
    token, target = _line_config()
    if not token or not target:
        return
    tw = timezone(timedelta(hours=8))
    tomorrow = datetime.now(tw) + timedelta(days=1)
    tmr = tomorrow.strftime("%Y-%m-%d")
    if not force:
        if DIGEST_STATE.get("sent_for") == tmr:
            return
        try:
            if _state_get("digest_sent_for") == tmr:
                DIGEST_STATE["sent_for"] = tmr
                return
        except Exception as e:
            # 讀不到「發過沒」就寧可不發，避免重複轟炸；下一輪（10 分鐘後）會再試
            DIGEST_STATE["error"] = f"讀取發送紀錄失敗：{e}"
            print(f"[send_tomorrow_digest] 讀取發送紀錄失敗，本輪不發：{e}", flush=True)
            return
    DIGEST_STATE.update({"at": datetime.now().isoformat(), "for": tmr, "count": None, "error": None})
    try:
        events = _collect_tomorrow_events(tmr)
    except Exception as e:
        DIGEST_STATE["error"] = repr(e)
        print(f"[send_tomorrow_digest] 收集行程失敗：{e!r}", flush=True)
        return
    DIGEST_STATE["count"] = len(events)
    if not events:
        return
    by_vendor = {}
    for e in events:
        by_vendor.setdefault(e["vendor"] or "（廠商未知）", []).append(e)
    sections = []
    for vendor in sorted(by_vendor):
        lines = []
        for e in sorted(by_vendor[vendor], key=lambda x: (x["time"] or "99", x["kind"])):
            head = f"• {e['kind']}" + (f" {e['time']}" if e["time"] else "")
            lines.append(f"{head}｜{e['case']} {e['alias']}".rstrip() + (f"（{e['extra']}）" if e["extra"] else ""))
        sections.append((f"【{vendor}】", lines))
    card = _card("📅 明日行程總覽｜給你", "#0F766E", f"明天 {_wd_label(tmr)}", subtitle=f"共 {len(events)} 筆",
                 sections=sections, button=("開啟主控台", _dash_url() + "/"))
    ok, err = _line_push_card(card)
    if ok:
        DIGEST_STATE["sent_for"] = tmr
        try:
            _state_set("digest_sent_for", tmr)
        except Exception as e:
            print(f"[send_tomorrow_digest] 寫入發送紀錄失敗（可能造成重發）：{e}", flush=True)
            DIGEST_STATE["error"] = f"寫入發送紀錄失敗：{e}"
    else:
        DIGEST_STATE["error"] = err
        print(f"[send_tomorrow_digest] 推播失敗：{err}", flush=True)


scheduler.add_job(send_tomorrow_digest, CronTrigger(hour="12-17", minute="5,15,25,35,45,55", timezone="Asia/Taipei"),
                  id="line_digest", replace_existing=True, misfire_grace_time=900, coalesce=True, max_instances=1)


@app.route("/api/line/run-job", methods=["POST"])
def line_run_job():
    """管理用：手動跑一次 LINE 排程工作（排查用，需要同步密鑰）。body: {key, job}，
    job＝deadline（回覆期限提醒）或 day_before（前日提醒）。同步執行並回傳執行狀態。"""
    body = request.get_json(force=True) or {}
    if not BIZ_SHEET_SYNC_KEY or body.get("key") != BIZ_SHEET_SYNC_KEY:
        return jsonify({"error": "unauthorized"}), 401
    job = body.get("job")
    if job == "day_before":
        send_day_before_reminders()
        return jsonify({"ok": True, "state": DAY_BEFORE_STATE})
    if job == "deadline":
        send_deadline_reminders()
        return jsonify({"ok": True})
    if job == "digest":
        send_tomorrow_digest(force=bool(body.get("force")))
        return jsonify({"ok": True, "state": DIGEST_STATE})
    return jsonify({"error": "job 必須是 deadline 或 day_before"}), 400


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


def _rep_bind_url(name):
    from urllib.parse import quote
    liff_id = os.environ.get("LIFF_ID", "").strip()
    if not liff_id or not (name or "").strip():
        return ""
    return f"https://liff.line.me/{liff_id}?bind=rep&name={quote(name.strip())}"


@app.route("/api/line/bound-names")
def line_bound_names():
    """已綁定 LINE 的所有名字（業務＋安排人員），主控台用來顯示「業務有沒有綁定」。不回 userId。"""
    try:
        recs = airtable_get_all(LINE_BIND_API_URL, f"NOT({{{FIELD_BIND_UID}}}='')", [FIELD_BIND_NAME, FIELD_BIND_UID])
        names = sorted({(r["fields"].get(FIELD_BIND_NAME) or "").strip() for r in recs if r["fields"].get(FIELD_BIND_UID)} - {""})
        return jsonify({"names": names})
    except Exception as e:
        return jsonify({"error": str(e), "names": []}), 502


@app.route("/api/line/rep-bind-url")
def line_rep_bind_url():
    name = (request.args.get("name") or "").strip()
    return jsonify({"url": _rep_bind_url(name)})


@app.route("/api/line/bind-rep", methods=["POST"])
def line_bind_rep():
    """業務自己用綁定連結（book.html?bind=rep&name=名字）綁 LINE，不需要先有任務連結。
    跟安排人員綁定一樣用 access token 向 LINE 驗證 userId；不會動到「安排人員」勾選。body: {access_token, name}"""
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
        fields = {FIELD_BIND_NAME: name, FIELD_BIND_UID: user_id, FIELD_BIND_DISPLAY: display}
        existing = _find_line_binding_record(name)
        if existing:
            resp = requests.patch(f"{LINE_BIND_API_URL}/{existing['id']}", headers=airtable_headers(),
                                  json={"fields": fields}, timeout=20)
        else:
            resp = requests.post(LINE_BIND_API_URL, headers=airtable_headers(), json={"fields": fields}, timeout=20)
        if resp.status_code >= 400:
            return jsonify({"error": "寫入失敗", "detail": resp.text}), 502
        return jsonify({"ok": True, "display_name": display, "name": name})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


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
        "day_before_last_run": DAY_BEFORE_STATE,
        "digest_last_run": DIGEST_STATE,
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


# ===================================================================
# 採購專區：變流器出廠證明歸檔紀錄（2026-10-07）
# ===================================================================
# 資料由使用者電腦上的 Claude 每日排程（cps-inverter-cert-sync）寫入：
# 每天 09:00 從碩天 CPSDrive 下載新的出廠暨保固證明書，歸檔到 G 槽案件
# 「07 設備保固及出廠證明」，再把結果寫進這張表。本後端只負責讀取，以及讓
# 使用者在主控台勾選「簡稱已確認」（推定的簡稱，例如 桃81，需人工確認一次）。
CERT_TABLE_ID = "tblNy1ls9aFLVMxHh"
CERT_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{CERT_TABLE_ID}"
CERT_FIELD_SRC_NAME = "fldA1EYvZ95wAGH1e"      # 原檔名（primary field）
CERT_FIELD_CASE_NO = "fld7suIlvN4YfwwE8"       # 案號（非案件為空）
CERT_FIELD_FILED_NAME = "fldwmZUgwyjE7DhL6"    # 歸檔檔名
CERT_FIELD_PATH = "fldHxASfgq18rbHyi"          # 放置路徑（G 槽資料夾）
CERT_FIELD_STATUS = "fldormzJT0aa8BWJs"        # 狀態：已歸檔／未歸檔／已存在
CERT_FIELD_ABBR_GUESSED = "fldzguJVqi14cBORj"  # 簡稱推定
CERT_FIELD_SHIP_DATE = "fldLuclXuC9N2YHf5"     # 出廠日期
CERT_FIELD_FILED_AT = "fldg52kpcleAmN2VH"      # 歸檔時間
CERT_FIELD_VENDOR = "flde14fVfgIONZ41p"        # 廠商（變流器廠，目前只有碩天）
CERT_FIELD_ABBR_OK = "fldn3CSuGgMjfOyNl"       # 簡稱已確認
# 以下 4 欄由本機 cert_agent.py（每分鐘）維護：主控台只寫「改名為」，實際改名在
# 使用者電腦的 G 槽執行，成功後清空「改名為」、更新「歸檔檔名」並寫「改名結果」。
CERT_FIELD_FILE = "fldqHpiW4nxDPOKOe"          # 檔案（PDF 附件，懸浮視窗預覽用）
CERT_FIELD_LISTING = "fldPzyenX1YJnwyqN"       # 資料夾檔案（放置資料夾目前的檔案清單，一行一個）
CERT_FIELD_RENAME_TO = "fldyc3EBmDTH0zWi8"     # 改名為（待處理的改名請求）
CERT_FIELD_RENAME_RESULT = "fldchBvCfrWH9ieFO" # 改名結果
# 2026-10-07 加入模組（元晶，Email → Apps Script → 收件匣 → 本機歸檔）後新增：
CERT_FIELD_EQUIPMENT = "fldx2emVeNU4E6CPJ"     # 設備類型：變流器／模組
CERT_FIELD_DOC_TYPE = "fldKeqpCoafrBw7Ex"      # 文件類型：出廠證明／序號表／發票／其他


@app.route("/api/procurement/inverter-certs")
def procurement_inverter_certs():
    try:
        records = airtable_get_all(CERT_API_URL, None, [
            CERT_FIELD_SRC_NAME, CERT_FIELD_CASE_NO, CERT_FIELD_FILED_NAME, CERT_FIELD_PATH,
            CERT_FIELD_STATUS, CERT_FIELD_ABBR_GUESSED, CERT_FIELD_SHIP_DATE,
            CERT_FIELD_FILED_AT, CERT_FIELD_VENDOR, CERT_FIELD_ABBR_OK,
            CERT_FIELD_FILE, CERT_FIELD_LISTING, CERT_FIELD_RENAME_TO, CERT_FIELD_RENAME_RESULT,
            CERT_FIELD_EQUIPMENT, CERT_FIELD_DOC_TYPE,
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    rows = []
    for r in records:
        f = r.get("fields", {})
        rows.append({
            "id": r["id"],
            "src_name": f.get(CERT_FIELD_SRC_NAME, ""),
            "case_no": f.get(CERT_FIELD_CASE_NO, ""),
            "filed_name": f.get(CERT_FIELD_FILED_NAME, ""),
            "path": f.get(CERT_FIELD_PATH, ""),
            "status": f.get(CERT_FIELD_STATUS, ""),
            "abbr_guessed": bool(f.get(CERT_FIELD_ABBR_GUESSED)),
            "abbr_ok": bool(f.get(CERT_FIELD_ABBR_OK)),
            "ship_date": f.get(CERT_FIELD_SHIP_DATE, ""),
            "filed_at": f.get(CERT_FIELD_FILED_AT, ""),
            "vendor": f.get(CERT_FIELD_VENDOR, ""),
            "file_url": (f.get(CERT_FIELD_FILE) or [{}])[0].get("url", ""),
            "folder_files": [x for x in (f.get(CERT_FIELD_LISTING) or "").split("\n") if x],
            "rename_to": f.get(CERT_FIELD_RENAME_TO, ""),
            "rename_result": f.get(CERT_FIELD_RENAME_RESULT, ""),
            "equipment": f.get(CERT_FIELD_EQUIPMENT, "") or "變流器",
            "doc_type": f.get(CERT_FIELD_DOC_TYPE, "") or "出廠證明",
            "file_name": (f.get(CERT_FIELD_FILE) or [{}])[0].get("filename", ""),
        })
    rows.sort(key=lambda x: x["filed_at"] or "", reverse=True)
    return jsonify({"certs": rows})


# ---- 設備資料盤點（2026-10-07）----
# 已進場／已掛表但尚未取得設備登記的潤特／工程案件，07 資料夾是否備齊 5 項設備文件。
# 由使用者電腦上的 cert_agent.py 每小時呼叫 equipment_inventory.sync() 覆寫（本後端看不到 G 槽）。
INV_TABLE_ID = "tbl4Cw68D1gx8BJ9a"
INV_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{INV_TABLE_ID}"
INV_FIELDS = {
    "case_no": "fldX4rFo0Mb6eoojj", "alias": "fldq2K6GCBvtPyVZj", "vendor": "fldFXTdNJ93TNM4Bv",
    "stage": "fld9z57gYbUIATIUp", "meter_date": "fldaAWEpbUrEUhcQB",
    "module_cert": "fldbpPDC1TeYblecn", "module_serial": "fldVN11gCbdaFtM7U", "module_invoice": "fldFJTdnmctnYmNWI",
    "inverter_cert": "fld09sMcyzVOp3Sb3", "inverter_invoice": "fldFf0omtjK60gRQr",
    "missing": "fldnNG8uIsTXlXjAE", "path": "fldbBn2h0FMaBYbW9", "files": "fldoQigIFPHRmyNsf",
    "updated_at": "fldawjwCFSu5vW8g3",
}
INV_CHECKS = ["module_cert", "module_serial", "module_invoice", "inverter_cert", "inverter_invoice"]


@app.route("/api/procurement/equipment-inventory")
def procurement_equipment_inventory():
    try:
        records = airtable_get_all(INV_API_URL, None, list(INV_FIELDS.values()))
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    rows = []
    for r in records:
        f = r.get("fields", {})
        row = {k: f.get(fid) for k, fid in INV_FIELDS.items()}
        for k in INV_CHECKS:
            row[k] = bool(row[k])
        row["missing"] = row["missing"] or 0
        row["files"] = [x for x in (row["files"] or "").split("\n") if x]
        row["id"] = r["id"]
        rows.append(row)
    rows.sort(key=lambda x: (-x["missing"], x["case_no"] or ""))
    return jsonify({"cases": rows})


# ---- 資料夾檔案預覽（2026-10-07）----
# 懸浮視窗點檔名預覽：07 資料夾的檔案由使用者電腦的 folder_preview.py 同步到「採購-資料夾預覽」
# （一個資料夾一筆、檔案放附件欄）。Airtable 附件網址約 2 小時過期，所以快取只放 60 秒。
FOLDER_PREVIEW_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/tblncHNB3oJZLXNR9"
FP_FIELD_PATH = "fldrmeBh8FbnteKh7"
FP_FIELD_FILES = "fld5yzzqe9nEgENME"
FP_FIELD_SKIPPED = "fldUELTpnTeUxehP8"
_FOLDER_PREVIEW_CACHE = {"at": 0, "by_path": {}}


@app.route("/api/procurement/folder-files")
def procurement_folder_files():
    path = (request.args.get("path") or "").strip()
    if not path:
        return jsonify({"error": "缺少 path"}), 400
    if time.time() - _FOLDER_PREVIEW_CACHE["at"] > 60:
        try:
            records = airtable_get_all(FOLDER_PREVIEW_API_URL, None, [FP_FIELD_PATH, FP_FIELD_FILES, FP_FIELD_SKIPPED])
        except Exception as e:
            return jsonify({"error": str(e)}), 502
        _FOLDER_PREVIEW_CACHE["by_path"] = {r.get("fields", {}).get(FP_FIELD_PATH, ""): r.get("fields", {}) for r in records}
        _FOLDER_PREVIEW_CACHE["at"] = time.time()
    f = _FOLDER_PREVIEW_CACHE["by_path"].get(path)
    if f is None:
        return jsonify({"files": [], "skipped": [], "synced": False})
    files = [{"name": a.get("filename", ""), "url": a.get("url", ""), "type": a.get("type", "")}
             for a in f.get(FP_FIELD_FILES, [])]
    skipped = [x for x in (f.get(FP_FIELD_SKIPPED) or "").split("\n") if x]
    return jsonify({"files": files, "skipped": skipped, "synced": True})


@app.route("/api/procurement/inverter-certs/<record_id>/rename", methods=["POST"])
def procurement_inverter_cert_rename(record_id):
    """送出改名請求（寫入「改名為」），本機 cert_agent.py 一分鐘內套用到 G 槽。"""
    body = request.get_json(force=True) or {}
    new_name = (body.get("new_name") or "").strip()
    if not new_name:
        return jsonify({"error": "請輸入新檔名"}), 400
    if any(c in new_name for c in '\\/:*?"<>|'):
        return jsonify({"error": '檔名不能含 \\ / : * ? " < > |'}), 400
    if not os.path.splitext(new_name)[1]:  # 沒打副檔名才補 .pdf（序號表是 .xlsx）
        new_name += ".pdf"
    resp = requests.patch(
        f"{CERT_API_URL}/{record_id}",
        headers=airtable_headers(),
        json={"fields": {CERT_FIELD_RENAME_TO: new_name, CERT_FIELD_RENAME_RESULT: "⏳ 等待本機套用改名…"}},
        timeout=20,
    )
    if resp.status_code >= 400:
        return jsonify({"error": resp.text}), 502
    return jsonify({"ok": True, "new_name": new_name})


@app.route("/api/procurement/inverter-certs/<record_id>/abbr-ok", methods=["POST"])
def procurement_inverter_cert_abbr_ok(record_id):
    body = request.get_json(force=True) or {}
    resp = requests.patch(
        f"{CERT_API_URL}/{record_id}",
        headers=airtable_headers(),
        json={"fields": {CERT_FIELD_ABBR_OK: bool(body.get("ok", True))}},
        timeout=20,
    )
    if resp.status_code >= 400:
        return jsonify({"error": resp.text}), 502
    return jsonify({"ok": True})


# ===================================================================
# PDF 公文更名（線上版，2026-10-08）
# ===================================================================
# 原本是使用者電腦上的本機工具（V2.15，127.0.0.1:8779，OCR 辨識），辨識不夠準。
# 改成線上：PDF 上傳到 Airtable「公文更名佇列」（狀態＝待辨識），後端背景排程
# 慢慢辨識（準確度優先，不求快）：
#   1. 第一次呼叫 Claude：讀整份 PDF，抽出函文類型／發文日期／字號／機關／主旨，
#      以及所有可以對應到案件的識別資料（台電受理編號、電號、同意備案編號、
#      契約編號、地址、申請人名稱…）。
#   2. 程式自己用這些識別資料去比對「專案細節」全部案件（精確比對編號、地址相似度、
#      送件名稱／別名），排出候選案件。
#   3. 第二次呼叫 Claude：把 PDF＋候選案件的完整資料一起給它，重新確認案號、
#      函文類型、日期，並給每一項信心分數。
#   4. 程式再做一次規則檢查（編號精確比對是否跟模型選的案件一致、兩次判讀是否一致、
#      日期合不合理），算出最終信心分數。高信心可設定自動確認，其餘留「待確認」。
# 人工確認後（或自動確認），可選擇把發文日期寫回「進度管理」對應里程碑的完成日期
# （只填空白的，不覆蓋既有日期）。實際歸檔到 G 槽仍由本機程式做：本機程式讀
# GET /api/pdf-rename/confirmed 下載檔案、照「確認檔名」歸檔後回報 /archived。
#
# 需要 Render 環境變數 ANTHROPIC_API_KEY；模型可用 PDF_RENAME_MODEL 覆寫。
# 設定（命名格式、函文類型規則、排程間隔…）存在「系統狀態」表 pdf_rename_settings。
PDF_TABLE_ID = "tblreT71hQpJMuf1B"
PDF_API_URL = f"https://api.airtable.com/v0/{BASE_ID}/{PDF_TABLE_ID}"
PDF_F = {
    "src_name": "fldb2SyKTU97wYsSY",     # 原檔名
    "file": "fldm6cFHtMdFVogj4",         # 檔案（PDF 附件）
    "status": "fldcqa8rjp5kc1g7u",       # 狀態
    "source": "fldJzR4IBBLyk0KO4",       # 來源
    "uploader": "fld8xLEBUTdmrjwqQ",     # 上傳人
    "case_no": "fld9FxfJDGGt9cGUN",      # 案號
    "alias": "fldpaTS6gTL06pwbr",        # 別名
    "doc_type": "fldM0eJIPQibq9E94",     # 函文類型
    "doc_date": "fldzeo6rFELXTT1Sq",     # 發文日期
    "doc_number": "fld59pJX7EGbHwiQ7",   # 發文字號
    "issuer": "fldBVeqKWB980gb40",       # 發文機關
    "subject": "flda6JqqpOWMDHseB",      # 主旨
    "suggested": "fldwNgB0tZBJU5UBC",    # 建議檔名
    "final_name": "fld9tJ6RUyEoMqHTF",   # 確認檔名
    "confidence": "fldK77eZ7eRT7sko0",   # 信心分數
    "evidence": "fld7MlEN4jJ95Aq1I",     # 辨識依據
    "result_json": "fldl2AhLoTIMfDXA3",  # 辨識結果JSON
    "attempts": "fld5YVd5LE5QjMUAT",     # 辨識次數
    "error": "fldEf6sJPs4gU4qPx",        # 錯誤訊息
    "recognized_at": "fldrZP7DlNOW4P0C2",  # 辨識時間（辨識中時＝開始時間，用來判斷卡住）
    "confirmed_at": "fldByrYevJJWzO9EN",   # 確認時間
    "confirmed_by": "fld83V6N168l590Sv",   # 確認人
    "writeback": "fldgx4NAfTB6Tv8hu",      # 寫回結果
    "uploaded_at": "fldFYljqhbJy70LH3",    # 上傳時間
    "hash": "fldMrCmFdyyt5WQWJ",           # 檔案雜湊（SHA1，擋重複上傳）
    "src_path": "fldzoWNBfEWLtfflB",       # 來源路徑（LINE 收件資料夾裡的原始路徑）
    "no_archive": "fldkHTxXMKSYLsjWL",     # 不歸檔（確認時選「只改名下載」，背景程式不放進 G 槽）
}
PDF_ST_QUEUED, PDF_ST_RUNNING, PDF_ST_REVIEW = "待辨識", "辨識中", "待確認"
PDF_ST_CONFIRMED, PDF_ST_ARCHIVED, PDF_ST_FAILED = "已確認", "已歸檔", "辨識失敗"
PDF_MAX_BYTES = 5 * 1024 * 1024   # Airtable uploadAttachment 單檔上限
PDF_MAX_ATTEMPTS = 3
PDF_STALE_MINUTES = 30
PDF_MODEL = os.environ.get("PDF_RENAME_MODEL", "claude-opus-5-5").strip()
PDF_STATE_KEY = "pdf_rename_settings"
TW_TZ = timezone(timedelta(hours=8))

# 「專案細節」比對用欄位（案號／別名／地址沿用上方常數）
FIELD_CASE_SUBMIT_NAME = "fldBVa5jakioAkUTB"   # 送件名稱
FIELD_CASE_EPC_PARTY = "fldQmtAOfu5Suld3o"     # EPC簽約對象
FIELD_CASE_CONTRACT_NO = "fldEVxxXvcb7nrz6S"   # 合約編號
FIELD_CASE_TP_ACCEPT_NO = "fldhkdJvJw6xDwtMl"  # 臺電受理編號
FIELD_CASE_ELEC_NO = "fldsevnrPtGTG7aIo"       # 電號
FIELD_CASE_TP_CONTRACT_NO = "fldgZkOWhJWi54wUD"  # 台電契約編號
FIELD_CASE_PV_NO = "fldBU6s0FgcDojilc"         # 併聯PV編號
FIELD_CASE_AGREE_NO = "fldOYJoRZy0Uoym41"      # 同意備案編號

# 2026-10-09：依使用者 G 槽 7,453 份已改名歷史檔案（tools/pdf_learn.py 報告）整理。
# name＝使用者實際檔名用的類型（出現最多的寫法）；synonyms＝檔名裡的其他寫法（學習工具歸併用）；
# category＝放哪個資料夾；milestone＝確認後寫回「進度管理」的里程碑；
# date_keys＝這類文件的日期前面會出現的字（依序找，找不到再用一般「發文日期／中華民國」規則）。
PDF_DEFAULT_DOC_TYPES = [
    # ---- 06 政府函文及相關文件 ----
    {"name": "併聯審查", "category": "06", "milestone": "併聯審查", "synonyms": "併聯審查函、併聯審查意見書",
     "keywords": "併聯審查意見書、併聯審查結果、併聯審查、同意併聯"},
    {"name": "同意備案", "category": "06", "milestone": "同意備案", "synonyms": "同意備案函",
     "keywords": "同意備案、准予備案、第三型再生能源發電設備"},
    {"name": "細部協商", "category": "06", "milestone": "細部協商", "synonyms": "細協",
     "keywords": "細部協商、併聯細部協商、協商結果"},
    {"name": "細協補件通知", "category": "06", "milestone": "", "synonyms": "",
     "keywords": "補件、補正、細部協商"},
    {"name": "審訖圖", "category": "06", "milestone": "台電審訖圖", "synonyms": "審迄圖、台電審訖圖",
     "keywords": "審訖、審迄、審定、單線圖審查"},
    {"name": "結構計算書", "category": "06", "milestone": "結構計算書", "synonyms": "",
     "keywords": "結構計算書、結構計算、風力計算、風壓、構件檢核", "date_keys": "日期、中華民國"},
    {"name": "免雜", "category": "06", "milestone": "免雜", "synonyms": "免雜函、免雜更正函",
     "keywords": "免請領雜項執照、免申請雜項執照、雜項執照、免雜"},
    {"name": "免雜附件", "category": "06", "milestone": "", "synonyms": "免雜附件一、免雜附件二、免雜附件三、免雜附件一、二、三、附件二免雜簽證表、附件四完竣證明書",
     "keywords": "簽證表、結構安全證明書、完竣證明書、免雜附件"},
    {"name": "台電契約", "category": "06", "milestone": "台電購售契約", "synonyms": "台電購售契約",
     "keywords": "再生能源發電設備購售電契約、購售電契約書、立契約書人、契約條款", "date_keys": "簽訂日期、簽約日期、中華民國"},
    {"name": "台電契約函", "category": "06", "milestone": "購售契約函文", "synonyms": "台電契約函文、購售契約函文",
     "keywords": "檢送、購售電契約、契約乙份"},
    {"name": "台電契約移轉", "category": "06", "milestone": "移轉契約", "synonyms": "",
     "keywords": "契約移轉、移轉、承受、過戶、轉讓"},
    {"name": "設備登記", "category": "06", "milestone": "設備登記", "synonyms": "設備登記函",
     "keywords": "設備登記、再生能源發電設備登記、准予登記"},
    {"name": "設備登記移轉", "category": "06", "milestone": "移轉設備", "synonyms": "",
     "keywords": "設備登記、移轉、變更登記、讓與"},
    {"name": "電表租約", "category": "06", "milestone": "電表租約", "synonyms": "電表租約(屋主)、電表租約函",
     "keywords": "電表租約、租用電表、電表租用、表租"},
    {"name": "正式售電函", "category": "06", "milestone": "正式售電函", "synonyms": "正式售電",
     "keywords": "正式購售電、正式售電、躉購費率、正式併聯"},
    {"name": "併聯試運轉函", "category": "06", "milestone": "併聯試運轉", "synonyms": "併聯試運轉",
     "keywords": "併聯試運轉、試運轉"},
    {"name": "竣工備查", "category": "06", "milestone": "竣工備查", "synonyms": "竣工備查函",
     "keywords": "竣工備查、竣工、准予備查"},
    {"name": "竣工試驗報告", "category": "06", "milestone": "", "synonyms": "",
     "keywords": "竣工試驗報告、試驗報告、功率追蹤、獨立型"},
    {"name": "補助同意函", "category": "06", "milestone": "", "synonyms": "補助同意通知函",
     "keywords": "補助、同意補助、補助款"},
    {"name": "臺電契約匯款帳戶", "category": "06", "milestone": "", "synonyms": "",
     "keywords": "虛擬帳號、專屬帳號、核銷作業、匯款帳戶"},
    {"name": "申請案件告知單", "category": "06", "milestone": "", "synonyms": "",
     "keywords": "告知單、申請案件"},
    # ---- 04 電廠設計圖 ----
    {"name": "支架拆圖", "category": "04", "milestone": "支架拆圖", "synonyms": "支架拆圖(用印版)、支架拆圖(用印)",
     "keywords": "支架拆圖、傾斜角度、模組傾斜、立柱、檁條", "date_keys": "日期"},
    {"name": "串併圖", "category": "04", "milestone": "串並圖", "synonyms": "串並圖、串並圖(工務版)、串接圖、串並、模組串併圖、串併圖(工務版)、串並圖(EPC版)",
     "keywords": "串接圖、串併圖、串並圖、串列", "date_keys": "日期"},
    {"name": "系統送審圖", "category": "04", "milestone": "系統送審圖", "synonyms": "系統送審、送審圖、台電送審圖",
     "keywords": "昇位圖、監造者、用電裝置、竣工圖、系統送審", "date_keys": "日期"},
    {"name": "單線圖", "category": "04", "milestone": "單線圖", "synonyms": "",
     "keywords": "單線圖", "date_keys": "日期"},
    # ---- 07 設備保固及出廠證明 ----
    {"name": "模組序號", "category": "07", "milestone": "", "synonyms": "模組序號表、模組設備序號表",
     "keywords": "序號、Serial、S/N、模組序號"},
    {"name": "變流器出廠暨保固證明書", "category": "07", "milestone": "", "synonyms": "變流器出廠證明",
     "keywords": "碩天科技、原廠出廠、變流器、逆變器、保固期間", "date_keys": "保固期間民國、保固期間為民國、保固期間"},
    {"name": "模組出廠證明書", "category": "07", "milestone": "", "synonyms": "模組出廠證明、高效能模組出廠證明",
     "keywords": "出廠證明書、友達光電、模組", "date_keys": "中華民國"},
    {"name": "模組出廠暨保固證明書", "category": "07", "milestone": "", "synonyms": "模組產品出廠暨保固證明書、產品出廠暨保固證明書、模組出廠保固證明",
     "keywords": "出廠暨保固證明書、模組、保固", "date_keys": "中華民國"},
    {"name": "模組發票", "category": "07", "milestone": "設備發票", "synonyms": "",
     "keywords": "電子發票證明聯、統一發票、營業稅、模組", "date_keys": "電子發票證明聯、發票日期"},
    {"name": "變流器發票", "category": "07", "milestone": "設備發票", "synonyms": "",
     "keywords": "電子發票證明聯、統一發票、營業稅、變流器、逆變器", "date_keys": "電子發票證明聯、發票日期"},
    {"name": "設備發票", "category": "07", "milestone": "設備發票", "synonyms": "",
     "keywords": "電子發票證明聯、統一發票、營業稅", "date_keys": "電子發票證明聯、發票日期"},
    {"name": "支架出廠證明", "category": "07", "milestone": "", "synonyms": "支架出場證明、支架出廠證明書",
     "keywords": "出貨日期、鋼鐵股份、支架、出廠證明", "date_keys": "出貨日期、中華民國"},
    {"name": "支架保固文件", "category": "07", "milestone": "支架保固文件", "synonyms": "支架保固文件(H鋼)、支架保固文件(C鋼)",
     "keywords": "支架、保固書、保固期限"},
    {"name": "支架材質證明", "category": "07", "milestone": "", "synonyms": "材質證明、材質證明-H",
     "keywords": "材質證明、化學成分、機械性質"},
    {"name": "熱浸鍍鋅證明", "category": "07", "milestone": "", "synonyms": "鍍鋅證明、熱浸鍍鋅檢驗報告、熱浸鍍鋅報告",
     "keywords": "熱浸鍍鋅、鍍鋅、附著量"},
    {"name": "太陽能系統保固書", "category": "07", "milestone": "", "synonyms": "太陽能保固書",
     "keywords": "系統保固、保固書、保固範圍"},
    {"name": "模組保固書", "category": "07", "milestone": "", "synonyms": "模組保固文件",
     "keywords": "模組、保固書、功率保固"},
    # ---- 03 契約 ----
    {"name": "公證書", "category": "03", "milestone": "公證日", "synonyms": "公證書(潤特)",
     "keywords": "公證書、公證人、認證", "date_keys": "中華民國"},
    {"name": "工程合約", "category": "03", "milestone": "工程合約簽約", "synonyms": "工程合約(潤特)、工程合約(EPC)、工程合約_EPC、工程契約、工程合約_尚展、工程合約_三創",
     "keywords": "工程合約、工程契約、太陽光電發電系統工程、甲方、乙方", "date_keys": "中華民國"},
    {"name": "協議書", "category": "03", "milestone": "", "synonyms": "協議書(潤特)、工程協議書、工程協議書(EPC)",
     "keywords": "協議書、立協議書人"},
    {"name": "採購委託書", "category": "03", "milestone": "", "synonyms": "",
     "keywords": "採購委託書、委託採購"},
    {"name": "終止契約", "category": "03", "milestone": "", "synonyms": "終止合約、工程終止協議書、工程終止協議書V",
     "keywords": "終止、解除契約、終止協議"},
    {"name": "同意書", "category": "03", "milestone": "", "synonyms": "建築改良物使用同意書、公證同意書",
     "keywords": "同意書、使用同意、立同意書人"},
    {"name": "屋頂租賃合約書", "category": "03", "milestone": "", "synonyms": "太陽光電發電系統屋頂租賃合約書",
     "keywords": "租賃、屋頂租賃、租金"},
    {"name": "增補協議書", "category": "03", "milestone": "", "synonyms": "(帳戶異動)第一次增補協議書、(房屋易主)第一次增補協議書",
     "keywords": "增補協議書、增補"},
]
PDF_DEFAULT_SETTINGS = {
    "enabled": True,                # 背景自動辨識
    "interval_min": 5,              # 每幾分鐘檢查一次佇列
    "batch_size": 5,                # 每輪最多辨識幾份（慢慢來，避免一次打太多 API）
    "auto_confirm": False,          # 高信心直接確認（不用人工按）
    "auto_confirm_threshold": 92,   # 自動確認門檻
    "writeback": True,              # 確認後把發文日期寫回進度管理（只填空白）
    "template": "{簡稱}_{日期}_{函文類型}",   # 使用者實際命名：桃1_20250106_併聯審查
    "doc_types": PDF_DEFAULT_DOC_TYPES,
    "rules_csv_url": "",            # 選填：Google Sheet「發布為 CSV」網址，欄位 函文類型/關鍵字/對應里程碑/說明
    "engine": "free",               # free＝完全免費（文字層＋Google OCR＋規則）／hybrid＝沒把握的才用 AI／ai＝全部用 AI
    "ocr_url": "",                  # 掃描檔用：使用者部署的 Apps Script 網址（Google 雲端硬碟 OCR）
    # LINE 收件資料夾（每位 PM 一個）：PM 電腦上的 tools/pdf_watcher.ps1 每分鐘讀這裡的設定，
    # 資料夾有新的 PDF 就送進佇列。[{pm, folder, enabled}]
    "watchers": [],
    # 自動歸檔到 G 槽：由 pm 那台電腦的背景程式，把「已確認」的檔案用確認檔名放進
    # 「根目錄底下的案場資料夾 → 03/04/06/07 分類資料夾」。roots 可多個（一行一個）。
    "archive": {"enabled": False, "pm": "", "roots": ""},
}
PDF_WATCHER_STATUS = {}   # {pm: 最後一次回報}，記憶體即可（背景程式每分鐘回報一次）
PDF_SETTINGS = {"data": None}
# 案號 → 簡稱（例如 潤特桃園1號 → 桃1、舊案保留原本的 千82／風29），從使用者 G 槽資料夾＋檔名學來，
# 存在「系統狀態」pdf_rename_aliases：{"map": {案號: 簡稱}, "rules": {案號前綴: 簡稱前綴}}。
PDF_ALIAS_KEY = "pdf_rename_aliases"
PDF_ALIASES = {"data": None}
PDF_RUN = {"running": False, "last_run_at": None, "last_finished_at": None, "last_error": None, "last_count": 0}
PDF_LOCK = threading.Lock()
PDF_CASE_REF = {"cases": [], "at": 0}
_ANTHROPIC_CLIENT = {"c": None}


def _tw_now_iso():
    return datetime.now(TW_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")


def _pdf_settings():
    if PDF_SETTINGS["data"] is None:
        data = dict(PDF_DEFAULT_SETTINGS)
        try:
            raw = _state_get_long(PDF_STATE_KEY)
            if raw:
                data.update(json.loads(raw))
        except Exception as e:
            print(f"[pdf_rename] 讀取設定失敗，用預設值：{e}", flush=True)
        # 2026-10-09 升級：還在用第一版預設值的設定，自動換成依歷史檔案整理的新版（使用者改過的不動）
        if data.get("template") == "{案號}_{函文類型}_{日期}":
            data["template"] = PDF_DEFAULT_SETTINGS["template"]
        old_names = {"併聯審查", "同意備案", "細部協商", "免雜", "購售契約函文", "台電購售契約", "併聯試運轉",
                     "正式售電函", "竣工備查", "設備登記", "台電審訖圖", "電表租約", "第一張電費單"}
        if {t.get("name") for t in data.get("doc_types") or []} == old_names:
            data["doc_types"] = PDF_DEFAULT_DOC_TYPES
        PDF_SETTINGS["data"] = data
    return PDF_SETTINGS["data"]


def _pdf_aliases():
    if PDF_ALIASES["data"] is None:
        data = {"map": {}, "rules": {}}
        # 預設值：repo 裡的 pdf_aliases.json（2026-10-09 由使用者 G 槽 546 個案場整理）；
        # 之後在主控台匯入新的學習報告會存到「系統狀態」並覆蓋這份
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_aliases.json"), encoding="utf-8") as f:
                data.update(json.load(f))
        except Exception as e:
            print(f"[pdf_rename] 讀取內建簡稱對照失敗：{e}", flush=True)
        try:
            raw = _state_get_long(PDF_ALIAS_KEY)
            if raw:
                saved = json.loads(raw)
                data["map"].update(saved.get("map") or {})
                data["rules"].update(saved.get("rules") or {})
        except Exception as e:
            print(f"[pdf_rename] 讀取簡稱對照失敗：{e}", flush=True)
        PDF_ALIASES["data"] = data
    return PDF_ALIASES["data"]


def _pdf_short_name(case_no):
    """案號 → 簡稱；對照表沒有的，用前綴規則推（潤特桃園95號 → 桃95）。"""
    if not case_no:
        return ""
    al = _pdf_aliases()
    if case_no in al["map"]:
        return al["map"][case_no]
    m = re.match(r"^(.+?)(\d+)號$", case_no)
    if m and m.group(1) in al["rules"]:
        return al["rules"][m.group(1)] + m.group(2)
    return ""


def _pdf_aliases_from_report(report):
    """pdf_learn.py 的 report.json → 簡稱對照。案場資料夾「003 潤特桃園3號_中壢…」取出案號，
    簡稱用檔名最常見的前綴；前綴怪怪的（人名、地址）就用同區規則補。"""
    good = re.compile(r"^[\u4e00-\u9fff]{1,3}\d+$")
    amap, others = {}, {}
    for a in report.get("aliases") or []:
        m = re.match(r"^\s*\d+\s*[-_.、 ]?\s*([^\s_（(]+?號)", a.get("case_dir") or "")
        if m and a.get("prefix"):
            amap.setdefault(m.group(1), a["prefix"])
            others[m.group(1)] = a.get("others") or []
    counter = {}
    for k, v in amap.items():
        a, b = re.match(r"^(.+?)(\d+)號$", k), re.match(r"^([\u4e00-\u9fff]{1,3})(\d+)$", v)
        if a and b and a.group(2) == b.group(2):
            counter.setdefault(a.group(1), {}).setdefault(b.group(1), 0)
            counter[a.group(1)][b.group(1)] += 1
    rules = {k: max(c, key=c.get) for k, c in counter.items()}
    for k, v in list(amap.items()):
        if good.match(v):
            continue
        alt = next((o for o in others.get(k, []) if good.match(o)), None)
        a = re.match(r"^(.+?)(\d+)號$", k)
        new = alt or (rules[a.group(1)] + a.group(2) if a and a.group(1) in rules else None)
        if new:
            amap[k] = new
        else:
            del amap[k]
    return {"map": amap, "rules": rules}


def _pdf_save_settings(data):
    _state_set_long(PDF_STATE_KEY, json.dumps(data, ensure_ascii=False))
    PDF_SETTINGS["data"] = data


def _pdf_load_rules_csv(url):
    """Google Sheet「檔案 → 共用 → 發布到網路 → CSV」的網址。第一列是標題，
    認得 函文類型/類型/名稱、關鍵字、對應里程碑/里程碑、說明/備註 這幾種欄名。"""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    rows = list(csv.reader(io.StringIO(resp.content.decode("utf-8-sig"))))
    if len(rows) < 2:
        raise Exception("CSV 沒有資料列")
    header = [h.strip() for h in rows[0]]

    def col(*names):
        for n in names:
            if n in header:
                return header.index(n)
        return None
    i_name = col("函文類型", "類型", "名稱", "文件類型")
    if i_name is None:
        raise Exception("CSV 找不到「函文類型」欄位（第一列標題）")
    i_kw, i_ms, i_note = col("關鍵字", "辨識關鍵字"), col("對應里程碑", "里程碑", "進度管理"), col("說明", "備註")
    out = []
    for r in rows[1:]:
        get = lambda i: (r[i].strip() if i is not None and i < len(r) else "")
        if get(i_name):
            out.append({"name": get(i_name), "keywords": get(i_kw), "milestone": get(i_ms), "note": get(i_note)})
    if not out:
        raise Exception("CSV 沒有任何函文類型")
    return out


def _pdf_get_record(record_id):
    resp = requests.get(f"{PDF_API_URL}/{record_id}", headers=airtable_headers(),
                        params={"returnFieldsByFieldId": "true"}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _pdf_patch(record_id, fields):
    resp = requests.patch(f"{PDF_API_URL}/{record_id}", headers=airtable_headers(),
                          json={"fields": fields}, timeout=30)
    if resp.status_code >= 400:
        raise Exception(resp.text)
    return resp.json()


def _pdf_doc_category(doc_type):
    """文件類型 → 要放的分類資料夾編號（03/04/06/07），沒設定就空白。"""
    rule = next((t for t in _pdf_settings().get("doc_types") or [] if t.get("name") == doc_type), None)
    return ((rule or {}).get("category") or "").strip()


def _pdf_record_to_dict(r):
    f = r.get("fields", {})
    g = lambda k: f.get(PDF_F[k])
    att = (g("file") or [{}])[0]
    try:
        result = json.loads(g("result_json") or "{}")
    except Exception:
        result = {}
    return {
        "id": r["id"],
        "src_name": g("src_name") or "",
        "status": g("status") or "",
        "source": g("source") or "",
        "uploader": g("uploader") or "",
        "uploaded_at": g("uploaded_at") or r.get("createdTime", ""),
        "src_path": g("src_path") or "",
        "category": _pdf_doc_category(g("doc_type") or ""),
        "no_archive": bool(g("no_archive")),
        "case_no": g("case_no") or "",
        "alias": g("alias") or "",
        "doc_type": g("doc_type") or "",
        "doc_date": g("doc_date") or "",
        "doc_number": g("doc_number") or "",
        "issuer": g("issuer") or "",
        "subject": g("subject") or "",
        "suggested_name": g("suggested") or "",
        "final_name": g("final_name") or "",
        "confidence": g("confidence"),
        "evidence": g("evidence") or "",
        "issues": result.get("issues") or [],
        "candidates": result.get("candidates") or [],
        "engine": result.get("engine") or "",
        "text_excerpt": result.get("text_excerpt") or "",
        "attempts": g("attempts") or 0,
        "error": g("error") or "",
        "recognized_at": g("recognized_at") or "",
        "confirmed_at": g("confirmed_at") or "",
        "confirmed_by": g("confirmed_by") or "",
        "writeback": g("writeback") or "",
        "file_url": att.get("url", ""),
        "file_size": att.get("size", 0),
    }


# ---------------- 案件比對 ----------------

def _pdf_case_ref(force=False):
    """全部「專案細節」案件的比對資料（含已結案的，舊案也可能收到函文）。6 小時更新一次。"""
    if not force and PDF_CASE_REF["cases"] and time.time() - PDF_CASE_REF["at"] < 6 * 3600:
        return PDF_CASE_REF["cases"]
    fields = [FIELD_CASE_NO, FIELD_ALIAS, FIELD_ADDRESS, FIELD_VENDOR, FIELD_CLOSE_STATUS,
              FIELD_CASE_SUBMIT_NAME, FIELD_CASE_EPC_PARTY, FIELD_CASE_CONTRACT_NO, FIELD_CASE_TP_ACCEPT_NO,
              FIELD_CASE_ELEC_NO, FIELD_CASE_TP_CONTRACT_NO, FIELD_CASE_PV_NO, FIELD_CASE_AGREE_NO]
    records = airtable_get_all(CASE_API_URL, None, fields)
    cases = []
    for r in records:
        f = r.get("fields", {})
        case_no = (f.get(FIELD_CASE_NO) or "").strip()
        if not case_no:
            continue
        cases.append({
            "record_id": r["id"],
            "case_no": case_no,
            "alias": (f.get(FIELD_ALIAS) or "").strip(),
            "address": (f.get(FIELD_ADDRESS) or "").strip(),
            "vendor": f.get(FIELD_VENDOR) or "",
            "closed": f.get(FIELD_CLOSE_STATUS) or "",
            "submit_name": (f.get(FIELD_CASE_SUBMIT_NAME) or "").strip(),
            "epc_party": (f.get(FIELD_CASE_EPC_PARTY) or "").strip(),
            "ids": {
                "合約編號": f.get(FIELD_CASE_CONTRACT_NO) or "",
                "臺電受理編號": f.get(FIELD_CASE_TP_ACCEPT_NO) or "",
                "電號": f.get(FIELD_CASE_ELEC_NO) or "",
                "台電契約編號": f.get(FIELD_CASE_TP_CONTRACT_NO) or "",
                "併聯PV編號": f.get(FIELD_CASE_PV_NO) or "",
                "同意備案編號": f.get(FIELD_CASE_AGREE_NO) or "",
            },
        })
    # 已公證但還沒建進 Airtable 的案件（業務自治區推送），只有案號／別名可比
    known = {c["case_no"] for c in cases}
    for c in CERTIFIED_CASE_CACHE.get("cases") or []:
        if c["case"] not in known:
            cases.append({"record_id": "", "case_no": c["case"], "alias": c.get("alias", ""), "address": "",
                          "vendor": c.get("vendor", ""), "closed": "", "submit_name": "", "epc_party": "", "ids": {}})
    PDF_CASE_REF["cases"] = cases
    PDF_CASE_REF["at"] = time.time()
    return cases


_FULLWIDTH = str.maketrans("０１２３４５６７８９－（）", "0123456789-()")


def _norm_id(s):
    return re.sub(r"[^0-9A-Z]", "", (s or "").translate(_FULLWIDTH).upper())


def _norm_text(s):
    s = (s or "").translate(_FULLWIDTH).replace("台", "臺")
    return re.sub(r"[\s,，、.。:：;；()（）\-]", "", s)


# 抽出的識別資料 → 案件欄位
_PDF_ID_MAP = {
    "taipower_accept_no": ["臺電受理編號"],
    "electricity_no": ["電號"],
    "agree_record_no": ["同意備案編號"],
    "contract_no": ["台電契約編號", "合約編號"],
    "pv_no": ["併聯PV編號"],
}


def _pdf_match_cases(ext, fulltext=None):
    """回傳 (候選清單, 強比對案號集合)。強比對＝某個編號精確相同（受理編號、電號…）。
    fulltext（免費辨識用）：另外拿每個案件的編號／案號直接在全文裡找。"""
    idents = ext.get("identifiers") or {}
    scores = {}

    def add(c, pts, why):
        s = scores.setdefault(c["case_no"], {"case": c, "score": 0, "why": [], "strong": False})
        s["score"] += pts
        s["why"].append(why)
        return s

    cases = _pdf_case_ref()
    if fulltext:
        _pdf_scan_fulltext(fulltext, add)
    for key, case_fields in _PDF_ID_MAP.items():
        for raw in idents.get(key) or []:
            v = _norm_id(raw)
            if len(v) < 5:
                continue
            for c in cases:
                for cf in case_fields:
                    cv = _norm_id(c["ids"].get(cf))
                    if cv and (cv == v or (len(v) >= 8 and (cv in v or v in cv))):
                        add(c, 100, f"{cf}相同（{raw}）")["strong"] = True
    for raw in idents.get("case_no_like") or []:
        v = _norm_text(raw)
        for c in cases:
            if v and _norm_text(c["case_no"]) == v:
                add(c, 80, f"文件內出現案號 {raw}")["strong"] = True
    for raw in idents.get("addresses") or []:
        a = _norm_text(raw)
        if len(a) < 6:
            continue
        for c in cases:
            ca = _norm_text(c["address"])
            if len(ca) < 6:
                continue
            ratio = difflib.SequenceMatcher(None, a, ca).ratio()
            # 門牌／地號數字是關鍵：數字對不上的只算「相近」，不算相符
            nums_ok = set(re.findall(r"\d+", ca)) <= set(re.findall(r"\d+", a))
            if ca in a or a in ca or (ratio >= 0.7 and nums_ok):
                add(c, 60, f"地址相符（{raw}）")
            elif ratio >= 0.75:
                add(c, 15, f"地址相近 {int(ratio * 100)}%（{raw}）")
    texts = [_norm_text(x) for x in (idents.get("names") or []) + [ext.get("subject") or "", ext.get("recipient") or ""]]
    texts = [t for t in texts if t]
    # 送件名稱很多案件共用（例如「潤特綠能股份有限公司」），共用 3 件以上的不拿來比
    name_count = {}
    for c in cases:
        if c["submit_name"]:
            name_count[c["submit_name"]] = name_count.get(c["submit_name"], 0) + 1
    for c in cases:
        for label, val, pts in (("送件名稱", c["submit_name"], 40), ("別名", c["alias"], 30)):
            if label == "送件名稱" and name_count.get(val, 0) >= 3:
                continue
            v = _norm_text(val)
            if len(v) >= 3 and any(v in t for t in texts):
                add(c, pts, f"{label}「{val}」出現在文件")
    ranked = sorted(scores.values(), key=lambda s: -s["score"])[:8]
    strong = {s["case"]["case_no"] for s in ranked if s["strong"]}
    return ranked, strong


# ---------------- Claude 辨識 ----------------

def _anthropic():
    if _ANTHROPIC_CLIENT["c"] is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise Exception("後端沒有設定 ANTHROPIC_API_KEY（Render → Environment）")
        import anthropic
        _ANTHROPIC_CLIENT["c"] = anthropic.Anthropic(max_retries=4, timeout=600)
    return _ANTHROPIC_CLIENT["c"]


def _pdf_system_prompt(settings):
    lines = []
    for t in settings.get("doc_types") or []:
        extra = "；".join(x for x in [t.get("keywords") and f"關鍵字：{t['keywords']}", t.get("note")] if x)
        lines.append(f"- {t['name']}" + (f"（{extra}）" if extra else ""))
    return (
        "你是台灣太陽光電 EPC 公司的公文判讀助理。公司會收到台電、縣市政府、能源署、建管單位等機關的函文"
        "與文件，需要正確判斷：這份文件屬於哪個案場（案號）、是哪一種函文、發文日期。判讀結果會直接拿來"
        "幫檔案改名並更新案件進度，所以準確比速度重要：\n"
        "- 每一個欄位都要以文件上實際印出的文字為依據，看不清楚或文件沒有寫就留空字串，絕對不要猜或編造。\n"
        "- 發文日期以函文上的「發文日期」為準（不是收文日、不是附件日期、不是契約生效日）。民國年要換算成"
        "西元（民國年＋1911），輸出 YYYY-MM-DD。沒有發文日期的文件（例如契約書、電費單）用文件上最主要的"
        "開立／簽訂日期，並在說明中註明。\n"
        "- 識別資料（台電受理編號、電號、同意備案編號、契約編號、地址、申請人名稱）要完整照抄，包括文件"
        "附件、說明欄、受文者欄位裡出現的，一份文件可能有多個。\n"
        "- 函文類型只能從下列清單選，判斷依據是函文主旨與內容，不要只看關鍵字；都不符合就選「其他」：\n"
        + "\n".join(lines) + "\n- 其他"
    )


def _pdf_doc_type_enum(settings):
    names = [t["name"] for t in settings.get("doc_types") or [] if t.get("name")]
    return list(dict.fromkeys(names + ["其他"]))


def _pdf_ask(system, pdf_b64, instruction, schema):
    """PDF 放在最前面並標 cache_control，兩次呼叫（抽取、確認）共用同一份快取。"""
    client = _anthropic()
    resp = client.beta.messages.create(
        model=PDF_MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        extra_body={"fallbacks": "default"},
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": schema}},
        system=system,
        messages=[{"role": "user", "content": [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64},
             "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": instruction},
        ]}],
    )
    if resp.stop_reason == "refusal":
        raise Exception("模型拒絕處理這份文件")
    if resp.stop_reason == "max_tokens":
        raise Exception("模型輸出被截斷（max_tokens）")
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(text)


def _str_list():
    return {"type": "array", "items": {"type": "string"}}


def _pdf_extract(settings, system, pdf_b64):
    schema = {
        "type": "object",
        "properties": {
            "doc_type": {"type": "string", "enum": _pdf_doc_type_enum(settings)},
            "doc_type_reason": {"type": "string"},
            "doc_date": {"type": "string"},
            "doc_date_raw": {"type": "string"},
            "doc_number": {"type": "string"},
            "issuer": {"type": "string"},
            "recipient": {"type": "string"},
            "subject": {"type": "string"},
            "identifiers": {
                "type": "object",
                "properties": {k: _str_list() for k in ("taipower_accept_no", "electricity_no", "agree_record_no",
                                                         "contract_no", "pv_no", "case_no_like", "addresses", "names")},
                "required": ["taipower_accept_no", "electricity_no", "agree_record_no", "contract_no", "pv_no",
                             "case_no_like", "addresses", "names"],
                "additionalProperties": False,
            },
            "notes": {"type": "string"},
        },
        "required": ["doc_type", "doc_type_reason", "doc_date", "doc_date_raw", "doc_number", "issuer",
                     "recipient", "subject", "identifiers", "notes"],
        "additionalProperties": False,
    }
    instruction = (
        "請仔細讀完整份文件（每一頁，包括附件），輸出：函文類型與判斷理由、發文日期（YYYY-MM-DD）與文件上"
        "原始寫法、發文字號、發文機關、受文者、主旨，以及所有識別資料：台電受理編號(taipower_accept_no)、"
        "電號(electricity_no)、同意備案編號(agree_record_no)、契約編號(contract_no)、併聯/PV 編號(pv_no)、"
        "看起來像公司內部案號的字串(case_no_like)、設置地址或地號(addresses)、申請人/發電業者/案場名稱(names)。"
        "notes 寫下任何不確定或特殊的地方。"
    )
    return _pdf_ask(system, pdf_b64, instruction, schema)


def _pdf_verify(settings, system, pdf_b64, ext, ranked):
    cands = [{
        "案號": s["case"]["case_no"], "別名": s["case"]["alias"], "地址": s["case"]["address"],
        "送件名稱": s["case"]["submit_name"], "EPC簽約對象": s["case"]["epc_party"],
        "施作廠商": s["case"]["vendor"], "結案狀態": s["case"]["closed"],
        **{k: v for k, v in s["case"]["ids"].items() if v},
        "程式比對依據": s["why"],
    } for s in ranked]
    schema = {
        "type": "object",
        "properties": {
            "case_no": {"type": "string"},
            "case_reason": {"type": "string"},
            "case_confidence": {"type": "integer"},
            "doc_type": {"type": "string", "enum": _pdf_doc_type_enum(settings)},
            "doc_type_confidence": {"type": "integer"},
            "doc_date": {"type": "string"},
            "doc_date_confidence": {"type": "integer"},
            "issues": _str_list(),
        },
        "required": ["case_no", "case_reason", "case_confidence", "doc_type", "doc_type_confidence",
                     "doc_date", "doc_date_confidence", "issues"],
        "additionalProperties": False,
    }
    instruction = (
        "這是第二次確認。先前一次判讀結果如下（可能有錯）：\n"
        + json.dumps({k: ext.get(k) for k in ("doc_type", "doc_date", "doc_date_raw", "doc_number", "issuer",
                                                  "subject", "identifiers")}, ensure_ascii=False)
        + "\n\n程式依識別資料比對出的候選案件（依分數排序，可能都不對）：\n"
        + (json.dumps(cands, ensure_ascii=False) if cands else "（沒有任何候選案件）")
        + "\n\n請重新對照文件原文逐項確認：\n"
        "1. case_no：只能填上面候選清單裡的案號，或空字串。必須有文件上的具體證據（編號完全相同、地址"
        "相同、申請人相同）才選，case_reason 寫出對照到的文件文字與案件欄位。證據不足或互相矛盾就留空。\n"
        "2. doc_type、doc_date（YYYY-MM-DD）：重新看一次文件判斷，不要直接沿用上一次的結果。\n"
        "3. 每一項給 0–100 的信心分數：100＝文件上清楚明確且與案件資料完全吻合；70＝大致確定但有一點疑慮；"
        "40 以下＝主要靠推測。\n"
        "4. issues：列出所有需要人工注意的地方（例如兩個案件都可能、日期模糊、文件不完整、跟上一次判讀不一致）。"
    )
    return _pdf_ask(system, pdf_b64, instruction, schema)


def _pdf_valid_date(s):
    try:
        d = datetime.strptime((s or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None
    today = datetime.now(TW_TZ).date()
    if d > today + timedelta(days=3) or d < today - timedelta(days=365 * 8):
        return None
    return d


def _pdf_build_name(template, case, doc_type, doc_date):
    d = _pdf_valid_date(doc_date) if doc_date else None
    case_no = case.get("case_no", "") if case else ""
    vals = {
        "案號": case_no,
        "簡稱": _pdf_short_name(case_no) or case_no,
        "別名": case.get("alias", "") if case else "",
        "函文類型": doc_type or "",
        "日期": d.strftime("%Y%m%d") if d else "",
        "西元日期": d.strftime("%Y-%m-%d") if d else "",
        "民國日期": f"{d.year - 1911:03d}{d.month:02d}{d.day:02d}" if d else "",
    }
    name = re.sub(r"\{(\S+?)\}", lambda m: vals.get(m.group(1), m.group(0)), template or PDF_DEFAULT_SETTINGS["template"])
    name = re.sub(r'[\\/:*?"<>|\r\n]', "", name)
    name = re.sub(r"_+", "_", name).strip("_ ")
    return (name or "未命名") + ".pdf"


# ---------------- 免費辨識（2026-10-08 改為預設）----------------
# 不呼叫付費 AI：電子檔 PDF 直接讀文字層；掃描檔交給使用者 Google 帳號底下的 Apps Script
# （Google 雲端硬碟內建 OCR，免費）轉文字；再用規則抓發文日期／字號／主旨／函文類型，
# 並拿 Airtable 每個案件的受理編號、電號、同意備案編號、案號直接在全文裡找，對到就幾乎確定。
# 設定 engine：free（預設，完全免費）／hybrid（免費辨識沒把握的才交給 AI）／ai（全部用 AI）。
PDF_MIN_TEXT_CHARS = 40


def _pdf_text_layer(pdf_bytes):
    """電子檔 PDF 的文字層（掃描檔會幾乎抽不到字）。"""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join((p.extract_text() or "") for p in reader.pages[:10])
    except Exception as e:
        print(f"[pdf_rename] 讀取文字層失敗：{e}", flush=True)
        return ""


PDF_OCR_LOGIN_HINT = ("Google 要求登入，代表 Apps Script 的存取權不是真正的「所有人」。公司 Workspace 帳號"
                      "（網址有 /a/macros/公司網域/）通常只能選「公司內的所有人」，請改用個人 Gmail 帳號部署，"
                      "或請公司 Google 管理員開放外部存取")


def _pdf_ocr_json(resp):
    """Apps Script 回應轉 JSON；被導到 Google 登入頁時給明確的原因。"""
    if "accounts.google.com" in resp.url or "ServiceLogin" in resp.text[:5000]:
        raise Exception(PDF_OCR_LOGIN_HINT)
    try:
        return resp.json()
    except ValueError:
        raise Exception("OCR 服務回傳的不是 JSON（HTTP %s），請確認部署時選「網頁應用程式」、存取權「所有人」" % resp.status_code)


def _pdf_ocr(pdf_bytes, url):
    """呼叫使用者部署的 Apps Script（Google 雲端硬碟 OCR）。"""
    resp = requests.post(url, json={"pdf": base64.b64encode(pdf_bytes).decode()}, timeout=300)
    data = _pdf_ocr_json(resp)
    if not data.get("ok"):
        raise Exception("OCR 失敗：" + str(data.get("error") or "未知錯誤"))
    return data.get("text") or ""


def _pdf_get_text(pdf_bytes, settings):
    text = _pdf_text_layer(pdf_bytes)
    if len(re.sub(r"\s", "", text)) >= PDF_MIN_TEXT_CHARS:
        return text, "PDF 文字層"
    url = (settings.get("ocr_url") or "").strip()
    if not url:
        raise Exception("這份是掃描檔（PDF 裡沒有文字），需要先在「⚙ 命名格式與函文規則」設定 Google OCR 網址")
    return _pdf_ocr(pdf_bytes, url), "Google OCR"


def _pdf_flat(text):
    t = (text or "").translate(_FULLWIDTH)
    t = t.replace("：", ":").replace("　", " ")
    return re.sub(r"\s+", "", t)


def _pdf_rule_date(flat, date_keys=""):
    """回傳 (YYYY-MM-DD, 文件原文, 信心)。date_keys＝這類文件日期前面會出現的字（規則設定），先找這些。"""
    for key in [k.strip() for k in re.split(r"[、,，;；]", date_keys or "") if k.strip()]:
        pat = re.escape(_pdf_flat(key)) + r"[^0-9]{0,6}?(?:中華民國|民國)?(\d{2,4})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})"
        for m in re.finditer(pat, flat):
            y, mo, d = (int(x) for x in m.groups())
            if y < 1000:
                y += 1911
            iso = f"{y:04d}-{mo:02d}-{d:02d}"
            if _pdf_valid_date(iso):
                return iso, m.group(0), 90
    pats = [
        (r"發文日期:?(?:中華民國)?(\d{2,3})年(\d{1,2})月(\d{1,2})日", True, 95),
        (r"發文日期:?(\d{2,3})[./-](\d{1,2})[./-](\d{1,2})", True, 90),
        (r"中華民國(\d{2,3})年(\d{1,2})月(\d{1,2})日", True, 65),
        (r"(20\d{2})年(\d{1,2})月(\d{1,2})日", False, 55),
        (r"(?<!\d)(20\d{2})[/.-](\d{1,2})[/.-](\d{1,2})(?!\d)", False, 50),   # 設計圖圖框常見 2023/12/01
        (r"(?<!\d)(\d{3})年(\d{1,2})月(\d{1,2})日", True, 55),
    ]
    for pat, roc, conf in pats:
        for m in re.finditer(pat, flat):
            y, mo, d = (int(x) for x in m.groups())
            if roc:
                y += 1911
            iso = f"{y:04d}-{mo:02d}-{d:02d}"
            if _pdf_valid_date(iso):
                return iso, m.group(0), conf
    return "", "", 0


# 從使用者 G 槽已改名歷史檔案學來的分類模型（tools/pdf_train.py 產生 pdf_model.json）
PDF_MODEL_CACHE = {"data": None, "loaded": False}


def _pdf_model():
    if not PDF_MODEL_CACHE["loaded"]:
        PDF_MODEL_CACHE["loaded"] = True
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_model.json"), encoding="utf-8") as f:
                PDF_MODEL_CACHE["data"] = json.load(f)
        except Exception as e:
            print(f"[pdf_rename] 沒有分類模型，改用關鍵字規則：{e}", flush=True)
    return PDF_MODEL_CACHE["data"]


def _pdf_model_doc_type(flat, settings):
    """用學習模型判斷類型。回傳 (類型, 信心, 理由) 或 None（沒有模型／沒有任何特徵命中）。"""
    model = _pdf_model()
    if not model:
        return None
    allowed = {t.get("name") for t in settings.get("doc_types") or []}
    head = flat[: int(model.get("head") or 1500)]
    grams = set()
    for seg in re.findall(r"[\u4e00-\u9fff]+", head):
        for n in (2, 3, 4):
            for i in range(len(seg) - n + 1):
                grams.add(seg[i:i + n])
    scored = []
    for name, m in (model.get("classes") or {}).items():
        if name not in allowed:
            continue
        hits = [(w, x) for x, w in m["w"].items() if x in grams]
        scored.append((sum(w for w, _ in hits) + 0.3 * m["prior"], name, hits))
    scored.sort(key=lambda x: -x[0])
    if not scored or not scored[0][2]:
        return None
    margin = scored[0][0] - (scored[1][0] if len(scored) > 1 else 0)
    conf = 50
    for lo, acc in model.get("calib") or []:
        if margin >= lo:
            conf = int(acc * 100)
    conf = min(conf, 97)
    top = "、".join(f"「{x}」" for _, x in sorted(scored[0][2], reverse=True)[:4])
    reason = f"依歷史檔案學到的用字判斷（命中 {len(scored[0][2])} 個特徵，例如 {top}）"
    if len(scored) > 1 and conf < 80:
        reason += f"；也可能是：{scored[1][1]}"
    return scored[0][1], conf, reason


def _pdf_rule_doc_type(flat, subject, settings):
    """先用學習模型；沒有模型或判斷不出來時，用關鍵字打分：主旨命中 ×3、全文命中 ×1。回傳 (類型, 信心, 理由)。"""
    learned = _pdf_model_doc_type(flat, settings)
    if learned:
        return learned
    results = []
    for t in settings.get("doc_types") or []:
        name = (t.get("name") or "").strip()
        if not name:
            continue
        raw = re.sub(r"[（(][^）)]*[）)]", "", (t.get("keywords") or ""))
        kws = {k.strip() for k in re.split(r"[、,，;；/\s]+", raw) if len(k.strip()) >= 2}
        kws.add(name)
        score, hits = 0, []
        # 文件標題就是類型名稱（或檔名常用的其他寫法）時，直接加重分：例如「串接圖」「產品出廠暨保固證明書」
        titles = {name} | {re.sub(r"[（(][^）)]*[）)]", "", x).strip() for x in re.split(r"[、,，]", t.get("synonyms") or "")}
        title_hit = next((x for x in sorted(titles, key=len, reverse=True) if len(x) >= 3 and _pdf_flat(x) in flat), None)
        if title_hit:
            score += 4
            hits.append(f"文件標題有「{title_hit}」")
        for k in kws:
            kf = _pdf_flat(k)
            if kf and kf in subject:
                score += 3
                hits.append(f"主旨有「{k}」")
            elif kf and kf in flat:
                score += 1
                hits.append(f"內文有「{k}」")
        if score:
            results.append((score, name, hits))
    if not results:
        return "其他", 0, "沒有命中任何函文類型關鍵字"
    results.sort(key=lambda x: -x[0])
    best = results[0]
    second = results[1][0] if len(results) > 1 else 0
    in_subject = any(h.startswith("主旨") or h.startswith("文件標題") for h in best[2])
    if in_subject and best[0] - second >= 2:
        conf = 92
    elif in_subject and best[0] > second:
        conf = 75
    elif best[0] > second:
        conf = 60
    else:
        conf = 40
    reason = "、".join(best[2][:4])
    if second and best[0] - second < 2:
        reason += f"（也可能是：{results[1][1]}）"
    return best[1], conf, reason


def _pdf_rule_extract(text, settings):
    flat = _pdf_flat(text)
    m = re.search(r"主旨:(.+?)(?:說明:|辦法:|正本:|附件:|$)", flat)
    subject = m.group(1)[:300] if m else ""
    m = re.search(r"發文字號:(.{2,40}?號)", flat)
    doc_number = m.group(1) if m else ""
    m = re.search(r"(臺灣電力股份有限公司[一-鿿]{0,12}?(?:區營業處|處|分處|公司)|台灣電力股份有限公司[一-鿿]{0,12}?(?:區營業處|處|分處|公司)"
                  r"|經濟部能源署|經濟部[一-鿿]{0,6}局|[一-鿿]{2,3}[縣市]政府(?:[一-鿿]{1,6}?(?:局|處))?)", flat)
    issuer = m.group(1) if m else ""
    doc_type, type_conf, type_reason = _pdf_rule_doc_type(flat, subject or flat[:200], settings)
    rule = next((t for t in settings.get("doc_types") or [] if t.get("name") == doc_type), {})
    learned_keys = ((_pdf_model() or {}).get("date_keys") or {}).get(doc_type) or []
    keys = "、".join(list(learned_keys) + [k for k in re.split(r"[、,，;；]", rule.get("date_keys") or "") if k.strip()])
    doc_date, date_raw, date_conf = _pdf_rule_date(flat, keys)
    addresses = re.findall(r"[一-鿿]{1,3}[縣市][一-鿿]{1,4}[鄉鎮市區][一-鿿0-9\-之巷弄段路街村里鄰]{2,30}?號", flat)
    addresses += re.findall(r"[一-鿿]{1,3}[縣市][一-鿿]{1,4}[鄉鎮市區][一-鿿]{1,8}段[0-9\-、]{1,30}地號", flat)
    ext = {
        "doc_type": doc_type, "doc_type_reason": type_reason, "doc_date": doc_date, "doc_date_raw": date_raw,
        "doc_number": doc_number, "issuer": issuer, "recipient": "", "subject": subject,
        "identifiers": {"addresses": list(dict.fromkeys(addresses))[:10], "names": [flat]},
        "notes": "",
    }
    return ext, type_conf, date_conf


def _pdf_scan_fulltext(flat, scores_add):
    """拿每個案件的編號／案號在全文裡找（OCR 可能把 - 或空白弄亂，所以比對前都去掉符號）。"""
    digits = _norm_id(flat)
    textn = _norm_text(flat)
    for c in _pdf_case_ref():
        for label, val in c["ids"].items():
            v = _norm_id(val)
            if len(v) >= 8 and v in digits:
                scores_add(c, 100, f"{label} {val} 出現在文件")["strong"] = True
        cn = _norm_text(c["case_no"])
        if len(cn) >= 4 and cn in textn:
            scores_add(c, 80, f"文件內出現案號 {c['case_no']}")["strong"] = True


def _pdf_free_analyze(text, source, settings):
    ext, type_conf, date_conf = _pdf_rule_extract(text, settings)
    ranked, strong = _pdf_match_cases(ext, fulltext=_pdf_flat(text))
    issues = []
    case_no, case_conf, case_reason = "", 0, ""
    if len(strong) == 1:
        case_no = next(iter(strong))
        case_conf = 95
        case_reason = "；".join(next(s["why"] for s in ranked if s["case"]["case_no"] == case_no))
    elif len(strong) > 1:
        top = [s for s in ranked if s["strong"]]
        case_no, case_conf = top[0]["case"]["case_no"], 50
        case_reason = "；".join(top[0]["why"])
        issues.append("多個案件的編號都出現在文件：" + "、".join(sorted(strong)))
    elif ranked:
        top = ranked[0]
        second = ranked[1]["score"] if len(ranked) > 1 else 0
        case_no = top["case"]["case_no"]
        case_reason = "；".join(top["why"])
        case_conf = 75 if top["score"] >= 60 and top["score"] - second >= 30 else 40
        issues.append("文件裡找不到案件編號，案號是用地址／名稱推測的，請確認")
    else:
        issues.append("無法確定案號，請人工選擇")
    if ext["doc_type"] == "其他":
        issues.append("函文類型沒有命中規則關鍵字，請人工選擇（也可以到規則裡補關鍵字）")
    elif type_conf < 75:
        issues.append(f"函文類型不太確定：{ext['doc_type_reason']}")
    if not ext["doc_date"]:
        issues.append("找不到發文日期")
    elif date_conf < 90:
        issues.append(f"沒有找到「發文日期」欄位，日期取自文件中的「{ext['doc_date_raw']}」，請確認")
    case = next((s["case"] for s in ranked if s["case"]["case_no"] == case_no), None)
    evidence = "\n".join([
        f"文字來源：{source}",
        f"案號：{case_reason or '—'}（信心 {case_conf}）",
        f"函文類型：{ext['doc_type_reason']}（信心 {type_conf}）",
        f"發文日期：文件寫「{ext['doc_date_raw'] or '—'}」（信心 {date_conf}）",
    ])
    ext_store = dict(ext, identifiers={"addresses": ext["identifiers"]["addresses"]})
    return {
        "case": case, "case_no": case_no, "doc_type": ext["doc_type"], "doc_date": ext["doc_date"],
        "doc_number": ext["doc_number"], "issuer": ext["issuer"], "subject": ext["subject"],
        "confidence": max(0, min(case_conf, type_conf, date_conf)), "evidence": evidence, "issues": issues,
        "conf_parts": [case_conf, type_conf, date_conf],
        "ranked": ranked,
        "result": {"engine": "free", "source": source, "extract": ext_store, "text_excerpt": (text or "")[:4000]},
    }


def _pdf_ai_analyze(pdf_bytes, settings):
    pdf_b64 = base64.b64encode(pdf_bytes).decode()
    system = _pdf_system_prompt(settings)
    ext = _pdf_extract(settings, system, pdf_b64)
    ranked, strong = _pdf_match_cases(ext)
    ver = _pdf_verify(settings, system, pdf_b64, ext, ranked)

    issues = list(ver.get("issues") or [])
    by_no = {s["case"]["case_no"]: s for s in ranked}
    case_no = (ver.get("case_no") or "").strip()
    if case_no and case_no not in by_no:
        issues.append(f"模型選的案號 {case_no} 不在候選清單，已清除")
        case_no = ""
    case_conf = int(ver.get("case_confidence") or 0) if case_no else 0
    if case_no and case_no in strong:
        case_conf = max(case_conf, 95) if len(strong) == 1 else min(case_conf, 70)
        if len(strong) > 1:
            issues.append("多個案件的編號都跟文件吻合：" + "、".join(sorted(strong)))
    elif case_no and strong:
        case_conf = min(case_conf, 40)
        issues.append("模型選的案件跟編號精確比對到的案件不同：" + "、".join(sorted(strong)))
    elif case_no:
        case_conf = min(case_conf, 80)   # 沒有任何編號精確吻合，只靠地址／名稱
    if not case_no:
        issues.append("無法確定案號，請人工選擇")

    doc_type = ver.get("doc_type") or ext.get("doc_type") or "其他"
    type_conf = int(ver.get("doc_type_confidence") or 0)
    if ext.get("doc_type") and ext["doc_type"] != doc_type:
        type_conf = min(type_conf, 55)
        issues.append(f"兩次判讀函文類型不一致：{ext['doc_type']} / {doc_type}")
    if doc_type == "其他":
        type_conf = min(type_conf, 50)
        issues.append("函文類型不在規則清單內")

    doc_date = (ver.get("doc_date") or "").strip()
    date_conf = int(ver.get("doc_date_confidence") or 0)
    if doc_date and not _pdf_valid_date(doc_date):
        issues.append(f"發文日期 {doc_date} 格式或範圍不合理，已清除")
        doc_date = ""
    if (ext.get("doc_date") or "").strip() and ext["doc_date"].strip() != doc_date:
        date_conf = min(date_conf, 55)
        issues.append(f"兩次判讀發文日期不一致：{ext['doc_date']} / {doc_date or '（空）'}")
    if not doc_date:
        date_conf = 0
        issues.append("找不到發文日期")

    evidence = "\n".join(x for x in [
        "文字來源：AI 讀 PDF",
        f"案號：{ver.get('case_reason') or '—'}（信心 {case_conf}）",
        f"函文類型：{ext.get('doc_type_reason') or '—'}（信心 {type_conf}）",
        f"發文日期：文件寫「{ext.get('doc_date_raw') or '—'}」（信心 {date_conf}）",
        ext.get("notes") and f"備註：{ext['notes']}",
    ] if x)
    return {
        "case": by_no[case_no]["case"] if case_no else None, "case_no": case_no, "doc_type": doc_type,
        "doc_date": doc_date, "doc_number": ext.get("doc_number") or "", "issuer": ext.get("issuer") or "",
        "subject": ext.get("subject") or "",
        "confidence": max(0, min(100, min(case_conf, type_conf, date_conf))), "evidence": evidence,
        "conf_parts": [case_conf, type_conf, date_conf],
        "issues": issues, "ranked": ranked,
        "result": {"engine": "ai", "model": PDF_MODEL, "extract": ext, "verify": ver},
    }


def _pdf_engine(settings):
    eng = settings.get("engine") or "free"
    return eng if eng in ("free", "hybrid", "ai") else "free"


def _pdf_recognize(rec):
    settings = _pdf_settings()
    f = rec.get("fields", {})
    att = (f.get(PDF_F["file"]) or [{}])[0]
    if not att.get("url"):
        raise Exception("記錄裡沒有 PDF 檔案")
    pdf = requests.get(att["url"], timeout=120)
    pdf.raise_for_status()

    engine = _pdf_engine(settings)
    threshold = int(settings.get("auto_confirm_threshold") or 92)
    if engine == "ai":
        out = _pdf_ai_analyze(pdf.content, settings)
    else:
        try:
            text, source = _pdf_get_text(pdf.content, settings)
            out = _pdf_free_analyze(text, source, settings)
        except Exception:
            if engine != "hybrid" or not os.environ.get("ANTHROPIC_API_KEY"):
                raise
            out = None
        if engine == "hybrid" and os.environ.get("ANTHROPIC_API_KEY") and (out is None or out["confidence"] < threshold):
            out = _pdf_ai_analyze(pdf.content, settings)

    # 文件上沒有日期 → 用收到檔案那天（LINE 收件＝下載到資料夾的時間；手動上傳＝上傳時間）。
    # 07 設備文件常常沒有日期，屬正常；其他類型（尤其 06 函文一定有發文日期）可能是 OCR 沒讀到，降信心提醒。
    if not out["doc_date"]:
        received = (f.get(PDF_F["uploaded_at"]) or rec.get("createdTime") or "")[:10]
        if _pdf_valid_date(received):
            normal = _pdf_doc_category(out["doc_type"]) == "07"
            out["doc_date"] = received
            out["issues"] = [x for x in out["issues"] if x != "找不到發文日期"]
            out["issues"].append(f"文件上沒有日期，先用收件日 {received}" + ("" if normal else "（這類文件通常有日期，可能是沒讀到，請確認）"))
            parts = list(out.get("conf_parts") or [out["confidence"]] * 3)
            parts[2] = 85 if normal else 45
            out["confidence"] = max(0, min(parts))
            out["evidence"] += f"\n日期：文件上沒有日期，用收件日 {received}（信心 {parts[2]}）"
    case, case_no, doc_type, doc_date = out["case"], out["case_no"], out["doc_type"], out["doc_date"]
    confidence = out["confidence"]
    suggested = _pdf_build_name(settings.get("template"), case, doc_type, doc_date)
    result = dict(out["result"], issues=out["issues"], candidates=[
        {"case_no": s["case"]["case_no"], "alias": s["case"]["alias"], "score": s["score"],
         "why": s["why"], "strong": s["strong"]} for s in out["ranked"]])
    fields = {
        PDF_F["case_no"]: case_no,
        PDF_F["alias"]: case["alias"] if case else "",
        PDF_F["doc_type"]: doc_type,
        PDF_F["doc_date"]: doc_date or None,
        PDF_F["doc_number"]: out["doc_number"],
        PDF_F["issuer"]: out["issuer"],
        PDF_F["subject"]: out["subject"],
        PDF_F["suggested"]: suggested,
        PDF_F["final_name"]: suggested,
        PDF_F["confidence"]: confidence,
        PDF_F["evidence"]: out["evidence"],
        PDF_F["result_json"]: json.dumps(result, ensure_ascii=False)[:95000],
        PDF_F["error"]: "",
        PDF_F["recognized_at"]: _tw_now_iso(),
        PDF_F["status"]: PDF_ST_REVIEW,
    }
    auto = (settings.get("auto_confirm") and case_no and doc_date and doc_type != "其他"
            and confidence >= threshold)
    if auto:
        fields[PDF_F["status"]] = PDF_ST_CONFIRMED
        fields[PDF_F["confirmed_at"]] = _tw_now_iso()
        fields[PDF_F["confirmed_by"]] = f"自動確認（信心 {confidence}）"
    _pdf_patch(rec["id"], fields)
    if auto and settings.get("writeback"):
        _pdf_writeback(rec["id"], case, doc_type, doc_date)
    return confidence


def _pdf_writeback(record_id, case, doc_type, doc_date):
    """把發文日期寫回「進度管理」對應里程碑的完成日期。只填空白；已有不同日期就不動、記下來給人看。"""
    msg = _pdf_writeback_msg(case, doc_type, doc_date)
    try:
        _pdf_patch(record_id, {PDF_F["writeback"]: msg})
    except Exception as e:
        print(f"[pdf_rename] 寫回結果記錄失敗：{e}", flush=True)
    return msg


def _pdf_writeback_msg(case, doc_type, doc_date):
    rule = next((t for t in _pdf_settings().get("doc_types") or [] if t.get("name") == doc_type), None)
    milestone = (rule or {}).get("milestone", "").strip()
    if not milestone:
        return "—（此函文類型沒有設定對應里程碑，不寫回）"
    if not case or not case.get("record_id"):
        return f"⚠ 案件不在 Airtable 專案細節，無法寫回「{milestone}」"
    if not doc_date:
        return "⚠ 沒有發文日期，無法寫回"
    try:
        resp = requests.get(f"{CASE_API_URL}/{case['record_id']}", headers=airtable_headers(),
                            params={"returnFieldsByFieldId": "true"}, timeout=30)
        resp.raise_for_status()
        ms_ids = resp.json().get("fields", {}).get(FIELD_MS_LINK_ON_CASE) or []
        found = []
        for i in range(0, len(ms_ids), 50):
            batch = ms_ids[i:i + 50]
            formula = "AND(OR(" + ",".join(f"RECORD_ID()='{m}'" for m in batch) + \
                      "),{" + FIELD_MS_TYPE + "}='" + milestone.replace("'", "\\'") + "')"
            found += airtable_get_all(MILESTONE_API_URL, formula, [FIELD_MS_TYPE, FIELD_MS_ACTUAL_DATE])
        if found:
            ms_id = found[0]["id"]
            existing = found[0].get("fields", {}).get(FIELD_MS_ACTUAL_DATE)
            if existing == doc_date:
                return f"✓ 進度管理「{milestone}」完成日期已是 {doc_date}"
            if existing:
                return f"⚠ 進度管理「{milestone}」已有完成日期 {existing}（文件 {doc_date}），未覆蓋，請人工確認"
        else:
            ms_id = ensure_milestone_record(case["record_id"], milestone)
        r = requests.patch(f"{MILESTONE_API_URL}/{ms_id}", headers=airtable_headers(),
                           json={"fields": {FIELD_MS_ACTUAL_DATE: doc_date}}, timeout=30)
        if r.status_code >= 400:
            raise Exception(r.text)
        return f"✓ 已寫入進度管理「{milestone}」完成日期 {doc_date}"
    except Exception as e:
        return f"✗ 寫回失敗：{str(e)[:300]}"


def _pdf_counts():
    recs = airtable_get_all(PDF_API_URL, None, [PDF_F["status"]])
    counts = {}
    for r in recs:
        st = r.get("fields", {}).get(PDF_F["status"]) or ""
        counts[st] = counts.get(st, 0) + 1
    return counts


def pdf_rename_run(force=False):
    """背景排程每分鐘叫一次；距上次執行超過設定的間隔才真的跑（force＝手動「立即辨識」）。"""
    settings = _pdf_settings()
    if not force:
        if not settings.get("enabled"):
            return
        last = PDF_RUN["last_run_at"]
        if last and time.time() - last < max(1, int(settings.get("interval_min") or 5)) * 60:
            return
    # 還沒設 API key 就先不動佇列（不然檔案會被計入失敗次數、最後變成「辨識失敗」）
    if not AIRTABLE_TOKEN or (_pdf_engine(settings) == "ai" and not os.environ.get("ANTHROPIC_API_KEY")):
        if force:
            PDF_RUN["last_error"] = "後端沒有設定 ANTHROPIC_API_KEY（Render → Environment）"
        return
    if not PDF_LOCK.acquire(blocking=False):
        return
    PDF_RUN.update(running=True, last_run_at=time.time(), last_error=None, last_count=0)
    try:
        # 卡在「辨識中」太久（process 被重啟之類）的放回佇列
        stale = airtable_get_all(PDF_API_URL, "{" + PDF_F["status"] + "}='" + PDF_ST_RUNNING + "'",
                                 [PDF_F["recognized_at"]])
        for r in stale:
            started = r.get("fields", {}).get(PDF_F["recognized_at"]) or ""
            try:
                age = datetime.now(TW_TZ) - datetime.fromisoformat(started)
            except ValueError:
                age = timedelta(days=1)
            if age > timedelta(minutes=PDF_STALE_MINUTES):
                _pdf_patch(r["id"], {PDF_F["status"]: PDF_ST_QUEUED})
        queued = airtable_get_all(PDF_API_URL, "{" + PDF_F["status"] + "}='" + PDF_ST_QUEUED + "'",
                                  list(PDF_F.values()))
        queued.sort(key=lambda r: r.get("createdTime", ""))
        for rec in queued[:max(1, int(settings.get("batch_size") or 5))]:
            attempts = int(rec.get("fields", {}).get(PDF_F["attempts"]) or 0) + 1
            _pdf_patch(rec["id"], {PDF_F["status"]: PDF_ST_RUNNING, PDF_F["attempts"]: attempts,
                                   PDF_F["recognized_at"]: _tw_now_iso()})
            try:
                conf = _pdf_recognize(rec)
                PDF_RUN["last_count"] += 1
                print(f"[pdf_rename] {rec['id']} 辨識完成，信心 {conf}", flush=True)
            except Exception as e:
                err = f"{type(e).__name__}: {e}"[:2000]
                print(f"[pdf_rename] {rec['id']} 第 {attempts} 次辨識失敗：{err}", flush=True)
                _pdf_patch(rec["id"], {PDF_F["error"]: err,
                                       PDF_F["status"]: PDF_ST_FAILED if attempts >= PDF_MAX_ATTEMPTS else PDF_ST_QUEUED})
                PDF_RUN["last_error"] = err
                if "ANTHROPIC_API_KEY" in err or "Google OCR 網址" in err:
                    break
    except Exception as e:
        PDF_RUN["last_error"] = f"{type(e).__name__}: {e}"[:2000]
        print(f"[pdf_rename] 執行失敗：{PDF_RUN['last_error']}", flush=True)
    finally:
        PDF_RUN.update(running=False, last_finished_at=_tw_now_iso())
        PDF_LOCK.release()


def _pdf_run_async():
    threading.Thread(target=pdf_rename_run, kwargs={"force": True}, daemon=True).start()


scheduler.add_job(pdf_rename_run, CronTrigger(minute="*"), id="pdf_rename", replace_existing=True,
                  max_instances=1, coalesce=True)


# ---------------- API ----------------

@app.route("/api/pdf-rename/status")
def pdf_rename_status():
    try:
        counts = _pdf_counts()
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    s = _pdf_settings()
    return jsonify({
        "counts": counts,
        "running": PDF_RUN["running"],
        "last_run_at": datetime.fromtimestamp(PDF_RUN["last_run_at"], TW_TZ).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        if PDF_RUN["last_run_at"] else None,
        "last_finished_at": PDF_RUN["last_finished_at"],
        "last_error": PDF_RUN["last_error"],
        "last_count": PDF_RUN["last_count"],
        "api_key_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "alias_count": len(_pdf_aliases()["map"]),
        "watchers_status": PDF_WATCHER_STATUS,
        "model": PDF_MODEL,
        "settings": s,
    })


@app.route("/api/pdf-rename/items")
def pdf_rename_items():
    status = (request.args.get("status") or "").strip()
    formula = None
    if status == "active":
        formula = "{" + PDF_F["status"] + "}!='" + PDF_ST_ARCHIVED + "'"
    elif status and status != "all":
        formula = "{" + PDF_F["status"] + "}='" + status.replace("'", "\\'") + "'"
    try:
        recs = airtable_get_all(PDF_API_URL, formula, list(PDF_F.values()))
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    items = [_pdf_record_to_dict(r) for r in recs]
    items.sort(key=lambda x: x["uploaded_at"] or "", reverse=True)
    return jsonify({"items": items})


def _pdf_create_from_bytes(name, data, uploader="", source="主控台上傳", src_path="", received_at=""):
    """建立一筆待辨識記錄並上傳 PDF。同一份內容（SHA1 相同）已經在佇列裡就不重複建立。"""
    import hashlib
    name = os.path.basename(name or "未命名.pdf")
    if not data.startswith(b"%PDF"):
        return {"name": name, "ok": False, "error": "不是 PDF 檔"}
    if len(data) > PDF_MAX_BYTES:
        return {"name": name, "ok": False, "error": "超過 5MB（Airtable 單檔上傳上限）"}
    digest = hashlib.sha1(data).hexdigest()
    try:
        dup = airtable_get_all(PDF_API_URL, "{" + PDF_F["hash"] + "}='" + digest + "'", [PDF_F["status"], PDF_F["src_name"]])
        if dup:
            return {"name": name, "ok": True, "duplicate": True, "id": dup[0]["id"],
                    "status": dup[0].get("fields", {}).get(PDF_F["status"], "")}
        resp = requests.post(PDF_API_URL, headers=airtable_headers(), json={"fields": {
            PDF_F["src_name"]: name, PDF_F["status"]: PDF_ST_QUEUED, PDF_F["source"]: source[:50],
            # 「上傳時間」欄位記的是收件時間：LINE 收件用檔案下載到資料夾的時間
            PDF_F["uploader"]: (uploader or "")[:50], PDF_F["uploaded_at"]: (received_at or "")[:30] or _tw_now_iso(),
            PDF_F["attempts"]: 0,
            PDF_F["hash"]: digest, PDF_F["src_path"]: (src_path or "")[:500],
        }}, timeout=30)
        if resp.status_code >= 400:
            raise Exception(resp.text)
        rid = resp.json()["id"]
        try:
            upload_attachment_to_ops_record(rid, PDF_F["file"], base64.b64encode(data).decode(), name,
                                            content_type="application/pdf")
        except Exception:
            requests.delete(f"{PDF_API_URL}/{rid}", headers=airtable_headers(), timeout=20)
            raise
        return {"name": name, "ok": True, "id": rid}
    except Exception as e:
        return {"name": name, "ok": False, "error": str(e)[:300]}


@app.route("/api/pdf-rename/upload", methods=["POST"])
def pdf_rename_upload():
    """主控台拖拉上傳。multipart：files[]（可多份），表單欄位 uploader、source。"""
    files = request.files.getlist("files") or request.files.getlist("files[]")
    if not files:
        return jsonify({"error": "沒有收到檔案"}), 400
    if len(files) > 30:
        return jsonify({"error": "一次最多 30 份"}), 400
    uploader = (request.form.get("uploader") or "").strip()[:50]
    source = (request.form.get("source") or "主控台上傳").strip()[:50]
    results = [_pdf_create_from_bytes(fs.filename, fs.read(), uploader, source) for fs in files]
    if any(r["ok"] and not r.get("duplicate") for r in results) and _pdf_settings().get("enabled"):
        _pdf_run_async()
    return jsonify({"results": results})


# ---- LINE 收件資料夾背景程式（tools/pdf_watcher.ps1，跑在每位 PM 的電腦上）----
@app.route("/api/pdf-rename/watcher-config")
def pdf_rename_watcher_config():
    pm = (request.args.get("pm") or "").strip()
    watchers = _pdf_settings().get("watchers") or []
    if not pm:
        return jsonify({"pms": [w.get("pm") for w in watchers if w.get("pm")]})
    w = next((w for w in watchers if w.get("pm") == pm), None)
    if not w:
        return jsonify({"error": f"主控台還沒設定「{pm}」的 LINE 收件資料夾"}), 404
    arc = _pdf_settings().get("archive") or {}
    return jsonify({"pm": pm, "folder": w.get("folder") or "", "enabled": bool(w.get("enabled", True)),
                    "interval_sec": 60, "max_mb": PDF_MAX_BYTES // (1024 * 1024),
                    # pm 留空＝任何開著的電腦都可以歸檔（大家都存同一個公司雲端），用 archive-claim 避免兩台搶同一份
                    "archive": {"enabled": bool(arc.get("enabled")) and (not arc.get("pm") or arc.get("pm") == pm),
                                "roots": [x.strip() for x in (arc.get("roots") or "").splitlines() if x.strip()]}})


@app.route("/api/pdf-rename/watcher-upload", methods=["POST"])
def pdf_rename_watcher_upload():
    """body: {pm, filename, path, data(base64)}"""
    body = request.get_json(force=True) or {}
    pm = (body.get("pm") or "").strip()
    if not pm:
        return jsonify({"error": "缺少 pm"}), 400
    try:
        data = base64.b64decode(body.get("data") or "")
    except Exception:
        return jsonify({"error": "檔案內容不是 base64"}), 400
    r = _pdf_create_from_bytes(body.get("filename"), data, uploader=pm, source=f"LINE／{pm}",
                               src_path=body.get("path") or "", received_at=body.get("received_at") or "")
    if r["ok"] and not r.get("duplicate") and _pdf_settings().get("enabled"):
        _pdf_run_async()
    return jsonify(r), (200 if r["ok"] else 400)


PDF_ARCHIVE_CLAIMS = {}   # {record_id: (pm, 領取時間)}；gunicorn 單一 worker，記憶體鎖即可


@app.route("/api/pdf-rename/<record_id>/archive-claim", methods=["POST"])
def pdf_rename_archive_claim(record_id):
    """背景程式歸檔前先領取，10 分鐘內同一份只給一台電腦處理。"""
    pm = ((request.get_json(force=True) or {}).get("pm") or "").strip()
    now = time.time()
    with PDF_LOCK_CLAIM:
        holder = PDF_ARCHIVE_CLAIMS.get(record_id)
        if holder and holder[0] != pm and now - holder[1] < 600:
            return jsonify({"ok": False, "holder": holder[0]}), 409
        PDF_ARCHIVE_CLAIMS[record_id] = (pm, now)
    return jsonify({"ok": True})


PDF_LOCK_CLAIM = threading.Lock()


@app.route("/api/pdf-rename/watcher-heartbeat", methods=["POST"])
def pdf_rename_watcher_heartbeat():
    body = request.get_json(force=True) or {}
    pm = (body.get("pm") or "").strip()
    if not pm:
        return jsonify({"error": "缺少 pm"}), 400
    PDF_WATCHER_STATUS[pm] = {
        "at": _tw_now_iso(), "host": str(body.get("host") or "")[:60], "folder": str(body.get("folder") or "")[:300],
        "folder_ok": bool(body.get("folder_ok")), "uploaded_total": int(body.get("uploaded_total") or 0),
        "skipped": int(body.get("skipped") or 0), "last_error": str(body.get("last_error") or "")[:300],
        "last_upload": str(body.get("last_upload") or "")[:200], "version": str(body.get("version") or "")[:20],
        "archived_total": int(body.get("archived_total") or 0), "last_archive": str(body.get("last_archive") or "")[:300],
        "archive_error": str(body.get("archive_error") or "")[:300], "case_folders": int(body.get("case_folders") or 0),
    }
    return jsonify({"ok": True})


@app.route("/api/pdf-rename/run", methods=["POST"])
def pdf_rename_run_now():
    if PDF_RUN["running"]:
        return jsonify({"ok": True, "message": "已經在辨識中"})
    _pdf_run_async()
    return jsonify({"ok": True})


@app.route("/api/pdf-rename/settings", methods=["POST"])
def pdf_rename_save_settings():
    body = request.get_json(force=True) or {}
    s = dict(_pdf_settings())
    for k in ("enabled", "auto_confirm", "writeback"):
        if k in body:
            s[k] = bool(body[k])
    for k, lo, hi in (("interval_min", 1, 1440), ("batch_size", 1, 30), ("auto_confirm_threshold", 50, 100)):
        if k in body:
            try:
                s[k] = max(lo, min(hi, int(body[k])))
            except (TypeError, ValueError):
                return jsonify({"error": f"{k} 必須是數字"}), 400
    if "template" in body:
        t = (body.get("template") or "").strip()
        if not t:
            return jsonify({"error": "命名格式不能空白"}), 400
        s["template"] = t
    if "rules_csv_url" in body:
        s["rules_csv_url"] = (body.get("rules_csv_url") or "").strip()
    if "watchers" in body:
        ws, seen = [], set()
        for w in body.get("watchers") or []:
            pm = (w.get("pm") or "").strip() if isinstance(w, dict) else ""
            if not pm or pm in seen:
                continue
            seen.add(pm)
            ws.append({"pm": pm[:30], "folder": (w.get("folder") or "").strip()[:300], "enabled": bool(w.get("enabled", True))})
        s["watchers"] = ws
    if isinstance(body.get("archive"), dict):
        a = body["archive"]
        s["archive"] = {"enabled": bool(a.get("enabled")), "pm": (a.get("pm") or "").strip()[:30],
                        "roots": (a.get("roots") or "").strip()[:2000]}
    if "engine" in body:
        if body["engine"] not in ("free", "hybrid", "ai"):
            return jsonify({"error": "engine 只能是 free／hybrid／ai"}), 400
        s["engine"] = body["engine"]
    if "ocr_url" in body:
        u = (body.get("ocr_url") or "").strip()
        if u and not u.startswith("https://script.google.com/"):
            return jsonify({"error": "OCR 網址應該是 https://script.google.com/ 開頭的 Apps Script 網址"}), 400
        s["ocr_url"] = u
    if "doc_types" in body:
        types = [{k: (t.get(k) or "").strip() for k in ("name", "keywords", "milestone", "note", "category", "synonyms", "date_keys")}
                 for t in body.get("doc_types") or [] if isinstance(t, dict) and (t.get("name") or "").strip()]
        if not types:
            return jsonify({"error": "至少要有一種函文類型"}), 400
        s["doc_types"] = types
    if body.get("reset_doc_types"):
        s["doc_types"] = PDF_DEFAULT_DOC_TYPES
    if body.get("reload_csv"):
        if not s.get("rules_csv_url"):
            return jsonify({"error": "還沒填 Google Sheet CSV 網址"}), 400
        try:
            s["doc_types"] = _pdf_load_rules_csv(s["rules_csv_url"])
        except Exception as e:
            return jsonify({"error": f"讀取 Google Sheet 失敗：{e}"}), 400
    try:
        _pdf_save_settings(s)
    except Exception as e:
        return jsonify({"error": f"儲存設定失敗：{e}"}), 502
    return jsonify({"ok": True, "settings": s})


@app.route("/api/pdf-rename/import-learn", methods=["POST"])
def pdf_rename_import_learn():
    """匯入 tools/pdf_learn.py 產生的 report.json：目前用來建立案號 → 簡稱對照（檔名 {簡稱}）。"""
    report = request.get_json(force=True) or {}
    al = _pdf_aliases_from_report(report)
    if not al["map"]:
        return jsonify({"error": "report.json 裡沒有可用的案場簡稱"}), 400
    try:
        _state_set_long(PDF_ALIAS_KEY, json.dumps(al, ensure_ascii=False))
    except Exception as e:
        return jsonify({"error": f"儲存失敗：{e}"}), 502
    PDF_ALIASES["data"] = al
    return jsonify({"ok": True, "count": len(al["map"]), "rules": al["rules"]})


@app.route("/api/pdf-rename/test-ocr", methods=["POST"])
def pdf_rename_test_ocr():
    """測試 Apps Script OCR 網址能不能連（Apps Script 的 doGet 會回 {ok: true}）。"""
    url = ((request.get_json(force=True) or {}).get("ocr_url") or _pdf_settings().get("ocr_url") or "").strip()
    if not url:
        return jsonify({"error": "還沒填 OCR 網址"}), 400
    if "/a/macros/" in url:
        return jsonify({"error": PDF_OCR_LOGIN_HINT}), 400
    try:
        resp = requests.get(url, timeout=60)
        data = _pdf_ocr_json(resp)
    except Exception as e:
        return jsonify({"error": f"連線失敗：{str(e)[:300]}"}), 400
    if not data.get("ok"):
        return jsonify({"error": str(data.get("error") or data)[:300]}), 400
    return jsonify({"ok": True, "message": data.get("message") or "連線成功"})


@app.route("/api/pdf-rename/preview-name", methods=["POST"])
def pdf_rename_preview_name():
    body = request.get_json(force=True) or {}
    case_no = (body.get("case_no") or "").strip()
    case = next((c for c in _pdf_case_ref() if c["case_no"] == case_no), None) if case_no else None
    return jsonify({"name": _pdf_build_name(_pdf_settings().get("template"), case or {"case_no": case_no},
                                            body.get("doc_type") or "", body.get("doc_date") or ""),
                    "alias": (case or {}).get("alias", ""), "known_case": bool(case)})


@app.route("/api/pdf-rename/<record_id>/confirm", methods=["POST"])
def pdf_rename_confirm(record_id):
    """人工確認（可同時修改案號／類型／日期／檔名）。"""
    body = request.get_json(force=True) or {}
    case_no = (body.get("case_no") or "").strip()
    doc_type = (body.get("doc_type") or "").strip()
    doc_date = (body.get("doc_date") or "").strip()
    final_name = (body.get("final_name") or "").strip()
    if not case_no or not doc_type or not final_name:
        return jsonify({"error": "案號、函文類型、檔名都要填"}), 400
    if doc_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", doc_date):
        return jsonify({"error": "日期格式要是 YYYY-MM-DD"}), 400
    if any(c in final_name for c in '\\/:*?"<>|'):
        return jsonify({"error": '檔名不能含 \\ / : * ? " < > |'}), 400
    if not final_name.lower().endswith(".pdf"):
        final_name += ".pdf"
    try:
        case = next((c for c in _pdf_case_ref() if c["case_no"] == case_no), None)
        _pdf_patch(record_id, {
            PDF_F["case_no"]: case_no, PDF_F["alias"]: (case or {}).get("alias", ""),
            PDF_F["doc_type"]: doc_type, PDF_F["doc_date"]: doc_date or None,
            PDF_F["final_name"]: final_name, PDF_F["status"]: PDF_ST_CONFIRMED,
            PDF_F["no_archive"]: not body.get("archive", True),
            PDF_F["confirmed_at"]: _tw_now_iso(), PDF_F["confirmed_by"]: (body.get("user") or "主控台").strip()[:50],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    wb = ""
    if _pdf_settings().get("writeback") and body.get("writeback", True):
        wb = _pdf_writeback(record_id, case, doc_type, doc_date)
    return jsonify({"ok": True, "writeback": wb, "final_name": final_name})


@app.route("/api/pdf-rename/<record_id>/retry", methods=["POST"])
def pdf_rename_retry(record_id):
    try:
        _pdf_patch(record_id, {PDF_F["status"]: PDF_ST_QUEUED, PDF_F["attempts"]: 0, PDF_F["error"]: ""})
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    _pdf_run_async()
    return jsonify({"ok": True})


@app.route("/api/pdf-rename/<record_id>/reopen", methods=["POST"])
def pdf_rename_reopen(record_id):
    try:
        _pdf_patch(record_id, {PDF_F["status"]: PDF_ST_REVIEW})
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    return jsonify({"ok": True})


@app.route("/api/pdf-rename/<record_id>", methods=["DELETE"])
def pdf_rename_delete(record_id):
    resp = requests.delete(f"{PDF_API_URL}/{record_id}", headers=airtable_headers(), timeout=20)
    if resp.status_code >= 400:
        return jsonify({"error": resp.text}), 502
    return jsonify({"ok": True})


@app.route("/api/pdf-rename/<record_id>/file")
def pdf_rename_file(record_id):
    """用確認檔名（或建議檔名）下載。?inline=1 給預覽用。"""
    from urllib.parse import quote
    try:
        d = _pdf_record_to_dict(_pdf_get_record(record_id))
        if not d["file_url"]:
            return jsonify({"error": "沒有檔案"}), 404
        pdf = requests.get(d["file_url"], timeout=120)
        pdf.raise_for_status()
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    name = d["final_name"] or d["suggested_name"] or d["src_name"] or "document.pdf"
    disp = "inline" if request.args.get("inline") else "attachment"
    return Response(pdf.content, mimetype="application/pdf", headers={
        "Content-Disposition": f"{disp}; filename=\"document.pdf\"; filename*=UTF-8''{quote(name)}"})


# 本機歸檔程式用：拿已確認待歸檔的清單，歸檔完回報。
@app.route("/api/pdf-rename/confirmed")
def pdf_rename_confirmed():
    try:
        # 確認時選「只改名下載、不歸檔」的不給背景程式
        recs = airtable_get_all(PDF_API_URL, "AND({" + PDF_F["status"] + "}='" + PDF_ST_CONFIRMED + "',NOT({"
                                + PDF_F["no_archive"] + "}))", list(PDF_F.values()))
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    return jsonify({"items": [_pdf_record_to_dict(r) for r in recs]})


@app.route("/api/pdf-rename/<record_id>/archived", methods=["POST"])
def pdf_rename_archived(record_id):
    body = request.get_json(force=True) or {}
    note = (body.get("result") or "").strip()
    if body.get("ok") is False:
        # 歸檔失敗：狀態留在「已確認」，原因記在寫回結果，主控台看得到
        try:
            old = _pdf_get_record(record_id).get("fields", {}).get(PDF_F["writeback"]) or ""
            old = "\n".join(x for x in old.splitlines() if not x.startswith("⚠ 歸檔失敗"))
            _pdf_patch(record_id, {PDF_F["writeback"]: (old + "\n" if old else "") + f"⚠ 歸檔失敗：{note}"})
        except Exception as e:
            return jsonify({"error": str(e)}), 502
        return jsonify({"ok": True})
    fields = {PDF_F["status"]: PDF_ST_ARCHIVED}
    if note:
        try:
            old = _pdf_get_record(record_id).get("fields", {}).get(PDF_F["writeback"]) or ""
        except Exception:
            old = ""
        fields[PDF_F["writeback"]] = (old + "\n" if old else "") + f"歸檔：{note}"
    try:
        _pdf_patch(record_id, fields)
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    return jsonify({"ok": True})


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
