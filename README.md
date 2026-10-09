# EPC 出貨／進場排程 後端

跟 line-pdf-collector 一樣的架構：Flask 程式部署到 Render，Airtable 金鑰只放在
伺服器的環境變數裡，前端網頁（主控台）只呼叫這支 API，不會接觸到金鑰。

## 資料更新架構（重要）

不是每次打開網頁就即時查 Airtable（那樣案件一多會很慢，30 秒～1 分多鐘）。改成：

- 伺服器背景排程，**每天 00:00／06:00／12:00／18:00（台北時間）**整批查一次 Airtable，
  存在記憶體的快取裡。
- 前端呼叫 `/api/pending-cases`、`/api/entry-cases` 時，直接讀這份快取，幾乎秒開。
- 使用者「排定日期」「排定進場日期」寫入 Airtable 成功後，後端會**立刻**觸發一次
  重新整理，讓清單馬上反映最新狀態（這個當下要等幾秒，因為要重新整批查一次）。
- 伺服器剛啟動（第一次部署、或 Render 重啟）時會立刻背景跑一次，不用等到下個整點。
  這段期間打開網頁會顯示「資料尚未準備好」，等約 1 分鐘後重新整理即可。

## 資料結構（已實際查證）

「[電廠] 案場管理」Base 裡：

- **專案細節**表：案件主表，一個案件一筆。
- **進度管理**表：里程碑表，**一個案件對應 18 筆記錄**，每筆代表一個階段
  （工程合約簽約、併聯審查、同意備案… 大料出貨時間、進場屋主預約…），
  各自有「預估日期」「實際日期」欄位。

出貨、進場的排定，寫的就是「進度管理」表裡對應那一筆的「實際日期」：

| 事件 | 對應里程碑（種類） |
|---|---|
| 模組／變流器出貨 | 大料出貨時間（視為同一個出貨事件，寫同一天） |
| 進場 | 進場屋主預約 |

「逆變器」欄位在 Airtable 是連結欄位，原始 API 回傳的是記錄代碼（recXXXX），
程式會另外查「採購-逆變器」表（`tbl7l7OM63jo3pxDN`）把代碼轉成型號文字。

## 本機測試

```bash
pip install -r requirements.txt
export AIRTABLE_TOKEN=你的PersonalAccessToken
python app.py
```

打開 http://localhost:5000/ 會看到目前快取狀態（updated_at、案件筆數）。
打開 http://localhost:5000/api/pending-cases 應該會看到 JSON 資料
（伺服器剛啟動時可能要等幾秒到十幾秒，背景整理完成後才有資料）。

Airtable PAT 需要有這個 Base 的 `data.records:read` 和 `data.records:write` 權限，
在 https://airtable.com/create/tokens 建立。

## 部署到 Render

1. 把這個資料夾 push 到 GitHub（可以跟 line-pdf-collector 同一個帳號，另開一個 repo）
2. Render 建立新的 Web Service，連結這個 repo
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`
5. Environment → 新增變數 `AIRTABLE_TOKEN`，貼上你的 Airtable Personal Access Token
6. 部署完成後會拿到一個網址，例如 `https://epc-backend-4aj2.onrender.com`
7. **強烈建議**用 UptimeRobot 每 5 分鐘 ping 一次首頁（`/`），避免免費方案閒置休眠——
   休眠後背景排程會停止運作，行為會退化成「醒來時才整理一次」

## API 一覽

| Method | Path | 說明 |
|---|---|---|
| GET | `/` | 健康檢查，附快取狀態（updated_at、pending_count、entry_count） |
| GET | `/api/pending-cases` | 待安排出貨案件（直接讀快取，不查 Airtable） |
| GET | `/api/entry-cases` | 案件進場安排（直接讀快取，不查 Airtable） |
| POST | `/api/refresh` | 手動觸發一次背景重新整理 |
| POST | `/api/schedule` | 排定出貨時間，body: `{milestone_record_id, ship_date}`，成功後自動重新整理快取 |
| POST | `/api/entry-date` | 排定進場日期，body: `{milestone_record_id, entry_date}`，成功後自動重新整理快取 |

