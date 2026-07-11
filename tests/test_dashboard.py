import unittest
from decimal import Decimal

from test_impl.order_management.dashboard import OrderDashboardService
from test_impl.order_management.order_entry import OrderLineService
from test_impl.order_management.order_entry.line_store import CLOSURE_FORCED


class TestOrderDashboard(unittest.TestCase):
    def setUp(self) -> None:
        self.lines = OrderLineService(db_path=":memory:")
        self.dashboard = OrderDashboardService(self.lines)

    def _line(self, **overrides):
        base = {
            "customer": "测试客户A",
            "order_date": "2026-05-01",
            "delivery_date": "2026-06-01",
            "order_no": "PO-1",
            "product_spec": "壳体",
            "po_qty": "100",
            "shipped_qty": "0",
            "unit": "PCS",
            "tax_rate": "0.13",
            "rmb_tax_incl_price": "10",
        }
        base.update(overrides)
        return self.lines.create_line(base)

    def test_overview_counts_open_and_closed(self) -> None:
        self._line(customer="客户甲", order_no="A1", po_qty="100", shipped_qty="0")
        ln2 = self._line(customer="客户甲", order_no="A2", product_spec="盖板", po_qty="50", shipped_qty="50")
        self.assertEqual(ln2.open_qty(), Decimal("0"))
        self.lines.force_close_line(
            self._line(customer="客户乙", order_no="B1", product_spec="轴", po_qty="20").id
        )

        data = self.dashboard.build_overview()
        self.assertTrue(data["ok"])
        kpis = data["kpis"]
        self.assertEqual(kpis["total_lines"], 3)
        self.assertEqual(kpis["open_lines"], 1)
        self.assertEqual(kpis["closed_lines"], 1)
        self.assertEqual(kpis["forced_closed_lines"], 1)
        self.assertEqual(kpis["customers"], 2)

    def test_overview_includes_shipment_monthly(self) -> None:
        ln = self._line(customer="客户甲", order_no="S1", po_qty="10", shipped_qty="0")
        self.lines.ship_line(ln.id, "4")
        data = self.dashboard.build_overview()
        self.assertGreaterEqual(data["kpis"]["shipment_events"], 1)
        self.assertTrue(data["monthly_shipments"])
        self.assertTrue(any(x["count"] >= 1 for x in data["monthly_shipments"]))


if __name__ == "__main__":
    unittest.main()
