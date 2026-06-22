import tempfile
import unittest
from pathlib import Path

from test_impl.integrations.db_assistant import (
    DatabaseAssistantError,
    build_data_context,
    build_schema_description,
    execute_readonly_query,
    validate_readonly_sql,
)
from test_impl.order_management.order_entry.line_store import LineStore


class TestDbAssistantSecurity(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db_path = Path(self._tmp.name)
        self.store = LineStore(self.db_path)
        self.store.upsert_customer("测试客户")
        self.store.insert_line(
            {
                "customer": "测试客户",
                "order_no": "PO-001",
                "product_spec": "散热片/A001",
                "po_qty": "100",
                "shipped_qty": "10",
            }
        )
        self.db_path = Path(self.store.db_path)

    def tearDown(self) -> None:
        self.store.close()
        try:
            Path(self.store.db_path).unlink(missing_ok=True)
        except OSError:
            pass

    def test_validate_blocks_mutations(self) -> None:
        for sql in (
            "DELETE FROM order_lines",
            "UPDATE order_lines SET customer='x'",
            "INSERT INTO order_lines (customer) VALUES ('x')",
        ):
            with self.assertRaises(DatabaseAssistantError):
                validate_readonly_sql(sql)

    def test_validate_allows_select(self) -> None:
        sql = validate_readonly_sql("SELECT customer, order_no FROM order_lines")
        self.assertIn("order_lines", sql)

    def test_execute_readonly_query(self) -> None:
        cols, rows, truncated = execute_readonly_query(
            self.db_path,
            "SELECT customer, order_no FROM order_lines",
        )
        self.assertEqual(cols, ["customer", "order_no"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["customer"], "测试客户")
        self.assertFalse(truncated)

    def test_schema_description(self) -> None:
        text = build_schema_description(self.db_path)
        self.assertIn("order_lines", text)
        self.assertIn("shipment_events", text)

    def test_data_context_includes_counts(self) -> None:
        text = build_data_context(self.db_path)
        self.assertIn("订单行总数", text)
        self.assertIn("出货", text)


if __name__ == "__main__":
    unittest.main()
