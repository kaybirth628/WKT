#!/usr/bin/env python3
"""按审计目录批量导入 BOM（passed + pending）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_bom_excel import _collect_files, _load_customer_names
from test_impl.order_management.cost_analysis.bom_form_import import (
    build_import_payload,
    parse_bom_workbook,
    preview_import_batch,
)
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.cost_analysis.record_service import CostRecordService
from test_impl.order_management.order_entry.line_store import LineStore, default_db_path

IN_DIR = ROOT / "data" / "bom_import_audit"
REPORT = IN_DIR / "import_result.json"


def main() -> int:
    files = _collect_files([IN_DIR])
    files = [f for f in files if not f.name.startswith("确认-")]
    if not files:
        print("No BOM Excel files found.")
        return 1

    db = default_db_path()
    store = CostStore(db_path=db)
    service = CostRecordService(store=store, line_store=LineStore(db_path=db))
    customers = _load_customer_names()

    imported = 0
    skipped = 0
    errors: list[dict] = []
    details: list[dict] = []

    try:
        for path in files:
            parsed = parse_bom_workbook(path.read_bytes(), filename=path.name)
            batch = preview_import_batch(
                parsed,
                store=store,
                filename=path.name,
                customer_names=customers,
            )
            for item in batch["items"]:
                tier = item.get("tier")
                sheet = item.get("sheet_name") or ""
                part = (item.get("parsed") or {}).get("product_part_no") or sheet
                if tier == "blocked":
                    skipped += 1
                    errors.append(
                        {
                            "file": path.name,
                            "sheet": sheet,
                            "part": part,
                            "tier": tier,
                            "issues": item.get("issues") or [],
                        }
                    )
                    continue
                payload = item.get("payload") or build_import_payload(item.get("parsed") or {})
                try:
                    result = service.import_bom_rows([payload], skip_supplier_check=True)
                    if result["errors"]:
                        skipped += 1
                        errors.append(
                            {
                                "file": path.name,
                                "sheet": sheet,
                                "part": part,
                                "error": result["errors"][0]["error"],
                            }
                        )
                    else:
                        imported += 1
                        details.append(
                            {
                                "file": path.name,
                                "sheet": sheet,
                                "part": part,
                                "record_id": result["record_ids"][0],
                                "customer": payload.get("customer_name"),
                            }
                        )
                except ValueError as exc:
                    skipped += 1
                    errors.append(
                        {
                            "file": path.name,
                            "sheet": sheet,
                            "part": part,
                            "error": str(exc),
                        }
                    )
    finally:
        store._conn.close()

    summary = {
        "files": len(files),
        "imported": imported,
        "skipped": skipped,
        "details": details,
        "errors": errors,
    }
    REPORT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"imported": imported, "skipped": skipped, "report": str(REPORT)}, ensure_ascii=False))
    return 0 if imported else 1


if __name__ == "__main__":
    raise SystemExit(main())
