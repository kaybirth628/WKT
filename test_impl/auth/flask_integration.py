"""Flask 登录守卫、认证 API、操作审计钩子。"""
from __future__ import annotations

import json
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from test_impl.integrations.wkt_events import notify_audit_action

from .audit_labels import action_label, ingest_audit_rules, module_label
from .service import AuditService, AuthError, AuthService, load_or_create_secret_key, user_to_public

SummaryFn = Callable[[], str]
AuditRule = Tuple[str, str, SummaryFn]

AUDIT_RULES: Dict[Tuple[str, str], AuditRule] = {}


def _rule(method: str, path: str, action: str, module: str, summary: str) -> None:
    AUDIT_RULES[(method.upper(), path)] = (action, module, lambda s=summary: s)


def _register_audit_rules() -> None:
    if AUDIT_RULES:
        return
    # 认证
    _rule("POST", "/api/auth/logout", "auth.logout", "system", "用户退出")
    _rule("POST", "/api/auth/change-password", "auth.change_password", "system", "修改密码")
    # 订单
    _rule("POST", "/api/lines", "line.create", "orders", "录入订单行")
    _rule("PUT", "/api/lines/<int:line_id>", "line.update", "orders", "修改订单行")
    _rule("DELETE", "/api/lines/<int:line_id>", "line.delete", "orders", "删除订单行")
    _rule("POST", "/api/lines/<int:line_id>/ship", "line.ship", "orders", "订单出货")
    _rule("POST", "/api/lines/<int:line_id>/force-close", "line.force_close", "orders", "强制结案")
    _rule("POST", "/api/lines/batch-ship", "line.batch_ship", "orders", "批量出货")
    _rule("POST", "/api/lines/batch-ship-draft", "line.batch_ship_draft", "orders", "批量出货草稿")
    _rule("POST", "/api/lines/import/preview", "line.import_preview", "orders", "Excel导入预览")
    _rule("POST", "/api/lines/import/stage-pending", "line.import_stage", "orders", "Excel导入暂存")
    _rule("POST", "/api/lines/import/confirm", "line.import_confirm", "orders", "Excel导入确认")
    _rule("POST", "/api/lines/recognize", "line.ocr", "orders", "OCR识别订单")
    _rule("POST", "/api/shipment-events/<int:event_id>/return-open", "line.return_open", "orders", "出货回退未结")
    # 客商
    _rule("POST", "/api/customer-profiles", "customer.update", "partners", "更新客户档案")
    _rule("POST", "/api/customer-profiles/create", "customer.create", "partners", "新建客户档案")
    _rule("POST", "/api/customer-profiles/delete", "customer.delete", "partners", "删除客户档案")
    _rule("POST", "/api/supplier-profiles", "supplier.update", "partners", "更新供应商档案")
    _rule("POST", "/api/supplier-profiles/create", "supplier.create", "partners", "新建供应商档案")
    _rule("POST", "/api/supplier-profiles/delete", "supplier.delete", "partners", "删除供应商档案")
    # 送货单
    _rule("POST", "/api/delivery-templates/upload", "delivery.upload_template", "delivery", "上传送货单模板")
    _rule("POST", "/api/delivery-templates/upload-for-customer", "delivery.upload_customer_template", "delivery", "上传客户送货单模板")
    _rule("POST", "/api/delivery-templates/mapping", "delivery.mapping", "delivery", "送货单映射")
    _rule("DELETE", "/api/delivery-templates/mapping", "delivery.mapping_delete", "delivery", "删除送货单映射")
    _rule("POST", "/api/delivery-templates/customer-info", "delivery.customer_info", "delivery", "更新客户送货信息")
    _rule("POST", "/api/delivery-notes/<int:event_id>/open-local", "delivery.open_local", "delivery", "打开本地送货单")
    # 库存
    _rule("POST", "/api/inventory/inbound", "inventory.inbound", "inventory", "入库")
    _rule("POST", "/api/inventory/outbound", "inventory.outbound", "inventory", "出库")
    _rule("POST", "/api/inventory/skip-outbound", "inventory.skip_outbound", "inventory", "跳序出库")
    _rule("POST", "/api/inventory/repair-out", "inventory.repair_out", "inventory", "返修")
    _rule("POST", "/api/inventory/repair-in", "inventory.repair_in", "inventory", "返修入库")
    _rule("POST", "/api/inventory/complete", "inventory.complete", "inventory", "完工入库")
    _rule("POST", "/api/inventory/outsource-send", "inventory.outsource_send", "inventory", "外发出库")
    _rule("POST", "/api/inventory/outsource-receive", "inventory.outsource_receive", "inventory", "外发回货")
    _rule("POST", "/api/inventory/ship", "inventory.ship", "inventory", "库存出货")
    _rule("POST", "/api/inventory/adjust", "inventory.adjust", "inventory", "库存校正")
    _rule("PUT", "/api/inventory/movements/<int:movement_id>", "inventory.movement_update", "inventory", "修改出入库流水")
    _rule("POST", "/api/inventory/replenish", "inventory.replenish", "inventory", "补货单")
    _rule("POST", "/api/inventory/seed-demo", "inventory.seed_demo", "inventory", "写入库存演示数据")
    _rule("POST", "/api/inventory/seed-board-demo", "inventory.seed_board", "inventory", "写入看板演示数据")
    # 成本/BOM
    _rule("POST", "/api/cost/records", "cost.record_create", "cost", "新建成本记录")
    _rule("POST", "/api/cost/bom-import/parse", "cost.bom_import_parse", "cost", "解析BOM Excel")
    _rule("POST", "/api/cost/bom-import/commit", "cost.bom_import_commit", "cost", "批量导入BOM")
    _rule("PUT", "/api/cost/records/<int:record_id>", "cost.record_update", "cost", "修改成本记录")
    _rule("DELETE", "/api/cost/records/<int:record_id>", "cost.record_delete", "cost", "删除成本记录")
    _rule("POST", "/api/cost/quote", "cost.quote", "cost", "成本报价试算")
    # 主数据
    _rule("POST", "/api/master/customer", "master.customer", "master", "主数据客户")
    _rule("POST", "/api/master/part", "master.part", "master", "主数据料号")
    # 用户管理
    _rule("POST", "/api/users", "user.create", "admin", "创建用户")
    _rule("PUT", "/api/users/<int:user_id>", "user.update", "admin", "修改用户")
    _rule("DELETE", "/api/users/<int:user_id>", "user.delete", "admin", "删除用户")
    _rule("POST", "/api/users/<int:user_id>/reset-password", "user.reset_password", "admin", "重置用户密码")
    _rule("POST", "/api/users/<int:user_id>/active", "user.set_active", "admin", "启用/禁用用户")
    # 其他
    _rule("POST", "/api/feishu/config", "feishu.config", "system", "更新飞书配置")
    _rule("POST", "/api/feishu/test", "feishu.test", "system", "飞书测试消息")
    _rule("POST", "/api/ai/chat", "ai.chat", "ai", "AI助手对话")
    _rule("POST", "/api/ai/memory", "ai.memory_save", "ai", "保存AI记忆")
    _rule("POST", "/api/ai/memory/remember", "ai.memory_remember", "ai", "AI记忆写入")
    _rule("POST", "/api/orders", "order.create", "orders", "创建销售订单")
    _rule("POST", "/api/orders/<order_no>/approve", "order.approve", "orders", "审核销售订单")
    _rule("POST", "/api/orders/<order_no>/cancel", "order.cancel", "orders", "取消销售订单")
    _rule("POST", "/api/orders/recognize", "order.recognize", "orders", "订单识别")


