import unittest
from datetime import date

from test_impl.order_management.reconciliation.period import (
    CALENDAR_MONTH,
    MONTH_21_20,
    normalize_reconciliation_period,
    reconciliation_period_for_ship_date,
    reconciliation_period_label,
)


class TestReconciliationPeriod(unittest.TestCase):
    def test_normalize_valid(self) -> None:
        self.assertEqual(normalize_reconciliation_period("calendar_month"), CALENDAR_MONTH)
        self.assertEqual(normalize_reconciliation_period("month_21_20"), MONTH_21_20)

    def test_normalize_legacy_text_keeps_empty(self) -> None:
        self.assertEqual(normalize_reconciliation_period("月结90天"), "")
        self.assertEqual(normalize_reconciliation_period(""), "")

    def test_period_label(self) -> None:
        self.assertIn("自然月", reconciliation_period_label(CALENDAR_MONTH))
        self.assertEqual(reconciliation_period_label(""), "未设置")

    def test_period_for_ship_date_calendar(self) -> None:
        self.assertEqual(
            reconciliation_period_for_ship_date(date(2025, 3, 15), CALENDAR_MONTH),
            "2025-03",
        )

    def test_period_for_ship_date_21_20(self) -> None:
        self.assertEqual(
            reconciliation_period_for_ship_date(date(2025, 1, 25), MONTH_21_20),
            "2025-02",
        )
        self.assertEqual(
            reconciliation_period_for_ship_date(date(2025, 2, 10), MONTH_21_20),
            "2025-02",
        )


if __name__ == "__main__":
    unittest.main()
