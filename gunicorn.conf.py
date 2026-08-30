"""
gunicorn 設定檔（2026-08-30 新增）
=============================
用途：確保 app.py 裡的背景排程（scheduler）跟開機初始化（_startup_refresh_all，
也就是刷新 DATA_CACHE / MODEL_OPTIONS_CACHE 那兩份記憶體快取）是在「真正處理
HTTP 請求的 worker process」裡執行，而不是 gunicorn 的 master process。

問題背景：
  gunicorn 啟動流程是「master process 先 import 一次 app.py → 再 fork() 出
  worker process」。如果背景執行緒／排程是在 app.py 模組最外層（import 當下）
  就直接 threading.Thread(...).start() 或 scheduler.start()，那這些背景工作
  會在 master process 裡開始執行；根據 Unix fork() 的行為，只有呼叫 fork 的
  那個執行緒本身會延續到子行程（worker），其他背景執行緒不會被複製過去。
  結果就是：worker process（真正回應前端請求的行程）自己的 DATA_CACHE /
  MODEL_OPTIONS_CACHE 永遠停留在剛 fork 完、還沒被填入任何資料的初始狀態，
  不管 master process 那邊背景執行緒或排程再怎麼跑、跑幾次都沒有用——因為
  master 跟 worker 是兩個完全獨立的記憶體空間。

修正方式：
  gunicorn 提供 post_fork(server, worker) 這個 hook，保證是在 fork() 完成、
  worker process 已經是獨立行程之後才呼叫，且是在 worker 自己的行程裡執行。
  在這裡才呼叫 scheduler.start() 跟啟動 _startup_refresh_all() 背景執行緒，
  這兩個背景工作就會真的在 worker 自己的記憶體空間裡執行、更新的也會是
  worker 自己那份快取——前端打進來的請求（由 worker 處理）才看得到正確結果。

  這個專案設定 --workers 1，理論上只會有一個 worker，post_fork 只會被呼叫
  一次；如果之後 workers 數量調整為大於 1，每個 worker 各自都會呼叫一次
  post_fork，代表每個 worker 都會各自有一份獨立的背景排程跟快取（目前
  DATA_CACHE / MODEL_OPTIONS_CACHE 都是 process 內的記憶體變數，本來就沒有
  跨 worker 共享，這點在維持 --workers 1 的前提下不影響正確性；如果未來要
  提高 workers 數量，需要額外考慮多個 worker 各自重複打 Airtable API 的
  頻率問題）。
"""

import threading


def post_fork(server, worker):
    from app import scheduler, _startup_refresh_all

    server.log.info(f"[gunicorn post_fork] worker pid={worker.pid} 啟動背景排程與初始化快取…")

    if not scheduler.running:
        scheduler.start()

    threading.Thread(target=_startup_refresh_all, daemon=True).start()
