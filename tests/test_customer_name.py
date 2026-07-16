import unittest

from test_impl.order_management.customer_name import (
    customer_names_match,
    dedupe_customer_names,
    normalize_customer_name,
    pick_canonical_customer_name,
)
from test_impl.order_management.order_entry import DuplicatePartNoError, OrderLineService


class TestCustomerNameNormalization(unittest.TestCase):
    def test_parenthesis_variants_match(self) -> None:
        full = "怡利电子科技（江苏）有限公司"
        half = "怡利电子科技(江苏)有限公司"
        self.assertTrue(customer_names_match(full, half))
        self.assertEqual(normalize_customer_name(full), normalize_customer_name(half))

    def test_dedupe_prefers_profile_canonical(self) -> None:
        names = dedupe_customer_names(
            [
                "怡利电子科技(江苏)有限公司",
                "怡利电子科技（江苏）有限公司",
            ]
        )
        self.assertEqual(names, ["怡利电子科技（江苏）有限公司"])

    def test_pick_canonical_customer_name(self) -> None:
        canonical = pick_canonical_customer_name(
            ["怡利", "怡利电子科技(江苏)有限公司", "怡利电子科技（江苏）有限公司"]
        )
        self.assertEqual(canonical, "怡利电子科技（江苏）有限公司")


class TestPartNoWithCustomerAlias(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = OrderLineService(db_path=":memory:")

    def test_same_customer_halfwidth_parenthesis_allowed(self) -> None:
        self.svc.create_line(
            {
                "customer": "怡利电子科技（江苏）有限公司",
                "order_date": "2026-07-01",
                "order_no": "PO-OLD",
                "product_spec": "1A321W2C001-0A铝挤型 散热片",
                "customer_part_no": "1A321W2C001-0A",
                "po_qty": "10",
            }
        )
        line = self.svc.create_line(
            {
                "customer": "怡利电子科技(江苏)有限公司",
                "order_date": "2026-07-16",
                "order_no": "PO-NEW",
                "product_spec": "1A321W2C001-0A铝挤型 散热片",
                "customer_part_no": "1A321W2C001-0A",
                "po_qty": "5",
            }
        )
        self.assertEqual(line.customer, "怡利电子科技（江苏）有限公司")

    def test_short_customer_alias_allowed(self) -> None:
        self.svc.create_line(
            {
                "customer": "怡利电子科技（江苏）有限公司",
                "order_date": "2026-07-01",
                "order_no": "PO-OLD",
                "product_spec": "散热片",
                "customer_part_no": "CP-YILI-001",
                "po_qty": "10",
            }
        )
        line = self.svc.create_line(
            {
                "customer": "怡利",
                "order_date": "2026-07-16",
                "order_no": "PO-NEW",
                "product_spec": "散热片2",
                "customer_part_no": "CP-YILI-001",
                "po_qty": "5",
            }
        )
        self.assertEqual(line.customer, "怡利电子科技（江苏）有限公司")

    def test_different_customer_same_part_still_rejected(self) -> None:
        self.svc.create_line(
            {
                "customer": "怡利电子科技（江苏）有限公司",
                "order_date": "2026-07-01",
                "order_no": "PO-OLD",
                "product_spec": "散热片",
                "customer_part_no": "CP-YILI-002",
                "po_qty": "10",
            }
        )
        with self.assertRaises(DuplicatePartNoError):
            self.svc.create_line(
                {
                    "customer": "其他客户",
                    "order_date": "2026-07-16",
                    "order_no": "PO-NEW",
                    "product_spec": "其他品名",
                    "customer_part_no": "CP-YILI-002",
                    "po_qty": "5",
                }
            )


if __name__ == "__main__":
    unittest.main()
