@echo off
cd /d "%~dp0"
echo === 同步功能到云端（代码 + 飞书通知配置，不覆盖订单/客商数据）===
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync-to-cloud.ps1"
echo.
pause
