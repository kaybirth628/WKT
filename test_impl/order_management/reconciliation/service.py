from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from test_impl.common.money import serialize_amount, serialize_price, serialize_qty
from test_impl.order_management.order_entry.line_store import LineStore, default_db_path

from .payment_schedule import (
    compute_payment_due_date,
    format_terms_label,
    load_reconciliation_config,
    parse_ship_local_date,
    payment_due_month_label,
)
from .period import PERIOD_OPTIONS, reconciliation_period_label

_TWO = Decimal("0.01")


def _parse_doc_no(delivery_note_json: str) -> str:
    raw = (delivery_note_json or "").strip()
    if not raw:
        return ""
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return str(data.get("doc_no") or "").strip()
    except ValueError:
        pass
    return ""


def _line_amount(ship_qty: str | Decimal, unit_price: str | Decimal) -> Decimal:
    qty = Decimal(str(ship_qty or "0"))
    price = Decimal(str(unit_price or "0"))
    return (qty * price).quantize(_TWO, rounding=ROUND_HALF_UP)


def _shipped_at_str(shipped_at: Any) -> str:
    if hasattr(shipped_at, "isoformat"):
        return shipped_at.isoformat()
    return str(shipped_at or "")


def _merge_key(row: Dict[str, Any]) -> Tuple[str, str, str, str, str, str]:
    """客户、出货时间、订单、客户料号、单价、出货单号 — 相同则合并数量与金额。"""
    return (
        row["customer"],
        row["shipped_at"],
        row["order_no"],
        row["customer_part_no"],
        row["rmb_tax_incl_price"],
        row["delivery_doc_no"],
    )


