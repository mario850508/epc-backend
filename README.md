# EPC 出貨／進場排程 後端

跟 line-pdf-collector 一樣的架構：Flask 程式部署到 Render，Airtable 金鑰只放在
伺服器的環境變數裡，前端網頁（主控台）只呼叫這支 API，不會接觸到金鑰。

## 資料結構（已實際查證，不需要再建欄位）

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

不需要另外新增欄位——你先前加在「進度管理」表的 3 個新欄位（模組出貨時間／
變流器出貨時間／進場日期）目前程式沒有用到，可以留著或之後刪掉都不影響運作。

## 本機測試

```bash
pip install -r requirements.txt
export AIRTABLE_TOKEN=你的PersonalAccessToken
python app.py
```

打開 http://localhost:5000/api/pending-cases 應該會看到 JSON 資料。

Airtable PAT 需要有這個 Base 的 `data.records:read` 和 `data.records:write` 權限，
在 https://airtable.com/create/tokens 建立。

## 部署到 Render

1. 把這個資料夾 push 到 GitHub（可以跟 line-pdf-collector 同一個帳號，另開一個 repo）
2. Render 建立新的 Web Service，連結這個 repo
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn app:app`
5. Environment → 新增變數 `AIRTABLE_TOKEN`，貼上你的 Airtable Personal Access Token
6. 部署完成後會拿到一個網址，例如 `https://epc-backend.onrender.com`
7. （可選）跟 line-pdf-collector 一樣，用 UptimeRobot 每 5 分鐘 ping 一次，避免免費方案休眠

## API 一覽

| Method | Path | 說明 |
|---|---|---|
| GET | `/api/pending-cases?vendor=三創` | 待安排出貨案件（vendor 參數可省略＝抓三創/尚展/曙光全部） |
| GET | `/api/entry-cases` | 案件進場安排 |
| POST | `/api/schedule` | 排定出貨時間，body: `{milestone_record_id, ship_date}` |
| POST | `/api/entry-date` | 排定進場日期，body: `{milestone_record_id, entry_date}` |

日期格式一律 `YYYY-MM-DD`。`milestone_record_id` 從 `/api/pending-cases`（欄位
`ship_milestone_record_id`）或 `/api/entry-cases`（欄位 `ship_milestone_record_id`／
`entry_milestone_record_id`）取得，不是案件本身的 record_id。

## 下一步

前端主控台（HTML）目前還是呼叫假資料，接下來要把 `pendingRows` 的載入邏輯改成
`fetch('https://你的Render網址/api/pending-cases')`，「排定日期」「排定進場日期」
的確認按鈕改成呼叫對應的 POST API。這部分可以在你把後端部署好、確認 API 能正常
回傳資料之後，我再幫你把前端接上去。
