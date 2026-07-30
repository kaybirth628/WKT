"""Debug 810 BOM search mismatch."""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from test_impl.order_management.cost_analysis.cost_store import CostStore

db = ROOT / "data" / "wkt_orders.db"
if not db.exists():
    db = ROOT / "data.local" / "wkt_orders.db"
print("DB:", db)

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

# Find customers containing 810
custs = conn.execute(
    """
    SELECT DISTINCT customer_name FROM cost_records
    WHERE customer_name LIKE '%810%' OR customer_name LIKE '%810%'
    ORDER BY customer_name
    """
).fetchall()
print("\nCustomers with 810 in name:", len(custs))
for r in custs:
    print(" ", r[0])

# All product names with 810
rows = conn.execute(
    """
    SELECT id, customer_name, product_part_no, product_name, updated_at
    FROM cost_records
    WHERE LOWER(product_name) LIKE '%810%'
    ORDER BY customer_name, product_part_no
    """
).fetchall()
print("\nAll records product_name LIKE %810%:", len(rows))
for r in rows:
    print(f"  {r['product_part_no']!r} | {r['customer_name']!r} | {r['product_name']!r}")

# Per customer - pick most likely customer from user report
for cust_pattern in ["810", "810%"]:
    matched_custs = conn.execute(
        "SELECT DISTINCT customer_name FROM cost_records WHERE customer_name LIKE ?",
        (f"%{cust_pattern}%",),
    ).fetchall()
    for c in matched_custs:
        cust = c[0]
        all_for_cust = conn.execute(
            """
            SELECT product_part_no, product_name FROM cost_records
            WHERE customer_name LIKE ?
            AND LOWER(product_name) LIKE '%810%'
            ORDER BY product_part_no
            """,
            (f"%{cust}%",) if cust_pattern == "810" else (cust,),
        ).fetchall()
        if not all_for_cust:
            continue
        print(f"\nCustomer {cust!r} + product_name 810: {len(all_for_cust)}")
        for r in all_for_cust:
            print(f"  {r['product_part_no']} | {r['product_name']}")

store = CostStore(str(db))
for q in ["810", "810%"]:
    items = store.search_part_numbers(q=q, limit=20)
    print(f"\nsearch_part_numbers(q={q!r}, limit=20): {len(items)}")
    for it in items:
        print(f"  {it['product_part_no']} | {it['customer_name']} | {it['product_name']}")

# Simulate API list_records with customer filter
from test_impl.order_management.cost_analysis.record_service import CostRecordService
from test_impl.order_management.order_entry.line_store import LineStore

line_store = LineStore(str(db))
svc = CostRecordService(store=store, line_store=line_store)
for cust in [r[0] for r in custs[:5]]:
    recs = svc.list_records(q="810", customer=cust)
    pn810 = [r for r in recs if "810" in (r.product_name or "").lower()]
    if pn810:
        print(f"\nlist_records(q=810, customer={cust!r}): total={len(recs)} name810={len(pn810)}")
        for r in pn810:
            print(f"  {r.product_part_no} | {r.product_name}")

conn.close()
