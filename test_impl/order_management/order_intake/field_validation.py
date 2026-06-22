"""单路 OCR + AI 结构化后的规则校验，标出需人工核对的字段。"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Tuple

VALIDATE_FIELDS = (
    "customer",
    "order_date",
    "delivery_date",
    "order_no",
    "product_spec",
    "customer_part_no",
    "po_qty",
    "unit_weight_g",
    "rmb_tax_incl_price",
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PART_NO_STRICT = re.compile(r"^B\d{10}$", re.I)
_PART_NO_LOOSE = re.compile(r"^[A-Z0-9][A-Z0-9\-]{5,}$", re.I)


def _norm(value: Any) -> str:
    if value is None:
        return ""
    s = unicodedata.normalize("NFKC", str(value).strip().lower())
    return s.replace(",", "").replace(" ", "")


def _value_in_text(value: str, corpus: str) -> bool:
    v = _norm(value)
    if not v:
        return True
    corpus_norm = _norm(corpus)
    if v in corpus_norm:
        return True
    if len(v) >= 4 and v[: min(12, len(v))] in corpus_norm:
        return True
    return False


def _is_spec_fragment(part_no: str, product_spec: str) -> bool:
    s = str(part_no or "").strip()
    spec = str(product_spec or "")
    if not s or len(s) > 8 or not spec or s not in spec:
        return False
    return bool(re.search(rf"[/\\]{re.escape(s)}(?:\s|$)|{re.escape(s)}\s+adc", spec, re.I))


def _validate_field(field: str, value: Any, *, product_spec: str, raw_text: str) -> Dict[str, Any]:
    v = str(value or "").strip()
    display = v

    if field == "customer":
        if not v:
            return {"status": "warn", "value": display, "message": "客户名称为空"}
        return {"status": "ok", "value": display, "message": ""}

    if field in ("order_date", "delivery_date"):
        if not v:
            return {"status": "ok", "value": display, "message": ""}
        if not _DATE_RE.match(v):
            return {"status": "warn", "value": display, "message": "日期格式应为 YYYY-MM-DD"}
        return {"status": "ok", "value": display, "message": ""}

    if field == "product_spec":
        if not v:
            return {"status": "warn", "value": display, "message": "品名规格为空"}
        return {"status": "ok", "value": display, "message": ""}

    if field == "customer_part_no":
        if not v:
            return {"status": "warn", "value": display, "message": "客户料号为空"}
        if _is_spec_fragment(v, product_spec):
            return {"status": "warn", "value": display, "message": "疑似品名内短编号，非独立料号"}
        if _PART_NO_STRICT.match(v):
            if raw_text and not _value_in_text(v, raw_text):
                return {"status": "warn", "value": display, "message": "OCR 原文中未找到该料号"}
            return {"status": "ok", "value": display, "message": ""}
        if len(v) <= 6 and re.fullmatch(r"\d+", v):
            return {"status": "warn", "value": display, "message": "料号过短，请核对是否为完整编码"}
        if not _PART_NO_LOOSE.match(v):
            return {"status": "warn", "value": display, "message": "料号格式异常，请核对"}
        if raw_text and len(v) >= 8 and not _value_in_text(v, raw_text):
            return {"status": "warn", "value": display, "message": "OCR 原文中未找到该料号"}
        return {"status": "ok", "value": display, "message": ""}

    if field == "po_qty":
        if not v or v == "0":
            return {"status": "warn", "value": display, "message": "PO 数量为空或为 0"}
        try:
            if float(v.replace(",", "")) <= 0:
                return {"status": "warn", "value": display, "message": "PO 数量应大于 0"}
        except ValueError:
            return {"status": "warn", "value": display, "message": "PO 数量不是有效数字"}
        return {"status": "ok", "value": display, "message": ""}

    if field == "unit_weight_g":
        if not v or v == "0":
            return {"status": "ok", "value": display, "message": ""}
        try:
            float(v.replace(",", ""))
            return {"status": "ok", "value": display, "message": ""}
        except ValueError:
            return {"status": "ok", "value": display, "message": ""}

    if field == "rmb_tax_incl_price":
        if not v or v == "0":
            return {"status": "ok", "value": display, "message": ""}
        try:
            float(v.replace(",", ""))
        except ValueError:
            return {"status": "warn", "value": display, "message": "数值格式异常"}
        return {"status": "ok", "value": display, "message": ""}

    if field == "order_no":
        return {"status": "ok", "value": display, "message": ""}

    return {"status": "ok", "value": display, "message": ""}


def validate_lines(
    lines: List[dict],
    *,
    ocr_scheme: str,
    raw_text: str = "",
) -> Tuple[List[dict], dict]:
    validated: List[dict] = []
    warn_details: List[dict] = []
    warn_field_count = 0

    for idx, row in enumerate(lines):
        row = dict(row)
        product_spec = str(row.get("product_spec") or "")
        field_checks: Dict[str, dict] = {}

        for f in VALIDATE_FIELDS:
            fv = _validate_field(f, row.get(f), product_spec=product_spec, raw_text=raw_text)
            field_checks[f] = fv
            if fv["status"] == "warn":
                warn_field_count += 1
                warn_details.append(
                    {
                        "row": idx + 1,
                        "field": f,
                        "value": fv.get("value", ""),
                        "message": fv.get("message", ""),
                    }
                )

        row_status = "warn" if any(v["status"] == "warn" for v in field_checks.values()) else "ok"
        row["_validate"] = {"status": row_status, "fields": field_checks}
        validated.append(row)

    ok_rows = sum(1 for r in validated if r.get("_validate", {}).get("status") == "ok")
    total_rows = len(validated)

    summary = {
        "ocr_scheme": ocr_scheme,
        "total_rows": total_rows,
        "ok_rows": ok_rows,
        "warn_rows": total_rows - ok_rows,
        "warn_fields": warn_field_count,
        "warn_details": warn_details,
        "warnings": [],
    }
    return validated, summary
