from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from test_impl.order_management.order_entry.line_store import default_db_path

from .deepseek_client import DeepSeekChatClient, DeepSeekClientError

_FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|ATTACH|DETACH|VACUUM|REINDEX|PRAGMA)\b",
    re.IGNORECASE,
)
_SELECT_START = re.compile(r"^(SELECT|WITH)\b", re.IGNORECASE | re.DOTALL)

_MAX_ROWS = 200
_MAX_CELL = 500

_SCHEMA_HINTS = """
业务说明（SQLite）：
- order_lines：订单行（一料号一行）。po_qty=订单数量，shipped_qty=已出货，未结数量=po_qty-shipped_qty。
  closure_type 为空=正常流程；'forced'=强制结案（可能仍有未结数量）。
  order_date/delivery_date 为文本日期 YYYY-MM-DD；金额字段多为 TEXT 存数字。
- shipment_events：出货记录。line_id 关联 order_lines.id；ship_qty=本次出货数量；
  shipped_at=出货时间 ISO 文本；source 如 open_ship；delivery_note_json 为送货单 JSON 快照。
- customers：客户主数据（name 唯一）。
- parts：品名规格与客户料号映射（product_spec 唯一）。
"""

_SQL_SYSTEM = (
    "你是 WKT 销售管理系统的数据库分析助手。根据用户问题生成只读 SQLite 查询。\n"
    "只输出 JSON 对象，不要 markdown，不要解释性段落。\n"
    "格式：{\"sql\": \"一条 SELECT 语句\", \"note\": \"一句话说明查询意图\"}\n"
    "规则：\n"
    "1. 仅允许 SELECT（可用 WITH 子句）；禁止修改数据。\n"
    "2. 单条语句；不要分号后接第二条语句。\n"
    "3. 尽量 LIMIT 200 以内；需要聚合时用 GROUP BY。\n"
    "4. 日期比较可用字符串比较（字段为 TEXT）。\n"
    "5. 无法查询时 sql 留空字符串，note 说明原因。\n"
    "数据库结构：\n"
)

_ANSWER_SYSTEM = (
    "你是 WKT 销售管理系统的 AI 助手。根据用户问题、执行的 SQL 与查询结果，"
    "用简洁中文回答。若结果为空说明可能无匹配数据。数字可格式化。"
    "不要编造未出现在结果中的数据。可简要说明查询逻辑。"
)


class DatabaseAssistantError(Exception):
    pass


def validate_readonly_sql(sql: str) -> str:
    text = (sql or "").strip()
    if not text:
        raise DatabaseAssistantError("模型未生成有效 SQL")
    if ";" in text.rstrip(";"):
        raise DatabaseAssistantError("仅允许单条查询语句")
    text = text.rstrip(";").strip()
    if _FORBIDDEN_SQL.search(text):
        raise DatabaseAssistantError("仅允许 SELECT 只读查询")
    if not _SELECT_START.match(text):
        raise DatabaseAssistantError("仅允许 SELECT / WITH 查询")
    return text


def _ensure_limit(sql: str, max_rows: int = _MAX_ROWS) -> str:
    if re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        return sql
    return f"{sql} LIMIT {max_rows}"


def build_schema_description(db_path: Path | str) -> str:
    conn = sqlite3.connect(str(db_path))
    try:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        lines: List[str] = []
        for name in tables:
            cols = conn.execute(f"PRAGMA table_info({name})").fetchall()
            col_text = ", ".join(f"{c[1]} {c[2] or 'TEXT'}" for c in cols)
            lines.append(f"- {name}: {col_text}")
        return "\n".join(lines) + "\n" + _SCHEMA_HINTS
    finally:
        conn.close()


