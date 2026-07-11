import unittest

from test_impl.common.filename_encoding import normalize_upload_filename, repair_utf8_mojibake


class TestFilenameEncoding(unittest.TestCase):
    def test_repair_utf8_mojibake(self) -> None:
        good = "送货单预览_上海金脉电子科技有限公司.xlsx"
        bad = good.encode("utf-8").decode("latin-1")
        self.assertNotEqual(bad, good)
        self.assertEqual(repair_utf8_mojibake(bad), good)

    def test_repair_leaves_ascii(self) -> None:
        self.assertEqual(repair_utf8_mojibake("template.xlsx"), "template.xlsx")

    def test_normalize_upload_filename_strips_path(self) -> None:
        self.assertEqual(
            normalize_upload_filename(r"C:\fake\迅铂送货单.xlsx"),
            "迅铂送货单.xlsx",
        )


if __name__ == "__main__":
    unittest.main()