_register_audit_rules()
ingest_audit_rules(AUDIT_RULES)

PUBLIC_PATHS = frozenset(
    {
        "/login",
        "/api/auth/login",
        "/api/health",
    }
)

PUBLIC_PREFIXES = (
    "/static/",
)


def _is_public() -> bool:
    path = request.path
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(p) for p in PUBLIC_PREFIXES)


def _client_ip() -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return forwarded or (request.remote_addr or "")


def get_session_user() -> Optional[Dict[str, Any]]:
    uid = session.get("user_id")
    if not uid:
        return None
    return {
        "id": int(uid),
        "username": session.get("username") or "",
        "display_name": session.get("display_name") or "",
        "role": session.get("role") or "user",
        "must_change_password": bool(session.get("must_change_password")),
    }


def login_required_admin(fn: Callable):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_session_user()
        if not user:
            return jsonify({"error": "请先登录", "code": "auth_required"}), 401
        if user.get("role") != "admin":
            return jsonify({"error": "需要管理员权限", "code": "forbidden"}), 403
        return fn(*args, **kwargs)

    return wrapper


def _audit_summary_enrich(action: str, summary: str) -> str:
    try:
        body = request.get_json(silent=True) or {}
    except Exception:
        body = {}
    if action == "line.create" and isinstance(body, dict):
        cust = body.get("customer") or ""
        order_no = body.get("order_no") or ""
        if cust or order_no:
            return f"录入订单行：{cust} {order_no}".strip()
    if action == "line.update" and isinstance(body, dict):
        return f"修改订单行 ID={request.view_args.get('line_id', '')}"
    if action == "line.ship":
        qty = (body or {}).get("ship_qty") or (body or {}).get("qty") or ""
        return f"出货 行ID={request.view_args.get('line_id', '')} 数量={qty}".strip()
    if action == "line.import_confirm" and isinstance(body, dict):
        tier = body.get("tier") or ""
        rows = body.get("rows") or []
        return f"Excel导入确认（{tier or 'passed'}）约 {len(rows)} 行"
    if action == "line.batch_ship" and isinstance(body, dict):
        items = body.get("items") or []
        return f"批量出货 {len(items)} 条料号"
    if action == "inventory.inbound" and isinstance(body, dict):
        return f"入库 料号={body.get('product_part_no', '')} 工序={body.get('process_code', '')} 数量={body.get('qty', '')}".strip()
    if action == "inventory.outbound" and isinstance(body, dict):
        return (
            f"出库 料号={body.get('product_part_no', '')} "
            f"{body.get('from_process_code', '')}→{body.get('to_process_code', '')} "
            f"数量={body.get('qty', '')}"
        ).strip()
    if action == "inventory.complete" and isinstance(body, dict):
        return f"完工入库 料号={body.get('product_part_no', '')} 工序={body.get('process_code', '')} 数量={body.get('qty', '')}".strip()
    if action == "inventory.outsource_send" and isinstance(body, dict):
        return f"外发出库 料号={body.get('product_part_no', '')} → {body.get('supplier_name', '')}".strip()
    if action == "inventory.outsource_receive" and isinstance(body, dict):
        return f"回货入库 料号={body.get('product_part_no', '')} 供应商={body.get('supplier_name', '')}".strip()
    if action == "inventory.ship" and isinstance(body, dict):
        return f"库存成品出货 料号={body.get('product_part_no', '')} 数量={body.get('qty', '')}".strip()
    if action == "inventory.adjust" and isinstance(body, dict):
        return (
            f"库存校正 料号={body.get('product_part_no', '')} "
            f"目标={body.get('target_qty', body.get('qty', ''))} {body.get('status', '')}"
        ).strip()
    if action == "inventory.movement_update":
        return f"修改出入库流水 ID={request.view_args.get('movement_id', '')} 数量={body.get('qty', '')}".strip()
    if action == "cost.record_create" and isinstance(body, dict):
        return f"BOM录入 料号={body.get('product_part_no', '')} 客户={body.get('customer_name', '')}".strip()
    if action == "customer.create" and isinstance(body, dict):
        return f"新建客户 {body.get('customer', '')}".strip()
    if action == "supplier.create" and isinstance(body, dict):
        return f"新建供应商 {body.get('supplier', '')}".strip()
    if action == "user.create" and isinstance(body, dict):
        return f"创建用户 {body.get('username', '')}"
    if action == "user.update" and isinstance(body, dict):
        return (
            f"修改用户 ID={request.view_args.get('user_id', '')} "
            f"姓名={body.get('display_name', '')} 角色={body.get('role', '')}"
        ).strip()
    if action == "user.delete":
        return f"删除用户 ID={request.view_args.get('user_id', '')}"
    return summary


