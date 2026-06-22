#!/usr/bin/env python3
"""生成双语专用送货单 Excel 模板（浙江金棒、上海金脉等）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_impl.order_management.delivery_note.bilingual_template import (  # noqa: E402
    CUSTOMER_LAYOUT,
    save_bilingual_template,
)

MAPPING = ROOT / "data" / "delivery_templates" / "mapping.json"
FILES = ROOT / "data" / "delivery_templates" / "files"


def main() -> None:
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    FILES.mkdir(parents=True, exist_ok=True)
    built = 0
    for customer, filename in mapping.items():
        if customer not in CUSTOMER_LAYOUT:
            continue
        path = save_bilingual_template(customer, FILES / filename)
        print(f"Wrote {path}")
        built += 1
    print(f"Done: {built} bilingual templates in {FILES}")


if __name__ == "__main__":
    main()
