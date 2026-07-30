"""供应商档案 JSON 存储。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from test_impl.order_management.reconciliation.period import (
    DEFAULT_SUPPLIER_RECONCILIATION_PERIOD,
    normalize_reconciliation_period,
    reconciliation_period_label,
)

ROOT = Path(__file__).resolve().parents[3]
PROFILES_FILE = ROOT / "data" / "supplier_profiles.json"
PROFILES_EXAMPLE = ROOT / "data" / "supplier_profiles.example.json"

PROFILE_FIELDS = (
    "address",
    "contact",
    "phone",
    "email",
    "payment_terms",
    "notes",
    "reconciliation_period",
)

EMPTY_PROFILE: Dict[str, str] = {k: "" for k in PROFILE_FIELDS}
EMPTY_PROFILE["reconciliation_period"] = DEFAULT_SUPPLIER_RECONCILIATION_PERIOD
EMPTY_PROFILE["created_at"] = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _created_sort_key(created_at: str, json_index: int, name: str) -> tuple:
    ca = (created_at or "").strip()
    if ca:
        return (ca, name.casefold())
    return (f"1970-01-01T00:00:00.{json_index:06d}Z", name.casefold())


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
    row["reconciliation_period"] = normalize_reconciliation_period(
        period_raw,
        default=DEFAULT_SUPPLIER_RECONCILIATION_PERIOD,
    )
    row["created_at"] = str(src.get("created_at") or "").strip()
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


def get_profile(supplier: str) -> Dict[str, str]:
    supplier = (supplier or "").strip()
    if not supplier:
        return dict(EMPTY_PROFILE)
    all_cfg = load_all_profiles()
    return dict(all_cfg.get(supplier, EMPTY_PROFILE))


def save_profile(supplier: str, info: dict, *, new_supplier: str = "") -> Dict[str, str]:
    old_name = (supplier or "").strip()
    new_name = (new_supplier or old_name).strip()
    if not new_name:
        raise ValueError("供应商名称不能为空")
    row = _normalize_row(info)
    all_cfg = load_all_profiles()
    old_key = _resolve_profile_key(all_cfg, old_name) if old_name else None

    if old_key:
        prev = all_cfg[old_key]
        row["created_at"] = str(prev.get("created_at") or row.get("created_at") or "").strip()
    elif not row.get("created_at"):
        row["created_at"] = _now_iso()

    dest = new_name
    if old_key and dest.casefold() != old_key.casefold():
        for key in all_cfg:
            if key.casefold() == dest.casefold():
                raise ValueError(f"供应商「{dest}」已存在")
        del all_cfg[old_key]
    elif not old_key:
        for key in all_cfg:
            if key.casefold() == dest.casefold():
                raise ValueError(f"供应商「{dest}」已存在")

    all_cfg[dest] = row
    PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_FILE.write_text(
        json.dumps(all_cfg, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return row


def list_profile_suppliers() -> List[str]:
    raw = _load_raw()
    items: List[tuple[str, Dict[str, str], int]] = []
    for idx, (key, val) in enumerate(raw.items()):
        name = str(key or "").strip()
        if not name:
            continue
        items.append((name, _normalize_row(val if isinstance(val, dict) else {}), idx))
    items.sort(key=lambda t: _created_sort_key(t[1].get("created_at", ""), t[2], t[0]), reverse=True)
    return [name for name, _, _ in items]


def resolve_supplier_name(raw: str) -> tuple[str, str | None]:
    """BOM 表常见简称 → supplier_profiles 全称。返回 (解析后名称, 可选提示)。"""
    s = (raw or "").strip()
    if not s:
        return "", None

    profiles = load_all_profiles()
    if not profiles:
        return s, None

    folded = s.casefold()
    for key in profiles:
        if key.casefold() == folded:
            return key, None

    if len(s) >= 2:
        contains = [k for k in profiles if folded in k.casefold()]
        if len(contains) == 1:
            canonical = contains[0]
            if canonical != s:
                return canonical, f"供应商「{s}」已匹配为「{canonical}」"
            return canonical, None
        if len(contains) > 1:
            best = _pick_supplier_substring_match(s, contains)
            if best:
                return best, f"供应商「{s}」已匹配为「{best}」"
            return s, f"供应商「{s}」对应多家({len(contains)}个)，请改全称"

    if len(s) >= 4:
        contained_in = [k for k in profiles if k.casefold() in folded]
        if len(contained_in) == 1:
            canonical = contained_in[0]
            return canonical, f"供应商「{s}」已匹配为「{canonical}」"

    notes_hits = [
        k
        for k, row in profiles.items()
        if folded in str(row.get("notes") or "").casefold()
    ]
    if len(notes_hits) == 1:
        canonical = notes_hits[0]
        return canonical, f"供应商「{s}」按备注匹配为「{canonical}」"

    return s, f"供应商「{s}」未在供应商列表中找到，请维护全称或补充档案"


def _pick_supplier_substring_match(needle: str, candidates: List[str]) -> str | None:
    """多家含同一简称时：优先更短全称，再比简称出现位置靠后（常见公司名字尾）。"""
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    folded = needle.casefold()

    def rank(name: str) -> tuple:
        pos = name.casefold().rfind(folded)
        return (len(name), -pos)

    ranked = sorted(candidates, key=rank)
    best = ranked[0]
    if len(ranked) > 1 and rank(best) == rank(ranked[1]):
        return None
    return best


def _resolve_profile_key(all_cfg: Dict[str, dict], name: str) -> str | None:
    target = (name or "").strip().casefold()
    if not target:
        return None
    for key in all_cfg:
        if str(key).strip().casefold() == target:
            return str(key)
    return None


def delete_profile(supplier: str) -> None:
    supplier = (supplier or "").strip()
    if not supplier:
        raise ValueError("供应商名称不能为空")
    all_cfg = load_all_profiles()
    key = _resolve_profile_key(all_cfg, supplier)
    if not key:
        raise ValueError(f"供应商「{supplier}」不存在")
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
