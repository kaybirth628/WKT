import tempfile
import unittest
from pathlib import Path

from test_impl.order_management.customer_profile import store


class TestCustomerProfileStore(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "customer_profiles.json"
        self._orig = store.PROFILES_FILE
        store.PROFILES_FILE = self.path

    def tearDown(self) -> None:
        store.PROFILES_FILE = self._orig
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
        self.assertEqual(row["address"], "地址A")
        loaded = store.get_profile("测试客户")
        self.assertEqual(loaded["contact"], "李四")
        self.assertEqual(loaded["reconciliation_cycle"], "月结60天·每月25日对账")


if __name__ == "__main__":
    unittest.main()
