"""对账周期类型：自然月 / 滚动月（上月 X 日～本月 Y 日）。"""
from __future__ import annotations

from datetime import date
from typing import Dict, List, Tuple

CALENDAR_MONTH = "calendar_month"
MONTH_21_20 = "month_21_20"
MONTH_26_25 = "month_26_25"
MONTH_22_21 = "month_22_21"
MONTH_16_15 = "month_16_15"

DEFAULT_SUPPLIER_RECONCILIATION_PERIOD = MONTH_21_20

# 滚动周期：起始日（含）→ 次月截止日（含）；标签 YYYY-MM 取截止日所在月。
ROLLING_PERIODS: Dict[str, Tuple[int, int, str]] = {
    MONTH_21_20: (21, 20, "21日～次月20日"),
    MONTH_26_25: (26, 25, "26日～次月25日"),
    MONTH_22_21: (22, 21, "22日～次月21日"),
    MONTH_16_15: (16, 15, "16日～次月15日"),
}

PERIOD_LABELS: Dict[str, str] = {
    CALENDAR_MONTH: "自然月（1日～月末）",
    **{code: label for code, (_, _, label) in ROLLING_PERIODS.items()},
}

PERIOD_OPTIONS: List[Dict[str, str]] = [
    {"value": code, "label": label} for code, label in PERIOD_LABELS.items()
]

_VALID = frozenset(PERIOD_LABELS)

_LEGACY_ALIASES: Dict[str, str] = {
    "自然月": CALENDAR_MONTH,
    "calendar_month": CALENDAR_MONTH,
    "calendar": CALENDAR_MONTH,
    "month_21_20": MONTH_21_20,
    "21-20": MONTH_21_20,
    "21日至次月20日": MONTH_21_20,
    "21日～次月20日": MONTH_21_20,
    "上月21号-当月20号": MONTH_21_20,
    "上月21日-当月20日": MONTH_21_20,
    "month_26_25": MONTH_26_25,
    "26-25": MONTH_26_25,
    "26日～次月25日": MONTH_26_25,
    "上月26号-本月25号": MONTH_26_25,
    "上月26日-本月25日": MONTH_26_25,
    "month_22_21": MONTH_22_21,
    "22-21": MONTH_22_21,
    "22日～次月21日": MONTH_22_21,
    "上月22号-本月21号": MONTH_22_21,
    "上月22日-本月21日": MONTH_22_21,
    "month_16_15": MONTH_16_15,
    "16-15": MONTH_16_15,
    "16日～次月15日": MONTH_16_15,
    "上月16号-本月15号": MONTH_16_15,
    "上月16日-本月15日": MONTH_16_15,
}


def normalize_reconciliation_period(raw: str | None, *, default: str = "") -> str:
    val = str(raw or "").strip()
    if val in _VALID:
        return val
    mapped = _LEGACY_ALIASES.get(val)
    if mapped:
        return mapped
    return default


def reconciliation_period_label(code: str | None) -> str:
    normalized = normalize_reconciliation_period(code, default="")
    if not normalized:
        return "未设置"
    return PERIOD_LABELS.get(normalized, normalized)


def _rolling_period_label(ship_date: date, start_day: int) -> str:
    y, m = ship_date.year, ship_date.month
    if ship_date.day >= start_day:
        m += 1
        if m > 12:
            y += 1
            m = 1
    return f"{y:04d}-{m:02d}"


def reconciliation_period_for_ship_date(ship_date: date, period_type: str) -> str:
    """返回对账期标签 YYYY-MM。"""
    mode = normalize_reconciliation_period(period_type, default=MONTH_21_20)
    if mode == CALENDAR_MONTH:
        return f"{ship_date.year:04d}-{ship_date.month:02d}"
    rolling = ROLLING_PERIODS.get(mode)
    if rolling:
        start_day, _, _ = rolling
        return _rolling_period_label(ship_date, start_day)
    return f"{ship_date.year:04d}-{ship_date.month:02d}"
