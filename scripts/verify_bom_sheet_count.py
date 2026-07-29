#!/usr/bin/env python3
"""验证：有效 Sheet 数 vs 解析 BOM 行数（新逻辑应 1:1，除换行多产品 Sheet）。"""
from __future__ import annotations

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

FILES = [
    ROOT / "Demo" / "BOM" / "锐霸产品BOM.xls",
    ROOT / "data" / "bom_import_audit" / "怡利BOM.xls",
    ROOT / "data" / "bom_import_audit" / "东硕BOM.xls",
    ROOT / "data" / "bom_import_audit" / "精达BOM.xls",
    ROOT / "data" / "bom_import_audit" / "欧菲光BOM.xls",
    ROOT / "data" / "bom_import_audit" / "红黑BOM格式.xls",
    ROOT / "data" / "bom_import_audit" / "日月照明BOM格式.xls",
]

# 已知：同 Sheet 换行多产品 → 解析行数 > Sheet 数
KNOWN_MULTI_ROW_SHEETS = {
    "怡利BOM.xls": {"金属转轴": 2},
}


def sheet_names(path: Path) -> list[str]:
    raw = path.read_bytes()
    book = xlrd.open_workbook(file_contents=raw)
    return [s.name for s in book.sheets()]


def analyze(path: Path) -> dict:
    if not path.is_file():
        return {"file": str(path), "missing": True}
    raw = path.read_bytes()
    all_sheets = sheet_names(path)
    work = [n for n in all_sheets if _norm_text(n).casefold() not in _SKIP_SHEET_NAMES]
    parsed = parse_bom_workbook(raw, filename=path.name)
    by_sheet = Counter(r["sheet_name"] for r in parsed)
    expected_extra = sum(
        (KNOWN_MULTI_ROW_SHEETS.get(path.name, {}).get(s, 0) - 1)
        for s in KNOWN_MULTI_ROW_SHEETS.get(path.name, {})
    )
    expected_rows = len(work) + expected_extra
    dup_parts = {
        p: c
        for p, c in Counter(r["product_part_no"] for r in parsed).items()
        if c > 1
    }
    missing = [s for s in work if s not in by_sheet and _norm_text(s) not in by_sheet]
    return {
        "file": path.name,
        "sheets": len(all_sheets),
        "work_sheets": len(work),
        "parsed_rows": len(parsed),
        "expected_rows": expected_rows,
        "match": len(parsed) == expected_rows,
        "dup_part_nos": len(dup_parts),
        "multi_row_sheets": {s: c for s, c in by_sheet.items() if c > 1},
        "missing_sheets": missing,
        "unique_parts": len(set(r["product_part_no"] for r in parsed)),
    }


def main() -> int:
    print("| 文件 | Sheet | 解析行 | 预期 | 一致 | 重复料号 | 备注 |")
    print("|------|-------|--------|------|------|----------|------|")
    all_ok = True
    for path in FILES:
        r = analyze(path)
        if r.get("missing"):
            print(f"| {path.name} | - | - | - | 缺文件 | - | |")
            continue
        note = ""
        if r["multi_row_sheets"]:
            note = f"多行Sheet: {r['multi_row_sheets']}"
        if r["missing_sheets"]:
            note += f" 未解析: {r['missing_sheets'][:2]}"
        if r["dup_part_nos"]:
            note += f" 重复料号{r['dup_part_nos']}种"
        ok = r["match"] and (r["dup_part_nos"] == 0 or r["file"] == "锐霸产品BOM.xls")
        if not ok:
            all_ok = False
        mark = "OK" if ok else "FAIL"
        print(
            f"| {r['file']} | {r['work_sheets']} | {r['parsed_rows']} | "
            f"{r['expected_rows']} | {mark} | {r['dup_part_nos']} | {note} |"
        )

    # 锐霸 819 料号抽检
    ruiba = ROOT / "Demo" / "BOM" / "锐霸产品BOM.xls"
    if ruiba.is_file():
        parsed = parse_bom_workbook(ruiba.read_bytes(), filename=ruiba.name)
        checks = [
            ("819 头壳", "11*000000/08016-01"),
            ("826头壳", "11*000000/09016-01"),
            ("826A头壳", "11*000000/10016-01"),
        ]
        by = {r["sheet_name"]: r for r in parsed}
        print("\n锐霸料号抽检:")
        for sheet, part in checks:
            got = by.get(sheet, {}).get("product_part_no", "?")
            print(f"  {sheet}: {got} {'OK' if got == part else 'FAIL'}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
