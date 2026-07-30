import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from test_impl.integrations.feishu import (
    FeishuNotifier,
    list_webhook_urls,
    load_feishu_config,
    public_feishu_config,
    save_feishu_config,
    send_text,
)
from test_impl.integrations.wkt_events import (
    build_deploy_audit_summary,
    deploy_delta_from_entries,
    format_deploy_transition,
    notify_audit_action,
    notify_inventory_movement,
    notify_line_shipped,
    notify_system_deploy,
    parse_changelog_entries,
    parse_changelog_head,
    parse_version_from_markdown,
)


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

    @patch("test_impl.integrations.feishu.urllib.request.urlopen")
    def test_notify_all_webhooks(self, mock_urlopen: MagicMock) -> None:
        self.cfg_path.write_text(
            json.dumps(
                {
                    "enabled": True,
                    "webhook_urls": [
                        "https://open.feishu.cn/hook/a",
                        "https://open.feishu.cn/hook/b",
                    ],
                    "sign_secret": "",
                    "events": {"audit_action": True},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = b'{"code":0}'
        mock_urlopen.return_value.__enter__.return_value = resp
        notifier = FeishuNotifier()
        self.assertTrue(notifier.notify_text("hello", event="audit_action"))
        self.assertEqual(mock_urlopen.call_count, 2)
        urls = {call.args[0].full_url for call in mock_urlopen.call_args_list}
        self.assertEqual(
            urls,
            {
                "https://open.feishu.cn/hook/a",
                "https://open.feishu.cn/hook/b",
            },
        )

    def test_list_webhook_urls_dedupes(self) -> None:
        urls = list_webhook_urls(
            {
                "webhook_url": "https://open.feishu.cn/hook/a",
                "webhook_urls": [
                    "https://open.feishu.cn/hook/a",
                    "https://open.feishu.cn/hook/b",
                ],
            }
        )
        self.assertEqual(urls, ["https://open.feishu.cn/hook/a", "https://open.feishu.cn/hook/b"])

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

    @patch.object(FeishuNotifier, "notify_async")
    def test_inventory_movement_message(self, mock_async: MagicMock) -> None:
        notify_inventory_movement(
            {
                "action_type": "complete",
                "product_part_no": "PL9-01100",
                "process_code": "01",
                "from_process_code": "",
                "from_status": "",
                "to_process_code": "01",
                "to_status": "inhouse",
                "qty": "100",
                "doc_no": "WG-20260725-001",
                "note": "完工转入 压铸",
            }
        )
        mock_async.assert_called_once()
        text = mock_async.call_args[0][0]
        self.assertIn("库存出入库", text)
        self.assertIn("完工转入", text)
        self.assertIn("PL9-01100", text)
        self.assertEqual(mock_async.call_args[1]["event"], "inventory_movement")

    @patch.object(FeishuNotifier, "notify_async")
    def test_audit_action_message(self, mock_async: MagicMock) -> None:
        notify_audit_action(
            action="line.create",
            module="orders",
            summary="录入订单行：怡利 PO-1",
            user={"display_name": "张三", "username": "zhangsan"},
            ip_address="127.0.0.1",
        )
        mock_async.assert_called_once()
        text = mock_async.call_args[0][0]
        self.assertIn("操作通知", text)
        self.assertIn("张三", text)
        self.assertIn("录入订单行", text)
        self.assertEqual(mock_async.call_args[1]["event"], "audit_action")

    @patch.object(FeishuNotifier, "notify_text")
    def test_system_deploy_message_sync(self, mock_text: MagicMock) -> None:
        mock_text.return_value = True
        ok = notify_system_deploy(
            version="v0.6.0",
            build="20260730-deploy-notify",
            prev_version="v0.6.0",
            prev_build="20260728-old-build",
            prev_top_cl="CL-0279",
            top_cl="CL-0280",
            cl_transition="CL-0279→CL-0280",
            changes=["[修复] CL-0280：部署飞书改同步发送"],
            host_label="云端",
            operator="Albert",
            sync=True,
        )
        mock_text.assert_called_once()
        self.assertTrue(ok)
        text = mock_text.call_args[0][0]
        self.assertIn("系统更新", text)
        self.assertIn("Albert", text)
        self.assertEqual(mock_text.call_args[1]["event"], "system_deploy")

    @patch.object(FeishuNotifier, "notify_async")
    def test_system_deploy_message(self, mock_async: MagicMock) -> None:
        notify_system_deploy(
            version="v0.6.0",
            build="20260730-deploy-notify",
            prev_version="v0.6.0",
            prev_build="20260728-old-build",
            prev_top_cl="CL-0279",
            top_cl="CL-0280",
            cl_transition="CL-0279→CL-0280",
            changes=["[修复] CL-0280：部署飞书改同步发送"],
            host_label="云端",
            operator="Albert",
        )
        mock_async.assert_called_once()
        text = mock_async.call_args[0][0]
        self.assertIn("系统更新", text)
        self.assertIn("v0.6.0", text)
        self.assertIn("20260728-old-build", text)
        self.assertIn("20260730-deploy-notify", text)
        self.assertIn("→", text)
        self.assertIn("Albert", text)
        self.assertIn("CL-0279", text)
        self.assertIn("CL-0280", text)
        self.assertIn("同步发送", text)

    def test_deploy_delta_since_cl(self) -> None:
        sample = """
### CL-0280 · 2026-07-30 · 修复（C）

| 字段 | 内容 |
|------|------|
| 变更内容 | 仅推送增量 CL |

### CL-0279 · 2026-07-30 · 优化（C）

| 字段 | 内容 |
|------|------|
| 变更内容 | 摘要居中 |

### CL-0278 · 2026-07-30 · 修复（C）

| 字段 | 内容 |
|------|------|
| 变更内容 | 飞书同步 |
"""
        entries = parse_changelog_entries(sample)
        changes, prev_cl, top_cl, cl_transition = deploy_delta_from_entries(
            entries, since_cl="CL-0279"
        )
        self.assertEqual(prev_cl, "CL-0279")
        self.assertEqual(top_cl, "CL-0280")
        self.assertEqual(cl_transition, "CL-0279→CL-0280")
        self.assertEqual(len(changes), 1)
        self.assertIn("CL-0280", changes[0])
        self.assertIn("增量 CL", changes[0])

    def test_format_deploy_transition(self) -> None:
        v_line, b_line = format_deploy_transition(
            {"version": "v0.5.1", "build": "build-a"},
            {"version": "v0.6.0", "build": "build-b"},
        )
        self.assertIn("v0.5.1", v_line)
        self.assertIn("v0.6.0", v_line)
        self.assertIn("build-a", b_line)
        self.assertIn("build-b", b_line)
        same_v, same_b = format_deploy_transition(
            {"version": "v0.6.0", "build": "build-old"},
            {"version": "v0.6.0", "build": "build-new"},
        )
        self.assertIn("v0.6.0 → v0.6.0", same_v)
        self.assertIn("build-old → build-new", same_b)

    def test_build_deploy_audit_summary(self) -> None:
        s = build_deploy_audit_summary({"cl_transition": "CL-0279→CL-0280"}, host_label="云端")
        self.assertEqual(s, "系统部署（云端）· CL-0279→CL-0280")

    def test_parse_changelog_head(self) -> None:
        bullet = """
### CL-0149 · 2026-07-25 · 优化（B）
- 变更内容：飞书审计统一推送
### CL-0148 · 2026-07-25 · 优化（B）
- 变更内容：扩展模块通知
"""
        items = parse_changelog_head(bullet, limit=2)
        self.assertEqual(len(items), 2)
        self.assertIn("[优化]", items[0])
        self.assertIn("CL-0149", items[0])
        self.assertIn("飞书审计", items[0])

        table = """
### CL-0278 · 2026-07-30 · 修复（C）

| 字段 | 内容 |
|------|------|
| 变更内容 | 部署飞书改同步发送（修复 notify_async 未发出） |
"""
        table_items = parse_changelog_head(table, limit=1)
        self.assertEqual(len(table_items), 1)
        self.assertIn("[修复]", table_items[0])
        self.assertIn("CL-0278", table_items[0])
        self.assertIn("同步发送", table_items[0])

    def test_parse_version_from_markdown(self) -> None:
        text = "| **版本号** | **v0.6.0** |"
        self.assertEqual(parse_version_from_markdown(text), "v0.6.0")


if __name__ == "__main__":
    unittest.main()
