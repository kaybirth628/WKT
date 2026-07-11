"""客户档案（地址、联系、账期、对账周期等）JSON 存储。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from test_impl.order_management.reconciliation.period import (
    normalize_reconciliation_period,
    reconciliation_period_label,
)

ROOT = Path(__file__).resolve().parents[3]
PROFILES_FILE = ROOT / "data" / "customer_profiles.json"
PROFILES_EXAMPLE = ROOT / "data" / "customer_profiles.example.json"

PROFILE_FIELDS = (
    "address",
    "contact",
    "phone",
    "email",
    "payment_terms",
    "reconciliation_period",
    "delivery_enabled",
)

EMPTY_PROFILE: Dict[str, str] = {k: "" for k in PROFILE_FIELDS}
EMPTY_PROFILE["delivery_enabled"] = "1"


def is_delivery_enabled(profile: dict | None) -> bool:
    """未配置时默认启用送货单（兼容旧档案）。"""
    if not profile:
        return True
    val = str(profile.get("delivery_enabled") or "").strip().lower()
    if not val:
        return True
    if val in ("0", "false", "no", "off", "否", "不用", "disabled"):
        return False
    return True


def _load_raw() -> Dict[str, dict]:
    path = PROFILES_FILE if PROFILES_FILE.exists() else PROFILES_EXAMPLE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _normalize_row(raw: dict | None) -> Dict[str, str]:
    src = raw if isinstance(raw, dict) else {}
    row = {k: str(src.get(k) or "").strip() for k in PROFILE_FIELDS if k != "reconciliation_period"}
    period_raw = src.get("reconciliation_period") or src.get("reconciliation_cycle")
    row["reconciliation_period"] = normalize_reconciliation_period(period_raw, default="")
    return row


def load_all_profiles() -> Dict[str, Dict[str, str]]:
    raw = _load_raw()
    out: Dict[str, Dict[str, str]] = {}
    for key, val in raw.items():
        name = str(key or "").strip()
        if not name:
            continue
        out[name] = _normalize_row(val if isinstance(val, dict) else {})
    return out


def get_profile(customer: str) -> Dict[str, str]:
    customer = (customer or "").strip()
    if not customer:
        return dict(EMPTY_PROFILE)
    all_cfg = load_all_profiles()
    return dict(all_cfg.get(customer, EMPTY_PROFILE))


def save_profile(customer: str, info: dict) -> Dict[str, str]:
    customer = (customer or "").strip()
    if not customer:
        raise ValueError("客户名称不能为空")
    all_cfg = load_all_profiles()
    row = _normalize_row(info)
    period = normalize_reconciliation_period(row.get("reconciliation_period"), default="")
    if customer not in all_cfg and not period:
        raise ValueError("请选择对账周期")
    row["reconciliation_period"] = period
    all_cfg[customer] = row
    PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_FILE.write_text(
        json.dumps(all_cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return row


def list_profile_customers() -> List[str]:
    return sorted(load_all_profiles().keys(), key=lambda x: (x.casefold(), x))


def _resolve_profile_key(all_cfg: Dict[str, dict], name: str) -> str | None:
    target = (name or "").strip().casefold()
    if not target:
        return None
    for key in all_cfg:
        if str(key).strip().casefold() == target:
            return str(key)
    return None


def delete_profile(customer: str) -> None:
    customer = (customer or "").strip()
    if not customer:
        raise ValueError("客户名称不能为空")
    all_cfg = load_all_profiles()
    key = _resolve_profile_key(all_cfg, customer)
    if not key:
        raise ValueError(f"客户「{customer}」档案不存在")
    del all_cfg[key]
    PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_FILE.write_text(
        json.dumps(all_cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def profile_with_labels(profile: Dict[str, str]) -> Dict[str, str]:
    out = dict(profile)
    out["reconciliation_period_label"] = reconciliation_period_label(profile.get("reconciliation_period"))
    return out
