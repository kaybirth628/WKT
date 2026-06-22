import unittest
from decimal import Decimal

from test_impl.order_management.delivery_note.wkt_document import (
    build_sample_document,
    document_to_dict,
    save_customer_delivery_info,
    _gen_doc_no,
)
from datetime import datetime, timezone


class TestWktDeliveryDocument(unittest.TestCase):
    def test_sample_document_dict(self) -> None:
        doc = build_sample_document("测试客")
        d = document_to_dict(doc)
        self.assertEqual(d["title_company"], "测试客")
        self.assertIn("年", d["ship_date_cn"])
        self.assertEqual(len(d["lines"]), 1)

    def test_doc_no_with_prefix(self) -> None:
        dt = datetime(2025, 11, 22, tzinfo=timezone.utc)
        self.assertEqual(_gen_doc_no("ABL", dt, 12), "ABL202511220012")

    def test_doc_no_draft_suffix(self) -> None:
        dt = datetime(2025, 11, 22, tzinfo=timezone.utc)
        self.assertTrue(_gen_doc_no("WKT", dt, 0).endswith("01"))


if __name__ == "__main__":
    unittest.main()
