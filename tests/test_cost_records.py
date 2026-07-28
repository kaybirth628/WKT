import unittest
from decimal import Decimal
from unittest.mock import patch

from test_impl.order_management.cost_analysis import CostRecordService
from test_impl.order_management.cost_analysis.models import PROCESS_ORDER_KEY
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.order_entry.line_store import LineStore

_TEST_SUPPLIER = "测试CNC厂"


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
        "process_prices": {
            "01": "1.5",
            "13": {"price": "3.2", "supplier": _TEST_SUPPLIER},
        },
    }
    base.update(overrides)
    return base


class TestCostRecordService(unittest.TestCase):
    def setUp(self) -> None:
        self.line_store = LineStore(db_path=":memory:")
        self._store = CostStore(db_path=":memory:")
        self.service = CostRecordService(store=self._store, line_store=self.line_store)
        self.supplier_patcher = patch(
            "test_impl.order_management.cost_analysis.record_service.list_profile_suppliers",
            return_value=[_TEST_SUPPLIER],
        )
        self.supplier_patcher.start()

    def tearDown(self) -> None:
        self.supplier_patcher.stop()
        self.line_store.close()
        self._store._conn.close()

    def test_create_and_get_record(self) -> None:
        record = self.service.create_record(_sample_payload())
        self.assertEqual(record.customer_name, "凯泰")
        self.assertEqual(record.product_part_no, "PL9-01050-00-0A")
        codes = {k for k in record.process_prices.keys() if k != PROCESS_ORDER_KEY}
        self.assertEqual(codes, {"01", "13"})
        self.assertEqual(Decimal(record.material_cost), Decimal("1.7600"))
        self.assertEqual(Decimal(record.process_total), Decimal("4.7000"))
        self.assertEqual(Decimal(record.unit_cost), Decimal("6.4600"))

        fetched = self.service.get_record(record.id)
        self.assertEqual(fetched.id, record.id)

        data = self.service.record_to_dict(fetched)
        self.assertEqual(set(data["selected_processes"]), {"压铸", "CNC"})
        self.assertEqual(data["selected_process_codes"], ["01", "13"])
        self.assertEqual(data["process_selections"][0]["code"], "01")
        self.assertEqual(data["process_selections"][0]["inhouse"], True)
        self.assertEqual(data["process_selections"][1]["supplier"], _TEST_SUPPLIER)

    def test_list_records_filter(self) -> None:
        self.service.create_record(_sample_payload())
        self.service.create_record(
            _sample_payload(
                customer_name="其他客户",
                product_name="其他产品",
                product_part_no="OTHER-001",
                process_prices={"22": {"price": "2", "supplier": _TEST_SUPPLIER}},
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

    def test_list_records_ordered_by_updated_at(self) -> None:
        first = self.service.create_record(_sample_payload(product_part_no="PART-A"))
        second = self.service.create_record(
            _sample_payload(
                customer_name="其他客户",
                product_name="其他产品",
                product_part_no="PART-B",
                process_prices={"22": {"price": "2", "supplier": _TEST_SUPPLIER}},
            )
        )
        updated = self.service.update_record(
            first.id,
            _sample_payload(product_part_no="PART-A", product_name="前挡板（已覆盖）"),
        )
        rows = self.service.list_records()
        self.assertEqual(rows[0].id, updated.id)
        self.assertEqual(rows[1].id, second.id)

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

    def test_reject_outsource_without_supplier(self) -> None:
        payload = _sample_payload(process_prices={"01": "1.5", "13": "3.2"})
        with self.assertRaisesRegex(ValueError, "请选择供应商"):
            self.service.create_record(payload)

    def test_reject_unknown_supplier(self) -> None:
        payload = _sample_payload(
            process_prices={"13": {"price": "3.2", "supplier": "不存在的供应商"}}
        )
        with self.assertRaisesRegex(ValueError, "不在供应商列表"):
            self.service.create_record(payload)

    def test_accept_inhouse_supplier_label(self) -> None:
        record = self.service.create_record(
            _sample_payload(
                process_prices={
                    "01": "1.5",
                    "28": {"price": "2.0", "supplier": "场内自制"},
                },
            )
        )
        data = self.service.record_to_dict(record)
        sel = next(s for s in data["process_selections"] if s["code"] == "28")
        self.assertEqual(sel["supplier"], "场内自制")
        self.assertTrue(sel["inhouse"])

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
                process_prices={
                    "01": "2.0",
                    "13": {"price": "4.0", "supplier": _TEST_SUPPLIER},
                },
            ),
        )
        self.assertEqual(updated.product_name, "更新产品")
        self.assertEqual(updated.unit_weight_g, "99")
        data = self.service.record_to_dict(updated)
        self.assertEqual(data["process_prices"]["01"], "2.0")
        self.assertEqual(Decimal(updated.unit_cost), Decimal("7.9800"))

    def test_delete_record(self) -> None:
        record = self.service.create_record(_sample_payload())
        self.service.delete_record(record.id)
        with self.assertRaisesRegex(ValueError, "不存在"):
            self.service.get_record(record.id)

    def test_reject_wrong_customer_for_part(self) -> None:
        self.service.create_record(_sample_payload(customer_name="凯泰"))
        with self.assertRaisesRegex(ValueError, "已绑定客户"):
            self.service.create_record(_sample_payload(customer_name="其他客户"))

    def test_legacy_process_alias_maps_to_die_cast(self) -> None:
        record = self.service.create_record(_sample_payload(process_prices={"埋轴": "1.0"}))
        data = self.service.record_to_dict(record)
        self.assertEqual(data["selected_process_codes"], ["01"])
        self.assertEqual(data["selected_processes"], ["压铸"])

    def test_process_suppliers_via_separate_field(self) -> None:
        record = self.service.create_record(
            _sample_payload(
                process_prices={"01": "1.5", "13": "3.2"},
                process_suppliers={"13": _TEST_SUPPLIER},
            )
        )
        data = self.service.record_to_dict(record)
        self.assertEqual(data["process_selections"][1]["supplier"], _TEST_SUPPLIER)

    def test_custom_process_order_persisted(self) -> None:
        record = self.service.create_record(
            _sample_payload(
                process_prices={
                    "01": "1.5",
                    "13": {"price": "3.2", "supplier": _TEST_SUPPLIER},
                },
                process_order=["13", "01"],
            )
        )
        data = self.service.record_to_dict(record)
        self.assertEqual(data["process_order"], ["13", "01"])
        self.assertEqual([s["code"] for s in data["process_selections"]], ["13", "01"])
        self.assertEqual(record.process_prices.get(PROCESS_ORDER_KEY), ["13", "01"])

        updated = self.service.update_record(
            record.id,
            _sample_payload(
                process_prices={
                    "01": "1.5",
                    "13": {"price": "3.2", "supplier": _TEST_SUPPLIER},
                },
                process_order=["01", "13"],
            ),
        )
        updated_data = self.service.record_to_dict(updated)
        self.assertEqual(updated_data["process_order"], ["01", "13"])


if __name__ == "__main__":
    unittest.main()
