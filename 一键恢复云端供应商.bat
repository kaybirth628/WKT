@echo off
cd /d "%~dp0"
echo === 从云端备份恢复 supplier_profiles.json（供应商最多的一份）===
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\restore-cloud-suppliers.ps1"
echo.
pause