def register_auth(app: Flask, auth_service: AuthService, audit_service: AuditService) -> None:
    app.secret_key = load_or_create_secret_key()
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    @app.before_request
    def _require_login():
        if _is_public():
            return None
        if request.method == "OPTIONS":
            return None
        user = get_session_user()
        if user:
            return None
        if request.path.startswith("/api/"):
            return jsonify({"error": "请先登录", "code": "auth_required"}), 401
        next_url = request.full_path if request.query_string else request.path
        if next_url.endswith("?"):
            next_url = next_url[:-1]
        return redirect(url_for("login_page", next=next_url))

    @app.after_request
    def _audit_mutations(response):
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return response
        if response.status_code >= 400:
            return response
        if _is_public() and request.path not in ("/api/auth/logout",):
            return response
        rule = request.url_rule.rule if request.url_rule else ""
        spec = AUDIT_RULES.get((request.method.upper(), rule))
        if not spec:
            return response
        action, module, summary_fn = spec
        user = get_session_user()
        summary = _audit_summary_enrich(action, summary_fn())
        try:
            audit_service.log(
                user=user,
                action=action,
                module=module,
                summary=summary,
                entity_type="",
                entity_id=str(request.view_args or ""),
                detail={"path": request.path, "method": request.method},
                ip_address=_client_ip(),
            )
            notify_audit_action(
                action=action,
                module=module,
                summary=summary,
                user=user,
                ip_address=_client_ip(),
            )
        except Exception:
            pass
        return response

    @app.route("/login")
    def login_page():
        if get_session_user():
            nxt = request.args.get("next") or "/"
            return redirect(nxt)
        return render_template("login.html")

    @app.route("/admin/audit")
    def audit_log_page():
        user = get_session_user()
        if not user:
            return redirect(url_for("login_page", next="/admin/audit"))
        return render_template("audit_log.html", active="audit", current_user=user)

    @app.route("/admin/users")
    @login_required_admin
    def users_admin_page():
        user = get_session_user()
        return render_template("users_admin.html", active="users_admin", current_user=user)

    @app.route("/api/auth/login", methods=["POST"])
    def auth_login():
        data = request.get_json(silent=True) or {}
        username = str(data.get("username") or "").strip()
        password = str(data.get("password") or "")
        if not username or not password:
            return jsonify({"error": "请输入用户名和密码"}), 400
        try:
            user = auth_service.authenticate(username, password)
        except AuthError as exc:
            return jsonify({"error": str(exc)}), 401
        session.clear()
        session["user_id"] = user.id
        session["username"] = user.username
        session["display_name"] = user.display_name
        session["role"] = user.role
        session["must_change_password"] = user.must_change_password
        session.permanent = True
        pub = user_to_public(user)
        try:
            audit_service.log(
                user=pub,
                action="auth.login",
                module="system",
                summary=f"用户登录：{user.display_name}（{user.username}）",
                ip_address=_client_ip(),
            )
            notify_audit_action(
                action="auth.login",
                module="system",
                summary=f"用户登录：{user.display_name}（{user.username}）",
                user=pub,
                ip_address=_client_ip(),
            )
        except Exception:
            pass
        return jsonify({"ok": True, "user": pub})

    @app.route("/api/auth/logout", methods=["POST"])
    def auth_logout():
        user = get_session_user()
        if user:
            try:
                audit_service.log(
                    user=user,
                    action="auth.logout",
                    module="system",
                    summary=f"用户退出：{user.get('display_name') or user.get('username')}",
                    ip_address=_client_ip(),
                )
                notify_audit_action(
                    action="auth.logout",
                    module="system",
                    summary=f"用户退出：{user.get('display_name') or user.get('username')}",
                    user=user,
                    ip_address=_client_ip(),
                )
            except Exception:
                pass
        session.clear()
        return jsonify({"ok": True})

    @app.route("/api/auth/me", methods=["GET"])
    def auth_me():
        user = get_session_user()
        if not user:
            return jsonify({"error": "未登录", "code": "auth_required"}), 401
        row = auth_service.store.get_user_by_id(int(user["id"]))
        if not row or not row.is_active:
            session.clear()
            return jsonify({"error": "未登录", "code": "auth_required"}), 401
        return jsonify({"user": user_to_public(row)})

    @app.route("/api/auth/change-password", methods=["POST"])
    def auth_change_password():
        user = get_session_user()
        if not user:
            return jsonify({"error": "请先登录", "code": "auth_required"}), 401
        data = request.get_json(silent=True) or {}
        try:
            auth_service.change_password(
                int(user["id"]),
                old_password=str(data.get("old_password") or ""),
                new_password=str(data.get("new_password") or ""),
            )
        except AuthError as exc:
            return jsonify({"error": str(exc)}), 400
        session["must_change_password"] = False
        return jsonify({"ok": True})

    @app.route("/api/audit-log", methods=["GET"])
    def audit_log_api():
        user = get_session_user()
        if not user:
            return jsonify({"error": "请先登录", "code": "auth_required"}), 401
        q_username = request.args.get("username", "").strip()
        if user.get("role") != "admin":
            q_username = user.get("username") or ""
        result = audit_service.query(
            username=q_username,
            module=request.args.get("module", "").strip(),
            action=request.args.get("action", "").strip(),
            date_from=request.args.get("date_from", "").strip(),
            date_to=request.args.get("date_to", "").strip(),
            limit=min(int(request.args.get("limit", 200)), 500),
            offset=max(int(request.args.get("offset", 0)), 0),
        )
        return jsonify(result)

    @app.route("/api/users", methods=["GET"])
    @login_required_admin
    def users_list_api():
        return jsonify({"items": auth_service.list_users_public()})

    @app.route("/api/users", methods=["POST"])
    @login_required_admin
    def users_create_api():
        data = request.get_json(silent=True) or {}
        try:
            created = auth_service.create_user(
                username=str(data.get("username") or ""),
                display_name=str(data.get("display_name") or ""),
                password=str(data.get("password") or ""),
                role=str(data.get("role") or "user"),
            )
        except AuthError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"ok": True, "user": created}), 201

    @app.route("/api/users/<int:user_id>", methods=["PUT"])
    @login_required_admin
    def users_update_api(user_id: int):
        data = request.get_json(silent=True) or {}
        try:
            updated = auth_service.update_user(
                user_id,
                display_name=str(data.get("display_name") or ""),
                role=str(data.get("role") or "user"),
            )
        except AuthError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"ok": True, "user": updated})

    @app.route("/api/users/<int:user_id>", methods=["DELETE"])
    @login_required_admin
    def users_delete_api(user_id: int):
        user = get_session_user() or {}
        try:
            auth_service.delete_user(user_id, actor_user_id=int(user.get("id") or 0))
        except AuthError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"ok": True})

    @app.route("/api/users/<int:user_id>/reset-password", methods=["POST"])
    @login_required_admin
    def users_reset_password_api(user_id: int):
        data = request.get_json(silent=True) or {}
        try:
            auth_service.admin_reset_password(user_id, str(data.get("password") or ""))
        except AuthError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"ok": True})

    @app.route("/api/users/<int:user_id>/active", methods=["POST"])
    @login_required_admin
    def users_active_api(user_id: int):
        data = request.get_json(silent=True) or {}
        try:
            auth_service.set_active(user_id, bool(data.get("active", True)))
        except AuthError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"ok": True})

    @app.context_processor
    def _inject_auth():
        return {"current_user": get_session_user()}
