import tempfile
import unittest
from pathlib import Path

from test_impl.order_management.customer_profile import store
from test_impl.order_management.customer_profile.delivery_sync import (
    format_receiver_contact,
    sync_delivery_from_profile,
)
from test_impl.order_management.customer_profile.service import CustomerProfileService
from test_impl.order_management.delivery_note import wkt_document
from test_impl.order_management.order_entry import OrderLineService


class TestCustomerProfileStore(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "customer_profiles.json"
        self.delivery_path = Path(self.tmp.name) / "customer_delivery.json"
        self._orig = store.PROFILES_FILE
        self._orig_delivery = wkt_document._CUSTOMER_FILE
        store.PROFILES_FILE = self.path
        wkt_document._CUSTOMER_FILE = self.delivery_path

    def tearDown(self) -> None:
        store.PROFILES_FILE = self._orig
        wkt_document._CUSTOMER_FILE = self._orig_delivery
        self.tmp.cleanup()

    def test_save_and_load(self) -> None:
        row = store.save_profile(
            "测试客户",
            {
                "address": "地址A",
                "contact": "李四",
                "phone": "0512-12345678",
                "email": "a@b.com",
                "payment_terms": "月结60天",
                "reconciliation_period": "month_21_20",
            },
        )
        self.assertEqual(row["contact"], "李四")
        self.assertTrue(str(row.get("created_at") or "").strip())
        loaded = store.get_profile("测试客户")
        self.assertEqual(loaded["reconciliation_period"], "month_21_20")

    def test_sort_names_by_created_at(self) -> None:
        store.save_profile(
            "客户B",
            {"address": "B", "reconciliation_period": "month_21_20", "created_at": "2026-07-02T10:00:00+00:00"},
        )
        store.save_profile(
            "客户A",
            {"address": "A", "reconciliation_period": "month_21_20", "created_at": "2026-07-01T10:00:00+00:00"},
        )
        self.assertEqual(store.sort_names_by_created_at(["客户B", "客户A"]), ["客户B", "客户A"])

    def test_delete_profile(self) -> None:
        store.save_profile(
            "测试客户",
            {
                "address": "地址A",
                "reconciliation_period": "month_21_20",
            },
        )
        store.delete_profile("测试客户")
        with self.assertRaises(ValueError):
            store.delete_profile("测试客户")

    def test_save_requires_reconciliation_period_on_create(self) -> None:
        with self.assertRaises(ValueError):
            store.save_profile("测试客户", {"address": "地址A"})

    def test_save_allows_empty_period_on_update(self) -> None:
        store.save_profile(
            "测试客户",
            {
                "address": "地址A",
                "reconciliation_period": "month_21_20",
                "delivery_enabled": "1",
            },
        )
        row = store.save_profile(
            "测试客户",
            {
                "address": "地址B",
                "reconciliation_period": "",
                "delivery_enabled": "1",
            },
        )
        self.assertEqual(row["address"], "地址B")
        self.assertEqual(row["reconciliation_period"], "")

    def test_delivery_enabled_default(self) -> None:
        self.assertTrue(store.is_delivery_enabled({}))
        self.assertTrue(store.is_delivery_enabled({"delivery_enabled": "1"}))
        self.assertFalse(store.is_delivery_enabled({"delivery_enabled": "0"}))

    def test_save_with_delivery_disabled_skips_sync(self) -> None:
        store.save_profile(
            "无送货单客户",
            {
                "address": "地址",
                "contact": "张三",
                "delivery_enabled": "0",
                "reconciliation_period": "month_21_20",
            },
        )
        sync_delivery_from_profile("无送货单客户", only_if_empty=True)
        raw = wkt_document.get_raw_customer_delivery_info("无送货单客户")
        self.assertEqual(raw, {})

    def test_format_receiver_contact(self) -> None:
        self.assertEqual(
            format_receiver_contact({"contact": "张三", "phone": "13800138000"}),
            "张三 13800138000",
        )
        self.assertEqual(format_receiver_contact({"contact": "张三", "phone": ""}), "张三")

    def test_sync_delivery_only_if_empty(self) -> None:
        store.save_profile(
            "测试客户",
            {
                "address": "公司地址",
                "contact": "王五",
                "phone": "111",
                "reconciliation_period": "calendar_month",
            },
        )
        sync_delivery_from_profile("测试客户", only_if_empty=True)
        info = wkt_document.get_customer_delivery_info("测试客户")
        self.assertEqual(info["receiver_address"], "公司地址")
        self.assertEqual(info["receiver_contact"], "王五")
        self.assertEqual(info["receiver_phone"], "111")

        wkt_document.save_customer_delivery_info(
            "测试客户",
            {
                "receiver_company": "测试客户",
                "receiver_address": "手工送货地址",
                "receiver_contact": "收货人",
                "doc_no_prefix": "",
            },
        )
        store.save_profile(
            "测试客户",
            {
                "address": "新档案地址",
                "contact": "王五",
                "phone": "111",
                "reconciliation_period": "calendar_month",
            },
        )
        sync_delivery_from_profile("测试客户", only_if_empty=True)
        raw = wkt_document.get_raw_customer_delivery_info("测试客户")
        self.assertEqual(raw["receiver_address"], "手工送货地址")


class TestCustomerProfileService(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "customer_profiles.json"
        self.delivery_path = Path(self.tmp.name) / "customer_delivery.json"
        self._orig = store.PROFILES_FILE
        self._orig_delivery = wkt_document._CUSTOMER_FILE
        store.PROFILES_FILE = self.path
        wkt_document._CUSTOMER_FILE = self.delivery_path
        self.lines = OrderLineService(db_path=":memory:")
        self.svc = CustomerProfileService(self.lines)

    def tearDown(self) -> None:
        store.PROFILES_FILE = self._orig
        wkt_document._CUSTOMER_FILE = self._orig_delivery
        self.tmp.cleanup()

    def test_create_customer_registers_master(self) -> None:
        row = self.svc.create(
            "新客户A",
            {
                "address": "苏州",
                "contact": "李四",
                "delivery_enabled": "1",
                "reconciliation_period": "month_21_20",
            },
        )
        self.assertEqual(row["address"], "苏州")
        names = self.lines.list_master().get("customers") or []
        self.assertIn("新客户A", names)

    def test_create_duplicate_raises(self) -> None:
        self.svc.create("重复客", {"reconciliation_period": "month_21_20"})
        with self.assertRaises(ValueError):
            self.svc.create("重复客", {"reconciliation_period": "month_21_20"})

    def test_delete_customer_without_orders(self) -> None:
        self.svc.create(
            "待删客户",
            {
                "address": "苏州",
                "reconciliation_period": "month_21_20",
            },
        )
        self.svc.delete("待删客户")
        names = self.lines.list_master().get("customers") or []
        self.assertNotIn("待删客户", names)
        self.assertEqual(store.get_profile("待删客户"), store.EMPTY_PROFILE)

    def test_delete_customer_with_orders_blocked(self) -> None:
        self.svc.create("有单客户", {"reconciliation_period": "month_21_20"})
        self.lines.create_line(
            {
                "customer": "有单客户",
                "order_date": "2026-01-01",
                "order_no": "PO-1",
                "product_spec": "测试品",
                "po_qty": "10",
            }
        )
        with self.assertRaisesRegex(ValueError, "已有订单"):
            self.svc.delete("有单客户")

    def test_delete_delivery_only_customer(self) -> None:
        wkt_document.save_customer_delivery_info(
            "仅送货单客户",
            {
                "receiver_company": "仅送货单客户",
                "receiver_address": "苏州",
                "receiver_contact": "李四",
                "doc_no_prefix": "",
            },
        )
        self.svc.delete("仅送货单客户")
        self.assertEqual(wkt_document.get_raw_customer_delivery_info("仅送货单客户"), {})
        self.assertEqual(store.get_profile("仅送货单客户"), store.EMPTY_PROFILE)


if __name__ == "__main__":
    unittest.main()
