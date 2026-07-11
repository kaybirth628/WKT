import unittest

from test_impl.order_management.cost_analysis import CostLookupService, CostRecordService
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.order_entry import DuplicatePartNoError, OrderLineService
from test_impl.order_management.order_entry.line_store import LineStore


def _insert_order_line(store: LineStore, **fields) -> None:
    store._conn.execute(
        """
        INSERT INTO order_lines (
            customer, order_date, delivery_date, order_no, product_spec,
            customer_part_no, unit_weight_g, material, po_qty, shipped_qty,
            unit, tax_rate, rmb_tax_incl_price, payment_terms, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            fields.get("customer", "凯泰"),
            fields.get("order_date", "2026-01-01"),
            fields.get("delivery_date", ""),
            fields.get("order_no", "PO-001"),
            fields.get("product_spec", "前挡板"),
            fields.get("customer_part_no", "PL9-01050-00-0A"),
            fields.get("unit_weight_g", "88"),
            fields.get("material", "ADC12"),
            fields.get("po_qty", "100"),
            fields.get("shipped_qty", "0"),
            fields.get("unit", "PCS"),
            fields.get("tax_rate", "0.13"),
            fields.get("rmb_tax_incl_price", "10"),
            fields.get("payment_terms", "月结30天"),
            fields.get("created_at", "2026-01-01T00:00:00+00:00"),
            fields.get("updated_at", "2026-01-01T00:00:00+00:00"),
        ),
    )
    store._conn.commit()


class TestCostLookupService(unittest.TestCase):
    def setUp(self) -> None:
        self.line_store = LineStore(db_path=":memory:")
        self.cost_store = CostStore(db_path=":memory:")
        self.record_service = CostRecordService(store=self.cost_store, line_store=self.line_store)
        self.lookup = CostLookupService(
            line_store=self.line_store,
            cost_store=self.cost_store,
            record_service=self.record_service,
        )

    def tearDown(self) -> None:
        self.line_store.close()
        self.cost_store._conn.close()

    def test_suggest_part_numbers(self) -> None:
        _insert_order_line(self.line_store)
        items = self.lookup.suggest_part_numbers("PL9")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["product_part_no"], "PL9-01050-00-0A")
        self.assertEqual(items[0]["customer_name"], "凯泰")

    def test_lookup_from_order_line(self) -> None:
        _insert_order_line(self.line_store)
        result = self.lookup.lookup_by_part_no("PL9-01050-00-0A")
        self.assertTrue(result["found"])
        self.assertEqual(result["customer_name"], "凯泰")
        self.assertEqual(result["suggested"]["customer_name"], "凯泰")
        self.assertEqual(result["suggested"]["product_name"], "前挡板")
        self.assertEqual(result["suggested"]["unit_weight_g"], "88")
        self.assertIn("unit_weight_g", result["auto_filled"])

    def test_lookup_skips_zero_weight_and_uses_older_order_value(self) -> None:
        _insert_order_line(
            self.line_store,
            order_no="PO-new",
            unit_weight_g="0",
            updated_at="2026-03-01T00:00:00+00:00",
        )
        _insert_order_line(
            self.line_store,
            order_no="PO-old",
            unit_weight_g="92.5",
            updated_at="2026-01-01T00:00:00+00:00",
        )
        result = self.lookup.lookup_by_part_no("PL9-01050-00-0A")
        self.assertEqual(result["suggested"]["unit_weight_g"], "92.5")

    def test_lookup_weight_from_cost_when_order_missing(self) -> None:
        _insert_order_line(self.line_store, unit_weight_g="0")
        self.record_service.create_record(
            {
                "customer_name": "凯泰",
                "product_name": "前挡板",
                "mold_no": "WKT-MJ-LV-24027",
                "product_part_no": "PL9-01050-00-0A",
                "cavity": "1*2",
                "unit_weight_g": "90",
                "material": "ADC12",
                "machine_tonnage": "280T",
                "material_unit_price": "0.02",
                "process_prices": {"01": "1.5"},
            }
        )
        result = self.lookup.lookup_by_part_no("PL9-01050-00-0A")
        self.assertEqual(result["suggested"]["unit_weight_g"], "90")

    def test_lookup_without_weight_leaves_manual(self) -> None:
        _insert_order_line(self.line_store, unit_weight_g="0")
        result = self.lookup.lookup_by_part_no("PL9-01050-00-0A")
        self.assertNotIn("unit_weight_g", result["suggested"])
        self.assertNotIn("unit_weight_g", result["auto_filled"])

    def test_lookup_rejects_conflicting_customers(self) -> None:
        _insert_order_line(self.line_store)
        _insert_order_line(
            self.line_store,
            customer="其他客户",
            product_spec="同名产品",
            order_no="PO-002",
        )
        with self.assertRaisesRegex(ValueError, "多个客户"):
            self.lookup.lookup_by_part_no("PL9-01050-00-0A")

    def test_lookup_merge_cost_record(self) -> None:
        _insert_order_line(self.line_store)
        self.record_service.create_record(
            {
                "customer_name": "凯泰",
                "product_name": "前挡板",
                "mold_no": "WKT-MJ-LV-24027",
                "product_part_no": "PL9-01050-00-0A",
                "cavity": "1*2",
                "unit_weight_g": "88",
                "material": "ADC12",
                "machine_tonnage": "280T",
                "material_unit_price": "0.02",
                "process_prices": {"01": "1.5"},
            }
        )
        result = self.lookup.lookup_by_part_no("PL9-01050-00-0A")
        self.assertTrue(result["from_cost_record"])
        self.assertEqual(result["suggested"]["mold_no"], "WKT-MJ-LV-24027")


class TestPartNoUniqueness(unittest.TestCase):
    def setUp(self) -> None:
        self.line_store = LineStore(db_path=":memory:")
        self.svc = OrderLineService(store=self.line_store)

    def tearDown(self) -> None:
        self.line_store.close()

    def test_same_customer_same_part_on_different_orders_allowed(self) -> None:
        self.svc.create_line(
            {
                "customer": "凯泰",
                "order_date": "2026-01-01",
                "order_no": "PO-1",
                "product_spec": "前挡板",
                "customer_part_no": "PL9-01050-00-0A",
                "po_qty": "10",
            }
        )
        line = self.svc.create_line(
            {
                "customer": "凯泰",
                "order_date": "2026-02-01",
                "order_no": "PO-2",
                "product_spec": "前挡板",
                "customer_part_no": "PL9-01050-00-0A",
                "po_qty": "20",
            }
        )
        self.assertEqual(line.customer_part_no, "PL9-01050-00-0A")

    def test_different_customer_same_part_rejected(self) -> None:
        self.svc.create_line(
            {
                "customer": "凯泰",
                "order_date": "2026-01-01",
                "order_no": "PO-1",
                "product_spec": "前挡板",
                "customer_part_no": "PL9-01050-00-0A",
                "po_qty": "10",
            }
        )
        with self.assertRaises(DuplicatePartNoError):
            self.svc.create_line(
                {
                    "customer": "其他客户",
                    "order_date": "2026-01-01",
                    "order_no": "PO-9",
                    "product_spec": "其他产品",
                    "customer_part_no": "PL9-01050-00-0A",
                    "po_qty": "5",
                }
            )


if __name__ == "__main__":
    unittest.main()
