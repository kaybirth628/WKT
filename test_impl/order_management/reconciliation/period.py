"""对账周期类型：自然月 / 21日～次月20日。"""
from __future__ import annotations

from datetime import date
from typing import Dict, List

CALENDAR_MONTH = "calendar_month"
MONTH_21_20 = "month_21_20"

DEFAULT_SUPPLIER_RECONCILIATION_PERIOD = MONTH_21_20

PERIOD_LABELS: Dict[str, str] = {
    CALENDAR_MONTH: "自然月（1日～月末）",
    MONTH_21_20: "21日～次月20日",
}

PERIOD_OPTIONS: List[Dict[str, str]] = [
    {"value": CALENDAR_MONTH, "label": PERIOD_LABELS[CALENDAR_MONTH]},
    {"value": MONTH_21_20, "label": PERIOD_LABELS[MONTH_21_20]},
]

_VALID = frozenset(PERIOD_LABELS)


def normalize_reconciliation_period(raw: str | None, *, default: str = "") -> str:
    val = str(raw or "").strip()
    if val in _VALID:
        return val
    legacy = {
        "自然月": CALENDAR_MONTH,
        "calendar_month": CALENDAR_MONTH,
        "calendar": CALENDAR_MONTH,
        "month_21_20": MONTH_21_20,
        "21-20": MONTH_21_20,
        "21日至次月20日": MONTH_21_20,
        "21日～次月20日": MONTH_21_20,
    }
    mapped = legacy.get(val)
    if mapped:
        return mapped
    return default


def reconciliation_period_label(code: str | None) -> str:
    normalized = normalize_reconciliation_period(code, default="")
    if not normalized:
        return "未设置"
    return PERIOD_LABELS.get(normalized, normalized)


def reconciliation_period_for_ship_date(ship_date: date, period_type: str) -> str:
    """返回对账期标签 YYYY-MM。"""
    mode = normalize_reconciliation_period(period_type, default=MONTH_21_20)
    if mode == CALENDAR_MONTH:
        return f"{ship_date.year:04d}-{ship_date.month:02d}"
    y, m = ship_date.year, ship_date.month
    if ship_date.day >= 21:
        m += 1
        if m > 12:
            y += 1
            m = 1
    return f"{y:04d}-{m:02d}"
