"""客户档案（地址、联系、账期、对账周期等）JSON 存储。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[3]
PROFILES_FILE = ROOT / "data" / "customer_profiles.json"
PROFILES_EXAMPLE = ROOT / "data" / "customer_profiles.example.json"

PROFILE_FIELDS = (
    "address",
    "contact",
    "phone",
    "email",
    "payment_terms",
    "reconciliation_cycle",
)

EMPTY_PROFILE: Dict[str, str] = {k: "" for k in PROFILE_FIELDS}


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
    return {k: str(src.get(k) or "").strip() for k in PROFILE_FIELDS}


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
    row = _normalize_row(info)
    all_cfg = load_all_profiles()
    all_cfg[customer] = row
    PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_FILE.write_text(
        json.dumps(all_cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return row


def list_profile_customers() -> List[str]:
    return sorted(load_all_profiles().keys(), key=lambda x: (x.casefold(), x))
