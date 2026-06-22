import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from test_impl.order_management.delivery_note import DeliveryNoteService, DeliveryTemplateStore
from test_impl.order_management.order_entry import OrderLineService

try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None  # type: ignore


class TestDeliveryNote(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tpl_root = Path(self.tmp.name) / "delivery_templates"
        self.svc = OrderLineService(db_path=":memory:")
        self.templates = DeliveryTemplateStore(self.tpl_root)
        self.dn = DeliveryNoteService(self.svc, self.templates)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_builtin_context_after_ship(self) -> None:
        line = self.svc.create_line(
            {
                "customer": "怡利",
                "order_date": "2026-05-26",
                "order_no": "PO-DN-1",
                "product_spec": "散热片",
                "po_qty": "100",
                "shipped_qty": "0",
                "unit": "PCS",
            }
        )
        _, ev = self.svc.ship_line(line.id, "40")
        ctx = self.dn.build_context(ev)
        self.assertEqual(ctx["客户"], "怡利")
        self.assertIn(ctx["本次出货"], ("40", "40.0"))
        self.assertEqual(ctx["订单号"], "PO-DN-1")

    def test_wkt_standard_xlsx_after_ship(self) -> None:
        if Workbook is None:
            self.skipTest("openpyxl not installed")
        line = self.svc.create_line(
            {
                "customer": "爱毕黎",
                "order_no": "PO-1",
                "product_spec": "双嘴钳",
                "customer_part_no": "P-001",
                "material": "钢",
                "po_qty": "100",
                "unit": "pcs",
            }
        )
        _, ev = self.svc.ship_line(line.id, "51")
        doc = self.dn.build_wkt_document(ev.id)
        self.assertEqual(doc.title_company, "爱毕黎")
        self.assertEqual(doc.lines[0].qty, "51")
        self.assertIn("威可特", doc.supplier_name)
        kind, payload = self.dn.render_for_event(ev.id)
        self.assertEqual(kind, "xlsx")
        data, _fname = payload
        self.assertTrue(len(data) > 500)
        import io

        from openpyxl import load_workbook

        wb2 = load_workbook(io.BytesIO(data))
        self.assertEqual(wb2.active["A1"].value, "爱毕黎")
        self.assertEqual(wb2.active["A2"].value, "送货单")

    def test_custom_excel_template_for_mapped_customer(self) -> None:
        if Workbook is None:
            self.skipTest("openpyxl not installed")
        files_dir = self.tpl_root / "files"
        files_dir.mkdir(parents=True, exist_ok=True)
        tpl_name = "专用客.xlsx"
        wb = Workbook()
        ws = wb.active
        ws["A1"] = "{{客户}}"
        ws["A2"] = "{{订单号}}"
        ws["A3"] = "{{本次出货}}"
        wb.save(files_dir / tpl_name)
        self.templates.set_customer_template("专用客", tpl_name)

        line = self.svc.create_line(
            {
                "customer": "专用客",
                "order_no": "PO-S",
                "product_spec": "测试件",
                "po_qty": "10",
                "unit": "PCS",
            }
        )
        _, ev = self.svc.ship_line(line.id, "3")
        kind, payload = self.dn.render_for_event(ev.id)
        self.assertEqual(kind, "xlsx")
        data, _fname = payload
        from openpyxl import load_workbook
        import io

        wb2 = load_workbook(io.BytesIO(data))
        self.assertEqual(wb2.active["A1"].value, "专用客")
        self.assertEqual(wb2.active["A2"].value, "PO-S")

    def test_default_wkt_for_unmapped_customer(self) -> None:
        meta = self.dn.template_info("普通客户")
        self.assertTrue(meta["is_wkt_standard"])

    def test_ship_with_delivery_note_snapshot(self) -> None:
        import json

        line = self.svc.create_line(
            {
                "customer": "确认客",
                "order_no": "PO-C",
                "product_spec": "垫片",
                "po_qty": "50",
                "unit": "pcs",
            }
        )
        note = {
            "receiver_company": "确认客有限公司",
            "receiver_address": "测试地址",
            "lines": [{"qty": "10", "batch_no": "B001", "product_name": "垫片"}],
            "warehouse_manager": "张三",
        }
        _, ev = self.svc.ship_line(line.id, "10", delivery_note=note)
        raw = self.svc._store.get_shipment_delivery_note_json(ev.id)
        snap = json.loads(raw)
        self.assertEqual(snap["receiver_address"], "测试地址")
        self.assertEqual(snap["lines"][0]["batch_no"], "B001")
        doc = self.dn.build_wkt_document(ev.id)
        self.assertEqual(doc.warehouse_manager, "张三")


if __name__ == "__main__":
    unittest.main()
