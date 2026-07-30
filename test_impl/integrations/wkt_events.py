"""将业务事件格式化为飞书消息。"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from test_impl.order_management.inventory.service import ACTION_LABELS

from .feishu import feishu_notifier, load_feishu_config

from test_impl.auth.audit_labels import MODULE_LABELS

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
    title_re = re.compile(r"^(CL-\d+)\s*·\s*(\d{4}-\d{2}-\d{2})\s*·\s*(.+)$")
    for block in re.split(r"\n(?=### CL-)", text):
        block = block.strip()
        if not block.startswith("### CL-"):
            continue
        lines = block.splitlines()
        title = lines[0].replace("### ", "").strip()
        body = _extract_cl_change_body(lines[1:])
        m = title_re.match(title)
        if m and body:
            cl_id = m.group(1)
            kind = _normalize_cl_kind(m.group(3))
            entries.append(f"[{kind}] {cl_id}：{body}")
        elif body:
            entries.append(f"{title}：{body}")
        else:
            entries.append(title)
        if len(entries) >= limit:
            break
    return entries


def _normalize_cl_kind(raw: str) -> str:
    s = str(raw or "").strip()
    for suffix in ("（A）", "（B）", "（C）", "（D）"):
        s = s.replace(suffix, "")
    return s.strip() or raw


def _extract_cl_change_body(lines: List[str]) -> str:
    for line in lines:
        s = line.strip()
        if s.startswith("- 变更内容："):
            return s.replace("- 变更内容：", "", 1).strip()
        m = re.match(r"^\|\s*变更内容\s*\|\s*(.+?)\s*\|\s*$", s)
        if m:
            return m.group(1).strip()
    return ""


def _read_snapshot_file(path: Path) -> Optional[Dict[str, Any]]:
    import json

    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def read_deploy_build(app_dir: Path) -> str:
    app_py = app_dir / "test_impl" / "web" / "app.py"
    if not app_py.is_file():
        return "unknown"
    m = re.search(r'"build":\s*"([^"]+)"', app_py.read_text(encoding="utf-8"))
    return m.group(1) if m else "unknown"


def read_deploy_version(app_dir: Path) -> str:
    info_dir = app_dir / "deploy-info"
    version_file = info_dir / "VERSION.md"
    if version_file.is_file():
        return parse_version_from_markdown(version_file.read_text(encoding="utf-8"))
    return ""


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


def pre_deploy_snapshot_path(app_dir: Path) -> Path:
    return app_dir / "data" / "pre-deploy-snapshot.json"


def last_deploy_snapshot_path(app_dir: Path) -> Path:
    return app_dir / "data" / "last-deploy.json"


def _legacy_pre_deploy_snapshot_path(app_dir: Path) -> Path:
    return app_dir / "deploy-info" / "pre-deploy-snapshot.json"


def _legacy_last_deploy_snapshot_path(app_dir: Path) -> Path:
    return app_dir / "deploy-info" / "last-deploy.json"


def deploy_audit_db_path(app_dir: Path) -> Path:
    """部署脚本写入 audit_log 时使用的 SQLite 路径（与 Flask 同库）。"""
    import os

    env = os.environ.get("WKT_DB_PATH", "").strip()
    if env:
        return Path(env)
    return app_dir / "data" / "wkt_orders.db"


def capture_pre_deploy_snapshot(app_dir: Path) -> Dict[str, Any]:
    """部署合并前写入当前云端版本/build（供部署后对比）。"""
    import json

    summary = collect_deploy_summary(app_dir)
    summary["captured_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    path = pre_deploy_snapshot_path(app_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def load_pre_deploy_snapshot(app_dir: Path) -> Optional[Dict[str, Any]]:
    for path in (
        pre_deploy_snapshot_path(app_dir),
        _legacy_pre_deploy_snapshot_path(app_dir),
    ):
        data = _read_snapshot_file(path)
        if data:
            return data
    for path in (
        last_deploy_snapshot_path(app_dir),
        _legacy_last_deploy_snapshot_path(app_dir),
    ):
        data = _read_snapshot_file(path)
        if data:
            return data
    return None


def save_last_deploy_snapshot(app_dir: Path, summary: Dict[str, Any]) -> None:
    import json

    payload = {
        "version": summary.get("version") or "",
        "build": summary.get("build") or "",
        "deployed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    path = last_deploy_snapshot_path(app_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def format_deploy_transition(
    previous: Optional[Dict[str, Any]],
    current: Dict[str, Any],
) -> tuple[str, str]:
    """返回 (版本行, build 行) 用于飞书/审计摘要。"""
    prev_ver = str((previous or {}).get("version") or "").strip()
    prev_build = str((previous or {}).get("build") or "").strip()
    cur_ver = str(current.get("version") or "").strip()
    cur_build = str(current.get("build") or "").strip()
    if previous is not None:
        version_line = f"版本：{prev_ver or '—'} → {cur_ver or '—'}"
        build_line = f"Build：{prev_build or '—'} → {cur_build or '—'}"
    else:
        version_line = f"版本：{cur_ver or '—'}"
        build_line = f"Build：{cur_build or '—'}"
    return version_line, build_line


def build_deploy_audit_summary(
    previous: Optional[Dict[str, Any]],
    current: Dict[str, Any],
    *,
    host_label: str = "云端",
    triggered_by: str = "",
    change_preview_len: int = 48,
) -> str:
    parts = [f"系统部署（{host_label}）"]
    prev_v = str((previous or {}).get("version") or "").strip()
    cur_v = str(current.get("version") or "").strip()
    if prev_v or cur_v:
        if prev_v and cur_v and prev_v != cur_v:
            parts.append(f"版本 {prev_v}→{cur_v}")
        else:
            parts.append(f"版本 {cur_v or prev_v}")
    prev_b = str((previous or {}).get("build") or "").strip()
    cur_b = str(current.get("build") or "").strip()
    if prev_b or cur_b:
        if prev_b and cur_b and prev_b != cur_b:
            parts.append(f"build {prev_b}→{cur_b}")
        else:
            parts.append(f"build {cur_b or prev_b}")
    changes = current.get("changes") or []
    if changes:
        preview = str(changes[0])
        if len(preview) > change_preview_len:
            preview = preview[: change_preview_len - 1] + "…"
        parts.append(preview)
        if len(changes) > 1:
            parts.append(f"共{len(changes)}项变更")
    op = str(triggered_by or "").strip()
    if op:
        parts.append(f"推送 {op}")
    return " · ".join(p for p in parts if p)


def log_system_deploy_audit(
    app_dir: Path,
    *,
    previous: Optional[Dict[str, Any]],
    current: Dict[str, Any],
    operator: str = "deploy",
    host_label: str = "云端",
) -> None:
    """写入操作记录 audit_log（与网页操作记录同源）。"""
    from test_impl.auth.service import AuditService
    from test_impl.auth.store import AuthStore

    summary = build_deploy_audit_summary(
        previous, current, host_label=host_label, triggered_by=triggered_by
    )
    triggered_by = str(operator or "deploy").strip() or "deploy"
    store = AuthStore(db_path=deploy_audit_db_path(app_dir))
    audit_user: Dict[str, Any] = {"username": "system", "display_name": "系统管理员"}
    for user in store.list_users():
        if user.role == "admin" and user.is_active:
            audit_user = {"id": user.id, "username": user.username, "display_name": user.display_name}
            break
    audit = AuditService(store=store)
    try:
        audit.log(
            user=audit_user,
            action="system.deploy",
            module="system",
            summary=summary,
            entity_type="deploy",
            entity_id=str(current.get("build") or ""),
            detail={
                "host": host_label,
                "triggered_by": triggered_by,
                "previous": {
                    "version": (previous or {}).get("version") or "",
                    "build": (previous or {}).get("build") or "",
                },
                "current": {
                    "version": current.get("version") or "",
                    "build": current.get("build") or "",
                },
                "changes": current.get("changes") or [],
            },
            ip_address="deploy",
        )
    finally:
        store.close()


def notify_system_deploy(
    *,
    version: str = "",
    build: str = "",
    prev_version: str = "",
    prev_build: str = "",
    changes: Optional[List[str]] = None,
    host_label: str = "云端",
    operator: str = "",
    sync: bool = False,
) -> bool:
    """系统迭代部署完成后推送版本与变更摘要。deploy 脚本须 sync=True 以免进程退出前未发完。"""
    previous = (
        {"version": prev_version, "build": prev_build}
        if (prev_version or prev_build)
        else None
    )
    current = {"version": version, "build": build}
    version_line, build_line = format_deploy_transition(previous, current)
    lines = [version_line, build_line, f"环境：{host_label}"]
    op = str(operator or "").strip()
    if op:
        lines.append(f"推送人：{op}")
    items = changes or []
    if items:
        lines.append("本次更新：")
        lines.extend(f"· {item}" for item in items)
    else:
        lines.append("本次更新：见 CHANGELOG（deploy-info 未打包时仅显示 build）")
    text = f"【{_app_title()} · 系统更新】\n时间：{_now_str()}\n" + "\n".join(lines)
    if sync:
        return feishu_notifier.notify_text(text, event="system_deploy")
    feishu_notifier.notify_async(text, event="system_deploy")
    return True


def send_test_message() -> None:
    text = (
        f"【{_app_title()} · 测试】\n"
        f"时间：{_now_str()}\n"
        f"飞书通知已连通。云端任意操作与系统迭代更新均将推送到此群。"
    )
    feishu_notifier.notify_text(text)
