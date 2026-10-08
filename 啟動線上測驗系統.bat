@echo off
chcp 65001 >nul
title 115頭前國中 線上測驗系統 - 九年七班
cd /d "%~dp0"

echo ========================================================
echo   🏫 115頭前國中 九年七班 線上測驗系統
echo ========================================================
echo.
echo 正在檢查資料庫...
if not exist "quiz.db" (
    echo 正在初始化測驗題庫與班級名冊...
    python init_db.py
)

echo.
echo 正在為您啟動瀏覽器並連線至測驗系統...
timeout /t 2 >nul
start "" http://localhost:8080

echo.
echo 🌐 測驗伺服器運作中 (請勿關閉此視窗)：
echo    本機網址: http://localhost:8080
echo.
echo 💡 老師帳號：jenny       密碼：123456
echo 💡 管理員：minijenny     密碼：123456789
echo ========================================================
echo.

python server.py

pause
