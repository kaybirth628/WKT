from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List

from test_impl.common.money import round_price, to_decimal
from .models import OrderStatus, SalesOrder, SalesOrderItem


def _dec(value, default: str = "0") -> Decimal:
    return to_decimal(value, default)


class OrderEntryService:
    """
    In-memory implementation for order entry in test isolation.
    Replace repository layer when wiring into real persistence.
    """

    def __init__(self) -> None:
        self._orders: Dict[str, SalesOrder] = {}

    def create_order(
        self,
        order_no: str,
        customer: str,
        created_by: str,
        items: List[dict],
        order_date: str = "",
        delivery_date: str = "",
        payment_terms: str = "",
    ) -> SalesOrder:
        if not order_no:
            raise ValueError("订单号不能为空")
        if not customer:
            raise ValueError("客户不能为空")
        if order_no in self._orders:
            raise ValueError(f"订单号已存在: {order_no}")
        if not items:
            raise ValueError("订单至少需要一条明细")

        normalized_items: List[SalesOrderItem] = []
        for idx, row in enumerate(items, start=1):
            item = SalesOrderItem(
                item_no=int(row.get("item_no", idx) or idx),
                product_spec=str(row.get("product_spec", "")).strip(),
                customer_part_no=str(row.get("customer_part_no", "")).strip(),
                unit_weight_g=_dec(row.get("unit_weight_g")),
                material=str(row.get("material", "")).strip(),
                po_qty=_dec(row.get("po_qty")),
                shipped_qty=_dec(row.get("shipped_qty")),
                unit=str(row.get("unit", "")).strip(),
                tax_rate=_dec(row.get("tax_rate")),
                rmb_tax_incl_price=round_price(row.get("rmb_tax_incl_price")),
            )
            item.validate()
            normalized_items.append(item)

        order = SalesOrder(
            order_no=order_no,
            customer=customer,
            created_by=created_by,
            order_date=order_date,
            delivery_date=delivery_date,
            payment_terms=payment_terms,
            items=normalized_items,
        )
        _ = order.total_amount()
        self._orders[order_no] = order
        return order

    def approve_order(self, order_no: str, approved_by: str) -> SalesOrder:
        order = self._require_order(order_no)
        if order.status != OrderStatus.DRAFT:
            raise ValueError("only draft orders can be approved")
        order.status = OrderStatus.APPROVED
        order.approved_by = approved_by
        order.approved_at = datetime.now(timezone.utc)
        return order

    def cancel_order(self, order_no: str, operator: str) -> SalesOrder:
        _ = operator
        order = self._require_order(order_no)
        if order.status in (OrderStatus.CLOSED, OrderStatus.CANCELLED):
            raise ValueError("closed/cancelled orders cannot be cancelled again")
        order.status = OrderStatus.CANCELLED
        return order

    def get_order(self, order_no: str) -> SalesOrder:
        return self._require_order(order_no)

    def list_orders(self) -> List[SalesOrder]:
        return list(self._orders.values())

    def _require_order(self, order_no: str) -> SalesOrder:
        try:
            return self._orders[order_no]
        except KeyError as exc:
            raise ValueError(f"order not found: {order_no}") from exc
