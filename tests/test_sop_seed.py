"""SOP 测试数据种子。"""
from __future__ import annotations

import os
import tempfile
import unittest

from test_impl.demo.sop_seed import (
    DEMO_ORDER_PREFIX,
    DEMO_PART_PREFIX,
    seed_sop_test_data,
)
from test_impl.order_management.cost_analysis import CostRecordService
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.order_entry.line_service import OrderLineService


class TestSopSeed(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        os.environ["WKT_DB_PATH"] = self._tmp.name

    def tearDown(self) -> None:
        os.environ.pop("WKT_DB_PATH", None)
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    def test_seed_creates_demo_tagged_rows(self) -> None:
        summary = seed_sop_test_data(count=12)
        self.assertTrue(summary["ok"])
        self.assertEqual(summary["bom_records"], 12)
        self.assertEqual(summary["order_lines"], 12)

        lines = OrderLineService()
        cost_store = CostStore(lines._store.db_path)
        records = CostRecordService(store=cost_store, line_store=lines._store)

        all_lines = lines.list_lines()
        self.assertEqual(len(all_lines), 12)
        for ln in all_lines:
            self.assertTrue(ln.is_demo)
            self.assertTrue(ln.order_no.startswith(DEMO_ORDER_PREFIX))
            self.assertTrue(ln.customer_part_no.startswith(DEMO_PART_PREFIX))

        recs = records.list_records()
        self.assertEqual(len(recs), 12)
        for r in recs:
            self.assertTrue(r.is_demo)

        shipped = lines.list_shipment_events()
        self.assertGreaterEqual(len(shipped), 5)

        open_rows = lines.list_lines(view="open")
        self.assertGreaterEqual(len(open_rows), 5)


if __name__ == "__main__":
    unittest.main()
