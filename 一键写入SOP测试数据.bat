@echo off
chcp 65001 >nul
title WKT · 写入 SOP 测试数据
cd /d "%~dp0"
echo.
echo  将清空 SQLite 业务数据（订单/BOM/库存/出货），
echo  保留 data\customer_profiles.json 与 supplier_profiles.json。
echo.
python scripts\seed_sop_test_data.py %*
echo.
pause
