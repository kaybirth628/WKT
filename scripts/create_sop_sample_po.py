#!/usr/bin/env python3
"""Generate a sample customer PO PDF for SOP OCR screenshots."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "sop_samples"
OUT_FILE = OUT_DIR / "sample_po.pdf"


def main() -> None:
    import fitz  # PyMuPDF

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    lines = [
        ("采购订单 PURCHASE ORDER", 18, 50, 40),
        ("", 0, 0, 0),
        ("供应商：昆山威可特精密电子有限公司", 11, 50, 70),
        ("客户：华东精密机械有限公司", 11, 50, 92),
        ("订单号 PO No.：PO-DEMO-20260723", 11, 50, 114),
        ("接单日期：2026-07-20    客户交期：2026-08-15", 11, 50, 136),
        ("账期：开票当月不算，从次月起月结60天", 11, 50, 158),
        ("", 0, 0, 0),
        ("序号  品名规格              客户料号           PO数量  单位  含税单价  税率", 10, 50, 190),
        ("-" * 72, 10, 50, 205),
        ("1     前挡板                PL9-01050-00-0A    1000    PCS   12.50     13%", 10, 50, 222),
        ("2     后盖                  PL9-01051-00-0A    500     PCS   8.80      13%", 10, 50, 239),
        ("", 0, 0, 0),
        ("备注：请按交期交货。料号以 BOM 建档为准。", 10, 50, 280),
        ("（本文件仅供 WKT 系统培训 OCR 演示）", 9, 50, 780),
    ]

    for text, size, x, y in lines:
        if not text:
            continue
        page.insert_text((x, y), text, fontsize=size, fontname="china-s")

    doc.save(str(OUT_FILE))
    doc.close()
    print(f"Created {OUT_FILE} ({OUT_FILE.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
