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
    STATUS_REPAIR,
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
        self.assertTrue(str(m1["doc_no"]).startswith("WKT"))
        m2 = self.inv.outbound(_PART, "01", "02", "5", supplier_name=_SUPPLIER)
        self.assertTrue(str(m2["doc_no"]).startswith("WKT"))
        m3 = self.inv.inbound(_PART, "02", "5", supplier_name=_SUPPLIER)
        self.assertTrue(str(m3["doc_no"]).startswith("WKT"))
        self.inv.outbound(_PART, "02", "28", "5")
        self.inv.inbound(_PART, "28", "5")
        self.inv.outbound(_PART, "28", "34", "5")
        self.inv.inbound(_PART, "34", "5")
        m4 = self.inv.ship_finished(_PART, "2")
        self.assertTrue(str(m4["doc_no"]).startswith("WKT"))
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

    def test_skip_outbound_forward_and_reverse(self) -> None:
        """跳序：1→3 跳过 2；3 入库后再 3→2 回补。"""
        self.inv.inbound(_PART, "01", "100")
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_INHOUSE), Decimal("100"))

        with self.assertRaises(ValueError):
            self.inv.outbound(_PART, "01", "28", "40")

        mov = self.inv.skip_outbound(_PART, "01", "28", "40", note="2道来不及先发3道")
        self.assertEqual(mov["action_type"], "skip_outbound")
        self.assertTrue(str(mov["doc_no"]).startswith("WKT"))
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_INHOUSE), Decimal("60"))
        self.assertEqual(self.inv.store.get_qty(_PART, "28", STATUS_OUTSOURCE, ""), Decimal("40"))
        self.assertEqual(self.inv.store.get_qty(_PART, "02", STATUS_OUTSOURCE, _SUPPLIER), Decimal("0"))

        self.inv.inbound(_PART, "28", "40")
        self.assertEqual(self.inv.store.get_qty(_PART, "28", STATUS_INHOUSE), Decimal("40"))

        self.inv.skip_outbound(
            _PART, "28", "02", "40", supplier_name=_SUPPLIER, note="3道做完回补2道"
        )
        self.assertEqual(self.inv.store.get_qty(_PART, "28", STATUS_INHOUSE), Decimal("0"))
        self.assertEqual(self.inv.store.get_qty(_PART, "02", STATUS_OUTSOURCE, _SUPPLIER), Decimal("40"))

        self.inv.inbound(_PART, "02", "40", supplier_name=_SUPPLIER)
        self.assertEqual(self.inv.store.get_qty(_PART, "02", STATUS_INHOUSE), Decimal("40"))

        skip_rows = [
            r for r in self.inv.list_movements(product_part_no=_PART) if r["action_type"] == "skip_outbound"
        ]
        self.assertEqual(len(skip_rows), 2)
        self.assertEqual(skip_rows[0]["action_label"], "跳序出库")

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
        self.assertNotIn("修改成品库存", mov["note"])
        self.assertTrue(str(mov["doc_no"]).startswith("WKT"))
        enriched = self.inv.list_movements(product_part_no=_PART, limit=1)[0]
        self.assertEqual(enriched["action_label"], "修改成品库存")
        self.assertEqual(enriched["qty"], "30")
        self.assertEqual(enriched["route_display"], "成品")

    def test_adjust_inhouse_balance(self) -> None:
        self.inv.inbound(_PART, "01", "100")
        mov = self.inv.adjust_balance(_PART, target_qty="80", process_code="01", status=STATUS_INHOUSE)
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_INHOUSE), Decimal("80"))
        self.assertNotIn("修改场内库存", mov["note"])
        enriched = self.inv.list_movements(product_part_no=_PART, limit=1)[0]
        self.assertEqual(enriched["action_label"], "修改场内库存")
        self.assertEqual(enriched["qty"], "20")
        self.assertIn("01", enriched["route_display"])
        self.assertNotIn("场内", enriched["route_display"])

    def test_adjust_rejects_noop(self) -> None:
        self.inv.inbound(_PART, "01", "50")
        with self.assertRaises(ValueError) as ctx:
            self.inv.adjust_balance(_PART, target_qty="50", process_code="01", status=STATUS_INHOUSE)
        self.assertIn("无需校正", str(ctx.exception))

    def test_adjust_outsource_balance(self) -> None:
        self.inv.inbound(_PART, "01", "50")
        self.inv.outbound(_PART, "01", "02", "30", supplier_name=_SUPPLIER)
        self.assertEqual(
            self.inv.store.get_qty(_PART, "02", STATUS_OUTSOURCE, _SUPPLIER), Decimal("30")
        )
        self.inv.adjust_balance(
            _PART,
            target_qty="25",
            process_code="02",
            status=STATUS_OUTSOURCE,
            supplier_name=_SUPPLIER,
        )
        self.assertEqual(
            self.inv.store.get_qty(_PART, "02", STATUS_OUTSOURCE, _SUPPLIER), Decimal("25")
        )

    def test_adjust_repair_balance(self) -> None:
        self.inv.inbound(_PART, "01", "40")
        self.inv.repair_out(_PART, "15", process_code="01")
        self.inv.adjust_balance(
            _PART, target_qty="10", process_code="01", status=STATUS_REPAIR
        )
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_REPAIR), Decimal("10"))

    def test_repair_semi_and_finished(self) -> None:
        self.inv.inbound(_PART, "01", "100")
        self.inv.repair_out(_PART, "20", process_code="01")
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_INHOUSE), Decimal("80"))
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_REPAIR), Decimal("20"))
        self.inv.repair_in(_PART, "20", process_code="01")
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_INHOUSE), Decimal("100"))
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_REPAIR), Decimal("0"))

        self.inv.outbound(_PART, "01", "02", "100", supplier_name=_SUPPLIER)
        self.inv.inbound(_PART, "02", "100", supplier_name=_SUPPLIER)
        self.inv.outbound(_PART, "02", "28", "100")
        self.inv.inbound(_PART, "28", "100")
        self.inv.outbound(_PART, "28", "34", "100")
        self.inv.inbound(_PART, "34", "100")
        self.assertEqual(self.inv.finished_qty(_PART), Decimal("100"))

        self.inv.repair_out(_PART, "30", process_code="FIN")
        self.assertEqual(self.inv.finished_qty(_PART), Decimal("70"))
        self.assertEqual(
            self.inv.store.get_qty(_PART, PROCESS_FINISHED, STATUS_REPAIR), Decimal("30")
        )
        board = self.inv.board(product_part_no=_PART)[0]
        self.assertEqual(float(board["finished_repair_qty"]), 30.0)

        self.inv.repair_in(_PART, "30", process_code="FIN")
        self.assertEqual(self.inv.finished_qty(_PART), Decimal("100"))
        self.assertEqual(
            self.inv.store.get_qty(_PART, PROCESS_FINISHED, STATUS_REPAIR), Decimal("0")
        )

    def test_board_stage_includes_supplier(self) -> None:
        self.inv.inbound(_PART, "01", "10")
        board = self.inv.board(product_part_no=_PART)[0]
        stage02 = next(s for s in board["stages"] if s["process_code"] == "02")
        self.assertEqual(stage02["supplier"], _SUPPLIER)

    def test_set_stage_buckets_syncs_supplier(self) -> None:
        self.inv.inbound(_PART, "01", "100")
        alt = "备用外协厂"
        with patch(
            "test_impl.order_management.cost_analysis.record_service.list_profile_suppliers",
            return_value=[_SUPPLIER, alt],
        ):
            self.inv.set_stage_buckets(
                _PART,
                "02",
                inhouse_qty="5",
                supplier_name=alt,
                note="换供应商",
            )
        route = self.inv.get_route(_PART)
        step02 = next(s for s in route if s["code"] == "02")
        self.assertEqual(step02["supplier"], alt)

    def test_set_stage_buckets_records_movements(self) -> None:
        self.inv.inbound(_PART, "01", "100")
        result = self.inv.set_stage_buckets(
            _PART,
            "01",
            inhouse_qty="80",
            outsource_qty="10",
            repair_qty="5",
            supplier_name="场内自制",
        )
        self.assertEqual(result["count"], 3)
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_INHOUSE), Decimal("80"))
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_OUTSOURCE), Decimal("10"))
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_REPAIR), Decimal("5"))
        movements = self.inv.list_movements(product_part_no=_PART, limit=10)
        adjust_rows = [
            m for m in movements if str(m.get("action_label", "")).startswith("修改")
        ]
        self.assertGreaterEqual(len(adjust_rows), 3)
        self.assertIn("场内自制", adjust_rows[0]["note"])

    def test_set_stage_buckets_noop_raises(self) -> None:
        self.inv.inbound(_PART, "01", "50")
        with self.assertRaises(ValueError) as ctx:
            self.inv.set_stage_buckets(_PART, "01", inhouse_qty="50")
        self.assertIn("未变更", str(ctx.exception))

    def test_adjust_outsource_balance_display(self) -> None:
        self.inv.inbound(_PART, "01", "100")
        self.inv.outbound(_PART, "01", "02", "50", supplier_name=_SUPPLIER)
        self.inv.adjust_balance(
            _PART,
            target_qty="80",
            process_code="02",
            status=STATUS_OUTSOURCE,
            supplier_name=_SUPPLIER,
        )
        enriched = self.inv.list_movements(product_part_no=_PART, limit=1)[0]
        self.assertEqual(enriched["action_label"], "修改在途库存")
        self.assertIn("02", enriched["route_display"])
        self.assertNotIn("在途", enriched["route_display"])
        self.assertEqual(enriched["qty"], "30")

    def test_stage_flow_same_process(self) -> None:
        self.inv.inbound(_PART, "01", "100")
        mov = self.inv.record_stage_flow(
            _PART,
            from_process_code="01",
            from_status="inhouse",
            to_process_code="01",
            to_status="repair",
            qty="15",
            note="返修送修",
        )
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_INHOUSE), Decimal("85"))
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_REPAIR), Decimal("15"))
        self.assertEqual(mov["action_type"], "stage_flow")
        self.assertTrue(str(mov["doc_no"]).startswith("WKT"))

    def test_stage_flow_cross_process(self) -> None:
        self.inv.inbound(_PART, "01", "50")
        self.inv.record_stage_flow(
            _PART,
            from_process_code="01",
            from_status="inhouse",
            to_process_code="02",
            to_status="outsource",
            qty="30",
            to_supplier_name=_SUPPLIER,
        )
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_INHOUSE), Decimal("20"))
        self.assertEqual(
            self.inv.store.get_qty(_PART, "02", STATUS_OUTSOURCE, _SUPPLIER), Decimal("30")
        )

    def test_stage_flow_external_in(self) -> None:
        self.inv.record_stage_flow(
            _PART,
            from_process_code="EXT",
            from_status="",
            to_process_code="01",
            to_status="inhouse",
            qty="40",
            note="来料",
        )
        self.assertEqual(self.inv.store.get_qty(_PART, "01", STATUS_INHOUSE), Decimal("40"))

    def test_stage_flow_movement_route_display(self) -> None:
        self.inv.inbound(_PART, "01", "100")
        self.inv.record_stage_flow(
            _PART,
            from_process_code="01",
            from_status="inhouse",
            to_process_code="02",
            to_status="outsource",
            qty="20",
            to_supplier_name=_SUPPLIER,
        )
        items = self.inv.list_movements(product_part_no=_PART)
        stage_flow = [r for r in items if r.get("action_type") == "stage_flow"]
        self.assertEqual(len(stage_flow), 1)
        self.assertIn("→", stage_flow[0]["route_display"])
        self.assertIn("01", stage_flow[0]["route_display"])


if __name__ == "__main__":
    unittest.main()
