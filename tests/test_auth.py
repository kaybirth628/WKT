"""Auth login, users, audit log tests."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import check_password_hash

from test_impl.auth.service import AuthService, AuditService
from test_impl.auth.store import AuthStore


class AuthTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "test.db"
        store = AuthStore(self.db_path)
        self.auth = AuthService(store=store)
        self.audit = AuditService(store=store)

    def tearDown(self) -> None:
        self.auth.store.close()
        self._tmp.cleanup()

    def test_bootstrap_admin_and_login(self) -> None:
        user = self.auth.authenticate("admin", "WKT@2026")
        self.assertEqual(user.username, "admin")
        self.assertEqual(user.role, "admin")
        self.assertTrue(user.must_change_password)

    def test_create_user_and_audit(self) -> None:
        self.auth.authenticate("admin", "WKT@2026")
        created = self.auth.create_user(
            username="zhangsan",
            display_name="张三",
            password="pass1234",
            role="user",
        )
        self.assertEqual(created["username"], "zhangsan")
        u = self.auth.authenticate("zhangsan", "pass1234")
        self.assertEqual(u.display_name, "张三")
        self.audit.log(
            user={"id": u.id, "username": u.username, "display_name": u.display_name},
            action="line.create",
            module="orders",
            summary="测试录入",
        )
        from test_impl.auth.audit_labels import ingest_audit_rules
        from test_impl.auth.flask_integration import AUDIT_RULES

        ingest_audit_rules(AUDIT_RULES)
        result = self.audit.query(username="zhangsan")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["action"], "line.create")
        from test_impl.auth.audit_labels import action_label, module_label

        item = result["items"][0]
        self.assertEqual(module_label(item["module"]), "订单管理")
        self.assertEqual(action_label(item["action"]), "录入订单行")
        self.assertEqual(item["module_label"], "订单管理")
        self.assertEqual(item["action_label"], "录入订单行")

    def test_change_password(self) -> None:
        admin = self.auth.authenticate("admin", "WKT@2026")
        self.auth.change_password(admin.id, old_password="WKT@2026", new_password="NewPass1")
        row = self.auth.store.get_user_by_id(admin.id)
        assert row is not None
        self.assertTrue(check_password_hash(row.password_hash, "NewPass1"))

    def test_update_user_and_delete(self) -> None:
        self.auth.authenticate("admin", "WKT@2026")
        created = self.auth.create_user(
            username="lisi",
            display_name="李四",
            password="pass1234",
            role="user",
        )
        uid = int(created["id"])
        updated = self.auth.update_user(uid, display_name="李四（销售）", role="user")
        self.assertEqual(updated["display_name"], "李四（销售）")
        admin = self.auth.store.get_user_by_id(1)
        assert admin is not None
        self.auth.delete_user(uid, actor_user_id=admin.id)
        self.assertIsNone(self.auth.store.get_user_by_id(uid))

    def test_audit_display_name_resolves_after_rename(self) -> None:
        self.auth.authenticate("admin", "WKT@2026")
        created = self.auth.create_user(
            username="1",
            display_name="1",
            password="pass1234",
            role="user",
        )
        uid = int(created["id"])
        self.audit.log(
            user={"id": uid, "username": "1", "display_name": "1"},
            action="line.create",
            module="orders",
            summary="改名前操作",
        )
        self.auth.update_user(uid, display_name="娟娟", role="user")
        result = self.audit.query(username="1")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["display_name"], "娟娟")

    def test_audit_log_uses_fresh_display_name(self) -> None:
        self.auth.authenticate("admin", "WKT@2026")
        created = self.auth.create_user(
            username="worker",
            display_name="旧名",
            password="pass1234",
            role="user",
        )
        uid = int(created["id"])
        self.auth.update_user(uid, display_name="娟娟", role="user")
        self.audit.log(
            user={"id": uid, "username": "worker", "display_name": "旧名"},
            action="line.update",
            module="orders",
            summary="改名后操作",
        )
        row = self.audit.query(username="worker")["items"][0]
        self.assertEqual(row["display_name"], "娟娟")

    def test_system_deploy_audit(self) -> None:
        from test_impl.auth.audit_labels import action_label, module_label
        from test_impl.integrations.wkt_events import log_system_deploy_audit

        app_dir = Path(self._tmp.name) / "app"
        (app_dir / "data").mkdir(parents=True)
        deploy_db = app_dir / "data" / "wkt_orders.db"
        deploy_db.write_bytes(self.db_path.read_bytes())

        log_system_deploy_audit(
            app_dir,
            previous={"version": "v0.6.0", "build": "build-old"},
            current={"version": "v0.6.0", "build": "build-new", "changes": ["CL-0277 · test"]},
            operator="Albert",
            host_label="云端",
        )
        deploy_store = AuthStore(deploy_db)
        deploy_audit = AuditService(store=deploy_store)
        result = deploy_audit.query(module="system")
        self.assertEqual(result["total"], 1)
        item = result["items"][0]
        self.assertEqual(item["action"], "system.deploy")
        self.assertEqual(action_label("system.deploy"), "系统部署")
        self.assertEqual(module_label("system"), "系统")
        self.assertIn("build-old", item["summary"])
        self.assertIn("build-new", item["summary"])
        self.assertEqual(item["display_name"], "系统管理员")
        deploy_store.close()

    def test_cannot_delete_admin_or_self(self) -> None:
        admin = self.auth.authenticate("admin", "WKT@2026")
        with self.assertRaises(Exception):
            self.auth.delete_user(admin.id, actor_user_id=admin.id)
        with self.assertRaises(Exception):
            self.auth.delete_user(admin.id, actor_user_id=999)


if __name__ == "__main__":
    unittest.main()
