"""将业务事件格式化为飞书消息。"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .feishu import feishu_notifier, load_feishu_config


def _now_str() -> str:
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")


def _app_title() -> str:
    return str(load_feishu_config().get("app_name") or "WKT销售系统")


def _line_bits(line: Dict[str, Any]) -> str:
    return (
        f"客户：{line.get('customer') or '—'}\n"
        f"订单号：{line.get('order_no') or '—'}\n"
        f"品名规格：{line.get('product_spec') or '—'}\n"
        f"客户料号：{line.get('customer_part_no') or '—'}\n"
        f"PO数量：{line.get('po_qty') or '—'}　已出货：{line.get('shipped_qty') or '0'}　未结：{line.get('open_qty') or '—'}"
    )


def notify_line_created(line: Dict[str, Any], *, source: str = "手动录入") -> None:
    text = (
        f"【{_app_title()} · 订单录入】\n"
        f"时间：{_now_str()}\n"
        f"来源：{source}\n"
        f"{_line_bits(line)}"
    )
    feishu_notifier.notify_async(text, event="line_created")


def notify_line_updated(line: Dict[str, Any]) -> None:
    text = (
        f"【{_app_title()} · 订单修改】\n"
        f"时间：{_now_str()}\n"
        f"行ID：{line.get('id') or '—'}\n"
        f"{_line_bits(line)}"
    )
    feishu_notifier.notify_async(text, event="line_updated")


def notify_line_deleted(line: Dict[str, Any]) -> None:
    text = (
        f"【{_app_title()} · 订单删除】\n"
        f"时间：{_now_str()}\n"
        f"行ID：{line.get('id') or '—'}\n"
        f"{_line_bits(line)}"
    )
    feishu_notifier.notify_async(text, event="line_deleted")


def notify_line_shipped(
    line: Dict[str, Any],
    *,
    ship_qty: str,
    shipment_event_id: Optional[int] = None,
    closed: bool = False,
    delivery_doc_no: str = "",
) -> None:
    status = "已结案" if closed else f"剩余未结 {line.get('open_qty') or '—'}"
    extra = f"\n送货单号：{delivery_doc_no}" if delivery_doc_no else ""
    if shipment_event_id:
        extra += f"\n出货记录ID：{shipment_event_id}"
    text = (
        f"【{_app_title()} · 出货】\n"
        f"时间：{_now_str()}\n"
        f"客户：{line.get('customer') or '—'}\n"
        f"订单号：{line.get('order_no') or '—'}\n"
        f"品名规格：{line.get('product_spec') or '—'}\n"
        f"本次出货：{ship_qty}\n"
        f"状态：{status}{extra}"
    )
    feishu_notifier.notify_async(text, event="line_shipped")


def notify_import_completed(result: Dict[str, Any], *, tier: str = "") -> None:
    tier_label = {"passed": "校验通过", "pending": "待确认", "all_importable": "可导入"}.get(
        tier, tier or "导入"
    )
    text = (
        f"【{_app_title()} · Excel导入】\n"
        f"时间：{_now_str()}\n"
        f"批次：{tier_label}\n"
        f"成功导入：{result.get('imported', 0)} 条\n"
        f"失败：{result.get('failed', 0)} 条\n"
        f"跳过重复：{result.get('skipped_duplicates', 0)} 条"
    )
    feishu_notifier.notify_async(text, event="import_completed")


def send_test_message() -> None:
    text = (
        f"【{_app_title()} · 测试】\n"
        f"时间：{_now_str()}\n"
        f"飞书通知已连通，后续订单录入、出货等变动将推送到此群。"
    )
    feishu_notifier.notify_text(text)
