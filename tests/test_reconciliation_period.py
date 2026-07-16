import unittest
from datetime import date

from test_impl.order_management.reconciliation.period import (
    CALENDAR_MONTH,
    MONTH_16_15,
    MONTH_21_20,
    MONTH_22_21,
    MONTH_26_25,
    normalize_reconciliation_period,
    reconciliation_period_for_ship_date,
    reconciliation_period_label,
)


class TestReconciliationPeriod(unittest.TestCase):
    def test_normalize_valid(self) -> None:
        self.assertEqual(normalize_reconciliation_period("calendar_month"), CALENDAR_MONTH)
        self.assertEqual(normalize_reconciliation_period("month_21_20"), MONTH_21_20)
        self.assertEqual(normalize_reconciliation_period("month_26_25"), MONTH_26_25)
        self.assertEqual(normalize_reconciliation_period("month_22_21"), MONTH_22_21)
        self.assertEqual(normalize_reconciliation_period("month_16_15"), MONTH_16_15)

    def test_normalize_legacy_text(self) -> None:
        self.assertEqual(normalize_reconciliation_period("自然月"), CALENDAR_MONTH)
        self.assertEqual(normalize_reconciliation_period("上月26号-本月25号"), MONTH_26_25)
        self.assertEqual(normalize_reconciliation_period("上月22号-本月21号"), MONTH_22_21)
        self.assertEqual(normalize_reconciliation_period("上月16号-本月15号"), MONTH_16_15)
        self.assertEqual(normalize_reconciliation_period("月结90天"), "")
        self.assertEqual(normalize_reconciliation_period(""), "")

    def test_period_label(self) -> None:
        self.assertIn("自然月", reconciliation_period_label(CALENDAR_MONTH))
        self.assertIn("26日", reconciliation_period_label(MONTH_26_25))
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

    def test_period_for_ship_date_26_25(self) -> None:
        self.assertEqual(
            reconciliation_period_for_ship_date(date(2025, 1, 30), MONTH_26_25),
            "2025-02",
        )
        self.assertEqual(
            reconciliation_period_for_ship_date(date(2025, 2, 10), MONTH_26_25),
            "2025-02",
        )
        self.assertEqual(
            reconciliation_period_for_ship_date(date(2025, 2, 26), MONTH_26_25),
            "2025-03",
        )

    def test_period_for_ship_date_22_21(self) -> None:
        self.assertEqual(
            reconciliation_period_for_ship_date(date(2025, 1, 25), MONTH_22_21),
            "2025-02",
        )
        self.assertEqual(
            reconciliation_period_for_ship_date(date(2025, 2, 15), MONTH_22_21),
            "2025-02",
        )

    def test_period_for_ship_date_16_15(self) -> None:
        self.assertEqual(
            reconciliation_period_for_ship_date(date(2025, 1, 10), MONTH_16_15),
            "2025-01",
        )
        self.assertEqual(
            reconciliation_period_for_ship_date(date(2025, 1, 20), MONTH_16_15),
            "2025-02",
        )
        self.assertEqual(
            reconciliation_period_for_ship_date(date(2025, 2, 10), MONTH_16_15),
            "2025-02",
        )
        self.assertEqual(
            reconciliation_period_for_ship_date(date(2025, 2, 20), MONTH_16_15),
            "2025-03",
        )


if __name__ == "__main__":
    unittest.main()
