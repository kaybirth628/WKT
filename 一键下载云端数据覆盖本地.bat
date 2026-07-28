@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  === 下载云端数据覆盖本地 ===
echo  云端 data/ 将覆盖本地 data/（本地会先备份到 data.local.bak-时间戳）
echo  不会修改云端任何数据。
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\pull-data-from-cloud.ps1" %*
echo.
if errorlevel 1 (
  echo [FAILED] see messages above.
) else (
  echo [OK] local data/ updated from cloud production.
)
echo.
pause
