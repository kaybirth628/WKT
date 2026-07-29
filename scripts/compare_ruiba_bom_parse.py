#!/usr/bin/env python3
"""对比 锐霸产品BOM.xls 解析行数 vs 库内入库条数。"""
from __future__ import annotations

import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import xlrd

from test_impl.order_management.cost_analysis.bom_form_import import (
    _SKIP_SHEET_NAMES,
    _norm_text,
    parse_bom_workbook,
)

EXCEL = ROOT / "Demo" / "BOM" / "锐霸产品BOM.xls"
DB = ROOT / "data" / "wkt_orders.db"


def main() -> int:
    if not EXCEL.is_file():
        print(f"Missing {EXCEL}")
        return 1
    raw = EXCEL.read_bytes()
    book = xlrd.open_workbook(file_contents=raw)
    all_sheets = [s.name for s in book.sheets()]

    parsed = parse_bom_workbook(raw, filename=EXCEL.name)
    parsed_sheet_names = {r["sheet_name"] for r in parsed}
    skipped = [n for n in all_sheets if _norm_text(n).casefold() in _SKIP_SHEET_NAMES]
    empty = [n for n in all_sheets if n not in parsed_sheet_names and n not in skipped]

    print("=== Excel 文件 ===")
    print(f"路径: {EXCEL}")
    print(f"Workbook Sheet 总数: {len(all_sheets)}")
    print(f"解析有效 BOM 行数: {len(parsed)}")
    print(f"跳过 Sheet: {skipped or '无'}")
    print(f"未能解析 Sheet 数: {len(empty)}")
    if empty:
        print("未解析 Sheet:", ", ".join(empty))

    dup_parts = {p: c for p, c in Counter(r["product_part_no"] for r in parsed).items() if c > 1}
    print(f"解析结果重复料号种数: {len(dup_parts)}")
    for part, count in sorted(dup_parts.items(), key=lambda x: -x[1]):
        sheets = [r["sheet_name"] for r in parsed if r["product_part_no"] == part]
        print(f"  {part} x{count} <- {sheets}")

    print("\n--- 819 / 826 / 1100006x 解析行 ---")
    for r in parsed:
        name = r.get("product_name", "")
        sheet = r.get("sheet_name", "")
        part = r.get("product_part_no", "")
        if any(x in name or x in sheet or part.startswith("1100006") for x in ("819", "826")):
            print(f"  {sheet} | {part} | {name}")

    conn = sqlite3.connect(DB)
    db_total = conn.execute(
        "SELECT COUNT(*) FROM cost_records WHERE customer_name LIKE ?",
        ("%锐霸%",),
    ).fetchone()[0]
    db_batch = conn.execute(
        "SELECT COUNT(*) FROM cost_records WHERE customer_name LIKE ? AND created_at LIKE ?",
        ("%锐霸%", "2026-07-28T03:32%"),
    ).fetchone()[0]
    conn.close()

    print("\n=== 数据库（苏州锐霸） ===")
    print(f"BOM 总条数: {db_total}")
    print(f"同批导入 (2026-07-28 03:32): {db_batch} 条")
    print(f"\n对比: Excel 解析 {len(parsed)} 行 vs 同批入库 {db_batch} 条 → 差 {len(parsed) - db_batch}")

    out = ROOT / "data" / "bom_import_audit" / "ruiba_parse_vs_db.md"
    lines = [
        "# 锐霸产品BOM.xls · 解析 vs 入库",
        "",
        f"| 项目 | 数量 |",
        f"|------|------|",
        f"| Excel Sheet 总数 | {len(all_sheets)} |",
        f"| 解析有效 BOM 行 | {len(parsed)} |",
        f"| 未能解析 Sheet | {len(empty)} |",
        f"| 库内同批入库 | {db_batch} |",
        f"| **差异** | **{len(parsed) - db_batch}** |",
        "",
        "## 全部 Sheet 名",
        "",
    ]
    for i, name in enumerate(all_sheets, 1):
        status = "✓" if name in parsed_sheet_names else ("跳过" if name in skipped else "未解析")
        lines.append(f"{i}. `{name}` — {status}")
    lines.extend(["", "## 解析明细 (Sheet | 料号 | 品名)", ""])
    for r in parsed:
        lines.append(f"- `{r['sheet_name']}` | {r['product_part_no']} | {r['product_name']}")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n明细已写: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
