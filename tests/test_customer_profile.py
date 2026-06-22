import tempfile
import unittest
from pathlib import Path

from test_impl.order_management.customer_profile import store
from test_impl.order_management.customer_profile.delivery_sync import (
    format_receiver_contact,
    sync_delivery_from_profile,
)
from test_impl.order_management.delivery_note import wkt_document


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
                "reconciliation_cycle": "月结60天·每月25日对账",
            },
        )
        self.assertEqual(row["contact"], "李四")
        loaded = store.get_profile("测试客户")
        self.assertEqual(loaded["reconciliation_cycle"], "月结60天·每月25日对账")

    def test_format_receiver_contact(self) -> None:
        self.assertEqual(
            format_receiver_contact({"contact": "张三", "phone": "13800138000"}),
            "张三 13800138000",
        )
        self.assertEqual(format_receiver_contact({"contact": "张三", "phone": ""}), "张三")

    def test_sync_delivery_only_if_empty(self) -> None:
        store.save_profile(
            "测试客户",
            {"address": "公司地址", "contact": "王五", "phone": "111"},
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
            {"address": "新档案地址", "contact": "王五", "phone": "111"},
        )
        sync_delivery_from_profile("测试客户", only_if_empty=True)
        raw = wkt_document.get_raw_customer_delivery_info("测试客户")
        self.assertEqual(raw["receiver_address"], "手工送货地址")


if __name__ == "__main__":
    unittest.main()