日期格式一律 `YYYY-MM-DD`。`milestone_record_id` 從 `/api/pending-cases`（欄位
`ship_milestone_record_id`）或 `/api/entry-cases`（欄位 `ship_milestone_record_id`／
`entry_milestone_record_id`）取得，不是案件本身的 record_id。

## PDF 公文更名（線上版，2026-10-08）

原本的本機工具（V2.15，OCR）改成線上：主控台上傳 PDF → Airtable「公文更名佇列」
（`tblreT71hQpJMuf1B`）→ 後端每分鐘檢查、依設定間隔背景辨識（Claude 讀 PDF 抽資料
→ 程式比對「專案細節」全部案件的受理編號／電號／同意備案編號／地址 → Claude 對照候選
案件再確認一次並給信心分數）。人工確認（或高信心自動確認）後，可把發文日期寫回「進度
管理」對應里程碑的完成日期（只填空白）。

**辨識方式（設定 `engine`）預設是 `free`，完全免費**：電子檔 PDF 直接讀文字層（pypdf），
掃描檔送到使用者 Google 帳號部署的 Apps Script（Google 雲端硬碟內建 OCR，程式碼在主控台設定畫面
可以複製），再用規則抓發文日期／字號／主旨／函文類型，並拿每個案件的受理編號、電號、同意備案編號、
案號直接在全文裡比對。`hybrid`＝免費辨識信心不夠的才交給 Claude；`ai`＝全部用 Claude，這兩種才
需要 Render 環境變數 `ANTHROPIC_API_KEY`（可選 `PDF_RENAME_MODEL`，預設 `claude-opus-5-5`）。命名格式、函文類型規則、排程間隔存在「系統狀態」表
`pdf_rename_settings`，在主控台「⚙ 命名格式與函文規則」修改，也可以指定 Google Sheet
發布的 CSV 網址當規則來源。

| Method | Path | 說明 |
|---|---|---|
| GET | `/api/pdf-rename/status` | 各狀態數量、排程狀態、設定 |
| GET | `/api/pdf-rename/items?status=` | 清單（`all`／`active`／單一狀態） |
| POST | `/api/pdf-rename/upload` | multipart `files`（可多份；PDF／Word .docx／Excel .xlsx ≤5MB，照片 JPG/PNG 會轉成 PDF）、`uploader`、`source` |
| POST | `/api/pdf-rename/run` | 立即辨識一輪 |
| POST | `/api/pdf-rename/settings` | 修改設定；`reload_csv: true` 從 Google Sheet 重新載入函文類型 |
| POST | `/api/pdf-rename/test-ocr` | 測試 Apps Script OCR 網址 |
| POST | `/api/pdf-rename/preview-name` | 依命名格式產生檔名（`ext`），並回傳同案場同類型的文件 `same_type` |
| POST | `/api/pdf-rename/<id>/confirm` | 確認（`case_no, doc_type, doc_date, final_name, user, ids`），寫回進度管理完成日期，並把文件上的編號（`ids`：同意備案／設備登記／臺電受理／台電契約／電表租約編號、電號）填進專案細節空白欄位 |
| POST | `/api/pdf-rename/<id>/retry` · `/reopen` | 重新辨識／改回待確認 |
| DELETE | `/api/pdf-rename/<id>` | 刪除 |
| GET | `/api/pdf-rename/<id>/file` | 用確認檔名下載（`?inline=1` 預覽） |
| GET | `/api/pdf-rename/confirmed` | 本機歸檔程式用：已確認、待歸檔清單 |
| POST | `/api/pdf-rename/<id>/archived` | 本機歸檔完成回報（`result`；`ok:false` 失敗；`conflict:true, existing` 資料夾已有同類型檔案，暫停歸檔） |
| POST | `/api/pdf-rename/<id>/archive-force` | 資料夾已有同類型檔案時仍要歸檔（兩份都留） |
| POST | `/api/pdf-rename/import-learn` | 匯入 `tools/pdf_learn.py` 的 report.json：案場簡稱對照，並用歷史文件上的編號（`case_ids`）補專案細節空白的編號欄位 |
