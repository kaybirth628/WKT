@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  WKT - 一键同步云端（程序 + 供应商主数据，不动服务器订单/客户/数据库）
echo  首次运行会生成 config\deploy.local.json，请填写 SSH 密码
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync-to-cloud.ps1"
echo.
pause
