#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.order_entry.line_store import default_db_path

BAD_PART = "数量"

store = CostStore(default_db_path())
cur = store._conn.execute(
    "DELETE FROM cost_records WHERE product_part_no = ?",
    (BAD_PART,),
)
store._conn.commit()
print(f"deleted {cur.rowcount} bad record(s)")
store._conn.close()
