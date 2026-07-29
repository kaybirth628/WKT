"""操作审计：模块 / 动作中文展示名（与顶栏模块名一致）。"""
from __future__ import annotations

from typing import Callable, Dict, Tuple

SummaryFn = Callable[[], str]
AuditRule = Tuple[str, str, SummaryFn]

# 与 `_order_sidebar.html` 顶栏模块名对齐
MODULE_LABELS: Dict[str, str] = {
    "orders": "订单管理",
    "inventory": "库存",
    "cost": "BOM信息",
    "partners": "客商信息维护",
    "delivery": "送货单",
    "admin": "用户管理",
    "system": "系统",
    "master": "主数据",
    "ai": "AI数据助手",
}

ACTION_LABELS: Dict[str, str] = {
    "auth.login": "用户登录",
}


def ingest_audit_rules(rules: Dict[Tuple[str, str], AuditRule]) -> None:
    """从 flask_integration.AUDIT_RULES 同步动作默认摘要为展示名。"""
    for action, _module, summary_fn in rules.values():
        ACTION_LABELS.setdefault(action, summary_fn())


def module_label(code: str) -> str:
    key = (code or "").strip()
    return MODULE_LABELS.get(key, key or "—")


def action_label(code: str) -> str:
    key = (code or "").strip()
    return ACTION_LABELS.get(key, key or "—")
