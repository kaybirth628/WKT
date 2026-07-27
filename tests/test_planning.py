import os
import tempfile
import unittest
from unittest.mock import patch

from test_impl.order_management.cost_analysis import CostRecordService
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.inventory import InventoryService, PlanningService
from test_impl.order_management.inventory.store import InventoryStore
from test_impl.order_management.order_entry import OrderLineService
from test_impl.order_management.cost_analysis.bom_service import BomService


class TestPlanningCompare(unittest.TestCase):
    def setUp(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self._db_path = path
        self.line_svc = OrderLineService(db_path=path)
        self.cost_store = CostStore(path)
        self.records = CostRecordService(store=self.cost_store, line_store=self.line_svc._store)
        self.line_svc._bom = BomService(cost_store=self.cost_store, record_service=self.records)
        self.inv = InventoryService(
            store=InventoryStore(path),
            cost_store=self.cost_store,
            record_service=self.records,
        )
        self.planning = PlanningService(self.line_svc, self.inv)
        self.supplier_patcher = patch(
            "test_impl.order_management.cost_analysis.record_service.list_profile_suppliers",
            return_value=["苏州麦凯良金属制品厂"],
        )
        self.supplier_patcher.start()

    def tearDown(self) -> None:
        self.supplier_patcher.stop()
        self.line_svc._store.close()
        self.inv.store.close()
        self.cost_store._conn.close()
        if os.path.exists(self._db_path):
            try:
                os.unlink(self._db_path)
            except OSError:
                pass

    def test_seed_planning_demo_gaps(self) -> None:
        result = self.planning.seed_planning_demo(self.records)
        items = {r["customer_part_no"]: r for r in result["items"]}
        self.assertEqual(float(items["PLAN-A"]["open_qty"]), 1000)
        self.assertEqual(float(items["PLAN-A"]["finished_qty"]), 200)
        self.assertEqual(float(items["PLAN-A"]["semifinished_qty"]), 300)
        self.assertEqual(float(items["PLAN-A"]["gap_ship"]), 800)
        self.assertEqual(float(items["PLAN-A"]["gap_cover"]), 500)
        self.assertEqual(float(items["PLAN-B"]["gap_cover"]), 400)
        self.assertEqual(float(items["PLAN-C"]["gap_cover"]), 300)


if __name__ == "__main__":
    unittest.main()
