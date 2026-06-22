#!/usr/bin/env python3
"""汇总已录入订单行，用于与 Excel 核对。"""
from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "imports" / "已录入订单汇总.txt"

sys.path.insert(0, str(ROOT))

from test_impl.common.money import fmt_amount, fmt_qty, round_amount, round_price, round_qty


def main() -> int:
    url = "http://127.0.0.1:5000/api/lines"
    try:
        with urlopen(url, timeout=15) as r:
            lines = json.loads(r.read().decode())
    except Exception as exc:
        print(f"无法读取 {url}，请先启动网页服务: {exc}")
        return 1

    total_po = Decimal("0")
    total_shipped = Decimal("0")
    total_open = Decimal("0")
    total_amount = Decimal("0")
    by_customer: dict = {}

    for ln in lines:
        po = round_qty(ln.get("po_qty"))
        sh = round_qty(ln.get("shipped_qty"))
        op = round_qty(ln.get("open_qty")) if ln.get("open_qty") not in (None, "") else round_qty(po - sh)
        amt = (
            round_amount(ln.get("amount"))
            if ln.get("amount") not in (None, "")
            else round_amount(po * round_price(ln.get("rmb_tax_incl_price")))
        )
        total_po += po
        total_shipped += sh
        total_open += op
        total_amount += amt
        c = ln.get("customer") or "未知"
        bucket = by_customer.setdefault(
            c,
            {"lines": 0, "po": Decimal("0"), "shipped": Decimal("0"), "open": Decimal("0"), "amount": Decimal("0")},
        )
        bucket["lines"] += 1
        bucket["po"] += po
        bucket["shipped"] += sh
        bucket["open"] += op
        bucket["amount"] += amt

    lines_out = [
        "WKT 已录入订单汇总（与 Excel 核对用）",
        "展示：千分位；整数不写小数，有小数则保留",
        "=" * 50,
        f"料号行数: {len(lines)}",
        f"PO 数量合计: {fmt_qty(total_po)}",
        f"已出货合计: {fmt_qty(total_shipped)}",
        f"未结数量合计: {fmt_qty(total_open)}",
        f"含税金额合计: {fmt_amount(total_amount)}",
        "",
        "按客户汇总",
        "-" * 50,
    ]
    for c in sorted(by_customer.keys()):
        b = by_customer[c]
        lines_out.append(
            f"{c} | 行数 {b['lines']} | PO {fmt_qty(b['po'])} | 已出货 {fmt_qty(b['shipped'])} | "
            f"未结 {fmt_qty(b['open'])} | 金额 {fmt_amount(b['amount'])}"
        )

    text = "\n".join(lines_out)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(text)
    print()
    print(f"已写入: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
