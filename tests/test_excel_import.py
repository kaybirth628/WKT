import io
import unittest
from decimal import Decimal

from openpyxl import Workbook

from test_impl.order_management.order_entry.excel_import import (
    build_template_bytes,
    map_headers,
    parse_excel_bytes,
    summarize_results,
    validate_import_row,
)


class TestExcelImport(unittest.TestCase):
    def test_map_headers(self) -> None:
        mapping, unknown = map_headers(
            ["客户", "订单号", "PO数量", "已出货", "未结数量", "人民币单价（含税）", "金额"]
        )
        self.assertIn(0, mapping)
        self.assertEqual(mapping[0], "customer")
        self.assertEqual(mapping[3], "shipped_qty")
        self.assertFalse(unknown)

    def test_blocked_list_in_summary(self) -> None:
        raw = {
            "customer": "A",
            "order_no": "PO1",
            "product_spec": "X",
            "po_qty": "100",
            "shipped_qty": "20",
            "_excel_open_qty": "50",
            "rmb_tax_incl_price": "1",
        }
        from test_impl.order_management.order_entry.excel_import import summarize_results

        r = validate_import_row(raw, row_no=5)
        summary = summarize_results([r])
        self.assertEqual(summary["blocked"], 1)
        self.assertEqual(len(summary["blocked_list"]), 1)
        self.assertEqual(summary["blocked_list"][0]["row_no"], 5)

    def test_review_status_tiers(self) -> None:
        from test_impl.order_management.order_entry.excel_import import (
            ImportIssue,
            ImportRowResult,
            summarize_results,
        )

        passed = ImportRowResult(row_no=1, data={"customer": "A"})
        pending = ImportRowResult(row_no=2, data={"customer": "B"})
        pending.issues.append(ImportIssue("tax_rate", "warn", "税率按0"))
        blocked = ImportRowResult(row_no=3, data={"customer": "C"})
        blocked.issues.append(ImportIssue("row", "error", "PO数量必须大于 0"))
        summary = summarize_results([passed, pending, blocked])
        self.assertEqual(summary["passed"], 1)
        self.assertEqual(summary["pending"], 1)
        self.assertEqual(summary["blocked"], 1)
        self.assertIn("阻断", summary["blocked_report"])

    def test_build_blocked_report(self) -> None:
        from test_impl.order_management.order_entry.excel_import import build_blocked_report

        text = build_blocked_report(
            [{"row_no": 5, "customer": "X", "order_no": "P", "product_spec": "Y", "errors": ["已出货超范围"]}]
        )
        self.assertIn("第 5 行", text)
        self.assertIn("已出货超范围", text)

    def test_unit_weight_text_passthrough(self) -> None:
        raw = {
            "customer": "A",
            "order_no": "PO1",
            "product_spec": "X",
            "po_qty": "100",
            "shipped_qty": "0",
            "unit_weight_g": "外购件",
            "rmb_tax_incl_price": "1",
        }
        r = validate_import_row(raw, row_no=71)
        self.assertTrue(r.importable)
        self.assertEqual(r.data["unit_weight_g"], "外购件")

    def test_numeric_field_error_names_column(self) -> None:
        raw = {
            "customer": "A",
            "order_no": "PO1",
            "product_spec": "X",
            "po_qty": "一千",
            "shipped_qty": "0",
            "rmb_tax_incl_price": "1",
        }
        r = validate_import_row(raw, row_no=71)
        self.assertFalse(r.importable)
        msg = " ".join(i.message for i in r.issues)
        self.assertIn("PO数量", msg)
        self.assertNotIn("ConversionSyntax", msg)

    def test_humanize_decimal_error(self) -> None:
        from test_impl.order_management.order_entry.excel_import import _humanize_error_message

        msg = _humanize_error_message("[<class 'decimal.ConversionSyntax'>]")
        self.assertIn("PO数量", msg)
        self.assertNotIn("class 'dec", msg)

    def test_payment_terms_text_from_excel(self) -> None:
        raw = {
            "customer": "A",
            "order_no": "PO1",
            "product_spec": "X",
            "po_qty": "100",
            "shipped_qty": "0",
            "payment_terms": "开票当月不算，从次月起月结60天",
            "tax_rate": "13%",
            "rmb_tax_incl_price": "1",
        }
        r = validate_import_row(raw, row_no=3)
        self.assertTrue(r.importable)
        self.assertEqual(r.data["payment_terms"], "开票当月不算，从次月起月结60天")

    def test_payment_terms_moved_from_tax_column(self) -> None:
        raw = {
            "customer": "A",
            "order_no": "PO1",
            "product_spec": "X",
            "po_qty": "100",
            "shipped_qty": "0",
            "tax_rate": "开票当月不算",
            "rmb_tax_incl_price": "1",
        }
        r = validate_import_row(raw, row_no=3)
        self.assertTrue(r.importable)
        self.assertEqual(r.data["payment_terms"], "开票当月不算")
        msg = " ".join(i.message for i in r.issues)
        self.assertNotIn("ConversionSyntax", msg)
        self.assertNotIn("class 'dec", msg)

    def test_validate_amount_mismatch(self) -> None:
        raw = {
            "customer": "A",
            "order_no": "PO1",
            "product_spec": "X",
            "po_qty": "100",
            "shipped_qty": "20",
            "_excel_open_qty": "80",
            "rmb_tax_incl_price": "2.5",
            "_excel_amount": "999",
        }
        r = validate_import_row(raw, row_no=2)
        self.assertFalse(r.importable)
        self.assertTrue(any(i.field == "amount" for i in r.issues))

    def test_validate_open_qty_ok(self) -> None:
        raw = {
            "customer": "A",
            "order_no": "PO1",
            "product_spec": "X",
            "po_qty": "100",
            "shipped_qty": "30",
            "_excel_open_qty": "70",
            "rmb_tax_incl_price": "10",
            "_excel_amount": "1000",
        }
        r = validate_import_row(raw, row_no=2)
        self.assertTrue(r.importable)
        self.assertEqual(r.calc_amount, "1000.00")

    def test_parse_xlsx_roundtrip(self) -> None:
        wb = Workbook()
        ws = wb.active
        ws.append(
            [
                "客户",
                "接单日期",
                "订单号",
                "品名规格",
                "PO数量",
                "已出货",
                "未结数量",
                "人民币单价（含税）",
                "金额",
            ]
        )
        ws.append(
            ["测试客户", "2026-01-01", "PO-99", "零件A", 500, 100, 400, 3.2, 1600]
        )
        buf = io.BytesIO()
        wb.save(buf)
        rows, _unknown = parse_excel_bytes(buf.getvalue(), "t.xlsx")
        summary = summarize_results(rows)
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["passed"], 1)
        self.assertEqual(summary["blocked"], 0)
        self.assertEqual(len(summary["blocked_list"]), 0)

    def test_template_bytes(self) -> None:
        data = build_template_bytes()
        self.assertGreater(len(data), 100)
        rows, _unknown = parse_excel_bytes(data, "template.xlsx")
        self.assertGreaterEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
