import os
import tempfile
import unittest

from test_impl.order_management.cost_analysis import BomService, CostLookupService, CostRecordService
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.order_entry import OrderLineService
from test_impl.order_management.order_entry.line_store import LineStore

from bom_helpers import seed_bom, seed_bom_conflict


class TestCostLookupService(unittest.TestCase):
    def setUp(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self._db_path = path
        self.line_store = LineStore(db_path=path)
        self.cost_store = CostStore(db_path=path)
        self.record_service = CostRecordService(store=self.cost_store, line_store=self.line_store)
        self.lookup = CostLookupService(
            line_store=self.line_store,
            cost_store=self.cost_store,
            record_service=self.record_service,
        )

    def tearDown(self) -> None:
        self.line_store.close()
        self.cost_store._conn.close()
        if os.path.exists(self._db_path):
            os.unlink(self._db_path)

    def test_suggest_part_numbers_from_bom(self) -> None:
        seed_bom(
            self.record_service,
            customer_name="凯泰",
            product_name="前挡板",
            product_part_no="PL9-01050-00-0A",
            unit_weight_g="88",
        )
        items = self.lookup.suggest_part_numbers("PL9")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["product_part_no"], "PL9-01050-00-0A")
        self.assertEqual(items[0]["customer_name"], "凯泰")
        self.assertEqual(items[0]["source"], "bom")

    def test_suggest_customers_from_bom(self) -> None:
        seed_bom(
            self.record_service,
            customer_name="东莞市凯泰智联科技有限公司",
            product_name="前挡板",
            product_part_no="PL9-01050-00-0A",
        )
        items = self.lookup.suggest_customers("凯泰")
        self.assertEqual(len(items), 1)
        self.assertIn("凯泰", items[0])

    def test_lookup_from_bom(self) -> None:
        seed_bom(
            self.record_service,
            customer_name="凯泰",
            product_name="前挡板",
            product_part_no="PL9-01050-00-0A",
            unit_weight_g="88",
            mold_no="WKT-MJ-LV-24027",
        )
        result = self.lookup.lookup_by_part_no("PL9-01050-00-0A")
        self.assertTrue(result["found"])
        self.assertTrue(result["from_bom"])
        self.assertEqual(result["customer_name"], "凯泰")
        self.assertEqual(result["suggested"]["product_name"], "前挡板")
        self.assertEqual(result["suggested"]["unit_weight_g"], "88")
        self.assertEqual(result["suggested"]["mold_no"], "WKT-MJ-LV-24027")

    def test_lookup_not_found(self) -> None:
        result = self.lookup.lookup_by_part_no("UNKNOWN-PART")
        self.assertFalse(result["found"])

    def test_lookup_rejects_conflicting_customers_in_bom(self) -> None:
        seed_bom_conflict(
            self.cost_store,
            "PL9-01050-00-0A",
            customers=[
                ("凯泰", "前挡板A"),
                ("其他客户", "前挡板B"),
            ],
        )
        with self.assertRaisesRegex(ValueError, "多个客户"):
            self.lookup.lookup_by_part_no("PL9-01050-00-0A")


class TestOrderRequiresBom(unittest.TestCase):
    def setUp(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self._db_path = path
        self.line_store = LineStore(db_path=path)
        self.cost_store = CostStore(db_path=path)
        self.record_service = CostRecordService(store=self.cost_store, line_store=self.line_store)
        self.svc = OrderLineService(
            store=self.line_store,
            bom_service=BomService(
                cost_store=self.cost_store,
                record_service=self.record_service,
            ),
        )

    def tearDown(self) -> None:
        self.line_store.close()
        self.cost_store._conn.close()
        if os.path.exists(self._db_path):
            os.unlink(self._db_path)

    def test_create_line_requires_bom(self) -> None:
        with self.assertRaisesRegex(ValueError, "BOM 录入"):
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

    def test_create_line_with_bom_ok(self) -> None:
        seed_bom(
            self.record_service,
            customer_name="凯泰",
            product_name="前挡板",
            product_part_no="PL9-01050-00-0A",
        )
        line = self.svc.create_line(
            {
                "customer": "凯泰",
                "order_date": "2026-01-01",
                "order_no": "PO-1",
                "product_spec": "前挡板",
                "customer_part_no": "PL9-01050-00-0A",
                "po_qty": "10",
            }
        )
        self.assertEqual(line.customer_part_no, "PL9-01050-00-0A")

    def test_different_customer_rejected(self) -> None:
        seed_bom(
            self.record_service,
            customer_name="凯泰",
            product_name="前挡板",
            product_part_no="PL9-01050-00-0A",
        )
        with self.assertRaisesRegex(ValueError, "BOM 绑定客户"):
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
