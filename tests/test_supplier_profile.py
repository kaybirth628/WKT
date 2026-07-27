import tempfile
import unittest
from pathlib import Path

from test_impl.order_management.supplier_profile import store
from test_impl.order_management.supplier_profile.service import SupplierProfileService


class TestSupplierProfileStore(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "supplier_profiles.json"
        self._orig = store.PROFILES_FILE
        store.PROFILES_FILE = self.path

    def tearDown(self) -> None:
        store.PROFILES_FILE = self._orig
        self.tmp.cleanup()

    def test_save_and_load(self) -> None:
        row = store.save_profile(
            "测试供应商",
            {
                "address": "地址A",
                "contact": "李四",
                "phone": "0512-12345678",
                "email": "a@b.com",
                "payment_terms": "月结60天",
                "notes": "主要供压铸",
            },
        )
        self.assertEqual(row["contact"], "李四")
        loaded = store.get_profile("测试供应商")
        self.assertEqual(loaded["notes"], "主要供压铸")

    def test_create_duplicate(self) -> None:
        svc = SupplierProfileService()
        store.save_profile("供应商A", {"address": "地址"})
        with self.assertRaises(ValueError):
            svc.create("供应商a", {})

    def test_list_sorted_by_created_at(self) -> None:
        store.save_profile("供应商B", {"address": "B", "created_at": "2026-07-02T10:00:00+00:00"})
        store.save_profile("供应商A", {"address": "A", "created_at": "2026-07-01T10:00:00+00:00"})
        svc = SupplierProfileService()
        names = [r["supplier"] for r in svc.list_rows()]
        self.assertEqual(names[:2], ["供应商B", "供应商A"])

    def test_create_sets_created_at(self) -> None:
        svc = SupplierProfileService()
        row = svc.create("新供应商", {"address": "地址"})
        self.assertTrue(str(row.get("created_at") or "").strip())

    def test_delete_supplier(self) -> None:
        svc = SupplierProfileService()
        svc.create("待删供应商", {"address": "地址A"})
        svc.delete("待删供应商")
        with self.assertRaises(ValueError):
            svc.delete("待删供应商")
        self.assertEqual(store.get_profile("待删供应商"), store.EMPTY_PROFILE)


if __name__ == "__main__":
    unittest.main()
