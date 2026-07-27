#!/usr/bin/env python3
"""删除错误 BOM 导入并按修正解析器重新导入。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.order_entry.line_store import default_db_path

RESULT = ROOT / "data" / "bom_import_audit" / "import_result.json"


def main() -> int:
    if not RESULT.is_file():
        print(f"Missing {RESULT}")
        return 1
    data = json.loads(RESULT.read_text(encoding="utf-8"))
    ids = [int(x["record_id"]) for x in data.get("details") or [] if x.get("record_id")]
    store = CostStore(default_db_path())
    for rid in ids:
        store.delete(rid)
    store._conn.close()
    print(f"deleted {len(ids)} record(s)")
    return subprocess.call([sys.executable, str(ROOT / "scripts" / "import_bom_audit_batch.py")])


if __name__ == "__main__":
    raise SystemExit(main())
