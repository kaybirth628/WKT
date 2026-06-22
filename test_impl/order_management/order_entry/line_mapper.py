"""把 OCR 识别结果映射为料号行预览数据（每个料号一行，字段对齐附件2）。"""

from __future__ import annotations

from typing import List


def intake_to_lines(recognition: dict) -> List[dict]:
    lines: List[dict] = []
    orders = recognition.get("orders") or []
    for order in orders:
        header = {
            "customer": order.get("customer", ""),
            "order_date": order.get("order_date", ""),
            "delivery_date": order.get("delivery_date", ""),
            "order_no": order.get("order_no", ""),
            "payment_terms": order.get("payment_terms", ""),
        }
        items = order.get("items") or []
        if not items:
            lines.append(
                {
                    **header,
                    "product_spec": "",
                    "customer_part_no": "",
                    "unit_weight_g": "0",
                    "material": "",
                    "po_qty": "0",
                    "shipped_qty": "0",
                    "unit": "",
                    "tax_rate": "0",
                    "rmb_tax_incl_price": "0",
                }
            )
            continue
        for it in items:
            lines.append(
                {
                    **header,
                    "product_spec": it.get("product_spec", ""),
                    "customer_part_no": it.get("customer_part_no", ""),
                    "unit_weight_g": it.get("unit_weight_g", "0"),
                    "material": it.get("material", ""),
                    "po_qty": it.get("po_qty", "0"),
                    "shipped_qty": it.get("shipped_qty", "0"),
                    "unit": it.get("unit", ""),
                    "tax_rate": it.get("tax_rate", "0"),
                    "rmb_tax_incl_price": it.get("rmb_tax_incl_price", "0"),
                }
            )
    return lines
