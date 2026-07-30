"""登录、用户管理、操作审计业务逻辑。"""
from __future__ import annotations

import json
import os
import secrets
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from werkzeug.security import check_password_hash, generate_password_hash

from .audit_labels import action_label, module_label
from .store import AuditRow, AuthStore, UserRow

ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_BOOTSTRAP_PASSWORD = "WKT@2026"


class AuthError(ValueError):
    pass


class AuthService:
    def __init__(self, store: Optional[AuthStore] = None) -> None:
        self._store = store or AuthStore()
        self._ensure_bootstrap_admin()

    @property
    def store(self) -> AuthStore:
        return self._store

    def _ensure_bootstrap_admin(self) -> None:
        if self._store.count_users() > 0:
            return
        password = os.environ.get("WKT_BOOTSTRAP_PASSWORD", _DEFAULT_BOOTSTRAP_PASSWORD).strip()
        self._store.create_user(
            username="admin",
            display_name="系统管理员",
            password_hash=generate_password_hash(password),
            role="admin",
            must_change_password=True,
        )

    def authenticate(self, username: str, password: str) -> UserRow:
        user = self._store.get_user_by_username(username)
        if not user or not user.is_active:
            raise AuthError("用户名或密码错误")
        if not check_password_hash(user.password_hash, password):
            raise AuthError("用户名或密码错误")
        self._store.touch_login(user.id)
        refreshed = self._store.get_user_by_id(user.id)
        assert refreshed is not None
        return refreshed

    def create_user(
        self,
        *,
        username: str,
        display_name: str,
        password: str,
        role: str = "user",
    ) -> Dict[str, Any]:
        username = username.strip()
        if not username:
            raise AuthError("用户名不能为空")
        if self._store.get_user_by_username(username):
            raise AuthError("用户名已存在")
        if role not in ("admin", "user"):
            raise AuthError("角色无效")
        if len(password) < 6:
            raise AuthError("密码至少 6 位")
        user = self._store.create_user(
            username=username,
            display_name=display_name.strip() or username,
            password_hash=generate_password_hash(password),
            role=role,
        )
        return user_to_public(user)

    def change_password(
        self,
        user_id: int,
        *,
        old_password: str,
        new_password: str,
    ) -> None:
        user = self._store.get_user_by_id(user_id)
        if not user or not user.is_active:
            raise AuthError("用户不存在")
        if not check_password_hash(user.password_hash, old_password):
            raise AuthError("原密码错误")
        if len(new_password) < 6:
            raise AuthError("新密码至少 6 位")
        self._store.update_user_password(user_id, generate_password_hash(new_password))

    def admin_reset_password(self, user_id: int, new_password: str) -> None:
        user = self._store.get_user_by_id(user_id)
        if not user:
            raise AuthError("用户不存在")
        if len(new_password) < 6:
            raise AuthError("密码至少 6 位")
        self._store.update_user_password(
            user_id,
            generate_password_hash(new_password),
            must_change=True,
        )

    def set_active(self, user_id: int, active: bool) -> None:
        user = self._store.get_user_by_id(user_id)
        if not user:
            raise AuthError("用户不存在")
        if user.username.lower() == "admin" and not active:
            raise AuthError("不能禁用 admin 账号")
        self._store.set_user_active(user_id, active)

    def update_user(
        self,
        user_id: int,
        *,
        display_name: str,
        role: str,
    ) -> Dict[str, Any]:
        user = self._store.get_user_by_id(user_id)
        if not user:
            raise AuthError("用户不存在")
        name = display_name.strip()
        if not name:
            raise AuthError("姓名不能为空")
        if role not in ("admin", "user"):
            raise AuthError("角色无效")
        if user.username.lower() == "admin" and role != "admin":
            raise AuthError("不能修改 admin 账号的角色")
        if user.role == "admin" and role != "admin":
            if self._store.count_active_admins(exclude_user_id=user_id) < 1:
                raise AuthError("至少保留一名管理员")
        updated = self._store.update_user_profile(user_id, display_name=name, role=role)
        return user_to_public(updated)

    def delete_user(self, user_id: int, *, actor_user_id: int) -> None:
        if user_id == actor_user_id:
            raise AuthError("不能删除当前登录账号")
        user = self._store.get_user_by_id(user_id)
        if not user:
            raise AuthError("用户不存在")
        if user.username.lower() == "admin":
            raise AuthError("不能删除 admin 账号")
        if user.role == "admin" and self._store.count_active_admins(exclude_user_id=user_id) < 1:
            raise AuthError("至少保留一名管理员")
        self._store.delete_user(user_id)

    def list_users_public(self) -> List[Dict[str, Any]]:
        return [user_to_public(u) for u in self._store.list_users()]


