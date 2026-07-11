@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  WKT - 提交并推送到 GitHub
echo  （有改动时会提示输入提交说明）
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\git-push.ps1"
echo.
pause
