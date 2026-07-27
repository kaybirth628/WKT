import os
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from test_impl.order_management.cost_analysis import CostRecordService
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.inventory.store import InventoryStore
from test_impl.order_management.order_entry.line_store import LineStore
from test_impl.order_management.reconciliation.payable_service import PayableService
from datetime import date

from test_impl.order_management.reconciliation.month_util import rolling_due_months
from test_impl.order_management.reconciliation.payment_schedule import (
    compute_payable_date,
    parse_supplier_payment_terms,
)

from bom_helpers import seed_bom

_SUPPLIER = "苏州麦凯良金属制品厂"
_PART = "PAY-DEMO-01"


class TestPayableSchedule(unittest.TestCase):
    def test_rolling_due_months_six_from_july(self) -> None:
        months = rolling_due_months(6, from_date=date(2026, 7, 23))
        self.assertEqual(months, ["2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12"])

    def test_parse_supplier_terms(self) -> None:
        self.assertEqual(parse_supplier_payment_terms("90天")["term_days"], 90)
        self.assertTrue(parse_supplier_payment_terms("现结")["is_cash"])

    def test_payable_date_cash(self) -> None:
        self.assertEqual(
            compute_payable_date(date(2026, 7, 10), "现结"),
            date(2026, 7, 10),
        )

    def test_payable_date_90_days(self) -> None:
        # 2026-04-01 + 90 = 2026-06-30 → 已过6月25日，顺延7月25日
        due = compute_payable_date(date(2026, 4, 1), "90天", payment_day=25)
        self.assertEqual(due, date(2026, 7, 25))


class TestPayableService(unittest.TestCase):
    def setUp(self) -> None:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self._db_path = path
        self.cost_store = CostStore(path)
        self.records = CostRecordService(store=self.cost_store, line_store=LineStore(path))
        self.inv_store = InventoryStore(path)
        self.payable = PayableService(
            inventory_store=self.inv_store,
            cost_store=self.cost_store,
            record_service=self.records,
        )
        self.supplier_patcher = patch(
            "test_impl.order_management.reconciliation.payable_service.get_profile",
            return_value={
                "payment_terms": "90天",
                "reconciliation_period": "calendar_month",
            },
        )
        self.supplier_patcher.start()
        seed_bom(
            self.records,
            customer_name="演示客户",
            product_name="应付演示品",
            product_part_no=_PART,
            mold_no="WKT-MJ-DEMO",
            unit_weight_g="100",
            process_prices={
                "01": "1.0",
                "02": {"price": "2.5", "supplier": _SUPPLIER},
            },
        )
        now = "2026-07-15T08:00:00+00:00"
        self.inv_store._conn.execute(
            """
            INSERT INTO inventory_movements (
                product_part_no, action_type, process_code,
                from_process_code, from_status, from_supplier,
                to_process_code, to_status, to_supplier,
                qty, doc_no, note, created_at
            ) VALUES (?, 'outsource_receive', '02', '02', 'outsource', ?, '02', 'inhouse', '', '40', 'RK-20260715-001', '测试回货', ?)
            """,
            (_PART, _SUPPLIER, now),
        )
        self.inv_store._conn.commit()

    def tearDown(self) -> None:
        self.supplier_patcher.stop()
        self.inv_store.close()
        self.cost_store._conn.close()
        if os.path.exists(self._db_path):
            try:
                os.unlink(self._db_path)
            except OSError:
                pass

    def test_list_lines_amount(self) -> None:
        lines = self.payable.list_lines(supplier=_SUPPLIER)
        self.assertEqual(len(lines), 1)
        row = lines[0]
        self.assertEqual(row["product_part_no"], _PART)
        self.assertEqual(row["qty"], "40")
        self.assertEqual(row["unit_price"], "2.5")
        self.assertEqual(row["amount"], "100")
        self.assertEqual(row["settlement_month"], "2026-07")
        self.assertFalse(row["price_missing"])

    def test_summarize_by_supplier_month(self) -> None:
        rows = self.payable.summarize_by_supplier_month()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["supplier"], _SUPPLIER)
        self.assertEqual(rows[0]["total_amount"], "100")

    def test_receive_date_filter(self) -> None:
        self.assertEqual(len(self.payable.list_lines(receive_from="2026-07-01")), 1)
        self.assertEqual(len(self.payable.list_lines(receive_from="2026-08-01")), 0)


    def test_payable_due_bucket_by_month(self) -> None:
        bucket = self.payable._payable_due_bucket("2026-10")
        self.assertEqual(len(bucket["rows"]), 1)
        self.assertEqual(bucket["rows"][0]["supplier"], _SUPPLIER)
        self.assertEqual(bucket["rows"][0]["total_amount"], "100")

    def test_due_outlook_returns_six_months(self) -> None:
        outlook = self.payable.due_outlook(month_count=6)
        self.assertEqual(len(outlook["months"]), 6)
        self.assertEqual(outlook["month_count"], 6)


if __name__ == "__main__":
    unittest.main()
