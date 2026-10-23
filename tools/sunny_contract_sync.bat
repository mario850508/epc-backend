@echo off
rem Sunny contract/detail-negotiation sync (run daily by Windows Task Scheduler)
rem 1) fix Anaconda SSL  2) download latest drawing_sync.py  3) sync, log to sync_log.txt
set PATH=%USERPROFILE%\anaconda3;%USERPROFILE%\anaconda3\Library\bin;%USERPROFILE%\anaconda3\Scripts;%PATH%
cd /d C:\sunny-tools
curl -sfL -o drawing_sync.py.new https://raw.githubusercontent.com/mario850508/epc-backend/main/tools/drawing_sync.py && move /y drawing_sync.py.new drawing_sync.py >nul
py drawing_sync.py --contracts-only > sync_log.txt 2>&1
