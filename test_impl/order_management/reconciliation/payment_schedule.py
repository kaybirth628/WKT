"""账期与应付日计算（默认月结90天、25日付款）。"""
from __future__ import annotations

import calendar
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[3]
CONFIG_FILE = ROOT / "data" / "reconciliation_config.json"
CONFIG_EXAMPLE = ROOT / "data" / "reconciliation_config.example.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "terms_label": "月结90天",
    "payment_day": 25,
    "term_days": 90,
    "description": "",
}


def load_reconciliation_config() -> Dict[str, Any]:
    path = CONFIG_FILE if CONFIG_FILE.exists() else CONFIG_EXAMPLE
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                cfg = dict(DEFAULT_CONFIG)
                cfg.update(raw)
                return cfg
        except (OSError, ValueError):
            pass
    return dict(DEFAULT_CONFIG)


def parse_ship_local_date(shipped_at: datetime | str) -> date:
    if isinstance(shipped_at, str):
        text = shipped_at.strip()
        if not text:
            return date.today()
        try:
            shipped_at = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return date.fromisoformat(text[:10])
    if shipped_at.tzinfo is not None:
        shipped_at = shipped_at.astimezone(timezone.utc)
    return shipped_at.date()


def compute_payment_due_date(
    ship_date: date,
    *,
    payment_day: int = 25,
    term_days: int = 90,
) -> date:
    """
    月结 N 天：从出货月最后一天 + term_days，应付日为 payment_day 日。
    若起算日落点所在月的 payment_day 已过，则顺延至下月 payment_day。
    例：1月出货 → 1/31+90=5/1 → 5月25日应付。
    """
    payment_day = max(1, min(int(payment_day), 28))
    term_days = max(1, int(term_days))
    last_day = calendar.monthrange(ship_date.year, ship_date.month)[1]
    month_end = date(ship_date.year, ship_date.month, last_day)
    anchor = month_end + timedelta(days=term_days)
    y, m = anchor.year, anchor.month
    if anchor.day > payment_day:
        m += 1
        if m > 12:
            y += 1
            m = 1
    last_pay = calendar.monthrange(y, m)[1]
    day = min(payment_day, last_pay)
    return date(y, m, day)


def payment_due_month_label(due_date: date) -> str:
    return f"{due_date.year:04d}-{due_date.month:02d}"


def format_terms_label(cfg: Dict[str, Any] | None = None) -> str:
    cfg = cfg or load_reconciliation_config()
    label = str(cfg.get("terms_label") or "月结90天").strip()
    day = int(cfg.get("payment_day") or 25)
    return f"{label}·每月{day}日付款"
