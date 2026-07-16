"""客户名称规范化：全角/半角括号、空格等视为同一客户。"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional

_PARENS = str.maketrans({"(": "（", ")": "）"})
_SPACE_RE = re.compile(r"\s+")


def normalize_customer_name(name: str) -> str:
    val = str(name or "").strip().translate(_PARENS)
    if not val:
        return ""
    return _SPACE_RE.sub("", val)


def customer_names_match(a: str, b: str) -> bool:
    left = normalize_customer_name(a).casefold()
    right = normalize_customer_name(b).casefold()
    return bool(left) and left == right


@lru_cache(maxsize=1)
def _profile_customer_names() -> tuple[str, ...]:
    path = Path(__file__).resolve().parents[2] / "data" / "customer_profiles.json"
    if not path.is_file():
        return ()
    import json

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    if not isinstance(data, dict):
        return ()
    return tuple(str(k).strip() for k in data if str(k).strip())


def pick_canonical_customer_name(candidates: Iterable[str]) -> str:
    """在多个写法中优先选 customer_profiles.json 里的标准全称。"""
    items = [str(c).strip() for c in candidates if str(c or "").strip()]
    if not items:
        return ""
    profiles = _profile_customer_names()
    profile_by_norm = {normalize_customer_name(p).casefold(): p for p in profiles}
    for item in sorted(items, key=lambda x: (-len(x), x)):
        hit = profile_by_norm.get(normalize_customer_name(item).casefold())
        if hit:
            return hit
    return max(items, key=lambda x: (len(x), x))


def dedupe_customer_names(names: Iterable[str]) -> List[str]:
    buckets: dict[str, str] = {}
    for raw in names:
        name = str(raw or "").strip()
        if not name:
            continue
        key = normalize_customer_name(name).casefold()
        prev = buckets.get(key)
        if prev is None:
            buckets[key] = name
            continue
        buckets[key] = pick_canonical_customer_name([prev, name])
    return sorted(buckets.values(), key=lambda x: (x.casefold(), x))
