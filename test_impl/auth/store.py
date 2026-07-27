"""用户与操作审计 SQLite 表（与 wkt_orders.db 同库）。"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "wkt_orders.db"

_AUTH_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    is_active INTEGER NOT NULL DEFAULT 1,
    must_change_password INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_login_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT NOT NULL,
    display_name TEXT NOT NULL,
    action TEXT NOT NULL,
    module TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT '',
    entity_id TEXT NOT NULL DEFAULT '',
    summary TEXT NOT NULL,
    detail_json TEXT NOT NULL DEFAULT '',
    ip_address TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_username ON audit_log(username);
CREATE INDEX IF NOT EXISTS idx_audit_module ON audit_log(module);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
"""


def default_db_path() -> Path:
    env = os.environ.get("WKT_DB_PATH", "").strip()
    if env:
        return Path(env)
    return _DEFAULT_DB


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class UserRow:
    id: int
    username: str
    display_name: str
    password_hash: str
    role: str
    is_active: bool
    must_change_password: bool
    created_at: str
    updated_at: str
    last_login_at: str


@dataclass
class AuditRow:
    id: int
    user_id: Optional[int]
    username: str
    display_name: str
    action: str
    module: str
    entity_type: str
    entity_id: str
    summary: str
    detail_json: str
    ip_address: str
    created_at: str


class AuthStore:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path or default_db_path())
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._conn.executescript(_AUTH_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def count_users(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        return int(row["c"])

    def get_user_by_username(self, username: str) -> Optional[UserRow]:
        row = self._conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
            (username.strip(),),
        ).fetchone()
        return self._row_to_user(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[UserRow]:
        row = self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self._row_to_user(row) if row else None

    def list_users(self) -> List[UserRow]:
        rows = self._conn.execute(
            "SELECT * FROM users ORDER BY username COLLATE NOCASE"
        ).fetchall()
        return [self._row_to_user(r) for r in rows]

    def create_user(
        self,
        *,
        username: str,
        display_name: str,
        password_hash: str,
        role: str = "user",
        must_change_password: bool = False,
    ) -> UserRow:
        now = _utc_now()
        cur = self._conn.execute(
            """
            INSERT INTO users (
                username, display_name, password_hash, role, is_active,
                must_change_password, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 1, ?, ?, ?)
            """,
            (
                username.strip(),
                display_name.strip(),
                password_hash,
                role,
                1 if must_change_password else 0,
                now,
                now,
            ),
        )
        self._conn.commit()
        user = self.get_user_by_id(int(cur.lastrowid))
        assert user is not None
        return user

    def update_user_password(self, user_id: int, password_hash: str, *, must_change: bool = False) -> None:
        now = _utc_now()
        self._conn.execute(
            """
            UPDATE users
            SET password_hash = ?, must_change_password = ?, updated_at = ?
            WHERE id = ?
            """,
            (password_hash, 1 if must_change else 0, now, user_id),
        )
        self._conn.commit()

    def set_user_active(self, user_id: int, active: bool) -> None:
        now = _utc_now()
        self._conn.execute(
            "UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?",
            (1 if active else 0, now, user_id),
        )
        self._conn.commit()

    def update_user_profile(
        self,
        user_id: int,
        *,
        display_name: str,
        role: str,
    ) -> UserRow:
        now = _utc_now()
        self._conn.execute(
            """
            UPDATE users
            SET display_name = ?, role = ?, updated_at = ?
            WHERE id = ?
            """,
            (display_name.strip(), role, now, user_id),
        )
        self._conn.commit()
        user = self.get_user_by_id(user_id)
        assert user is not None
        return user

    def delete_user(self, user_id: int) -> None:
        self._conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self._conn.commit()

    def count_active_admins(self, *, exclude_user_id: Optional[int] = None) -> int:
        sql = "SELECT COUNT(*) AS c FROM users WHERE role = 'admin' AND is_active = 1"
        params: list[Any] = []
        if exclude_user_id is not None:
            sql += " AND id <> ?"
            params.append(int(exclude_user_id))
        row = self._conn.execute(sql, params).fetchone()
        return int(row["c"])

    def touch_login(self, user_id: int) -> None:
        now = _utc_now()
        self._conn.execute(
            "UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?",
            (now, now, user_id),
        )
        self._conn.commit()

    def insert_audit(
        self,
        *,
        user_id: Optional[int],
        username: str,
        display_name: str,
        action: str,
        module: str,
        summary: str,
        entity_type: str = "",
        entity_id: str = "",
        detail_json: str = "",
        ip_address: str = "",
    ) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO audit_log (
                user_id, username, display_name, action, module,
                entity_type, entity_id, summary, detail_json, ip_address, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                display_name,
                action,
                module,
                entity_type,
                entity_id,
                summary,
                detail_json,
                ip_address,
                _utc_now(),
            ),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def list_audit(
        self,
        *,
        username: str = "",
        module: str = "",
        action: str = "",
        date_from: str = "",
        date_to: str = "",
        limit: int = 200,
        offset: int = 0,
    ) -> List[AuditRow]:
        clauses = ["1=1"]
        params: List[Any] = []
        if username:
            clauses.append("username = ? COLLATE NOCASE")
            params.append(username)
        if module:
            clauses.append("module = ?")
            params.append(module)
        if action:
            clauses.append("action = ?")
            params.append(action)
        if date_from:
            clauses.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("created_at <= ?")
            params.append(date_to)
        where = " AND ".join(clauses)
        params.extend([limit, offset])
        rows = self._conn.execute(
            f"""
            SELECT * FROM audit_log
            WHERE {where}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            params,
        ).fetchall()
        return [self._row_to_audit(r) for r in rows]

    def count_audit(
        self,
        *,
        username: str = "",
        module: str = "",
        action: str = "",
        date_from: str = "",
        date_to: str = "",
    ) -> int:
        clauses = ["1=1"]
        params: List[Any] = []
        if username:
            clauses.append("username = ? COLLATE NOCASE")
            params.append(username)
        if module:
            clauses.append("module = ?")
            params.append(module)
        if action:
            clauses.append("action = ?")
            params.append(action)
        if date_from:
            clauses.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            clauses.append("created_at <= ?")
            params.append(date_to)
        where = " AND ".join(clauses)
        row = self._conn.execute(
            f"SELECT COUNT(*) AS c FROM audit_log WHERE {where}",
            params,
        ).fetchone()
        return int(row["c"])

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> UserRow:
        return UserRow(
            id=int(row["id"]),
            username=str(row["username"]),
            display_name=str(row["display_name"]),
            password_hash=str(row["password_hash"]),
            role=str(row["role"]),
            is_active=bool(row["is_active"]),
            must_change_password=bool(row["must_change_password"]),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            last_login_at=str(row["last_login_at"] or ""),
        )

    @staticmethod
    def _row_to_audit(row: sqlite3.Row) -> AuditRow:
        return AuditRow(
            id=int(row["id"]),
            user_id=int(row["user_id"]) if row["user_id"] is not None else None,
            username=str(row["username"]),
            display_name=str(row["display_name"]),
            action=str(row["action"]),
            module=str(row["module"]),
            entity_type=str(row["entity_type"] or ""),
            entity_id=str(row["entity_id"] or ""),
            summary=str(row["summary"]),
            detail_json=str(row["detail_json"] or ""),
            ip_address=str(row["ip_address"] or ""),
            created_at=str(row["created_at"]),
        )
