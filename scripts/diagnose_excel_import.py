#!/usr/bin/env python3
"""解析 Excel 并打印阻断行原因。用法:
  python scripts/diagnose_excel_import.py "路径\\客户订单未结及出货明细表.xlsx"
或将 xlsx 放到项目 imports/ 目录后:
  python scripts/diagnose_excel_import.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_impl.order_management.order_entry.excel_import import (  # noqa: E402
    parse_excel_bytes,
    summarize_results,
)


def main() -> int:
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    else:
        imports_dir = ROOT / "imports"
        files = list(imports_dir.glob("*.xlsx")) + list(imports_dir.glob("*.csv"))
        if not files:
            print("请指定文件，或将 xlsx 放入 imports/ 目录")
            print('示例: python scripts/diagnose_excel_import.py "D:\\台账.xlsx"')
            return 1
        path = files[0]
        print(f"使用: {path}")

    if not path.is_file():
        print(f"文件不存在: {path}")
        return 1

    data = path.read_bytes()
    rows, unknown = parse_excel_bytes(data, path.name)
    summary = summarize_results(rows, unknown_headers=unknown or None)
    if summary.get("header_warnings"):
        for w in summary["header_warnings"]:
            print(f"提示: {w}")
        print()
    print(f"\n共 {summary['total']} 行，可导入 {summary['importable']}，阻断 {summary['blocked']}\n")

    for b in summary.get("blocked_list") or []:
        print(f"--- Excel 第 {b['row_no']} 行 ---")
        print(f"  客户: {b['customer']}")
        print(f"  订单号: {b['order_no']}")
        print(f"  品名: {b['product_spec']}")
        print(f"  PO: {b['po_qty']}  已出货: {b['shipped_qty']}")
        if b.get("excel_open_qty"):
            print(f"  Excel未结: {b['excel_open_qty']}  应为: {b['calc_open_qty']}")
        for e in b.get("errors") or []:
            print(f"  ✗ {e}")
        print()

    if summary["blocked"] == 0:
        print("无阻断行。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