def execute_readonly_query(db_path: Path | str, sql: str) -> Tuple[List[str], List[Dict[str, Any]], bool]:
    safe_sql = validate_readonly_sql(sql)
    safe_sql = _ensure_limit(safe_sql)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(safe_sql)
        if cur.description is None:
            return [], [], False
        columns = [d[0] for d in cur.description]
        rows: List[Dict[str, Any]] = []
        truncated = False
        for i, row in enumerate(cur):
            if i >= _MAX_ROWS:
                truncated = True
                break
            item: Dict[str, Any] = {}
            for col in columns:
                val = row[col]
                if val is None:
                    item[col] = None
                else:
                    s = str(val)
                    item[col] = s[:_MAX_CELL] + ("…" if len(s) > _MAX_CELL else "")
            rows.append(item)
        return columns, rows, truncated
    finally:
        conn.close()


class DatabaseAssistant:
    def __init__(
        self,
        db_path: Optional[Path | str] = None,
        client: Optional[DeepSeekChatClient] = None,
    ) -> None:
        self.db_path = Path(db_path or default_db_path())
        self.client = client or DeepSeekChatClient()

    def is_configured(self) -> bool:
        return self.client.is_configured()

    def ask(self, message: str, history: Optional[List[dict[str, str]]] = None) -> dict:
        message = (message or "").strip()
        if not message:
            raise DatabaseAssistantError("请输入问题")
        if not self.is_configured():
            raise DatabaseAssistantError(
                "未配置 DeepSeek API Key。请在 config/secrets.local.json 填写 deepseek_api_key"
            )

        schema = build_schema_description(self.db_path)
        history = history or []

        sql_payload = self._generate_sql(message, history, schema)
        sql = str(sql_payload.get("sql") or "").strip()
        sql_note = str(sql_payload.get("note") or "").strip()

        columns: List[str] = []
        rows: List[Dict[str, Any]] = []
        truncated = False
        executed_sql = ""

        if sql:
            executed_sql = _ensure_limit(validate_readonly_sql(sql))
            columns, rows, truncated = execute_readonly_query(self.db_path, sql)

        answer = self._summarize(message, history, executed_sql, columns, rows, sql_note, truncated)

        return {
            "answer": answer,
            "sql": executed_sql,
            "sql_note": sql_note,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": truncated,
        }

    def _generate_sql(
        self, message: str, history: List[dict[str, str]], schema: str
    ) -> dict:
        messages: List[dict[str, str]] = [
            {"role": "system", "content": _SQL_SYSTEM + schema},
        ]
        for item in history[-6:]:
            role = item.get("role") or "user"
            content = str(item.get("content") or "").strip()
            if content and role in ("user", "assistant"):
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        try:
            raw = self.client.chat(
                messages,
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=2048,
            )
            return self.client.parse_json_object(raw)
        except DeepSeekClientError as exc:
            raise DatabaseAssistantError(str(exc)) from exc

    def _summarize(
        self,
        message: str,
        history: List[dict[str, str]],
        sql: str,
        columns: List[str],
        rows: List[Dict[str, Any]],
        sql_note: str,
        truncated: bool,
    ) -> str:
        preview_rows = rows[:30]
        payload = {
            "question": message,
            "sql": sql,
            "sql_note": sql_note,
            "truncated": truncated,
            "row_count": len(rows),
            "columns": columns,
            "rows": preview_rows,
        }
        messages: List[dict[str, str]] = [
            {"role": "system", "content": _ANSWER_SYSTEM},
        ]
        for item in history[-4:]:
            role = item.get("role") or "user"
            content = str(item.get("content") or "").strip()
            if content and role in ("user", "assistant"):
                messages.append({"role": role, "content": content})
        messages.append(
            {
                "role": "user",
                "content": "用户问题与查询结果 JSON：\n" + str(payload),
            }
        )
        try:
            return self.client.chat(messages, temperature=0.2, max_tokens=2048)
        except DeepSeekClientError as exc:
            if rows:
                return f"查询完成，共 {len(rows)} 行（回答生成失败：{exc}）"
            return sql_note or str(exc)
