import unittest
from decimal import Decimal

from test_impl.order_management.cost_analysis import CostRecordService
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.order_entry.line_store import LineStore


def _sample_payload(**overrides):
    base = {
        "customer_name": "凯泰",
        "product_name": "PL9-01050-00-0A-前挡板",
        "mold_no": "WKT-MJ-LV-24027",
        "product_part_no": "PL9-01050-00-0A",
        "cavity": "1*2",
        "unit_weight_g": "88",
        "material": "ADC12",
        "machine_tonnage": "280T",
        "material_unit_price": "0.02",
        "process_prices": {"01": "1.5", "13": "3.2"},
    }
    base.update(overrides)
    return base


class TestCostRecordService(unittest.TestCase):
    def setUp(self) -> None:
        self.line_store = LineStore(db_path=":memory:")
        self._store = CostStore(db_path=":memory:")
        self.service = CostRecordService(store=self._store, line_store=self.line_store)

    def tearDown(self) -> None:
        self.line_store.close()
        self._store._conn.close()

    def test_create_and_get_record(self) -> None:
        record = self.service.create_record(_sample_payload())
        self.assertEqual(record.customer_name, "凯泰")
        self.assertEqual(record.product_part_no, "PL9-01050-00-0A")
        self.assertEqual(set(record.process_prices.keys()), {"01", "13"})
        self.assertEqual(Decimal(record.material_cost), Decimal("1.7600"))
        self.assertEqual(Decimal(record.process_total), Decimal("4.7000"))
        self.assertEqual(Decimal(record.unit_cost), Decimal("6.4600"))

        fetched = self.service.get_record(record.id)
        self.assertEqual(fetched.id, record.id)

        data = self.service.record_to_dict(fetched)
        self.assertEqual(set(data["selected_processes"]), {"压铸", "CNC"})
        self.assertEqual(data["selected_process_codes"], ["01", "13"])
        self.assertEqual(data["process_selections"][0]["code"], "01")

    def test_list_records_filter(self) -> None:
        self.service.create_record(_sample_payload())
        self.service.create_record(
            _sample_payload(
                customer_name="其他客户",
                product_name="其他产品",
                product_part_no="OTHER-001",
                process_prices={"22": "2"},
            )
        )

        all_rows = self.service.list_records()
        self.assertEqual(len(all_rows), 2)

        by_customer = self.service.list_records(customer="凯泰")
        self.assertEqual(len(by_customer), 1)

        by_part = self.service.list_records(product_part_no="OTHER")
        self.assertEqual(len(by_part), 1)

        by_q = self.service.list_records(q="前挡板")
        self.assertEqual(len(by_q), 1)

    def test_reject_missing_basic_field(self) -> None:
        payload = _sample_payload(customer_name="")
        with self.assertRaisesRegex(ValueError, "客户名称"):
            self.service.create_record(payload)

    def test_reject_no_process(self) -> None:
        payload = _sample_payload(process_prices={})
        with self.assertRaisesRegex(ValueError, "至少选择"):
            self.service.create_record(payload)

    def test_reject_unknown_process(self) -> None:
        payload = _sample_payload(process_prices={"不存在的工艺": "1"})
        with self.assertRaisesRegex(ValueError, "未知工艺"):
            self.service.create_record(payload)

    def test_custom_material_allowed(self) -> None:
        record = self.service.create_record(_sample_payload(material="自定义合金"))
        self.assertEqual(record.material, "自定义合金")

    def test_update_record(self) -> None:
        record = self.service.create_record(_sample_payload())
        updated = self.service.update_record(
            record.id,
            _sample_payload(
                product_name="更新产品",
                unit_weight_g="99",
                process_prices={"01": "2.0", "13": "4.0"},
            ),
        )
        self.assertEqual(updated.product_name, "更新产品")
        self.assertEqual(updated.unit_weight_g, "99")
        self.assertEqual(updated.process_prices["01"], "2.0")
        self.assertEqual(Decimal(updated.unit_cost), Decimal("7.9800"))

    def test_delete_record(self) -> None:
        record = self.service.create_record(_sample_payload())
        self.service.delete_record(record.id)
        with self.assertRaisesRegex(ValueError, "不存在"):
            self.service.get_record(record.id)

    def test_reject_wrong_customer_for_part(self) -> None:
        self.line_store._conn.execute(
            """
            INSERT INTO order_lines (
                customer, order_date, delivery_date, order_no, product_spec,
                customer_part_no, unit_weight_g, material, po_qty, shipped_qty,
                unit, tax_rate, rmb_tax_incl_price, payment_terms, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "凯泰", "2026-01-01", "", "PO-1", "前挡板", "PL9-01050-00-0A",
                "88", "ADC12", "10", "0", "PCS", "0.13", "10", "月结", "", "2026-01-01",
            ),
        )
        self.line_store._conn.commit()
        with self.assertRaisesRegex(ValueError, "已绑定客户"):
            self.service.create_record(_sample_payload(customer_name="其他客户"))

    def test_legacy_process_alias_maps_to_die_cast(self) -> None:
        record = self.service.create_record(_sample_payload(process_prices={"埋轴": "1.0"}))
        self.assertEqual(record.process_prices, {"01": "1.0"})
        data = self.service.record_to_dict(record)
        self.assertEqual(data["selected_process_codes"], ["01"])
        self.assertEqual(data["selected_processes"], ["压铸"])


if __name__ == "__main__":
    unittest.main()
