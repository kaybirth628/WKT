@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  === 一键推送云端和 GitHub ===
echo  1) 提交并推送到 GitHub（不含本地订单库 *.db）
echo  2) 部署程序代码到云端（不覆盖云端生产 data/ 业务数据）
echo.
echo  规范见 docs\change\PRODUCTION-SAFETY.md
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\push-cloud-and-github.ps1" %*
echo.
if errorlevel 1 (
  echo [FAILED] see messages above.
) else (
  echo [OK] GitHub + cloud code deploy finished. Open cloud site and Ctrl+F5.
)
echo.
pause
