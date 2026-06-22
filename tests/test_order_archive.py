import tempfile
import unittest
from pathlib import Path

from test_impl.order_management.order_archive import (
    archive_order_file,
    build_archive_filename,
    sanitize_path_part,
)


class TestOrderArchive(unittest.TestCase):
    def test_sanitize_path_part(self) -> None:
        self.assertEqual(sanitize_path_part("浙江红黑科技有限公司"), "浙江红黑科技有限公司")
        self.assertEqual(sanitize_path_part('bad/name'), "bad_name")

    def test_build_archive_filename(self) -> None:
        name = build_archive_filename("2026-05-12", "PO1B260512063", ".pdf")
        self.assertEqual(name, "2026-05-12_PO1B260512063.pdf")

    def test_archive_order_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "orders"
            lines = [
                {
                    "customer": "华东精密机械",
                    "order_date": "2026-05-12",
                    "order_no": "PO-001",
                }
            ]
            path = archive_order_file(b"pdf-content", "scan.PDF", lines, root)
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_bytes(), b"pdf-content")
            self.assertEqual(path.name, "2026-05-12_PO-001.pdf")
            self.assertEqual(path.parent.name, "华东精密机械")

    def test_archive_duplicate_adds_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "orders"
            lines = [{"customer": "A", "order_date": "2026-01-01", "order_no": "X"}]
            archive_order_file(b"1", "a.pdf", lines, root)
            path2 = archive_order_file(b"2", "a.pdf", lines, root)
            self.assertEqual(path2.name, "2026-01-01_X_1.pdf")


if __name__ == "__main__":
    unittest.main()
