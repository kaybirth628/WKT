@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  WKT - 一键同步云端（只更新程序，不动服务器数据）
echo  首次运行会生成 config\deploy.local.json，请填写 SSH 密码
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync-to-cloud.ps1"
echo.
pause
