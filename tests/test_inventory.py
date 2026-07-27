import os
import tempfile
import unittest
from decimal import Decimal
from unittest.mock import patch

from test_impl.order_management.cost_analysis import CostRecordService
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.inventory import InventoryService
from test_impl.order_management.inventory.store import (
    PROCESS_FINISHED,
    STATUS_FINISHED,
    STATUS_INHOUSE,
    STATUS_OUTSOURCE,
    InventoryStore,
)
from test_impl.order_management.order_entry.line_store import LineStore

from bom_helpers import seed_bom

_SUPPLIER = "苏州麦凯良金属制品厂"
_PART = "PL9-01100-00-0A"


class TestInventoryService(unittest.TestCase):
    def setUp(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self._db_path = path
        self.cost_store = CostStore(path)
        self.records = CostRecordService(store=self.cost_store, line_store=LineStore(path))
        self.inv = InventoryService(
            store=InventoryStore(path),
            cost_store=self.cost_store,
            record_service=self.records,
        )
        self.supplier_patcher = patch(
            "test_impl.order_management.cost_analysis.record_service.list_profile_suppliers",
            return_value=[_SUPPLIER],
        )
        self.supplier_patcher.start()
        seed_bom(
            self.records,
            customer_name="东莞市凯泰智联科技有限公司",
            product_name="超频主机上盖",
            product_part_no=_PART,
            mold_no="WKT-MJ-LV-25006",
            unit_weight_g="136",
            process_prices={
                "01": "1.0",
                "02": {"price": "0.5", "supplier": _SUPPLIER},
                "28": {"price": "0.3", "supplier": "场内自制"},
                "34": {"price": "0.2", "supplier": "场内自制"},
            },
        )

    def tearDown(self) -> None:
        self.supplier_patcher.stop()
        self.inv.store.close()
        self.cost_store._conn.close()
        if os.path.exists(self._db_path):
            try:
                os.unlink(self._db_path)
            except OSError:
                pass

    def test_demo_flow_balances(self) -> None:
        self.inv.seed_demo_flow(_PART)
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_INHOUSE), Decimal("300"))
        self.assertEqual(self.inv.store.get_qty(_PART, "02", STATUS_OUTSOURCE, _SUPPLIER), Decimal("0"))
        self.assertEqual(self.inv.store.get_qty(_PART, "02", STATUS_INHOUSE), Decimal("0"))
        self.assertEqual(self.inv.store.get_qty(_PART, "28", STATUS_INHOUSE), Decimal("0"))
        self.assertEqual(self.inv.store.get_qty(_PART, PROCESS_FINISHED, STATUS_FINISHED), Decimal("150"))
        board = self.inv.board(product_part_no=_PART)[0]
        self.assertEqual(board["product_name"], "超频主机上盖")
        self.assertEqual(board["customer_name"], "东莞市凯泰智联科技有限公司")
        self.assertEqual(float(board["finished_qty"]), 150.0)

    def test_board_filter_by_customer(self) -> None:
        self.inv.seed_demo_flow(_PART)
        all_rows = self.inv.board()
        self.assertGreaterEqual(len(all_rows), 1)
        matched = self.inv.board(customer_name="凯泰")
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["product_part_no"], _PART)
        self.assertEqual(self.inv.board(customer_name="不存在客户"), [])

    def test_inbound_outsource_goes_to_same_process_inhouse(self) -> None:
        self.inv.inbound(_PART, "01", "100")
        self.inv.outbound(_PART, "01", "02", "40", supplier_name=_SUPPLIER)
        self.inv.inbound(_PART, "02", "40", supplier_name=_SUPPLIER)
        self.assertEqual(self.inv.store.get_qty(_PART, "02", STATUS_OUTSOURCE, _SUPPLIER), Decimal("0"))
        self.assertEqual(self.inv.store.get_qty(_PART, "02", STATUS_INHOUSE), Decimal("40"))
        self.assertEqual(self.inv.store.get_qty(_PART, "28", STATUS_INHOUSE), Decimal("0"))

    def test_outbound_next_from_same_process_inhouse(self) -> None:
        """本道场内后，发下一道：本道场内减、下道在途加，再入库进下道场内。"""
        self.inv.inbound(_PART, "01", "100")
        self.inv.outbound(_PART, "01", "02", "40", supplier_name=_SUPPLIER)
        self.inv.inbound(_PART, "02", "40", supplier_name=_SUPPLIER)
        self.inv.outbound(_PART, "02", "28", "40")
        self.inv.inbound(_PART, "28", "40")
        self.assertEqual(self.inv.store.get_qty(_PART, "02", STATUS_INHOUSE), Decimal("0"))
        self.assertEqual(self.inv.store.get_qty(_PART, "28", STATUS_INHOUSE), Decimal("40"))

    def test_auto_doc_no_by_action(self) -> None:
        m1 = self.inv.inbound(_PART, "01", "10")
        self.assertTrue(str(m1["doc_no"]).startswith("RK-"))
        m2 = self.inv.outbound(_PART, "01", "02", "5", supplier_name=_SUPPLIER)
        self.assertTrue(str(m2["doc_no"]).startswith("CK-"))
        m3 = self.inv.inbound(_PART, "02", "5", supplier_name=_SUPPLIER)
        self.assertTrue(str(m3["doc_no"]).startswith("RK-"))
        self.inv.outbound(_PART, "02", "28", "5")
        self.inv.inbound(_PART, "28", "5")
        self.inv.outbound(_PART, "28", "34", "5")
        self.inv.inbound(_PART, "34", "5")
        m4 = self.inv.ship_finished(_PART, "2")
        self.assertTrue(str(m4["doc_no"]).startswith("CK-"))
        m5 = self.inv.inbound(_PART, "01", "1", doc_no="MANUAL-1")
        self.assertEqual(m5["doc_no"], "MANUAL-1")

    def test_legacy_doc_no_display_normalized(self) -> None:
        mov = self.inv.inbound(_PART, "01", "1")
        mid = int(mov["id"])
        self.inv.store._conn.execute(
            "UPDATE inventory_movements SET doc_no=?, action_type=? WHERE id=?",
            ("WG-20260725-099", "complete", mid),
        )
        self.inv.store._conn.commit()
        row = self.inv.list_movements(product_part_no=_PART)[0]
        self.assertEqual(row["doc_no"], "RK-20260725-099")
        self.assertEqual(row["action_label"], "入库")

    def test_movement_labels_inbound_outbound(self) -> None:
        self.inv.inbound(_PART, "01", "10")
        self.inv.outbound(_PART, "01", "02", "5", supplier_name=_SUPPLIER)
        items = self.inv.list_movements(product_part_no=_PART)
        labels = {r["action_type"]: r["action_label"] for r in items}
        self.assertEqual(labels.get("inbound"), "入库")
        self.assertEqual(labels.get("outbound"), "出库")
        outbound = next(r for r in items if r["action_type"] == "outbound")
        self.assertIn("01", outbound["route_display"])

    def test_seed_board_demo_ten_parts(self) -> None:
        parts = [f"BOARD-DEMO-{i:02d}" for i in range(1, 11)]
        result = self.inv.seed_board_demo(
            self.records,
            parts=[
                {
                    "product_part_no": p,
                    "product_name": f"看板演示品{i}",
                    "customer_name": "演示库存客户",
                }
                for i, p in enumerate(parts, start=1)
            ],
        )
        self.assertEqual(result["count"], 10)
        board = self.inv.board()
        self.assertGreaterEqual(len(board), 10)
        by_part = {r["product_part_no"]: r for r in board}
        for i, p in enumerate(parts, start=1):
            row = by_part[p]
            self.assertEqual(row["product_name"], f"看板演示品{i}")
            self.assertGreater(float(row["finished_qty"]), 0)
            self.assertTrue(row["stages"])
            stage_qty = sum(
                float(s["inhouse_qty"]) + float(s["outsource_qty"]) for s in row["stages"]
            )
            self.assertGreater(stage_qty, 0)
            self.assertEqual(row["data_tag"], "测")
            self.assertTrue(row["is_demo"])

    def test_list_movements_filter_on_date(self) -> None:
        from datetime import date

        self.inv.inbound(_PART, "01", "10")
        today = date.today().isoformat()
        today_items = self.inv.list_movements(on_date=today)
        self.assertGreaterEqual(len(today_items), 1)
        self.assertTrue(all(r["product_part_no"] == _PART for r in today_items))
        self.assertEqual(today_items[0]["product_name"], "超频主机上盖")
        self.assertIn("压铸", today_items[0]["route_display"])
        self.assertEqual(self.inv.list_movements(on_date="2000-01-01"), [])

    def test_list_movements_filter_by_customer(self) -> None:
        self.inv.inbound(_PART, "01", "10")
        matched = self.inv.list_movements(customer_name="凯泰")
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["customer_name"], "东莞市凯泰智联科技有限公司")
        self.assertEqual(self.inv.list_movements(customer_name="不存在"), [])

    def test_correct_movement_qty(self) -> None:
        mov = self.inv.inbound(_PART, "01", "100")
        mid = int(mov["id"])
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_INHOUSE), Decimal("100"))
        updated = self.inv.correct_movement(mid, qty="80", note="数量改少")
        self.assertEqual(float(updated["qty"]), 80.0)
        self.assertEqual(updated["note"], "数量改少")
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_INHOUSE), Decimal("80"))

    def test_correct_movement_rejects_order_ship_note(self) -> None:
        self.inv.inbound(_PART, "01", "20")
        self.inv.outbound(_PART, "01", "02", "20", supplier_name=_SUPPLIER)
        self.inv.inbound(_PART, "02", "20", supplier_name=_SUPPLIER)
        self.inv.outbound(_PART, "02", "28", "20")
        self.inv.inbound(_PART, "28", "20")
        self.inv.outbound(_PART, "28", "34", "20")
        self.inv.inbound(_PART, "34", "20")
        mov = self.inv.ship_finished(_PART, "5", note="订单出货 PO-TEST")
        mid = int(mov["id"])
        with self.assertRaises(ValueError) as ctx:
            self.inv.correct_movement(mid, qty="3")
        self.assertIn("订单出货", str(ctx.exception))

    def test_adjust_finished_balance(self) -> None:
        self.inv.seed_demo_flow(_PART)
        self.assertEqual(self.inv.store.get_qty(_PART, PROCESS_FINISHED, STATUS_FINISHED), Decimal("150"))
        mov = self.inv.adjust_balance(_PART, target_qty="120", status=STATUS_FINISHED)
        self.assertEqual(self.inv.store.get_qty(_PART, PROCESS_FINISHED, STATUS_FINISHED), Decimal("120"))
        self.assertEqual(float(mov["qty"]), 30.0)
        self.assertIn("库存校正", mov["note"])
        self.assertIn("150", mov["note"])
        self.assertIn("120", mov["note"])
        self.assertTrue(str(mov["doc_no"]).startswith("TZ-"))

    def test_adjust_inhouse_balance(self) -> None:
        self.inv.inbound(_PART, "01", "100")
        mov = self.inv.adjust_balance(_PART, target_qty="80", process_code="01", status=STATUS_INHOUSE)
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_INHOUSE), Decimal("80"))
        self.assertIn("库存校正", mov["note"])
        self.assertIn("100", mov["note"])
        self.assertIn("80", mov["note"])

    def test_adjust_rejects_noop(self) -> None:
        self.inv.inbound(_PART, "01", "50")
        with self.assertRaises(ValueError) as ctx:
            self.inv.adjust_balance(_PART, target_qty="50", process_code="01", status=STATUS_INHOUSE)
        self.assertIn("无需校正", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