class AuditService:
    def __init__(self, store: Optional[AuthStore] = None) -> None:
        self._store = store or AuthStore()

    def _resolve_operator(self, user: Optional[Dict[str, Any]]) -> tuple[Optional[int], str, str]:
        username = str((user or {}).get("username") or "system").strip() or "system"
        display_name = str((user or {}).get("display_name") or username).strip() or username
        user_id = (user or {}).get("id")
        uid = int(user_id) if user_id is not None else None
        if uid is not None:
            row = self._store.get_user_by_id(uid)
            if row:
                return row.id, row.username, row.display_name
        if username.lower() != "system":
            row = self._store.get_user_by_username(username)
            if row:
                return row.id, row.username, row.display_name
        return uid, username, display_name

    def _display_name_map(self) -> tuple[Dict[int, str], Dict[str, str]]:
        by_id: Dict[int, str] = {}
        by_username: Dict[str, str] = {}
        for user in self._store.list_users():
            by_id[user.id] = user.display_name
            by_username[user.username.casefold()] = user.display_name
        return by_id, by_username

    @staticmethod
    def _resolve_audit_display_name(
        row: AuditRow,
        *,
        by_id: Dict[int, str],
        by_username: Dict[str, str],
    ) -> str:
        if row.user_id is not None and row.user_id in by_id:
            return by_id[row.user_id]
        key = row.username.casefold()
        if key in by_username:
            return by_username[key]
        snap = str(row.display_name or "").strip()
        if snap and snap.casefold() != key:
            return snap
        return snap or row.username

    def log(
        self,
        *,
        user: Optional[Dict[str, Any]],
        action: str,
        module: str,
        summary: str,
        entity_type: str = "",
        entity_id: str = "",
        detail: Optional[Dict[str, Any]] = None,
        ip_address: str = "",
    ) -> int:
        user_id, username, display_name = self._resolve_operator(user)
        detail_json = json.dumps(detail or {}, ensure_ascii=False)
        return self._store.insert_audit(
            user_id=user_id,
            username=username,
            display_name=display_name,
            action=action,
            module=module,
            summary=summary[:500],
            entity_type=entity_type,
            entity_id=str(entity_id or ""),
            detail_json=detail_json,
            ip_address=ip_address,
        )

    def query(
        self,
        *,
        username: str = "",
        module: str = "",
        action: str = "",
        date_from: str = "",
        date_to: str = "",
        limit: int = 200,
        offset: int = 0,
    ) -> Dict[str, Any]:
        rows = self._store.list_audit(
            username=username,
            module=module,
            action=action,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
        total = self._store.count_audit(
            username=username,
            module=module,
            action=action,
            date_from=date_from,
            date_to=date_to,
        )
        by_id, by_username = self._display_name_map()
        items = []
        for row in rows:
            payload = audit_to_dict(row)
            payload["display_name"] = self._resolve_audit_display_name(
                row, by_id=by_id, by_username=by_username
            )
            items.append(payload)
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }


def user_to_public(user: UserRow) -> Dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "is_active": user.is_active,
        "must_change_password": user.must_change_password,
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
    }


def audit_to_dict(row: AuditRow) -> Dict[str, Any]:
    payload = asdict(row)
    payload["module_label"] = module_label(row.module)
    payload["action_label"] = action_label(row.action)
    if row.detail_json:
        try:
            payload["detail"] = json.loads(row.detail_json)
        except json.JSONDecodeError:
            payload["detail"] = {}
    else:
        payload["detail"] = {}
    return payload


def load_or_create_secret_key() -> str:
    env = os.environ.get("WKT_SECRET_KEY", "").strip()
    if env:
        return env
    path = ROOT / "data" / "auth_secret.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_hex(32)
    path.write_text(key, encoding="utf-8")
    return key
