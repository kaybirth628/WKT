"""从 OCR 原文补全 AI 未填的客户料号（如大沃「物料编码」列）。"""

from __future__ import annotations

import re
from typing import List

# 大沃等客户 PO：物料编码列，如 1-000797
_MATERIAL_CODE_RE = re.compile(r"\b(\d-\d{6})\b")


def _unique_ordered(values: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _fill_item_from_line(item: dict, raw_text: str) -> bool:
    spec = str(item.get("product_spec") or "").strip()
    if not spec or len(spec) < 4:
        return False
    best_code: str | None = None
    best_score = 0
    for line in raw_text.splitlines():
        score = len(spec) if spec in line else 0
        if score == 0:
            for n in range(min(len(spec), 12), 3, -1):
                if spec[:n] in line or spec[-n:] in line:
                    score = n
                    break
        if score <= best_score:
            continue
        m = _MATERIAL_CODE_RE.search(line)
        if m:
            best_score = score
            best_code = m.group(1)
    if best_code:
        item["customer_part_no"] = best_code
        return True
    return False


def fill_part_no_from_raw_text(orders: dict, raw_text: str) -> dict:
    """对 customer_part_no 为空的明细，尝试从 OCR 原文匹配物料编码。"""
    if not raw_text or not orders:
        return orders

    for order in orders.get("orders") or []:
        items = order.get("items") or []
        empty: List[int] = [
            i
            for i, it in enumerate(items)
            if not str(it.get("customer_part_no") or "").strip()
        ]
        if not empty:
            continue

        for i in empty:
            _fill_item_from_line(items[i], raw_text)

        still_empty = [
            i
            for i in empty
            if not str(items[i].get("customer_part_no") or "").strip()
        ]
        if not still_empty:
            continue

        codes = _unique_ordered(_MATERIAL_CODE_RE.findall(raw_text))
        if len(codes) >= len(still_empty):
            for idx, code in zip(still_empty, codes):
                items[idx]["customer_part_no"] = code

    return orders
