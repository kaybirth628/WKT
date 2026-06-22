import unittest
from datetime import date

from test_impl.order_management.reconciliation.payment_schedule import (
    compute_payment_due_date,
    payment_due_month_label,
)
from test_impl.order_management.reconciliation.service import _merge_lines


class TestPaymentSchedule(unittest.TestCase):
    def test_jan_shipment_may_25(self) -> None:
        due = compute_payment_due_date(date(2026, 1, 15), payment_day=25, term_days=90)
        self.assertEqual(due, date(2026, 5, 25))

    def test_jan_end_shipment(self) -> None:
        due = compute_payment_due_date(date(2026, 1, 31), payment_day=25, term_days=90)
        self.assertEqual(due, date(2026, 5, 25))

    def test_due_month_label(self) -> None:
        self.assertEqual(payment_due_month_label(date(2026, 5, 25)), "2026-05")


class TestReconciliationMerge(unittest.TestCase):
    def test_merge_same_key_sums_qty_and_amount(self) -> None:
        base = {
            "customer": "A",
            "shipped_at": "2026-06-01T10:00:00",
            "order_no": "PO1",
            "customer_part_no": "P-1",
            "rmb_tax_incl_price": "10.0000",
            "delivery_doc_no": "DN001",
            "receivable_date": "2026-10-25",
            "collection_time": "2026-10",
            "ship_month": "2026-06",
        }
        rows = [
            {**base, "id": 1, "ship_qty": "1.0", "amount": "10.00"},
            {**base, "id": 2, "ship_qty": "2.0", "amount": "20.00"},
        ]
        merged = _merge_lines(rows)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["ship_qty"], "3")
        self.assertEqual(merged[0]["amount"], "30")
        self.assertEqual(merged[0]["merge_count"], 2)

    def test_different_ship_time_stays_separate(self) -> None:
        base = {
            "customer": "A",
            "order_no": "PO1",
            "customer_part_no": "P-1",
            "rmb_tax_incl_price": "10.0000",
            "delivery_doc_no": "DN001",
            "receivable_date": "2026-10-25",
            "collection_time": "2026-10",
            "ship_month": "2026-06",
            "ship_qty": "1.0",
            "amount": "10.00",
        }
        rows = [
            {**base, "id": 1, "shipped_at": "2026-06-01T10:00:00"},
            {**base, "id": 2, "shipped_at": "2026-06-01T11:00:00"},
        ]
        self.assertEqual(len(_merge_lines(rows)), 2)


if __name__ == "__main__":
    unittest.main()
