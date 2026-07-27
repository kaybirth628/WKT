@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync-to-cloud.ps1" -FullData
echo.
if errorlevel 1 (
  echo [FAILED] see messages above.
) else (
  echo [OK] open http://121.43.162.47:8088/ then Ctrl+F5
)
echo.
pause
