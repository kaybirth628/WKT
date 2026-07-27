import os
import tempfile
import unittest
from decimal import Decimal
from unittest.mock import patch

from test_impl.order_management.cost_analysis import CostRecordService
from test_impl.order_management.cost_analysis.bom_service import BomService
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.inventory import InventoryService
from test_impl.order_management.inventory.store import (
    PROCESS_FINISHED,
    STATUS_FINISHED,
    InventoryStore,
)
from test_impl.order_management.order_entry import OrderLineService

from bom_helpers import seed_bom

_SUPPLIER = "苏州麦凯良金属制品厂"
_PART = "FG-SHIP-001"


class TestReplenishAndShipDeduct(unittest.TestCase):
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
        self.line_svc.set_inventory_service(self.inv)
        self.supplier_patcher = patch(
            "test_impl.order_management.cost_analysis.record_service.list_profile_suppliers",
            return_value=[_SUPPLIER],
        )
        self.supplier_patcher.start()
        seed_bom(
            self.records,
            customer_name="扣库测试客户",
            product_name="扣库测试品",
            product_part_no=_PART,
            mold_no="M-FG-SHIP",
            process_prices={
                "01": "1",
                "02": {"price": "0.5", "supplier": _SUPPLIER},
                "28": {"price": "0.3", "supplier": "场内自制"},
                "34": {"price": "0.2", "supplier": "场内自制"},
            },
        )

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

    def test_create_replenish_binds_sales_order(self) -> None:
        row = self.inv.create_replenish(
            product_part_no=_PART,
            qty="500",
            sales_order_no="PO-SALES-1",
            line_id=12,
            note="缺口补产",
        )
        self.assertTrue(row["doc_no"].startswith("BC-"))
        self.assertEqual(row["sales_order_no"], "PO-SALES-1")
        self.assertEqual(row["line_id"], 12)
        self.assertEqual(float(row["qty"]), 500)
        listed = self.inv.list_replenish()
        self.assertEqual(len(listed), 1)

    def test_ship_deducts_finished_stock(self) -> None:
        self.inv.inject_balances(
            _PART,
            [{"process_code": PROCESS_FINISHED, "status": STATUS_FINISHED, "qty": "100"}],
        )
        line = self.line_svc.create_line(
            {
                "customer": "扣库测试客户",
                "order_date": "2026-07-21",
                "delivery_date": "2026-08-01",
                "order_no": "PO-DED-1",
                "product_spec": "扣库测试品",
                "customer_part_no": _PART,
                "po_qty": "80",
                "shipped_qty": "0",
                "unit": "PCS",
            }
        )
        updated, _ev = self.line_svc.ship_line(line.id, "30")
        self.assertEqual(float(updated.shipped_qty), 30)
        self.assertEqual(self.inv.finished_qty(_PART), Decimal("70"))

    def test_ship_rejects_when_finished_insufficient(self) -> None:
        self.inv.inject_balances(
            _PART,
            [{"process_code": PROCESS_FINISHED, "status": STATUS_FINISHED, "qty": "10"}],
        )
        line = self.line_svc.create_line(
            {
                "customer": "扣库测试客户",
                "order_date": "2026-07-21",
                "delivery_date": "2026-08-01",
                "order_no": "PO-DED-2",
                "product_spec": "扣库测试品",
                "customer_part_no": _PART,
                "po_qty": "80",
                "shipped_qty": "0",
                "unit": "PCS",
            }
        )
        with self.assertRaises(ValueError) as ctx:
            self.line_svc.ship_line(line.id, "20")
        self.assertIn("成品库存不足", str(ctx.exception))
        again = self.line_svc.get_line(line.id)
        self.assertEqual(float(again.shipped_qty), 0)
        self.assertEqual(self.inv.finished_qty(_PART), Decimal("10"))


if __name__ == "__main__":
    unittest.main()
