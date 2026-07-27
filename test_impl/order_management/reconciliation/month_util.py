"""对账月份工具。"""
from __future__ import annotations

from datetime import date
from typing import List, Tuple


def this_and_next_month() -> Tuple[str, str]:
    today = date.today()
    this_m = f"{today.year:04d}-{today.month:02d}"
    if today.month == 12:
        next_m = f"{today.year + 1}-01"
    else:
        next_m = f"{today.year:04d}-{today.month + 1:02d}"
    return this_m, next_m


def rolling_due_months(count: int = 6, *, from_date: date | None = None) -> List[str]:
    """从当月起重连续 count 个 YYYY-MM。"""
    today = from_date or date.today()
    y, m = today.year, today.month
    out: List[str] = []
    for _ in range(max(1, int(count))):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


def month_display_label(month: str) -> str:
    text = (month or "").strip()
    if len(text) >= 7 and text[4] == "-":
        try:
            return f"{text[:4]}年{int(text[5:7])}月"
        except ValueError:
            pass
    return text