def _merge_lines(lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[Tuple[str, ...], Dict[str, Any]] = {}
    for row in lines:
        key = _merge_key(row)
        bucket = buckets.get(key)
        if bucket is None:
            buckets[key] = {
                **row,
                "ship_qty": Decimal(str(row["ship_qty"] or "0")),
                "amount": Decimal(str(row["amount"] or "0")),
                "merge_count": 1,
                "source_event_ids": [row["id"]],
            }
            continue
        bucket["ship_qty"] += Decimal(str(row["ship_qty"] or "0"))
        bucket["amount"] += Decimal(str(row["amount"] or "0"))
        bucket["merge_count"] += 1
        bucket["source_event_ids"].append(row["id"])
    out: List[Dict[str, Any]] = []
    for bucket in buckets.values():
        out.append(
            {
                **{k: v for k, v in bucket.items() if k not in ("ship_qty", "amount", "merge_count", "source_event_ids")},
                "ship_qty": serialize_qty(bucket["ship_qty"]),
                "amount": serialize_amount(bucket["amount"]),
                "merge_count": bucket["merge_count"],
                "source_event_ids": bucket["source_event_ids"],
            }
        )
    return out


class ReconciliationService:
    def __init__(self, store: Optional[LineStore] = None) -> None:
        self._store = store or LineStore(default_db_path())

    def get_config(self) -> Dict[str, Any]:
        cfg = load_reconciliation_config()
        cfg["terms_display"] = format_terms_label(cfg)
        cfg["reconciliation_period_options"] = PERIOD_OPTIONS
        return cfg

    def list_lines(
        self,
        q: str = "",
        customer: str = "",
        due_month: str = "",
        ship_month: str = "",
        collection_month: str = "",
    ) -> List[Dict[str, Any]]:
        cfg = load_reconciliation_config()
        payment_day = int(cfg.get("payment_day") or 25)
        term_days = int(cfg.get("term_days") or 90)
        terms_display = format_terms_label(cfg)
        month_filter = (collection_month or due_month).strip()
        store_customer = ""
        if customer and customer != "(未填客户)":
            store_customer = customer
        rows = self._store.list_shipment_reconciliation_sources(q=q, customer=store_customer)
        if customer == "(未填客户)":
            rows = [row for row in rows if not (row.get("customer") or "").strip()]
        raw: List[Dict[str, Any]] = []
        for row in rows:
            ship_date = parse_ship_local_date(row["shipped_at"])
            due = compute_payment_due_date(
                ship_date, payment_day=payment_day, term_days=term_days
            )
            collection_time = payment_due_month_label(due)
            ship_month_label = f"{ship_date.year:04d}-{ship_date.month:02d}"
            if month_filter and collection_time != month_filter:
                continue
            if ship_month and ship_month_label != ship_month.strip():
                continue
            amount = _line_amount(row["ship_qty"], row["rmb_tax_incl_price"])
            shipped_at_str = _shipped_at_str(row["shipped_at"])
            raw.append(
                {
                    "id": int(row["event_id"]),
                    "line_id": int(row["line_id"]),
                    "shipped_at": shipped_at_str,
                    "ship_month": ship_month_label,
                    "customer": row["customer"] or "",
                    "order_no": row["order_no"] or "",
                    "customer_part_no": row["customer_part_no"] or "",
                    "ship_qty": serialize_qty(Decimal(str(row["ship_qty"] or "0"))),
                    "unit": row.get("unit") or "",
                    "rmb_tax_incl_price": serialize_price(
                        Decimal(str(row["rmb_tax_incl_price"] or "0"))
                    ),
                    "amount": serialize_amount(amount),
                    "delivery_doc_no": _parse_doc_no(row.get("delivery_note_json") or ""),
                    "receivable_date": due.isoformat(),
                    "collection_time": collection_time,
                    "payment_terms": (row.get("payment_terms") or "").strip() or terms_display,
                    "terms_display": terms_display,
                }
            )
        out = _merge_lines(raw)
        customer_totals: Dict[str, Decimal] = {}
        for row in out:
            name = row["customer"] or "(未填客户)"
            customer_totals[name] = customer_totals.get(name, Decimal("0")) + Decimal(
                str(row["amount"] or "0")
            )
        out.sort(
            key=lambda r: (
                -customer_totals[r["customer"] or "(未填客户)"],
                r["customer"] or "(未填客户)",
                r["receivable_date"],
                r["shipped_at"],
                r["order_no"],
            ),
        )
        return out

    def summarize_by_customer(
        self,
        q: str = "",
        customer: str = "",
        due_month: str = "",
        ship_month: str = "",
        collection_month: str = "",
    ) -> List[Dict[str, Any]]:
        lines = self.list_lines(
            q=q,
            customer=customer,
            due_month=due_month,
            ship_month=ship_month,
            collection_month=collection_month,
        )
        buckets: Dict[str, Dict[str, Any]] = {}
        for row in lines:
            name = row["customer"] or "(未填客户)"
            bucket = buckets.setdefault(
                name,
                {
                    "customer": name,
                    "line_count": 0,
                    "total_amount": Decimal("0"),
                    "collection_time": row["collection_time"],
                },
            )
            bucket["line_count"] += 1
            bucket["total_amount"] += Decimal(str(row["amount"] or "0"))
        result = []
        for item in buckets.values():
            result.append(
                {
                    "customer": item["customer"],
                    "line_count": item["line_count"],
                    "total_amount": serialize_amount(item["total_amount"]),
                    "collection_time": item["collection_time"],
                }
            )
        result.sort(key=lambda r: (-Decimal(str(r["total_amount"])), r["customer"]))
        return result

    def summarize_by_customer_month(
        self,
        q: str = "",
        due_month: str = "",
        ship_month: str = "",
        collection_month: str = "",
    ) -> List[Dict[str, Any]]:
        """每个客户 × 收款月份一条汇总（应收金额合计）。"""
        lines = self.list_lines(
            q=q,
            due_month=due_month,
            ship_month=ship_month,
            collection_month=collection_month,
        )
        buckets: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for row in lines:
            customer = row["customer"] or "(未填客户)"
            month = row["collection_time"]
            key = (customer, month)
            bucket = buckets.setdefault(
                key,
                {
                    "customer": customer,
                    "collection_time": month,
                    "receivable_date": row["receivable_date"],
                    "line_count": 0,
                    "total_amount": Decimal("0"),
                },
            )
            bucket["line_count"] += 1
            bucket["total_amount"] += Decimal(str(row["amount"] or "0"))
        customer_totals: Dict[str, Decimal] = {}
        for item in buckets.values():
            customer_totals[item["customer"]] = customer_totals.get(
                item["customer"], Decimal("0")
            ) + item["total_amount"]
        result = []
        for item in buckets.values():
            result.append(
                {
                    "customer": item["customer"],
                    "collection_time": item["collection_time"],
                    "receivable_date": item["receivable_date"],
                    "line_count": item["line_count"],
                    "total_amount": serialize_amount(item["total_amount"]),
                }
            )
        result.sort(
            key=lambda r: (
                -customer_totals[r["customer"]],
                r["customer"],
                -int((r["collection_time"] or "0").replace("-", "") or 0),
            ),
        )
        return result

    def list_due_months(self) -> List[str]:
        cfg = load_reconciliation_config()
        payment_day = int(cfg.get("payment_day") or 25)
        term_days = int(cfg.get("term_days") or 90)
        months: set[str] = set()
        for row in self._store.list_shipment_reconciliation_sources():
            ship_date = parse_ship_local_date(row["shipped_at"])
            due = compute_payment_due_date(
                ship_date, payment_day=payment_day, term_days=term_days
            )
            months.add(payment_due_month_label(due))
        return sorted(months, reverse=True)
