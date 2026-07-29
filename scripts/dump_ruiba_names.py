# -*- coding: utf-8 -*-
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))

from test_impl.order_management.cost_analysis.bom_form_import import parse_bom_workbook, preview_import_batch
from test_impl.order_management.cost_analysis.cost_store import CostStore

xls = ROOT / "Demo/BOM/锐霸产品BOM.xls"
parsed = parse_bom_workbook(xls.read_bytes(), filename=xls.name)
batch = preview_import_batch(parsed, store=CostStore(":memory:"), filename=xls.name, customer_names=["苏州锐霸智能科技有限公司"])

print("=== EXCEL 46 rows ===")
for i, item in enumerate(batch["items"], 1):
    p = item["parsed"]
    print(f"{i:2}. [{item.get('sheet_name','')}] {p.get('product_name')} | {p.get('product_part_no')}")

conn = sqlite3.connect(ROOT / "data/wkt_orders.db")
cur = conn.cursor()
cur.execute("""
SELECT product_name, product_part_no, id FROM cost_records
WHERE customer_name LIKE '%锐霸%' AND updated_at LIKE '2026-07-29T03:33:26%'
ORDER BY id
""")
rows = cur.fetchall()
print("\n=== DB latest 46 ===")
for i, r in enumerate(rows, 1):
    print(f"{i:2}. {r[0]} | {r[1]} | id={r[2]}")
conn.close()
