@echo off
echo 設置環境變量以使用本地 data 目錄...
set BULLPS_USE_LOCAL_DATA_DIR=true
echo 環境變量已設置: BULLPS_USE_LOCAL_DATA_DIR=true
echo.
echo 現在您可以啟動應用程序，它將使用 data 目錄作為數據存儲位置。
echo 您可以直接將文件複製到 data 目錄中，應用程序將自動讀取這些文件。
echo.
echo 按任意鍵啟動應用程序...
pause > nul
python -m backend.main
