#!/usr/bin/env python3
"""为 4 家专用送货单客户生成占位 Excel 模板（可后续替换为正式版式）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MAPPING = ROOT / "data" / "delivery_templates" / "mapping.json"
FILES = ROOT / "data" / "delivery_templates" / "files"

PLACEHOLDERS = [
    ("A1", "客户：{{客户}}"),
    ("A2", "订单号：{{订单号}}"),
    ("A3", "品名规格：{{品名规格}}"),
    ("A4", "客户料号：{{客户料号}}"),
    ("A5", "材质：{{材质}}"),
    ("A6", "单位：{{单位}}"),
    ("A7", "本次出货：{{本次出货}}"),
    ("A8", "出货日期：{{出货日期}}"),
    ("A10", "【占位模板】请替换为正式专用版式，保留 {{…}} 占位符即可自动填数"),
]


def main() -> None:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise SystemExit("需要 openpyxl：pip install openpyxl") from exc

    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    FILES.mkdir(parents=True, exist_ok=True)
    for _customer, filename in mapping.items():
        path = FILES / filename
        wb = Workbook()
        ws = wb.active
        ws.title = "送货单"
        for cell, val in PLACEHOLDERS:
            ws[cell] = val
        wb.save(path)
        print(f"Wrote {path}")
    print(f"Done: {len(mapping)} special templates in {FILES}")


if __name__ == "__main__":
    main()
