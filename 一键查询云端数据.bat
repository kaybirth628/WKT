@echo off
cd /d "%~dp0"
echo === 查询云端 data 概况（供应商数、备份目录等）===
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\inspect-cloud-data.ps1"
echo.
pause
