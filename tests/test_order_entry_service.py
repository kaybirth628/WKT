import unittest
from decimal import Decimal

from test_impl.order_management.order_entry import OrderEntryService, OrderStatus


def _item(**overrides):
    base = {
        "item_no": 1,
        "product_spec": "壳体/Φ50",
        "customer_part_no": "CPN-001",
        "unit_weight_g": "120",
        "material": "ADC12",
        "po_qty": "1000",
        "shipped_qty": "0",
        "unit": "PCS",
        "tax_rate": "0.13",
        "rmb_tax_incl_price": "2.50",
    }
    base.update(overrides)
    return base


class TestOrderEntryService(unittest.TestCase):
    def setUp(self) -> None:
        self.service = OrderEntryService()

    def test_create_order_success(self) -> None:
        order = self.service.create_order(
            order_no="SO-20260530-001",
            customer="华东精密",
            created_by="alice",
            order_date="2026-05-30",
            delivery_date="2026-06-20",
            payment_terms="月结30天",
            items=[_item(po_qty="1000", rmb_tax_incl_price="2.50")],
        )
        self.assertEqual(order.status, OrderStatus.DRAFT)
        self.assertEqual(order.customer, "华东精密")
        self.assertEqual(order.payment_terms, "月结30天")
        # 行含税金额 = 1000 * 2.50 = 2500.00
        self.assertEqual(order.total_amount(), Decimal("2500.00"))

    def test_open_qty_computed(self) -> None:
        order = self.service.create_order(
            order_no="SO-20260530-002",
            customer="客户A",
            created_by="alice",
            items=[_item(po_qty="1000", shipped_qty="300")],
        )
        self.assertEqual(order.items[0].open_qty(), Decimal("700"))

    def test_duplicate_order_no(self) -> None:
        payload = dict(order_no="SO-X", customer="C", created_by="a", items=[_item()])
        self.service.create_order(**payload)
        with self.assertRaisesRegex(ValueError, "订单号已存在"):
            self.service.create_order(**payload)

    def test_reject_shipped_over_po(self) -> None:
        with self.assertRaisesRegex(ValueError, "已出货数量"):
            self.service.create_order(
                order_no="SO-20260530-003",
                customer="客户A",
                created_by="alice",
                items=[_item(po_qty="100", shipped_qty="200")],
            )

    def test_reject_invalid_tax_rate(self) -> None:
        with self.assertRaisesRegex(ValueError, "税率"):
            self.service.create_order(
                order_no="SO-20260530-004",
                customer="客户A",
                created_by="alice",
                items=[_item(tax_rate="1.5")],
            )

    def test_approve_order_from_draft_only(self) -> None:
        self.service.create_order(
            order_no="SO-20260530-005",
            customer="客户A",
            created_by="alice",
            items=[_item()],
        )
        approved = self.service.approve_order("SO-20260530-005", approved_by="bob")
        self.assertEqual(approved.status, OrderStatus.APPROVED)
        with self.assertRaisesRegex(ValueError, "only draft orders"):
            self.service.approve_order("SO-20260530-005", approved_by="bob")


if __name__ == "__main__":
    unittest.main()
