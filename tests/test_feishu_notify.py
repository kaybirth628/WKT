import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from test_impl.integrations.feishu import (
    FeishuNotifier,
    load_feishu_config,
    public_feishu_config,
    save_feishu_config,
    send_text,
)
from test_impl.integrations.wkt_events import notify_line_shipped


class TestFeishuNotify(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg_path = Path(self.tmp.name) / "feishu_config.json"
        self.cfg_path.write_text(
            json.dumps(
                {
                    "enabled": True,
                    "webhook_url": "https://open.feishu.cn/hook/test-token",
                    "sign_secret": "",
                    "events": {"line_shipped": True},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self._patch = patch("test_impl.integrations.feishu._CONFIG_FILE", self.cfg_path)
        self._patch.start()

    def tearDown(self) -> None:
        self._patch.stop()
        self.tmp.cleanup()

    @patch("test_impl.integrations.feishu.urllib.request.urlopen")
    def test_send_text_ok(self, mock_urlopen: MagicMock) -> None:
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = b'{"code":0}'
        mock_urlopen.return_value.__enter__.return_value = resp
        send_text("https://open.feishu.cn/hook/test-token", "hello")
        req = mock_urlopen.call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["msg_type"], "text")
        self.assertIn("hello", body["content"]["text"])

    def test_public_config_masks_url(self) -> None:
        pub = public_feishu_config()
        self.assertTrue(pub["configured"])
        self.assertIn("…", pub["webhook_url_masked"])

    @patch.object(FeishuNotifier, "notify_async")
    def test_ship_event_message(self, mock_async: MagicMock) -> None:
        notify_line_shipped(
            {
                "customer": "怡利",
                "order_no": "PO-1",
                "product_spec": "散热片",
                "open_qty": "60",
            },
            ship_qty="40",
            shipment_event_id=9,
            closed=False,
            delivery_doc_no="WKT202601010009",
        )
        mock_async.assert_called_once()
        text = mock_async.call_args[0][0]
        self.assertIn("出货", text)
        self.assertIn("怡利", text)
        self.assertIn("40", text)


if __name__ == "__main__":
    unittest.main()
