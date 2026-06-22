from __future__ import annotations

import re
from typing import Callable, List, Optional

from test_impl.order_management.order_entry.line_mapper import intake_to_lines
from test_impl.order_management.order_entry.line_service import OrderLineService

from .deepseek import DeepSeekStructurer
from .field_validation import validate_lines
from .text_extract import extract_text, extract_text_with_meta

ProgressCallback = Optional[Callable[[int, str], None]]

_CRITICAL_FIELDS = ("customer_part_no", "product_spec", "po_qty")


def _to_number_str(value, default: str = "0") -> str:
    if value is None:
        return default
    s = str(value).strip()
    if s == "":
        return default
    s = s.replace(",", "")
    m = re.search(r"-?\d+(\.\d+)?", s)
    return m.group(0) if m else default


def _to_tax_rate(value) -> str:
    if value is None or str(value).strip() == "":
        return "0"
    s = str(value).strip()
    has_percent = "%" in s
    num = _to_number_str(s, "0")
    try:
        rate = float(num)
    except ValueError:
        return "0"
    if has_percent or rate > 1:
        rate = rate / 100.0
    return str(round(rate, 6))


def normalize_order(raw_order: dict) -> dict:
    raw_order = raw_order or {}
    items_raw = raw_order.get("items") or []
    if isinstance(items_raw, dict):
        items_raw = [items_raw]

    items = []
    for idx, it in enumerate(items_raw, start=1):
        it = it or {}
        items.append(
            {
                "item_no": idx,
                "product_spec": str(it.get("product_spec", "") or "").strip(),
                "customer_part_no": str(it.get("customer_part_no", "") or "").strip(),
                "material": str(it.get("material", "") or "").strip(),
                "unit_weight_g": _to_number_str(it.get("unit_weight_g")),
                "po_qty": _to_number_str(it.get("po_qty")),
                "shipped_qty": _to_number_str(it.get("shipped_qty")),
                "unit": str(it.get("unit", "") or "").strip(),
                "tax_rate": _to_tax_rate(it.get("tax_rate")),
                "rmb_tax_incl_price": _to_number_str(it.get("rmb_tax_incl_price")),
            }
        )

    return {
        "customer": str(raw_order.get("customer", "") or "").strip(),
        "order_no": str(raw_order.get("order_no", "") or "").strip(),
        "order_date": str(raw_order.get("order_date", "") or "").strip(),
        "delivery_date": str(raw_order.get("delivery_date", "") or "").strip(),
        "payment_terms": str(raw_order.get("payment_terms", "") or "").strip(),
        "items": items,
    }


def normalize_extraction(raw: dict) -> dict:
    raw = raw or {}
    orders_raw = raw.get("orders")
    if orders_raw is None:
        orders_raw = [raw] if (raw.get("items") or raw.get("order_no") or raw.get("customer")) else []
    if isinstance(orders_raw, dict):
        orders_raw = [orders_raw]
    orders = [normalize_order(o) for o in orders_raw]
    return {"orders": orders}


def _count_empty_critical(lines: List[dict]) -> int:
    n = 0
    for ln in lines:
        for f in _CRITICAL_FIELDS:
            v = str(ln.get(f, "") or "").strip()
            if not v or v == "0":
                n += 1
    return n


class IntakeService:
    """单路 OCR -> DeepSeek 结构化 -> 规则校验。"""

    def __init__(
        self,
        structurer: Optional[DeepSeekStructurer] = None,
        line_service: Optional[OrderLineService] = None,
    ) -> None:
        self.structurer = structurer or DeepSeekStructurer()
        self.line_service = line_service

    def recognize(self, file_bytes: bytes, filename: str) -> dict:
        raw_text = extract_text(file_bytes, filename)
        structured = self.structurer.structure(raw_text)
        result = normalize_extraction(structured)
        result["_raw_text"] = raw_text[:5000]
        return result

    def recognize_lines(
        self,
        file_bytes: bytes,
        filename: str,
        progress: ProgressCallback = None,
    ) -> dict:
        def report(pct: int, msg: str) -> None:
            if progress:
                progress(pct, msg)

        report(5, "准备识别…")
        extracted = extract_text_with_meta(file_bytes, filename, progress=progress)

        report(45, "AI 结构化…")
        structured = self.structurer.structure(extracted.text)
        lines = intake_to_lines(normalize_extraction(structured))

        if self.line_service:
            lines = self.line_service.enrich_recognized_lines(lines)

        if _count_empty_critical(lines) > 0:
            report(70, "关键字段遗漏，AI 重试补全…")
            structured = self.structurer.structure_retry(extracted.text)
            lines = intake_to_lines(normalize_extraction(structured))
            if self.line_service:
                lines = self.line_service.enrich_recognized_lines(lines)

        report(88, "规则校验…")
        validated, validation = validate_lines(
            lines,
            ocr_scheme=extracted.scheme,
            raw_text=extracted.text,
        )

        report(100, "识别完成")
        return {
            "lines": validated,
            "validation": validation,
            "ocr_text": {
                "scheme": extracted.scheme,
                "text": extracted.text[:20000],
                "truncated": len(extracted.text) > 20000,
            },
        }
