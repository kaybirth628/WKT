"""应付对账：外发回货 × 供应商 × BOM 工序价。"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from test_impl.common.money import serialize_amount, serialize_price, serialize_qty
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.cost_analysis.models import PROCESS_BY_CODE
from test_impl.order_management.inventory.store import InventoryStore
from test_impl.order_management.order_entry.line_store import default_db_path
from test_impl.order_management.supplier_profile.store import get_profile

from .month_util import month_display_label, rolling_due_months
from .payment_schedule import (
    compute_payable_date,
    load_reconciliation_config,
    parse_ship_local_date,
    payment_due_month_label,
)
from .period import (
    DEFAULT_SUPPLIER_RECONCILIATION_PERIOD,
    PERIOD_OPTIONS,
    reconciliation_period_for_ship_date,
)

ACTION_OUT_RECV = "outsource_receive"
ACTION_INBOUND = "inbound"
_TWO = Decimal("0.01")


def _line_amount(qty: str | Decimal, unit_price: str | Decimal) -> Decimal:
    q = Decimal(str(qty or "0"))
    p = Decimal(str(unit_price or "0"))
    return (q * p).quantize(_TWO, rounding=ROUND_HALF_UP)


def _received_at_str(received_at: Any) -> str:
    if hasattr(received_at, "isoformat"):
        return received_at.isoformat()
    return str(received_at or "")


def _merge_key(row: Dict[str, Any]) -> Tuple[str, str, str, str, str, str]:
    return (
        row["supplier"],
        row["received_at"],
        row["product_part_no"],
        row["process_code"],
        row["unit_price"],
        row["doc_no"],
    )


def _merge_lines(lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[Tuple[str, ...], Dict[str, Any]] = {}
    for row in lines:
        key = _merge_key(row)
        bucket = buckets.get(key)
        if bucket is None:
            qty = Decimal(str(row["qty"] or "0"))
            amount_raw = row.get("amount")
            amount = Decimal(str(amount_raw)) if amount_raw not in (None, "") else Decimal("0")
            buckets[key] = {
                **row,
                "qty": qty,
                "amount": amount,
                "merge_count": 1,
                "source_event_ids": [row["id"]],
            }
            continue
        bucket["qty"] += Decimal(str(row["qty"] or "0"))
        if row.get("amount") not in (None, ""):
            bucket["amount"] += Decimal(str(row["amount"] or "0"))
        bucket["merge_count"] += 1
        bucket["source_event_ids"].append(row["id"])
    out: List[Dict[str, Any]] = []
    for bucket in buckets.values():
        amount_val = bucket["amount"]
        out.append(
            {
                **{
                    k: v
                    for k, v in bucket.items()
                    if k not in ("qty", "amount", "merge_count", "source_event_ids")
                },
                "qty": serialize_qty(bucket["qty"]),
                "amount": serialize_amount(amount_val) if bucket.get("unit_price") else "",
                "merge_count": bucket["merge_count"],
                "source_event_ids": bucket["source_event_ids"],
            }
        )
    return out


class PayableService:
    def __init__(
        self,
        inventory_store: Optional[InventoryStore] = None,
        cost_store: Optional[CostStore] = None,
        record_service: Optional[Any] = None,
    ) -> None:
        db = str(default_db_path())
        self._inv = inventory_store or InventoryStore(db)
        self._cost = cost_store or CostStore(db)
        self._records = record_service
        if self._records is None:
            from test_impl.order_management.cost_analysis.record_service import CostRecordService

            self._records = CostRecordService(store=self._cost)

    def get_config(self) -> Dict[str, Any]:
        cfg = load_reconciliation_config()
        return {
            "reconciliation_period_options": PERIOD_OPTIONS,
            "default_supplier_period": DEFAULT_SUPPLIER_RECONCILIATION_PERIOD,
        }

    def _process_unit_price(self, product_part_no: str, process_code: str) -> Tuple[Optional[Decimal], bool]:
        row = self._cost.find_latest_by_part_no(product_part_no)
        if row is None:
            return None, True
        cost_dict = self._records.record_to_dict(row)
        prices = cost_dict.get("process_prices") or {}
        code = (process_code or "").strip()
        if code not in prices:
            return None, True
        try:
            return Decimal(str(prices[code] or "0")), False
        except Exception:
            return None, True

    def _list_receive_sources(self) -> List[dict]:
        rows = self._inv._conn.execute(
            """
            SELECT * FROM inventory_movements
            WHERE action_type IN (?, ?)
               OR (action_type = ? AND from_status = ? AND COALESCE(from_supplier, '') != '')
            ORDER BY datetime(created_at) DESC, id DESC
            """,
            (ACTION_OUT_RECV, ACTION_INBOUND, ACTION_INBOUND, "outsource"),
        ).fetchall()
        return [dict(r) for r in rows]

    def _build_line(self, row: dict, *, cfg: dict) -> Optional[Dict[str, Any]]:
        part = str(row.get("product_part_no") or "").strip()
        process_code = str(row.get("process_code") or "").strip()
        supplier = str(row.get("from_supplier") or "").strip() or "(未填供应商)"
        receive_date = parse_ship_local_date(row.get("created_at") or "")
        profile = get_profile(supplier if supplier != "(未填供应商)" else "")
        period = profile.get("reconciliation_period") or DEFAULT_SUPPLIER_RECONCILIATION_PERIOD
        payment_terms = profile.get("payment_terms") or ""
        settlement_month = reconciliation_period_for_ship_date(receive_date, period)
        payment_day = int(cfg.get("payment_day") or 25)
        payable = compute_payable_date(receive_date, payment_terms, payment_day=payment_day)
        payment_month = payment_due_month_label(payable)
        receive_month = f"{receive_date.year:04d}-{receive_date.month:02d}"
        unit_price, price_missing = self._process_unit_price(part, process_code)
        qty = Decimal(str(row.get("qty") or "0"))
        amount_str = ""
        if unit_price is not None and not price_missing:
            amount_str = serialize_amount(_line_amount(qty, unit_price))
        process_name = PROCESS_BY_CODE.get(process_code, process_code)
        return {
            "id": int(row["id"]),
            "received_at": _received_at_str(row.get("created_at")),
            "receive_date": receive_date.isoformat(),
            "receive_month": receive_month,
            "supplier": supplier,
            "product_part_no": part,
            "process_code": process_code,
            "process_name": process_name,
            "qty": serialize_qty(qty),
            "unit_price": serialize_price(unit_price) if unit_price is not None else "",
            "amount": amount_str,
            "price_missing": price_missing,
            "doc_no": str(row.get("doc_no") or "").strip(),
            "note": str(row.get("note") or "").strip(),
            "settlement_month": settlement_month,
            "payable_date": payable.isoformat(),
            "payment_month": payment_month,
            "payment_terms": payment_terms,
        }

    def list_lines(
        self,
        q: str = "",
        supplier: str = "",
        settlement_month: str = "",
        payment_month: str = "",
        receive_from: str = "",
        receive_to: str = "",
    ) -> List[Dict[str, Any]]:
        cfg = load_reconciliation_config()
        q_lower = (q or "").strip().lower()
        supplier_filter = (supplier or "").strip()
        settlement_filter = (settlement_month or "").strip()
        payment_filter = (payment_month or "").strip()
        from_date = (receive_from or "").strip()[:10]
        to_date = (receive_to or "").strip()[:10]
        raw: List[Dict[str, Any]] = []
        for row in self._list_receive_sources():
            line = self._build_line(row, cfg=cfg)
            if line is None:
                continue
            if q_lower:
                hay = " ".join(
                    [
                        line["supplier"],
                        line["product_part_no"],
                        line["process_code"],
                        line["process_name"],
                        line["doc_no"],
                    ]
                ).lower()
                if q_lower not in hay:
                    continue
            if supplier_filter and line["supplier"] != supplier_filter:
                continue
            if settlement_filter and line["settlement_month"] != settlement_filter:
                continue
            if payment_filter and line["payment_month"] != payment_filter:
                continue
            rd = line["receive_date"]
            if from_date and rd < from_date:
                continue
            if to_date and rd > to_date:
                continue
            raw.append(line)
        out = _merge_lines(raw)
        supplier_totals: Dict[str, Decimal] = {}
        for row in out:
            name = row["supplier"]
            if row.get("amount"):
                supplier_totals[name] = supplier_totals.get(name, Decimal("0")) + Decimal(
                    str(row["amount"] or "0")
                )
        out.sort(
            key=lambda r: (
                -supplier_totals.get(r["supplier"], Decimal("0")),
                r["supplier"],
                r["payable_date"],
                r["received_at"],
                r["product_part_no"],
            ),
        )
        return out

    def summarize_by_supplier_month(
        self,
        q: str = "",
        settlement_month: str = "",
        payment_month: str = "",
    ) -> List[Dict[str, Any]]:
        lines = self.list_lines(
            q=q,
            settlement_month=settlement_month,
            payment_month=payment_month,
        )
        buckets: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for row in lines:
            name = row["supplier"]
            month = row["settlement_month"]
            key = (name, month)
            bucket = buckets.setdefault(
                key,
                {
                    "supplier": name,
                    "settlement_month": month,
                    "payable_date": row["payable_date"],
                    "line_count": 0,
                    "total_qty": Decimal("0"),
                    "total_amount": Decimal("0"),
                    "missing_price_count": 0,
                },
            )
            bucket["line_count"] += 1
            bucket["total_qty"] += Decimal(str(row["qty"] or "0"))
            if row.get("price_missing"):
                bucket["missing_price_count"] += 1
            elif row.get("amount"):
                bucket["total_amount"] += Decimal(str(row["amount"] or "0"))
        supplier_totals: Dict[str, Decimal] = {}
        for item in buckets.values():
            supplier_totals[item["supplier"]] = supplier_totals.get(
                item["supplier"], Decimal("0")
            ) + item["total_amount"]
        result = []
        for item in buckets.values():
            result.append(
                {
                    "supplier": item["supplier"],
                    "settlement_month": item["settlement_month"],
                    "payable_date": item["payable_date"],
                    "line_count": item["line_count"],
                    "total_qty": serialize_qty(item["total_qty"]),
                    "total_amount": serialize_amount(item["total_amount"]),
                    "missing_price_count": item["missing_price_count"],
                }
            )
        result.sort(
            key=lambda r: (
                -supplier_totals[r["supplier"]],
                r["supplier"],
                -int((r["settlement_month"] or "0").replace("-", "") or 0),
            ),
        )
        return result

    def list_settlement_months(self) -> List[str]:
        months: set[str] = set()
        cfg = load_reconciliation_config()
        for row in self._list_receive_sources():
            line = self._build_line(row, cfg=cfg)
            if line:
                months.add(line["settlement_month"])
        return sorted(months, reverse=True)

    def list_payment_months(self) -> List[str]:
        months: set[str] = set()
        cfg = load_reconciliation_config()
        for row in self._list_receive_sources():
            line = self._build_line(row, cfg=cfg)
            if line:
                months.add(line["payment_month"])
        return sorted(months, reverse=True)

    def due_outlook(self, *, month_count: int = 6) -> Dict[str, Any]:
        """自本月起重连续 month_count 个付款月的供应商汇总。"""
        months = rolling_due_months(month_count)
        buckets = [self._payable_due_bucket(m) for m in months]
        total = sum(Decimal(str(b.get("total_amount") or "0")) for b in buckets)
        return {
            "months": buckets,
            "month_count": len(buckets),
            "total_amount": serialize_amount(total),
        }

    def _payable_due_bucket(self, month: str) -> Dict[str, Any]:
        lines = self.list_lines(payment_month=month)
        buckets: Dict[str, Dict[str, Any]] = {}
        for row in lines:
            name = row["supplier"] or "(未填供应商)"
            bucket = buckets.setdefault(
                name,
                {"supplier": name, "line_count": 0, "total_amount": Decimal("0")},
            )
            bucket["line_count"] += 1
            if row.get("amount"):
                bucket["total_amount"] += Decimal(str(row["amount"] or "0"))
        rows = sorted(
            buckets.values(),
            key=lambda r: (-r["total_amount"], r["supplier"]),
        )
        total = sum(r["total_amount"] for r in rows)
        return {
            "month": month,
            "label": month_display_label(month),
            "rows": [
                {
                    "supplier": r["supplier"],
                    "line_count": r["line_count"],
                    "total_amount": serialize_amount(r["total_amount"]),
                    "payment_month": month,
                }
                for r in rows
            ],
            "supplier_count": len(rows),
            "total_amount": serialize_amount(total),
        }
