import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from test_impl.integrations.ai_memory import (
    append_business_rule,
    format_memory_for_prompt,
    load_memory,
    memory_file_path,
    save_memory,
)


class TestAiMemory(unittest.TestCase):
    def test_append_and_format(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mem.json"
            with mock.patch("test_impl.integrations.ai_memory.MEMORY_FILE", path):
                with mock.patch(
                    "test_impl.integrations.ai_memory.memory_file_path", return_value=path
                ):
                    data = append_business_rule("威可特=本公司主要客户简称")
                    self.assertIn("威可特=本公司主要客户简称", data["business_rules"])
                    text = format_memory_for_prompt(data)
                    self.assertIn("威可特=本公司主要客户简称", text)
                    self.assertTrue(path.exists())

    def test_save_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mem.json"
            with mock.patch(
                "test_impl.integrations.ai_memory.memory_file_path", return_value=path
            ):
                save_memory(
                    {
                        "business_rules": ["规则A"],
                        "glossary": {"出货": "shipped_at"},
                        "custom_prompt": "测试",
                    }
                )
                raw = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(raw["business_rules"], ["规则A"])
                loaded = load_memory()
                self.assertEqual(loaded["glossary"]["出货"], "shipped_at")


if __name__ == "__main__":
    unittest.main()
