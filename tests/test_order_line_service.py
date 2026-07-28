import os
import tempfile
import unittest
from decimal import Decimal

from test_impl.order_management.cost_analysis import BomService, CostRecordService
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.order_entry import OrderLineService, DuplicateLineError, intake_to_lines
from test_impl.order_management.order_entry.line_models import normalize_line_fields

from bom_helpers import seed_bom


class TestOrderLineService(unittest.TestCase):
    def setUp(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self._db_path = path
        self.svc = OrderLineService(db_path=path)
        self.cost_store = CostStore(path)
        self.record_service = CostRecordService(store=self.cost_store, line_store=self.svc._store)
        self.svc._bom = BomService(
            cost_store=self.cost_store,
            record_service=self.record_service,
        )

    def tearDown(self) -> None:
        self.svc._store.close()
        self.cost_store._conn.close()
        try:
            self.svc._bom.store._conn.close()
        except Exception:
            pass
        if os.path.exists(self._db_path):
            try:
                os.unlink(self._db_path)
            except OSError:
                pass

    def _seed_bom(self, **kwargs) -> None:
        seed_bom(self.record_service, **kwargs)

    def test_create_and_list(self) -> None:
        self._seed_bom(
            customer_name="测试客户A",
            product_name="壳体 Φ50",
            product_part_no="CPN-001",
        )
        line = self.svc.create_line(
            {
                "customer": "测试客户A",
                "order_date": "2026-05-30",
                "delivery_date": "2026-06-20",
                "order_no": "PO-TEST-001",
                "product_spec": "壳体 Φ50",
                "customer_part_no": "CPN-001",
                "unit_weight_g": "120",
                "material": "ADC12",
                "po_qty": "100",
                "shipped_qty": "0",
                "unit": "PCS",
                "tax_rate": "0.13",
                "rmb_tax_incl_price": "2.50",
                "payment_terms": "月结30天",
            }
        )
        self.assertEqual(line.id, 1)
        self.assertIsNotNone(line.created_at)
        self.assertEqual(line.open_qty(), Decimal("100"))
        self.assertEqual(line.amount(), Decimal("250.00"))

        rows = self.svc.list_lines()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].product_spec, "壳体 Φ50")

    def test_create_line_with_bom_missing_customer_name(self) -> None:
        """BOM 未填客户时仍应能按料号匹配，不能误报「未建档」。"""
        import json

        self.cost_store.insert(
            {
                "customer_name": "",
                "product_name": "前挡板",
                "mold_no": "M-TEST",
                "product_part_no": "PL9-12580-10-0A",
                "cavity": "1*1",
                "unit_weight_g": "120",
                "material": "ADC12",
                "machine_tonnage": "280T",
                "material_unit_price": "0.02",
                "process_prices_json": json.dumps({"01": "1.0"}, ensure_ascii=False),
                "material_cost": "1.0",
                "process_total": "1.0",
                "unit_cost": "2.0",
                "quote_price": "0",
            }
        )
        line = self.svc.create_line(
            {
                "customer": "东莞市凯泰智联科技有限公司",
                "order_date": "2026-04-29",
                "delivery_date": "2026-05-08",
                "order_no": "P02026",
                "product_spec": "前挡板",
                "customer_part_no": "PL9-12580-10-0A",
                "unit_weight_g": "0",
                "material": "ADC12",
                "po_qty": "15000",
                "shipped_qty": "0",
                "unit": "个",
                "tax_rate": "0.13",
                "rmb_tax_incl_price": "4",
            }
        )
        self.assertEqual(line.customer_part_no, "PL9-12580-10-0A")

    def test_create_line_rejects_bom_part_with_extra_suffix(self) -> None:
        from test_impl.order_management.cost_analysis.bom_service import BomNotFoundError

        self._seed_bom(
            customer_name="东莞市凯泰智联科技有限公司",
            product_name="前挡板",
            product_part_no="PL9-12580-10-0A-前挡板",
        )
        with self.assertRaises(BomNotFoundError):
            self.svc.create_line(
                {
                    "customer": "东莞市凯泰智联科技有限公司",
                    "order_date": "2026-04-29",
                    "delivery_date": "2026-05-08",
                    "order_no": "P02026",
                    "product_spec": "前挡板",
                    "customer_part_no": "PL9-12580-10-0A",
                    "unit_weight_g": "0",
                    "material": "ADC12",
                    "po_qty": "15000",
                    "shipped_qty": "0",
                    "unit": "个",
                    "tax_rate": "0.13",
                    "rmb_tax_incl_price": "4",
                }
            )

    def test_create_line_bom_part_no_unicode_dash(self) -> None:
        self._seed_bom(
            customer_name="东莞市凯泰智联科技有限公司",
            product_name="前挡板",
            product_part_no="PL9-12580-10-0A",
        )
        line = self.svc.create_line(
            {
                "customer": "东莞市凯泰智联科技有限公司",
                "order_date": "2026-04-29",
                "delivery_date": "2026-05-08",
                "order_no": "P02026",
                "product_spec": "前挡板",
                "customer_part_no": "PL9\u201112580\u201110\u20110A",
                "unit_weight_g": "120",
                "material": "ADC12",
                "po_qty": "100",
                "shipped_qty": "0",
                "unit": "个",
                "tax_rate": "0.13",
                "rmb_tax_incl_price": "4",
            }
        )
        self.assertEqual(line.customer_part_no, "PL9\u201112580\u201110\u20110A")

    def test_duplicate_line_rejected(self) -> None:
        base = {
            "customer": "怡利",
            "order_date": "2026-05-26",
            "order_no": "PO-DUP-001",
            "product_spec": "测试品名A",
            "po_qty": "1500",
            "rmb_tax_incl_price": "9.04",
        }
        first = self.svc.create_line(base)
        with self.assertRaises(DuplicateLineError) as ctx:
            self.svc.create_line({**base, "order_date": "2026-05-28"})
        self.assertEqual(ctx.exception.line_id, first.id)
        self.assertEqual(len(self.svc.list_lines()), 1)

    def test_unit_weight_text_waigou(self) -> None:
        line = self.svc.create_line(
            {
                "customer": "测试客户",
                "order_date": "2026-01-01",
                "order_no": "PO-W",
                "product_spec": "零件",
                "po_qty": "10",
                "unit_weight_g": "外购件",
            }
        )
        self.assertEqual(line.unit_weight_g, "外购件")

    def test_tax_rate_percent_input(self) -> None:
        self._seed_bom(
            customer_name="客户B",
            product_name="端盖",
            product_part_no="C-X",
        )
        line = self.svc.create_line(
            {
                "customer": "客户B",
                "order_date": "2026-05-30",
                "order_no": "PO-002",
                "product_spec": "端盖",
                "customer_part_no": "C-X",
                "po_qty": "50",
                "tax_rate": "13%",
                "rmb_tax_incl_price": "2.5678",
            }
        )
        self.assertEqual(line.tax_rate, Decimal("0.13"))
        self.assertEqual(line.rmb_tax_incl_price, Decimal("2.5678"))

    def test_lookup_customer_part(self) -> None:
        self._seed_bom(
            customer_name="测试",
            product_name="冷热传导盖 AC",
            product_part_no="B601000137C",
        )
        cp = self.svc.lookup_customer_part("冷热传导盖 AC")
        self.assertEqual(cp, "B601000137C")

    def test_add_customer_and_part(self) -> None:
        self.svc.add_customer("新客户X")
        master = self.svc.list_master()["customers"]
        self.assertIn("新客户X", master)

    def test_persist_sqlite_file(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            svc1 = OrderLineService(db_path=path)
            svc1.create_line(
                {
                    "customer": "持久化客户",
                    "order_date": "2026-05-30",
                    "order_no": "PO-DB",
                    "product_spec": "件X",
                    "po_qty": "1",
                }
            )
            svc1._store.close()
            svc1._bom.store._conn.close()
            svc2 = OrderLineService(db_path=path)
            self.assertEqual(len(svc2.list_lines()), 1)
            self.assertEqual(svc2.list_lines()[0].customer, "持久化客户")
            svc2._store.close()
            svc2._bom.store._conn.close()
        finally:
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass

    def test_list_master_includes_customers_from_lines(self) -> None:
        self.svc.create_line(
            {
                "customer": "锐霸",
                "order_date": "2026-05-30",
                "order_no": "PO-RB",
                "product_spec": "零件A",
                "po_qty": "10",
            }
        )
        self.assertIn("锐霸", self.svc.list_master()["customers"])
        self.svc.add_part("新品名", "NEW-CPN")
        self._seed_bom(customer_name="锐霸", product_name="新品名", product_part_no="NEW-CPN")
        self.assertEqual(self.svc.lookup_customer_part("新品名"), "NEW-CPN")

    def test_enrich_recognized_lines_keeps_payment_terms(self) -> None:
        self.svc.add_customer("浙江红黑科技有限公司")
        self._seed_bom(
            customer_name="浙江红黑科技有限公司",
            product_name="冷热传导盖 AC",
            product_part_no="B601000137C",
        )
        lines = self.svc.enrich_recognized_lines(
            [
                {
                    "customer": "浙江红黑",
                    "payment_terms": "T/T Monthly settlement 90 days",
                    "product_spec": "冷热传导盖 AC",
                    "customer_part_no": "",
                }
            ]
        )
        self.assertEqual(lines[0]["customer"], "浙江红黑科技有限公司")
        self.assertEqual(lines[0]["payment_terms"], "T/T Monthly settlement 90 days")
        self.assertEqual(lines[0]["customer_part_no"], "B601000137C")

    def test_enrich_recognized_bom_customer_mismatch_flag(self) -> None:
        self._seed_bom(
            customer_name="苏州大沃工具科技有限公司",
            product_name="演示件",
            product_part_no="DW-001",
        )
        lines = self.svc.enrich_recognized_lines(
            [
                {
                    "customer": "大沃",
                    "customer_part_no": "DW-001",
                    "product_spec": "演示件",
                    "po_qty": "10",
                }
            ]
        )
        self.assertTrue(lines[0].get("_customer_bom_mismatch"))
        self.assertEqual(lines[0]["_bom_customer_name"], "苏州大沃工具科技有限公司")
        self.assertEqual(lines[0]["customer"], "大沃")

    def test_auto_fill_customer_part(self) -> None:
        self._seed_bom(
            customer_name="浙江红黑科技有限公司",
            product_name="冷热传导盖 AC",
            product_part_no="B601000137C",
        )
        line = self.svc.create_line(
            {
                "customer": "浙江红黑科技有限公司",
                "order_date": "2026-05-30",
                "order_no": "PO-AUTO",
                "product_spec": "冷热传导盖 AC",
                "customer_part_no": "",
                "po_qty": "10",
                "rmb_tax_incl_price": "1",
            }
        )
        self.assertEqual(line.customer_part_no, "B601000137C")

    def test_list_lines_views(self) -> None:
        self.svc.create_line(
            {
                "customer": "V客户", "order_date": "2026-05-30", "order_no": "PO-V1",
                "product_spec": "开", "po_qty": "100", "shipped_qty": "30",
            }
        )
        self.svc.create_line(
            {
                "customer": "V客户", "order_date": "2026-05-30", "order_no": "PO-V2",
                "product_spec": "结", "po_qty": "50", "shipped_qty": "50",
            }
        )
        self.svc.create_line(
            {
                "customer": "V客户", "order_date": "2026-05-30", "order_no": "PO-V3",
                "product_spec": "零未结未出", "po_qty": "80", "shipped_qty": "0",
            }
        )
        self.assertEqual(len(self.svc.list_lines(view="all")), 3)
        self.assertEqual(len(self.svc.list_shipment_events()), 0)
        open_rows = self.svc.list_lines(view="open")
        closed_rows = self.svc.list_lines(view="closed")
        self.assertEqual(len(open_rows), 2)
        self.assertEqual(len(closed_rows), 1)
        self.assertEqual(closed_rows[0].product_spec, "结")
        self.assertTrue(all(ln.open_qty() > 0 for ln in open_rows))
        self.assertTrue(all(ln.open_qty() <= 0 for ln in closed_rows))

    def test_search_filter(self) -> None:
        self._seed_bom(customer_name="Alpha", product_name="件A", product_part_no="CA1")
        self._seed_bom(customer_name="Beta", product_name="件B", product_part_no="CB1")
        self.svc.create_line(
            {
                "customer": "Alpha", "order_date": "2026-05-30", "order_no": "PO-S1",
                "product_spec": "件A", "customer_part_no": "CA1", "po_qty": "1",
            }
        )
        self.svc.create_line(
            {
                "customer": "Beta", "order_date": "2026-05-29", "order_no": "PO-S2",
                "product_spec": "件B", "customer_part_no": "CB1", "po_qty": "2",
            }
        )
        self.assertEqual(len(self.svc.list_lines(customer="Alpha")), 1)
        self.assertEqual(len(self.svc.list_lines(q="PO-S2")), 1)

    def test_ship_line_partial_and_close(self) -> None:
        line = self.svc.create_line(
            {
                "customer": "出货测",
                "order_date": "2026-05-30",
                "order_no": "PO-SHIP",
                "product_spec": "件S",
                "po_qty": "500",
                "shipped_qty": "0",
            }
        )
        mid, ev1 = self.svc.ship_line(line.id, "300")
        self.assertEqual(mid.shipped_qty, Decimal("300"))
        self.assertEqual(mid.open_qty(), Decimal("200"))
        self.assertEqual(ev1.ship_qty, Decimal("300"))
        self.assertEqual(len(self.svc.list_lines(view="open")), 1)
        done, ev2 = self.svc.ship_line(line.id, "200")
        self.assertEqual(done.open_qty(), Decimal("0"))
        self.assertEqual(ev2.ship_qty, Decimal("200"))
        self.assertEqual(len(self.svc.list_lines(view="open")), 0)
        self.assertEqual(len(self.svc.list_lines(view="closed")), 1)
        events = self.svc.list_shipment_events()
        self.assertEqual(len(events), 2)
        self.assertEqual(sum(e.ship_qty for e in events), Decimal("500"))

    def test_force_close_line(self) -> None:
        line = self.svc.create_line(
            {
                "customer": "强制结案测",
                "order_date": "2026-05-30",
                "order_no": "PO-FC",
                "product_spec": "件F",
                "po_qty": "100",
                "shipped_qty": "20",
            }
        )
        forced = self.svc.force_close_line(line.id)
        self.assertEqual(forced.closure_type, "forced")
        self.assertEqual(forced.open_qty(), Decimal("80"))
        self.assertEqual(len(self.svc.list_lines(view="open")), 0)
        self.assertEqual(len(self.svc.list_lines(view="closed")), 0)
        forced_rows = self.svc.list_lines(view="closed_forced")
        self.assertEqual(len(forced_rows), 1)
        self.assertEqual(forced_rows[0].id, line.id)
        self.assertEqual(len(self.svc.list_shipment_events()), 0)

    def test_reverse_shipment_event_returns_to_open(self) -> None:
        line = self.svc.create_line(
            {
                "customer": "返回测",
                "order_date": "2026-05-30",
                "order_no": "PO-RET",
                "product_spec": "件R",
                "po_qty": "1300",
                "shipped_qty": "0",
            }
        )
        mid, ev = self.svc.ship_line(line.id, "1049")
        self.assertEqual(mid.open_qty(), Decimal("251"))
        self.assertEqual(len(self.svc.list_lines(view="open")), 1)
        self.assertEqual(len(self.svc.list_shipment_events()), 1)

        restored, removed_id = self.svc.reverse_shipment_event(ev.id)
        self.assertEqual(removed_id, ev.id)
        self.assertEqual(restored.shipped_qty, Decimal("0"))
        self.assertEqual(restored.open_qty(), Decimal("1300"))
        self.assertEqual(len(self.svc.list_shipment_events()), 0)
        self.assertEqual(len(self.svc.list_lines(view="open")), 1)

    def test_reverse_shipment_import_source(self) -> None:
        line = self.svc.create_line(
            {
                "customer": "导入测",
                "order_date": "2026-05-30",
                "order_no": "PO-IMP",
                "product_spec": "件I",
                "po_qty": "10",
                "shipped_qty": "5",
            }
        )
        ev = self.svc._store.insert_shipment_event(line.id, "5", source="import")
        restored, removed_id = self.svc.reverse_shipment_event(ev.id)
        self.assertEqual(removed_id, ev.id)
        self.assertEqual(restored.shipped_qty, Decimal("0"))
        self.assertEqual(len(self.svc.list_shipment_events()), 0)

    def test_ship_line_with_duplicate_sibling_rows(self) -> None:
        """库中存在同客户·订单号·品名重复行时，出货仍应成功。"""
        self._seed_bom(customer_name="重复测", product_name="同料号", product_part_no="A1")
        self._seed_bom(customer_name="重复测", product_name="同料号", product_part_no="A2")
        base = {
            "customer": "重复测",
            "order_date": "2026-05-30",
            "order_no": "PO-DUP-SHIP",
            "product_spec": "同料号",
            "po_qty": "100",
            "shipped_qty": "0",
        }
        a = self.svc.create_line({**base, "customer_part_no": "A1"})
        dup_fields = normalize_line_fields(
            self.svc.enrich_line_dict(
                {**OrderLineService._line_to_dict(a), "customer_part_no": "A2"}
            )
        )
        b = self.svc._store.insert_line(dup_fields)
        self.assertNotEqual(a.id, b.id)
        shipped, ev = self.svc.ship_line(a.id, "40")
        self.assertEqual(shipped.shipped_qty, Decimal("40"))
        self.assertEqual(ev.ship_qty, Decimal("40"))
        self.assertEqual(shipped.open_qty(), Decimal("60"))
        self.assertEqual(b.shipped_qty, Decimal("0"))
        self.assertEqual(len(self.svc.list_shipment_events()), 1)

    def test_ship_line_over_open_rejected(self) -> None:
        line = self.svc.create_line(
            {
                "customer": "出货测",
                "order_date": "2026-05-30",
                "order_no": "PO-SHIP2",
                "product_spec": "件S2",
                "po_qty": "100",
                "shipped_qty": "0",
            }
        )
        with self.assertRaises(ValueError):
            self.svc.ship_line(line.id, "101")

    def test_created_at_preserved_on_update(self) -> None:
        line = self.svc.create_line(
            {
                "customer": "客户C",
                "order_date": "2026-05-30",
                "order_no": "PO-TIME",
                "product_spec": "零件T",
                "po_qty": "10",
            }
        )
        created = line.created_at
        updated = self.svc.update_line(
            line.id,
            {"customer": "客户C", "order_no": "PO-TIME", "product_spec": "零件T", "po_qty": "20"},
        )
        self.assertEqual(updated.created_at, created)
        self.assertGreaterEqual(updated.updated_at, created)

    def test_update_and_delete(self) -> None:
        self._seed_bom(customer_name="U客户", product_name="件U", product_part_no="UC1")
        line = self.svc.create_line(
            {
                "customer": "U客户", "order_date": "2026-05-30", "order_no": "PO-U",
                "product_spec": "件U", "customer_part_no": "UC1", "po_qty": "5",
                "rmb_tax_incl_price": "3",
            }
        )
        updated = self.svc.update_line(line.id, {"po_qty": "10"})
        self.assertEqual(updated.po_qty, Decimal("10"))
        self.assertEqual(updated.open_qty(), Decimal("10"))
        self.svc.delete_line(line.id)
        with self.assertRaises(ValueError):
            self.svc.get_line(line.id)
        self.assertEqual(self.svc.count_lines(), 0)

    def test_sqlite_id_increments_after_delete(self) -> None:
        self._seed_bom(customer_name="U客户", product_name="件U", product_part_no="UC1")
        line = self.svc.create_line(
            {
                "customer": "U客户", "order_date": "2026-05-30", "order_no": "PO-U",
                "product_spec": "件U", "customer_part_no": "UC1", "po_qty": "5",
                "rmb_tax_incl_price": "3",
            }
        )
        self.svc.delete_line(line.id)
        again = self.svc.create_line(
            {
                "customer": "U客户", "order_date": "2026-05-30", "order_no": "PO-U2",
                "product_spec": "件U", "customer_part_no": "UC1", "po_qty": "1",
            }
        )
        self.assertEqual(again.id, line.id + 1)


class TestIntakeToLines(unittest.TestCase):
    def test_multi_items_flatten_attachment2_fields(self) -> None:
        recognition = {
            "orders": [
                {
                    "customer": "浙江红黑",
                    "order_date": "2026-05-11",
                    "delivery_date": "2026-06-12",
                    "order_no": "PO1",
                    "payment_terms": "月结60天",
                    "items": [
                        {
                            "product_spec": "壳体", "customer_part_no": "B601",
                            "unit_weight_g": "120", "material": "ADC12",
                            "po_qty": "982", "shipped_qty": "0", "unit": "PCS",
                            "tax_rate": "0.13", "rmb_tax_incl_price": "2.50",
                        },
                        {
                            "product_spec": "端盖", "customer_part_no": "B603",
                            "po_qty": "500", "rmb_tax_incl_price": "1.80",
                        },
                    ],
                }
            ]
        }
        lines = intake_to_lines(recognition)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["product_spec"], "壳体")
        self.assertEqual(lines[0]["customer_part_no"], "B601")
        self.assertEqual(lines[0]["material"], "ADC12")
        self.assertEqual(lines[0]["payment_terms"], "月结60天")
        self.assertEqual(lines[1]["order_no"], "PO1")


if __name__ == "__main__":
    unittest.main()
