import unittest

from test_impl.order_management.order_intake.field_validation import validate_lines


class TestFieldValidation(unittest.TestCase):
    def _sample_line(self, **overrides) -> dict:
        base = {
            "customer": "甲公司",
            "order_no": "PO1",
            "order_date": "2026-05-30",
            "delivery_date": "",
            "product_spec": "散热片/8513 ADC12（外观喷黑色漆）/Φ42.5X16",
            "po_qty": "100",
            "customer_part_no": "B6030000533",
            "unit_weight_g": "120",
            "rmb_tax_incl_price": "2.5",
            "payment_terms": "",
        }
        base.update(overrides)
        return base

    def test_all_ok(self) -> None:
        line = self._sample_line()
        raw = "B6030000533 散热片 PO数量 100"
        merged, summary = validate_lines([line], ocr_scheme="PDF 文字层", raw_text=raw)
        self.assertEqual(merged[0]["_validate"]["status"], "ok")
        self.assertEqual(summary["ok_rows"], 1)
        self.assertEqual(summary["warn_fields"], 0)

    def test_empty_part_no_warns(self) -> None:
        line = self._sample_line(customer_part_no="")
        merged, summary = validate_lines([line], ocr_scheme="RapidOCR")
        self.assertEqual(merged[0]["_validate"]["fields"]["customer_part_no"]["status"], "warn")
        self.assertGreater(summary["warn_fields"], 0)

    def test_spec_fragment_part_no_warns(self) -> None:
        line = self._sample_line(customer_part_no="8513")
        merged, summary = validate_lines([line], ocr_scheme="RapidOCR")
        fv = merged[0]["_validate"]["fields"]["customer_part_no"]
        self.assertEqual(fv["status"], "warn")
        self.assertIn("短编号", fv["message"])

    def test_part_no_not_in_raw_text_warns(self) -> None:
        line = self._sample_line(customer_part_no="B6010001370")
        merged, _ = validate_lines([line], ocr_scheme="RapidOCR", raw_text="无关文字")
        self.assertEqual(merged[0]["_validate"]["fields"]["customer_part_no"]["status"], "warn")

    def test_invalid_po_qty(self) -> None:
        line = self._sample_line(po_qty="0")
        merged, _ = validate_lines([line], ocr_scheme="RapidOCR")
        self.assertEqual(merged[0]["_validate"]["fields"]["po_qty"]["status"], "warn")


if __name__ == "__main__":
    unittest.main()
