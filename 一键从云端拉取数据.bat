@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [WKT] Pull data from cloud to local (local data will be backed up first)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\pull-data-from-cloud.ps1"
echo.
if errorlevel 1 (
  echo [FAILED] see messages above.
) else (
  echo [OK] local data/ updated from cloud.
)
echo.
pause
