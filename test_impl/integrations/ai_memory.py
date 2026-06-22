from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
MEMORY_FILE = ROOT / "data" / "ai_assistant_memory.json"
MEMORY_EXAMPLE = ROOT / "data" / "ai_assistant_memory.example.json"

DEFAULT_MEMORY: Dict[str, Any] = {
    "version": 1,
    "business_rules": [
        "用户说「X月出货」「本月出货」按 shipment_events.shipped_at 统计，不是 order_lines.order_date。",
        "用户未写年份时默认当前年份，禁止臆测 2024 等历史年份。",
        "「未结订单」：open_qty > 0 且 closure_type 不是 forced。",
        "「正常结案」：出货清零且 closure_type 为空；「强制结案」：closure_type = forced。",
    ],
    "glossary": {
        "出货": "shipment_events 表，按 shipped_at 时间",
        "结单": "结案订单，含正常结案与强制结案",
    },
    "query_examples": [
        {
            "question": "6月份出货多少",
            "note": "SELECT 汇总 ship_qty，WHERE substr(shipped_at,1,7)='2026-06'",
        }
    ],
    "custom_prompt": "",
    "updated_at": "",
}


def memory_file_path() -> Path:
    env = os.environ.get("WKT_AI_MEMORY_PATH", "").strip()
    if env:
        return Path(env)
    return MEMORY_FILE


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_memory(raw: Optional[dict]) -> Dict[str, Any]:
    data = dict(DEFAULT_MEMORY)
    if not raw:
        return data
    if isinstance(raw.get("business_rules"), list):
        data["business_rules"] = [str(x).strip() for x in raw["business_rules"] if str(x).strip()]
    if isinstance(raw.get("glossary"), dict):
        data["glossary"] = {
            str(k).strip(): str(v).strip()
            for k, v in raw["glossary"].items()
            if str(k).strip() and str(v).strip()
        }
    if isinstance(raw.get("query_examples"), list):
        examples: List[dict] = []
        for item in raw["query_examples"]:
            if not isinstance(item, dict):
                continue
            q = str(item.get("question") or "").strip()
            n = str(item.get("note") or "").strip()
            if q:
                examples.append({"question": q, "note": n})
        data["query_examples"] = examples
    if raw.get("custom_prompt") is not None:
        data["custom_prompt"] = str(raw.get("custom_prompt") or "").strip()
    data["updated_at"] = str(raw.get("updated_at") or "") or _now_iso()
    return data


def load_memory() -> Dict[str, Any]:
    path = memory_file_path()
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return _normalize_memory(raw if isinstance(raw, dict) else None)
        except (OSError, ValueError):
            pass
    if MEMORY_EXAMPLE.exists():
        try:
            raw = json.loads(MEMORY_EXAMPLE.read_text(encoding="utf-8"))
            data = _normalize_memory(raw if isinstance(raw, dict) else None)
            save_memory(data)
            return data
        except (OSError, ValueError):
            pass
    data = _normalize_memory(None)
    save_memory(data)
    return data


def save_memory(data: Dict[str, Any]) -> Path:
    path = memory_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_memory(data)
    normalized["updated_at"] = _now_iso()
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def append_business_rule(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("记忆内容不能为空")
    data = load_memory()
    rules = data.get("business_rules") or []
    if text not in rules:
        rules.append(text)
    data["business_rules"] = rules
    save_memory(data)
    return data


def append_glossary(term: str, meaning: str) -> Dict[str, Any]:
    term = (term or "").strip()
    meaning = (meaning or "").strip()
    if not term or not meaning:
        raise ValueError("术语与解释均不能为空")
    data = load_memory()
    glossary = dict(data.get("glossary") or {})
    glossary[term] = meaning
    data["glossary"] = glossary
    save_memory(data)
    return data


def append_query_example(question: str, note: str = "") -> Dict[str, Any]:
    question = (question or "").strip()
    note = (note or "").strip()
    if not question:
        raise ValueError("示例问题不能为空")
    data = load_memory()
    examples = list(data.get("query_examples") or [])
    examples.append({"question": question, "note": note})
    if len(examples) > 50:
        examples = examples[-50:]
    data["query_examples"] = examples
    save_memory(data)
    return data


def format_memory_for_prompt(memory: Optional[Dict[str, Any]] = None) -> str:
    data = memory or load_memory()
    lines: List[str] = ["【业务记忆（长期有效，每次查询都会参考）】"]

    custom = str(data.get("custom_prompt") or "").strip()
    if custom:
        lines.append("补充说明：" + custom)

    rules = data.get("business_rules") or []
    if rules:
        lines.append("业务规则：")
        for i, rule in enumerate(rules, 1):
            lines.append(f"{i}. {rule}")

    glossary = data.get("glossary") or {}
    if glossary:
        lines.append("术语对照：")
        for term, meaning in glossary.items():
            lines.append(f"- 「{term}」→ {meaning}")

    examples = data.get("query_examples") or []
    if examples:
        lines.append("问法示例：")
        for ex in examples[-15:]:
            q = ex.get("question", "")
            n = ex.get("note", "")
            line = f"- 问：{q}"
            if n:
                line += f"（{n}）"
            lines.append(line)

    updated = str(data.get("updated_at") or "")
    if updated:
        lines.append(f"记忆更新时间：{updated}")

    return "\n".join(lines)


def memory_to_api_dict(memory: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = memory or load_memory()
    return {
        "business_rules": list(data.get("business_rules") or []),
        "glossary": dict(data.get("glossary") or {}),
        "query_examples": list(data.get("query_examples") or []),
        "custom_prompt": str(data.get("custom_prompt") or ""),
        "updated_at": str(data.get("updated_at") or ""),
        "path": str(memory_file_path()),
    }
