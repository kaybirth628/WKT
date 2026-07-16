@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo  WKT - 一键同步云端（程序 + 主数据；不覆盖服务器订单库）
echo  会同步：客户档案、送货单模板、供应商、飞书配置等
echo  不会动：wkt_orders.db、出货附件 delivery_notes
echo  首次运行会生成 config\deploy.local.json，请填写 SSH 密码
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync-to-cloud.ps1"
echo.
pause
