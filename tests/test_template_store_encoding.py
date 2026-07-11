import json
import tempfile
import unittest
from pathlib import Path

from test_impl.order_management.delivery_note.template_store import DeliveryTemplateStore


class TestTemplateStoreEncoding(unittest.TestCase):
    def test_load_mapping_repairs_mojibake(self) -> None:
        good = "送货单预览_上海金脉电子科技有限公司.xlsx"
        bad = good.encode("utf-8").decode("latin-1")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = DeliveryTemplateStore(root=root)
            store.mapping_file.write_text(
                json.dumps({"上海金脉": bad}, ensure_ascii=False),
                encoding="utf-8",
            )
            mapping = store.load_mapping()
            self.assertEqual(mapping["上海金脉"], good)
            saved = json.loads(store.mapping_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["上海金脉"], good)


if __name__ == "__main__":
    unittest.main()
