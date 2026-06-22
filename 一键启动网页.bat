@echo off
chcp 65001 >nul
title WKT Sales Web
cd /d "%~dp0"
echo.
echo  Starting WKT web...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\restart_web.ps1"
if errorlevel 1 (
    echo.
    echo  PowerShell script failed. Trying direct start...
    echo.
    set WKT_PORT=5000
    set FLASK_DEBUG=1
    start "WKT Flask" cmd /k "cd /d %~dp0 && python test_impl\web\app.py"
    timeout /t 3 /nobreak >nul
    start http://127.0.0.1:5000/
)
echo.
echo  You can close this window. Service runs in another window.
pause
