@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  WKT - 提交并推送到 GitHub
echo  （含客户档案/送货单模板等主数据；不含订单库 *.db）
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\git-push.ps1"
echo.
pause
