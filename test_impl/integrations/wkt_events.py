"""将业务事件格式化为飞书消息。"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from test_impl.order_management.inventory.service import ACTION_LABELS

from .feishu import feishu_notifier, load_feishu_config

MODULE_LABELS = {
    "orders": "订单",
    "partners": "客商",
    "inventory": "库存",
    "cost": "BOM",
    "delivery": "送货单",
    "master": "主数据",
    "admin": "用户管理",
    "system": "系统",
    "ai": "AI助手",
}

SKIP_FEISHU_ACTIONS = frozenset({"feishu.test"})


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


def _bom_bits(record: Dict[str, Any]) -> str:
    return (
        f"客户：{record.get('customer_name') or '—'}\n"
        f"料号：{record.get('product_part_no') or '—'}\n"
        f"品名：{record.get('product_name') or '—'}"
    )


def _movement_bits(movement: Dict[str, Any]) -> str:
    action_type = str(movement.get("action_type") or "")
    action = movement.get("action_label") or ACTION_LABELS.get(action_type, action_type or "—")
    from_bits = "/".join(
        x
        for x in (
            movement.get("from_process_code"),
            movement.get("from_status"),
            movement.get("from_supplier"),
        )
        if x
    ) or "—"
    to_bits = "/".join(
        x
        for x in (
            movement.get("to_process_code"),
            movement.get("to_status"),
            movement.get("to_supplier"),
        )
        if x
    ) or "—"
    return (
        f"动作：{action}\n"
        f"料号：{movement.get('product_part_no') or '—'}\n"
        f"工序：{movement.get('process_code') or '—'}\n"
        f"从：{from_bits}\n"
        f"到：{to_bits}\n"
        f"数量：{movement.get('qty') or '—'}\n"
        f"单号：{movement.get('doc_no') or '—'}\n"
        f"备注：{movement.get('note') or '—'}"
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


def notify_line_force_closed(line: Dict[str, Any]) -> None:
    text = (
        f"【{_app_title()} · 订单强制结案】\n"
        f"时间：{_now_str()}\n"
        f"行ID：{line.get('id') or '—'}\n"
        f"{_line_bits(line)}"
    )
    feishu_notifier.notify_async(text, event="line_force_closed")


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


def notify_shipment_reversed(line: Dict[str, Any], *, event_id: int) -> None:
    text = (
        f"【{_app_title()} · 撤销出货】\n"
        f"时间：{_now_str()}\n"
        f"出货记录ID：{event_id}\n"
        f"{_line_bits(line)}"
    )
    feishu_notifier.notify_async(text, event="shipment_reversed")


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


def notify_inventory_movement(movement: Dict[str, Any]) -> None:
    text = (
        f"【{_app_title()} · 库存出入库】\n"
        f"时间：{_now_str()}\n"
        f"{_movement_bits(movement)}"
    )
    feishu_notifier.notify_async(text, event="inventory_movement")


def notify_bom_record(action: str, record: Dict[str, Any]) -> None:
    title = {"created": "BOM录入", "updated": "BOM修改", "deleted": "BOM删除"}.get(
        action, "BOM变动"
    )
    event = {"created": "bom_created", "updated": "bom_updated", "deleted": "bom_deleted"}.get(
        action, "bom_updated"
    )
    rid = record.get("id")
    extra = f"记录ID：{rid}\n" if rid else ""
    text = (
        f"【{_app_title()} · {title}】\n"
        f"时间：{_now_str()}\n"
        f"{extra}{_bom_bits(record)}"
    )
    feishu_notifier.notify_async(text, event=event)


def notify_customer_profile(action: str, customer: str) -> None:
    label = {"created": "新建", "updated": "修改", "deleted": "删除"}.get(action, action)
    text = (
        f"【{_app_title()} · 客户档案{label}】\n"
        f"时间：{_now_str()}\n"
        f"客户：{customer or '—'}"
    )
    feishu_notifier.notify_async(text, event="customer_profile")


def notify_supplier_profile(action: str, supplier: str) -> None:
    label = {"created": "新建", "updated": "修改", "deleted": "删除"}.get(action, action)
    text = (
        f"【{_app_title()} · 供应商档案{label}】\n"
        f"时间：{_now_str()}\n"
        f"供应商：{supplier or '—'}"
    )
    feishu_notifier.notify_async(text, event="supplier_profile")


def notify_master_data(kind: str, name: str) -> None:
    kind_label = {"customer": "客户主数据", "part": "品名料号主数据"}.get(kind, kind)
    text = (
        f"【{_app_title()} · {kind_label}】\n"
        f"时间：{_now_str()}\n"
        f"名称：{name or '—'}"
    )
    feishu_notifier.notify_async(text, event="master_data")


def _operator_label(user: Optional[Dict[str, Any]]) -> str:
    if not user:
        return "—"
    display = str(user.get("display_name") or "").strip()
    username = str(user.get("username") or "").strip()
    if display and username:
        return f"{display}（{username}）"
    return display or username or "—"


def notify_audit_action(
    *,
    action: str,
    module: str,
    summary: str,
    user: Optional[Dict[str, Any]] = None,
    ip_address: str = "",
) -> None:
    """审计钩子：云端/本地任意已登记写操作统一推送飞书。"""
    if action in SKIP_FEISHU_ACTIONS:
        return
    mod = MODULE_LABELS.get(module, module or "—")
    text = (
        f"【{_app_title()} · 操作通知】\n"
        f"时间：{_now_str()}\n"
        f"操作人：{_operator_label(user)}\n"
        f"模块：{mod}\n"
        f"摘要：{summary or action}"
    )
    if ip_address:
        text += f"\nIP：{ip_address}"
    feishu_notifier.notify_async(text, event="audit_action")


def parse_version_from_markdown(text: str) -> str:
    m = re.search(r"\*\*(v[\d.]+)\*\*", text)
    return m.group(1) if m else ""


def parse_changelog_head(text: str, *, limit: int = 8) -> List[str]:
    entries: List[str] = []
    for block in re.split(r"\n(?=### CL-)", text):
        block = block.strip()
        if not block.startswith("### CL-"):
            continue
        lines = block.splitlines()
        title = lines[0].replace("### ", "").strip()
        body = ""
        for line in lines[1:]:
            s = line.strip()
            if s.startswith("- 变更内容："):
                body = s.replace("- 变更内容：", "", 1).strip()
                break
        entries.append(f"{title}：{body}" if body else title)
        if len(entries) >= limit:
            break
    return entries


def read_deploy_build(app_dir: Path) -> str:
    app_py = app_dir / "test_impl" / "web" / "app.py"
    if not app_py.is_file():
        return "unknown"
    m = re.search(r'"build":\s*"([^"]+)"', app_py.read_text(encoding="utf-8"))
    return m.group(1) if m else "unknown"


def collect_deploy_summary(app_dir: Path, *, changelog_limit: int = 8) -> Dict[str, Any]:
    info_dir = app_dir / "deploy-info"
    version = ""
    version_file = info_dir / "VERSION.md"
    if version_file.is_file():
        version = parse_version_from_markdown(version_file.read_text(encoding="utf-8"))
    changelog_file = info_dir / "CHANGELOG.md"
    changes: List[str] = []
    if changelog_file.is_file():
        changes = parse_changelog_head(changelog_file.read_text(encoding="utf-8"), limit=changelog_limit)
    return {
        "version": version,
        "build": read_deploy_build(app_dir),
        "changes": changes,
    }


def notify_system_deploy(
    *,
    version: str = "",
    build: str = "",
    changes: Optional[List[str]] = None,
    host_label: str = "云端",
) -> None:
    """系统迭代部署完成后推送版本与变更摘要。"""
    lines = [f"版本：{version or '—'}", f"Build：{build or '—'}", f"环境：{host_label}"]
    items = changes or []
    if items:
        lines.append("本次迭代：")
        lines.extend(f"· {item}" for item in items)
    else:
        lines.append("本次迭代：见 CHANGELOG（deploy-info 未打包时仅显示 build）")
    text = f"【{_app_title()} · 系统更新】\n时间：{_now_str()}\n" + "\n".join(lines)
    feishu_notifier.notify_async(text, event="system_deploy")


def send_test_message() -> None:
    text = (
        f"【{_app_title()} · 测试】\n"
        f"时间：{_now_str()}\n"
        f"飞书通知已连通。云端任意操作与系统迭代更新均将推送到此群。"
    )
    feishu_notifier.notify_text(text)
