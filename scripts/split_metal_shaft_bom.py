#!/usr/bin/env python3
"""拆分误合并的双产品 BOM（怡利·金属转轴）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from test_impl.order_management.cost_analysis.bom_form_import import (
    parse_bom_workbook,
    preview_import_rows,
)
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.cost_analysis.record_service import CostRecordService
from test_impl.order_management.order_entry.line_store import LineStore, default_db_path

PARTS = ("1A104D0A001-00", "1A104D0A003-00")


def main() -> int:
    db = default_db_path()
    store = CostStore(db_path=db)
    service = CostRecordService(store=store, line_store=LineStore(db_path=db))

    try:
        rows = store._conn.execute(
            "SELECT id, product_part_no FROM cost_records "
            "WHERE product_part_no IN (?, ?) OR product_part_no LIKE ?",
            (*PARTS, "%\n%"),
        ).fetchall()
        for rid, part in rows:
            if "\n" in str(part) or str(part) in PARTS:
                store.delete(int(rid))

        raw = Path("data/bom_import_audit/怡利BOM.xls").read_bytes()
        parsed = [
            r for r in parse_bom_workbook(raw, filename="怡利BOM.xls")
            if r.get("sheet_name") == "金属转轴"
        ]
        if len(parsed) != 2:
            raise SystemExit(f"expected 2 rows, got {len(parsed)}")

        previews = preview_import_rows(parsed, store=store)
        result = service.import_bom_rows(
            [p["payload"] for p in previews],
            skip_supplier_check=True,
        )
        if result["errors"]:
            raise SystemExit(str(result["errors"]))
        for p, rid in zip(previews, result["record_ids"]):
            row = p["parsed"]
            print(
                rid,
                row["product_part_no"],
                row["product_name"],
                row["unit_weight_g"],
            )
        return 0
    finally:
        store._conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
