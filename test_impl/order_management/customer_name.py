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


def _profile_match_key(name: str) -> str:
    """将简称/全称映射到 customer_profiles 中的同一客户键（用于 BOM 与订单客户比对）。"""
    norm = normalize_customer_name(name).casefold()
    if not norm:
        return ""
    matches: list[str] = []
    for profile in _profile_customer_names():
        pnorm = normalize_customer_name(profile).casefold()
        if norm == pnorm or pnorm.startswith(norm) or norm.startswith(pnorm):
            matches.append(profile)
    if len(matches) == 1:
        return normalize_customer_name(matches[0]).casefold()
    return norm


def customer_names_match(a: str, b: str) -> bool:
    left = normalize_customer_name(a).casefold()
    right = normalize_customer_name(b).casefold()
    if left and left == right:
        return True
    key_a = _profile_match_key(a)
    key_b = _profile_match_key(b)
    return bool(key_a) and key_a == key_b


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


_FILENAME_BOM_SUFFIX_RE = re.compile(r"(?i)(?:新产品)?BOM表?$|产品BOM表?$|BOM格式$")
_FILENAME_BOM_TAIL_RE = re.compile(r"(?i)_?BOM$")

# 文件名简称 → 客商档案全称（BOM 批量导入确认）
_FILENAME_CUSTOMER_ALIASES: dict[str, str] = {
    "日月照明": "江苏日月照明电器有限公司",
    "欧菲光": "安徽欧菲智能车联科技有限公司",
    "红黑": "浙江红黑科技有限公司",
}


def extract_customer_hint_from_filename(filename: str) -> str:
    """从上传文件名提取客户简称，如「东硕BOM.xls」→「东硕」。"""
    stem = Path(filename or "").stem.strip()
    if not stem:
        return ""
    prev = None
    while prev != stem:
        prev = stem
        stem = _FILENAME_BOM_SUFFIX_RE.sub("", stem).strip()
        stem = _FILENAME_BOM_TAIL_RE.sub("", stem).strip()
    return stem


def resolve_customer_from_hint(
    hint: str,
    known_customers: Iterable[str],
) -> tuple[Optional[str], str]:
    """将文件名简称匹配到系统客户全称；返回 (客户名, 错误说明)。"""
    hint = str(hint or "").strip()
    if not hint:
        return None, "无法从文件名识别客户简称，请使用如「东硕BOM.xlsx」的命名"
    customers = dedupe_customer_names(known_customers)
    if not customers:
        return None, "系统尚无客户档案，请先在客商信息维护中建立客户"

    hint_norm = normalize_customer_name(hint).casefold()
    alias_target = _FILENAME_CUSTOMER_ALIASES.get(hint)
    if alias_target:
        alias_norm = normalize_customer_name(alias_target).casefold()
        for name in customers:
            if normalize_customer_name(name).casefold() == alias_norm:
                return name, ""
        return alias_target, ""

    matches: List[str] = []

    for name in customers:
        name_norm = normalize_customer_name(name).casefold()
        if hint_norm == name_norm:
            matches.append(name)
            continue
        if customer_names_match(hint, name):
            matches.append(name)
            continue
        parts = re.split(r"[-－—]", str(name))
        matched = False
        for part in parts:
            part_norm = normalize_customer_name(part).casefold()
            if part_norm == hint_norm:
                matches.append(name)
                matched = True
                break
        if matched:
            continue
        if len(parts) >= 2:
            last_norm = normalize_customer_name(parts[-1]).casefold()
            if last_norm == hint_norm:
                matches.append(name)

    matches = dedupe_customer_names(matches)
    if len(matches) == 1:
        return matches[0], ""
    if len(matches) > 1:
        joined = "、".join(matches[:5])
        extra = f" 等{len(matches)}个" if len(matches) > 5 else ""
        return (
            None,
            f"文件名「{hint}」匹配多个客户（{joined}{extra}），请改用更明确的文件名",
        )
    return None, f"未找到客户「{hint}」，请先在客商信息维护中建立客户档案后再导入 BOM"
