"""
WKT 销售管理系统 - Web 演示（test_impl 隔离区）
运行: python test_impl/web/app.py
访问: http://127.0.0.1:5000
"""

from __future__ import annotations

import io
import sys
import threading
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORDERS_DIR = ROOT / "orders"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flask import Flask, jsonify, redirect, render_template, request, send_file

from test_impl.order_management.order_entry import (
    OrderEntryService,
    OrderLineService,
    DuplicateLineError,
    intake_to_lines,
)
from test_impl.order_management.cost_analysis import (
    CostAnalysisService,
    CostLookupService,
    CostRecordService,
    BomService,
)
from test_impl.order_management.cost_analysis.bom_form_import import (
    apply_batch_duplicate_part_hints,
    parse_bom_workbook,
    preview_import_batch,
    preview_import_rows,
    revalidate_preview_item,
)
from test_impl.order_management.customer_name import (
    extract_customer_hint_from_filename,
    resolve_customer_from_hint,
)
from test_impl.order_management.inventory import InventoryService, PlanningService
from test_impl.order_management.order_intake.source_preview import render_document_preview_pages
from test_impl.order_management.order_intake import (
    IntakeService,
    TextExtractionError,
    DeepSeekError,
)
from test_impl.order_management.order_archive import try_archive_order_file
from test_impl.order_management.order_entry.excel_import import (
    build_template_bytes,
    parse_excel_bytes,
    summarize_results,
    validate_import_row,
)
from test_impl.common.money import (
    rmb_upper,
    serialize_amount,
    serialize_price,
    serialize_qty,
)
from test_impl.web.design_catalog import catalog_summary, load_design_catalog
from test_impl.order_management.delivery_note import DeliveryNoteService
from test_impl.order_management.customer_profile import CustomerProfileService
from test_impl.order_management.customer_profile.store import list_profile_customers
from test_impl.order_management.supplier_profile import SupplierProfileService
from test_impl.order_management.reconciliation import ReconciliationService
from test_impl.order_management.reconciliation.payable_service import PayableService
from test_impl.order_management.dashboard import OrderDashboardService
from test_impl.integrations.feishu import public_feishu_config, save_feishu_config
from test_impl.integrations.db_assistant import DatabaseAssistant, DatabaseAssistantError
from test_impl.integrations.deepseek_client import DeepSeekChatClient
from test_impl.integrations.ai_memory import (
    append_business_rule,
    append_glossary,
    append_query_example,
    load_memory,
    memory_to_api_dict,
    save_memory,
)
from test_impl.common.filename_encoding import normalize_upload_filename
from test_impl.integrations.wkt_events import send_test_message
from test_impl.auth.service import AuthService, AuditService
from test_impl.auth.flask_integration import register_auth
from test_impl.auth.store import AuthStore

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)

service = OrderEntryService()
line_service = OrderLineService()
delivery_note_service = DeliveryNoteService(line_service)
customer_profile_service = CustomerProfileService(line_service)
supplier_profile_service = SupplierProfileService()
reconciliation_service = ReconciliationService(line_service._store)
dashboard_service = OrderDashboardService(line_service)
cost_service = CostAnalysisService()
cost_record_service = CostRecordService(line_store=line_service._store)
cost_lookup_service = CostLookupService(
    line_store=line_service._store,
    cost_store=cost_record_service._store,
    record_service=cost_record_service,
)
bom_service = BomService(
    cost_store=cost_record_service._store,
    record_service=cost_record_service,
)
inventory_service = InventoryService(
    cost_store=cost_record_service._store,
    record_service=cost_record_service,
)
payable_service = PayableService(
    inventory_store=inventory_service.store,
    cost_store=cost_record_service._store,
    record_service=cost_record_service,
)
planning_service = PlanningService(line_service, inventory_service)
line_service.set_inventory_service(inventory_service)
intake_service = IntakeService(line_service=line_service)
db_assistant = DatabaseAssistant(db_path=line_service.db_path)

_auth_store = AuthStore(db_path=line_service.db_path)
auth_service = AuthService(store=_auth_store)
audit_service = AuditService(store=_auth_store)
register_auth(app, auth_service, audit_service)

from test_impl.order_management.delivery_note.custom_excel_attachment import register_save_hook

register_save_hook(
    lambda event_ids, rel_path: delivery_note_service.persist_attachment_saved(event_ids, rel_path)
)

# 识别任务（内存，重启清空）
_recognize_jobs: dict = {}
_recognize_previews: dict[str, list[bytes]] = {}
_jobs_lock = threading.Lock()


def _last_shipment_fields(info: tuple[str, str] | None) -> dict:
    if not info:
        return {"last_shipped_at": "", "last_delivery_doc_no": ""}
    shipped_at, doc_no = info
    return {"last_shipped_at": shipped_at, "last_delivery_doc_no": doc_no}


def _line_to_dict(
    line,
    last_shipment: tuple[str, str] | None = None,
    *,
    stock: dict | None = None,
) -> dict:
    payload = {
        "id": line.id,
        "customer": line.customer,
        "order_date": line.order_date,
        "delivery_date": line.delivery_date,
        "order_no": line.order_no,
        "product_spec": line.product_spec,
        "customer_part_no": line.customer_part_no,
        "unit_weight_g": str(line.unit_weight_g),
        "material": line.material,
        "po_qty": serialize_qty(line.po_qty),
        "shipped_qty": serialize_qty(line.shipped_qty),
        "open_qty": serialize_qty(line.open_qty()),
        "unit": line.unit,
        "tax_rate": str(line.tax_rate),
        "rmb_tax_incl_price": serialize_price(line.rmb_tax_incl_price),
        "amount": serialize_amount(line.amount()),
        "payment_terms": line.payment_terms,
        "created_at": line.created_at.isoformat(),
        "updated_at": line.updated_at.isoformat(),
        "closure_type": (line.closure_type or "").strip(),
        "is_demo": bool(getattr(line, "is_demo", False)),
        "data_tag": "测" if getattr(line, "is_demo", False) else "实",
    }
    if last_shipment is not None:
        payload.update(_last_shipment_fields(last_shipment))
    if stock is not None:
        payload.update(
            {
                "finished_qty": stock.get("finished_qty", "0"),
                "semifinished_qty": stock.get("semifinished_qty", "0"),
                "gap_ship": stock.get("gap_ship", "0"),
                "gap_cover": stock.get("gap_cover", "0"),
                "suggest_qty": stock.get("suggest_qty", "0"),
                "stock_warn_level": stock.get("stock_warn_level", "ok"),
            }
        )
    return payload


def _order_to_dict(order) -> dict:
    return {
        "order_no": order.order_no,
        "customer": order.customer,
        "created_by": order.created_by,
        "order_date": order.order_date,
        "delivery_date": order.delivery_date,
        "payment_terms": order.payment_terms,
        "status": order.status.value,
        "total_amount": serialize_amount(order.total_amount()),
        "total_amount_upper": rmb_upper(order.total_amount()),
        "created_at": order.created_at.isoformat(),
        "approved_by": order.approved_by,
        "approved_at": order.approved_at.isoformat() if order.approved_at else None,
        "items": [
            {
                "item_no": it.item_no,
                "product_spec": it.product_spec,
                "customer_part_no": it.customer_part_no,
                "unit_weight_g": str(it.unit_weight_g),
                "material": it.material,
                "po_qty": serialize_qty(it.po_qty),
                "shipped_qty": serialize_qty(it.shipped_qty),
                "open_qty": serialize_qty(it.open_qty()),
                "unit": it.unit,
                "tax_rate": str(it.tax_rate),
                "rmb_tax_incl_price": serialize_price(it.rmb_tax_incl_price),
                "amount": serialize_amount(it.amount()),
            }
            for it in order.items
        ],
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/cost")
def cost_page():
    return redirect("/bom/entry")


@app.route("/bom")
def bom_page():
    return redirect("/bom/entry")


@app.route("/bom/entry")
def bom_entry_page():
    return render_template("cost_entry.html", active="bom_entry")


@app.route("/bom/query")
def bom_query_page():
    return render_template("cost_query.html", active="bom_query")


@app.route("/inventory")
def inventory_page():
    return render_template("inventory.html", active="inventory")


@app.route("/inventory/entry")
def inventory_entry_page():
    return redirect("/inventory")


@app.route("/inventory/movements")
def inventory_movements_page():
    return render_template("inventory_movements.html", active="inventory_movements")


@app.route("/inventory/planning")
def inventory_planning_page():
    return redirect("/inventory")


@app.route("/cost/entry")
def cost_entry_page():
    return redirect("/bom/entry")


@app.route("/cost/query")
def cost_query_page():
    return redirect("/bom/query")


@app.route("/themes")
def themes_page():
    return render_template("theme_preview.html")


@app.route("/design-gallery")
def design_gallery_page():
    return render_template("design_gallery.html")


@app.route("/api/health")
def api_health():
    return jsonify(
        {
            "ok": True,
            "build": "20260730-batch-force-close",
            "storage": "sqlite",
            "db_path": str(line_service.db_path),
            "line_count": line_service.count_lines(),
            "features": [
                "excel_import_tiers",
                "humanized_errors",
                "blocked_report",
                "payment_terms_free_text",
                "sqlite_persist",
                "shipment_events",
                "open_order_ship",
                "delivery_note_templates",
                "wkt_standard_delivery_note",
                "ship_delivery_confirm",
                "batch_ship_merge",
                "force_close",
                "batch_force_close",
                "feishu_notify",
                "ai_db_assistant",
                "ai_business_memory",
                "reconciliation",
                "payable",
                "customer_profiles",
                "supplier_profiles",
                "order_dashboard",
                "auth_login",
                "audit_log",
            ],
            "feishu": public_feishu_config(),
        }
    )


@app.route("/api/dashboard/overview", methods=["GET"])
def dashboard_overview():
    return jsonify(dashboard_service.build_overview())


@app.route("/api/design-catalog")
def design_catalog_api():
    return jsonify({"summary": catalog_summary(), "items": load_design_catalog()})


@app.route("/api/master", methods=["GET"])
def list_master():
    return jsonify(line_service.list_master())


@app.route("/api/master/customers", methods=["GET"])
def master_customers_suggest():
    q = request.args.get("q", "")
    try:
        limit = int(request.args.get("limit", "20"))
    except ValueError:
        limit = 20
    items = line_service.suggest_customers(q=q, limit=limit)
    return jsonify({"items": items, "total": len(items)})


@app.route("/api/master/customer", methods=["POST"])
def add_customer():
    data = request.get_json(force=True) or {}
    try:
        customer = line_service.add_customer(data.get("name", ""))
        return jsonify({"name": customer.name}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/master/part", methods=["POST"])
def add_part():
    data = request.get_json(force=True) or {}
    try:
        part = line_service.add_part(
            data.get("product_spec", ""),
            data.get("customer_part_no", ""),
        )
        return jsonify(part), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/master/lookup", methods=["GET"])
def lookup_master():
    spec = request.args.get("product_spec", "")
    part_no = request.args.get("customer_part_no", "")
    if part_no.strip():
        info = bom_service.lookup_for_order(part_no)
        if info:
            return jsonify(info)
    if spec.strip():
        cpn = bom_service.lookup_part_no_by_product_name(spec)
        if cpn:
            info = bom_service.lookup_for_order(cpn)
            if info:
                return jsonify(info)
        return jsonify({"customer_part_no": line_service.lookup_customer_part(spec)})
    return jsonify({"customer_part_no": ""})


@app.route("/api/bom/lookup", methods=["GET"])
def bom_lookup_for_order():
    part_no = request.args.get("customer_part_no", "") or request.args.get("product_part_no", "")
    info = bom_service.lookup_for_order(part_no)
    if not info:
        return jsonify(
            {
                "found": False,
                "error": f"料号「{part_no.strip()}」未在 BOM 中建档，请先在「BOM 录入」中维护",
            }
        ), 404
    return jsonify({"found": True, **info})


@app.route("/api/inventory/route", methods=["GET"])
def inventory_route():
    part_no = request.args.get("product_part_no", "")
    customer = request.args.get("customer_name", "")
    try:
        route = inventory_service.get_route(part_no, customer_name=customer)
        bom = inventory_service.lookup_bom_header(part_no, customer_name=customer)
        return jsonify(
            {
                "product_part_no": part_no.strip(),
                "product_name": (bom or {}).get("product_name", ""),
                "customer_name": (bom or {}).get("customer_name", ""),
                "route": route,
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/board", methods=["GET"])
def inventory_board():
    part_no = request.args.get("product_part_no", "")
    customer = request.args.get("customer_name", "")
    return jsonify(
        {"items": inventory_service.board(product_part_no=part_no, customer_name=customer)}
    )


@app.route("/api/inventory/movements", methods=["GET"])
def inventory_movements():
    part_no = request.args.get("product_part_no", "")
    on_date = request.args.get("on_date", "")
    customer = request.args.get("customer_name", "")
    try:
        limit = max(1, min(int(request.args.get("limit", "200")), 500))
    except ValueError:
        limit = 200
    return jsonify(
        {
            "items": inventory_service.list_movements(
                product_part_no=part_no,
                on_date=on_date,
                limit=limit,
                customer_name=customer,
            )
        }
    )


@app.route("/api/inventory/movements/<int:movement_id>", methods=["PUT"])
def inventory_movement_update(movement_id: int):
    data = request.get_json(force=True) or {}
    qty = data.get("qty")
    if qty in (None, ""):
        return jsonify({"error": "数量不能为空"}), 400
    note = str(data.get("note") or "")
    try:
        movement = inventory_service.correct_movement(movement_id, qty=qty, note=note)
        return jsonify({"ok": True, "movement": movement})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


def _inv_payload():
    data = request.get_json(force=True) or {}
    part_no = str(data.get("product_part_no") or "").strip()
    qty = data.get("qty")
    if not part_no:
        return None, (jsonify({"error": "产品料号不能为空"}), 400)
    if qty in (None, ""):
        return None, (jsonify({"error": "数量不能为空"}), 400)
    return {
        "part_no": part_no,
        "qty": qty,
        "doc_no": str(data.get("doc_no") or "").strip(),
        "note": str(data.get("note") or "").strip(),
        "process_code": str(data.get("process_code") or "").strip(),
        "supplier_name": str(data.get("supplier_name") or "").strip(),
        "raw": data,
    }, None


@app.route("/api/inventory/inbound", methods=["POST"])
def inventory_inbound():
    payload, err = _inv_payload()
    if err:
        return err
    if not payload["process_code"]:
        return jsonify({"error": "入库工序不能为空"}), 400
    try:
        result = inventory_service.inbound(
            payload["part_no"],
            payload["process_code"],
            payload["qty"],
            supplier_name=payload["supplier_name"],
            doc_no=payload["doc_no"],
            note=payload["note"],
        )
        return jsonify({"ok": True, "movement": result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/outbound", methods=["POST"])
def inventory_outbound():
    data = request.get_json(force=True) or {}
    part = str(data.get("product_part_no") or "").strip()
    qty = data.get("qty")
    from_code = str(data.get("from_process_code") or "").strip()
    to_code = str(data.get("to_process_code") or "").strip()
    if not part:
        return jsonify({"error": "产品料号不能为空"}), 400
    if qty in (None, ""):
        return jsonify({"error": "数量不能为空"}), 400
    if not from_code:
        return jsonify({"error": "出库起始工序不能为空"}), 400
    try:
        result = inventory_service.outbound(
            part,
            from_code,
            to_code,
            qty,
            supplier_name=str(data.get("supplier_name") or "").strip(),
            doc_no=str(data.get("doc_no") or "").strip(),
            note=str(data.get("note") or "").strip(),
        )
        return jsonify({"ok": True, "movement": result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/skip-outbound", methods=["POST"])
def inventory_skip_outbound():
    data = request.get_json(force=True) or {}
    part = str(data.get("product_part_no") or "").strip()
    qty = data.get("qty")
    from_code = str(data.get("from_process_code") or "").strip()
    to_code = str(data.get("to_process_code") or "").strip()
    if not part:
        return jsonify({"error": "产品料号不能为空"}), 400
    if qty in (None, ""):
        return jsonify({"error": "数量不能为空"}), 400
    if not from_code or not to_code:
        return jsonify({"error": "跳序出库须选择从工序与到工序"}), 400
    try:
        result = inventory_service.skip_outbound(
            part,
            from_code,
            to_code,
            qty,
            supplier_name=str(data.get("supplier_name") or "").strip(),
            doc_no=str(data.get("doc_no") or "").strip(),
            note=str(data.get("note") or "").strip(),
        )
        return jsonify({"ok": True, "movement": result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/complete", methods=["POST"])
def inventory_complete():
    payload, err = _inv_payload()
    if err:
        return err
    if not payload["process_code"]:
        return jsonify({"error": "工序不能为空"}), 400
    try:
        result = inventory_service.complete(
            payload["part_no"],
            payload["process_code"],
            payload["qty"],
            doc_no=payload["doc_no"],
            note=payload["note"],
        )
        return jsonify({"ok": True, "movement": result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/outsource-send", methods=["POST"])
def inventory_outsource_send():
    payload, err = _inv_payload()
    if err:
        return err
    if not payload["process_code"] or not payload["supplier_name"]:
        return jsonify({"error": "工序与供应商不能为空"}), 400
    try:
        result = inventory_service.outsource_send(
            payload["part_no"],
            payload["process_code"],
            payload["supplier_name"],
            payload["qty"],
            doc_no=payload["doc_no"],
            note=payload["note"],
        )
        return jsonify({"ok": True, "movement": result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/outsource-receive", methods=["POST"])
def inventory_outsource_receive():
    payload, err = _inv_payload()
    if err:
        return err
    if not payload["process_code"] or not payload["supplier_name"]:
        return jsonify({"error": "工序与供应商不能为空"}), 400
    try:
        result = inventory_service.outsource_receive(
            payload["part_no"],
            payload["process_code"],
            payload["supplier_name"],
            payload["qty"],
            doc_no=payload["doc_no"],
            note=payload["note"],
        )
        return jsonify({"ok": True, "movement": result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/ship", methods=["POST"])
def inventory_ship():
    payload, err = _inv_payload()
    if err:
        return err
    try:
        result = inventory_service.ship_finished(
            payload["part_no"],
            payload["qty"],
            doc_no=payload["doc_no"],
            note=payload["note"],
        )
        return jsonify({"ok": True, "movement": result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/stage-flow", methods=["POST"])
def inventory_stage_flow():
    data = request.get_json(force=True) or {}
    part = str(data.get("product_part_no") or "").strip()
    qty = data.get("qty")
    if not part:
        return jsonify({"error": "产品料号不能为空"}), 400
    if qty in (None, ""):
        return jsonify({"error": "数量不能为空"}), 400
    try:
        movement = inventory_service.record_stage_flow(
            part,
            from_process_code=str(data.get("from_process_code") or "").strip(),
            from_status=str(data.get("from_status") or "").strip(),
            to_process_code=str(data.get("to_process_code") or "").strip(),
            to_status=str(data.get("to_status") or "").strip(),
            qty=qty,
            from_supplier_name=str(data.get("from_supplier_name") or "").strip(),
            to_supplier_name=str(data.get("to_supplier_name") or "").strip(),
            note=str(data.get("note") or "").strip(),
        )
        return jsonify({"ok": True, "movement": movement})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/stage-set", methods=["POST"])
def inventory_stage_set():
    data = request.get_json(force=True) or {}
    part = str(data.get("product_part_no") or "").strip()
    code = str(data.get("process_code") or "").strip()
    if not part:
        return jsonify({"error": "产品料号不能为空"}), 400
    if not code:
        return jsonify({"error": "须指定工序"}), 400
    try:
        result = inventory_service.set_stage_buckets(
            part,
            code,
            inhouse_qty=data.get("inhouse_qty"),
            outsource_qty=data.get("outsource_qty"),
            repair_qty=data.get("repair_qty"),
            finished_qty=data.get("finished_qty"),
            finished_repair_qty=data.get("finished_repair_qty"),
            supplier_name=str(data.get("supplier_name") or "").strip(),
            note=str(data.get("note") or "").strip(),
        )
        movements = result.get("movements") or []
        return jsonify(
            {
                "ok": True,
                "count": result.get("count", len(movements)),
                "movements": movements,
                "movement": movements[-1] if movements else None,
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/adjust", methods=["POST"])
def inventory_adjust():
    data = request.get_json(force=True) or {}
    part = str(data.get("product_part_no") or "").strip()
    target = data.get("target_qty") if data.get("target_qty") is not None else data.get("qty")
    if not part:
        return jsonify({"error": "产品料号不能为空"}), 400
    if target in (None, ""):
        return jsonify({"error": "请填写正确数量"}), 400
    try:
        result = inventory_service.adjust_balance(
            part,
            target_qty=target,
            process_code=str(data.get("process_code") or "").strip(),
            status=str(data.get("status") or "").strip(),
            supplier_name=str(data.get("supplier_name") or "").strip(),
            note=str(data.get("note") or "").strip(),
        )
        return jsonify({"ok": True, "movement": result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/repair-out", methods=["POST"])
def inventory_repair_out():
    data = request.get_json(force=True) or {}
    part = str(data.get("product_part_no") or "").strip()
    qty = data.get("qty")
    if not part:
        return jsonify({"error": "产品料号不能为空"}), 400
    if qty in (None, ""):
        return jsonify({"error": "数量不能为空"}), 400
    try:
        result = inventory_service.repair_out(
            part,
            qty,
            process_code=str(data.get("process_code") or "").strip(),
            doc_no=str(data.get("doc_no") or "").strip(),
            note=str(data.get("note") or "").strip(),
        )
        return jsonify({"ok": True, "movement": result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/repair-in", methods=["POST"])
def inventory_repair_in():
    data = request.get_json(force=True) or {}
    part = str(data.get("product_part_no") or "").strip()
    qty = data.get("qty")
    if not part:
        return jsonify({"error": "产品料号不能为空"}), 400
    if qty in (None, ""):
        return jsonify({"error": "数量不能为空"}), 400
    try:
        result = inventory_service.repair_in(
            part,
            qty,
            process_code=str(data.get("process_code") or "").strip(),
            doc_no=str(data.get("doc_no") or "").strip(),
            note=str(data.get("note") or "").strip(),
        )
        return jsonify({"ok": True, "movement": result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/seed-demo", methods=["POST"])
def inventory_seed_demo():
    """写入演示 BOM（若不存在）并跑通一版示例流水。"""
    from unittest.mock import patch

    data = request.get_json(silent=True) or {}
    part_no = str(data.get("product_part_no") or "PL9-01100-00-0A").strip()
    supplier = "苏州麦凯良金属制品厂"
    try:
        try:
            inventory_service.get_route(part_no)
        except ValueError:
            with patch(
                "test_impl.order_management.cost_analysis.record_service.list_profile_suppliers",
                return_value=[supplier],
            ):
                cost_record_service.create_record(
                    {
                        "customer_name": "东莞市凯泰智联科技有限公司",
                        "product_name": "超频主机上盖1个单芯/2个单芯",
                        "mold_no": "WKT-MJ-LV-25006",
                        "product_part_no": part_no,
                        "cavity": "1*1",
                        "unit_weight_g": "136",
                        "material": "ADC12",
                        "machine_tonnage": "280T",
                        "material_unit_price": "0",
                        "process_prices": {
                            "01": "0",
                            "02": {"price": "0", "supplier": supplier},
                            "28": {"price": "0", "supplier": "场内自制"},
                            "34": {"price": "0", "supplier": "场内自制"},
                        },
                    }
                )
        result = inventory_service.seed_demo_flow(part_no)
        return jsonify({"ok": True, **result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/seed-board-demo", methods=["POST"])
def inventory_seed_board_demo():
    """从订单中挑约 10 个料号建 BOM（若缺）并写入各工序在途/成品库存，供总览看板。"""
    data = request.get_json(silent=True) or {}
    try:
        limit = max(1, min(int(data.get("limit") or 10), 30))
    except (TypeError, ValueError):
        limit = 10
    try:
        result = inventory_service.seed_board_demo(cost_record_service, limit=limit)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/inventory/replenish", methods=["GET"])
def inventory_replenish_list():
    status = request.args.get("status", "")
    try:
        limit = max(1, min(int(request.args.get("limit", "100")), 300))
    except ValueError:
        limit = 100
    return jsonify({"items": inventory_service.list_replenish(limit=limit, status=status)})


@app.route("/api/inventory/replenish", methods=["POST"])
def inventory_replenish_create():
    data = request.get_json(force=True) or {}
    part = str(data.get("product_part_no") or "").strip()
    qty = data.get("qty")
    sales_order_no = str(data.get("sales_order_no") or "").strip()
    note = str(data.get("note") or "").strip()
    line_id = data.get("line_id")
    try:
        lid = int(line_id) if line_id not in (None, "") else None
    except (TypeError, ValueError):
        return jsonify({"error": "line_id 无效"}), 400
    try:
        row = inventory_service.create_replenish(
            product_part_no=part,
            qty=qty,
            sales_order_no=sales_order_no,
            line_id=lid,
            note=note,
        )
        return jsonify({"ok": True, "item": row})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


def _shipment_to_dict(ev) -> dict:
    from test_impl.common.money import serialize_qty

    payload = {
        "id": ev.id,
        "line_id": ev.line_id,
        "ship_qty": serialize_qty(ev.ship_qty),
        "source": ev.source,
        "source_label": ev.source_label,
        "shipped_at": ev.shipped_at.isoformat(),
        "customer": ev.customer,
        "order_date": ev.order_date,
        "order_no": ev.order_no,
        "product_spec": ev.product_spec,
        "customer_part_no": ev.customer_part_no,
        "po_qty": serialize_qty(ev.po_qty),
        "shipped_qty_after": serialize_qty(ev.shipped_qty_after),
        "open_qty_after": serialize_qty(ev.open_qty_after),
    }
    payload["delivery_doc_no"] = delivery_note_service.resolve_delivery_doc_no(
        ev.id,
        getattr(ev, "delivery_note_json", "") or "",
    )
    try:
        ui = delivery_note_service.ship_ui_mode(ev.customer or "")
        payload["delivery_note_mode"] = ui.get("mode", "wkt_standard")
        if ui.get("mode") == "custom_excel":
            payload["delivery_note_download_url"] = f"/api/delivery-notes/{ev.id}/download"
            payload["delivery_note_open_local_url"] = f"/api/delivery-notes/{ev.id}/open-local"
            rel = line_service._store.get_shipment_attachment(ev.id)
            payload["delivery_note_attachment"] = rel
            payload["has_delivery_note_attachment"] = bool(rel)
            if rel:
                try:
                    st = delivery_note_service.attachment_status(ev.id)
                    payload["saved_at"] = st.get("saved_at", "")
                except ValueError:
                    payload["saved_at"] = ""
        elif ui.get("raw_download_url"):
            payload["delivery_note_download_url"] = ui["raw_download_url"]
        elif ui.get("mode") == "wkt_standard":
            payload["delivery_note_print_url"] = f"/delivery-note/print/{ev.id}"
            payload["delivery_note_download_url"] = f"/api/delivery-notes/{ev.id}/download"
    except ValueError:
        payload["delivery_note_mode"] = "none"
    return payload


@app.route("/api/shipment-events", methods=["GET"])
def list_shipment_events():
    """出货明细：仅未结出货登记与历史导入，与 /api/lines 分离。"""
    q = request.args.get("q", "")
    customer = request.args.get("customer", "")
    events = line_service.list_shipment_events(q=q, customer=customer)
    return jsonify([_shipment_to_dict(ev) for ev in events])


@app.route("/api/shipment-events/<int:event_id>/return-open", methods=["POST"])
def return_shipment_to_open(event_id: int):
    """撤销误出货：删除出货明细记录，已出货数量回退，料号回到未结订单。"""
    try:
        line, removed_id = line_service.reverse_shipment_event(event_id)
        payload = _line_to_dict(line)
        payload["removed_shipment_event_id"] = removed_id
        payload["open_qty"] = serialize_qty(line.open_qty())
        payload["returned_to_open"] = line.open_qty() > 0
        return jsonify(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc) or "撤销失败"}), 500


@app.route("/api/lines", methods=["GET"])
def list_lines():
    q = request.args.get("q", "")
    customer = request.args.get("customer", "")
    view = request.args.get("view", "all")
    if (view or "").strip().lower() == "shipped":
        return jsonify([])
    lines = line_service.list_lines(q=q, customer=customer, view=view)
    if (view or "").strip().lower() == "closed":
        last_map = line_service.get_last_shipment_info_for_lines([ln.id for ln in lines])
        return jsonify([_line_to_dict(ln, last_map.get(ln.id)) for ln in lines])
    if (view or "").strip().lower() == "open":
        stock_map = {
            row["line_id"]: row
            for row in planning_service.compare_open_lines(customer=customer, q=q)
        }
        return jsonify([_line_to_dict(ln, stock=stock_map.get(ln.id)) for ln in lines])
    return jsonify([_line_to_dict(ln) for ln in lines])


@app.route("/api/lines", methods=["POST"])
def create_line():
    data = request.get_json(force=True) or {}
    data.pop("notify_source", None)
    try:
        line = line_service.create_line(data)
        payload = _line_to_dict(line)
        return jsonify(payload), 201
    except DuplicateLineError as exc:
        return jsonify({"error": str(exc), "duplicate_id": exc.line_id}), 409
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/lines/<int:line_id>", methods=["PUT"])
def update_line(line_id: int):
    data = request.get_json(force=True) or {}
    try:
        line = line_service.update_line(line_id, data)
        payload = _line_to_dict(line)
        return jsonify(payload)
    except DuplicateLineError as exc:
        return jsonify({"error": str(exc), "duplicate_id": exc.line_id}), 409
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/lines/<int:line_id>/force-close", methods=["POST"])
def force_close_line(line_id: int):
    """未结订单强制结案：不记出货、不纳入对账。"""
    try:
        line = line_service.force_close_line(line_id)
        payload = _line_to_dict(line)
        payload["force_closed"] = True
        return jsonify(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/lines/force-close-batch", methods=["POST"])
def force_close_lines_batch():
    """未结订单批量强制结案：不记出货、不纳入对账。"""
    data = request.get_json(force=True) or {}
    raw_ids = data.get("line_ids")
    if not isinstance(raw_ids, list) or len(raw_ids) < 1:
        return jsonify({"error": "请至少选择一条料号"}), 400
    try:
        line_ids = [int(x) for x in raw_ids]
    except (TypeError, ValueError):
        return jsonify({"error": "line_ids 格式无效"}), 400
    closed, errors = line_service.force_close_lines_batch(line_ids)
    if not closed:
        err_msg = errors[0]["error"] if errors else "强制结案失败"
        return jsonify({"error": err_msg, "errors": errors}), 400
    payloads = []
    for line in closed:
        payload = _line_to_dict(line)
        payload["force_closed"] = True
        payloads.append(payload)
    return jsonify(
        {
            "ok": True,
            "closed": payloads,
            "closed_count": len(closed),
            "errors": errors,
        }
    )


@app.route("/delivery-note/ship-confirm")
def delivery_note_ship_confirm():
    """出货确认：与正式送货单相同版式，字段可编辑。"""
    line_id = request.args.get("line_id", type=int)
    qty = (request.args.get("qty") or request.args.get("ship_qty") or "").strip()
    if not line_id:
        return "缺少 line_id", 400
    if not qty:
        return "缺少出货数量", 400
    try:
        doc = delivery_note_service.build_ship_draft(line_id, qty)
        return render_template("delivery_note_wkt_confirm.html", doc=doc)
    except ValueError as exc:
        return str(exc), 400


def _parse_batch_ship_items_param(raw: str) -> list[dict]:
    items: list[dict] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        lid, qty = part.split(":", 1)
        lid = lid.strip()
        qty = qty.strip()
        if not lid or not qty:
            continue
        items.append({"line_id": int(lid), "qty": qty})
    return items


@app.route("/delivery-note/batch-ship-confirm")
def delivery_note_batch_ship_confirm():
    """合并出货确认：同一客户多料号共用一张送货单。"""
    raw = (request.args.get("items") or "").strip()
    items = _parse_batch_ship_items_param(raw)
    if len(items) < 2:
        return "合并出货至少需要两条料号（items 格式：line_id:qty,line_id:qty）", 400
    try:
        doc = delivery_note_service.build_batch_ship_draft(items)
        from test_impl.order_management.delivery_note.wkt_document import document_from_dict

        return render_template("delivery_note_wkt_confirm.html", doc=document_from_dict(doc))
    except ValueError as exc:
        return str(exc), 400


@app.route("/api/lines/batch-ship-draft", methods=["POST"])
def batch_ship_delivery_draft():
    data = request.get_json(force=True) or {}
    items = data.get("items")
    if not isinstance(items, list) or len(items) < 2:
        return jsonify({"error": "合并出货至少需要两条料号"}), 400
    try:
        doc = delivery_note_service.build_batch_ship_draft(items)
        return jsonify({"ok": True, "doc": doc})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/lines/batch-ship", methods=["POST"])
def batch_ship_lines():
    data = request.get_json(force=True) or {}
    items = data.get("items")
    if not isinstance(items, list) or len(items) < 2:
        return jsonify({"error": "合并出货至少需要两条料号"}), 400
    delivery_note = data.get("delivery_note")
    try:
        updated_lines, events = line_service.ship_lines_batch(
            items,
            delivery_note=delivery_note if isinstance(delivery_note, dict) else None,
        )
        doc_no = ""
        if isinstance(delivery_note, dict):
            doc_no = str(delivery_note.get("doc_no") or "").strip()
        line_payloads = []
        for line, event in zip(updated_lines, events):
            payload = _line_to_dict(line)
            payload["closed"] = line.open_qty() <= 0
            payload["shipment_event_id"] = event.id
            line_payloads.append(payload)
        first_event_id = events[0].id
        batch_payload = {
            "ok": True,
            "customer": updated_lines[0].customer,
            "shipment_event_id": first_event_id,
            "shipment_event_ids": [ev.id for ev in events],
            "lines": line_payloads,
        }
        _enrich_ship_delivery_urls(batch_payload, updated_lines[0].customer, first_event_id)
        return jsonify(batch_payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/lines/<int:line_id>/ship-delivery-draft", methods=["GET"])
def ship_delivery_draft(line_id: int):
    qty = request.args.get("qty") or request.args.get("ship_qty")
    if qty is None or str(qty).strip() == "":
        return jsonify({"error": "请填写本次出货数量"}), 400
    try:
        doc = delivery_note_service.build_ship_draft(line_id, str(qty).strip())
        return jsonify({"ok": True, "doc": doc})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


def _enrich_ship_delivery_urls(payload: dict, customer: str, event_id: int) -> None:
    try:
        ui = delivery_note_service.ship_ui_mode(customer)
    except ValueError:
        return
    mode = ui.get("mode")
    if mode == "none":
        payload.pop("delivery_note_print_url", None)
        payload.pop("delivery_note_download_url", None)
        payload["delivery_note_mode"] = "none"
        return
    if mode == "custom_excel":
        payload["delivery_note_mode"] = "custom_excel"
        payload.pop("delivery_note_print_url", None)
        payload["delivery_note_download_url"] = f"/api/delivery-notes/{event_id}/download"
        payload["delivery_note_open_local_url"] = f"/api/delivery-notes/{event_id}/open-local"
        return
    payload["delivery_note_mode"] = "wkt_standard"
    payload["delivery_note_print_url"] = f"/delivery-note/print/{event_id}"
    payload["delivery_note_download_url"] = f"/api/delivery-notes/{event_id}/download"


@app.route("/api/lines/<int:line_id>/ship", methods=["POST"])
def ship_line(line_id: int):
    data = request.get_json(force=True) or {}
    qty = data.get("qty") if data.get("qty") is not None else data.get("ship_qty")
    if qty is None or str(qty).strip() == "":
        return jsonify({"error": "请填写本次出货数量"}), 400
    delivery_note = data.get("delivery_note")
    try:
        line, event = line_service.ship_line(
            line_id, qty, delivery_note=delivery_note if isinstance(delivery_note, dict) else None
        )
        payload = _line_to_dict(line)
        payload["closed"] = line.open_qty() <= 0
        payload["shipment_event_id"] = event.id
        _enrich_ship_delivery_urls(payload, line.customer, event.id)
        doc_no = ""
        if isinstance(delivery_note, dict):
            doc_no = str(delivery_note.get("doc_no") or "").strip()
        return jsonify(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/delivery-note/settings")
def delivery_note_settings_page():
    """兼容旧链接，进入订单管理送货单维护子模块。"""
    return redirect("/#delivery")


@app.route("/delivery-note/print/<int:event_id>")
def delivery_note_print(event_id: int):
    try:
        doc = delivery_note_service.build_wkt_document_dict(event_id)
        return render_template(
            "delivery_note_wkt.html",
            doc=doc,
            download_url=f"/api/delivery-notes/{event_id}/download",
        )
    except ValueError as exc:
        return str(exc), 404


@app.route("/api/delivery-notes/<int:event_id>/download")
def delivery_note_download(event_id: int):
    try:
        kind, payload = delivery_note_service.render_for_event(event_id)
        if kind != "xlsx":
            return jsonify({"error": "无法生成 Excel 送货单"}), 400
        data, fname = payload
        return send_file(
            io.BytesIO(data),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=fname,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/delivery-notes/<int:event_id>/open-local", methods=["POST"])
def delivery_note_open_local(event_id: int):
    data = request.get_json(force=True, silent=True) or {}
    batch_ids = data.get("batch_event_ids") or data.get("event_ids") or []
    if not isinstance(batch_ids, list):
        batch_ids = []
    regenerate = data.get("regenerate", True)
    if isinstance(regenerate, str):
        regenerate = regenerate.lower() not in ("0", "false", "no")
    try:
        return jsonify(
            delivery_note_service.open_custom_excel_local(
                event_id,
                [int(x) for x in batch_ids if str(x).strip().isdigit()],
                regenerate=bool(regenerate),
            )
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/delivery-notes/<int:event_id>/attachment-status", methods=["GET"])
def delivery_note_attachment_status(event_id: int):
    try:
        return jsonify(delivery_note_service.attachment_status(event_id))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/delivery-note/preview-sample")
def delivery_note_preview_sample():
    customer = (request.args.get("customer") or "").strip()
    embed = request.args.get("embed") == "1"
    if not customer:
        return "缺少客户参数", 400
    try:
        info = delivery_note_service.preview_for_customer(customer)
        if info.get("is_custom_excel"):
            return render_template(
                "delivery_note_custom_preview.html",
                customer=customer,
                template_file=info.get("template_file") or "",
                template_missing=info.get("template_missing"),
                download_url=info.get("raw_download_url") or info.get("preview_download_url"),
                embed=embed,
            )
        doc = delivery_note_service.render_sample_html_doc(customer)
        return render_template(
            "delivery_note_wkt.html",
            doc=doc,
            download_url=info.get("preview_download_url"),
            embed=embed,
        )
    except ValueError as exc:
        return str(exc), 404


@app.route("/api/delivery-templates/preview", methods=["GET"])
def delivery_template_preview_meta():
    customer = (request.args.get("customer") or "").strip()
    try:
        return jsonify(delivery_note_service.preview_for_customer(customer))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/delivery-templates/preview-download", methods=["GET"])
def delivery_template_preview_download():
    customer = (request.args.get("customer") or "").strip()
    try:
        kind, payload = delivery_note_service.render_sample_for_customer(customer)
        if kind != "xlsx":
            return jsonify({"error": "无法生成 Excel 预览"}), 400
        data, fname = payload
        return send_file(
            io.BytesIO(data),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=False,
            download_name=fname,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/delivery-templates/raw", methods=["GET"])
def delivery_template_raw():
    customer = (request.args.get("customer") or "").strip()
    try:
        data, fname = delivery_note_service.raw_template_bytes(customer)
        return send_file(
            io.BytesIO(data),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=False,
            download_name=fname,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/delivery-templates/ship-ui", methods=["GET"])
def delivery_template_ship_ui():
    customer = (request.args.get("customer") or "").strip()
    try:
        return jsonify({"ok": True, **delivery_note_service.ship_ui_mode(customer)})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/delivery-templates/upload-for-customer", methods=["POST"])
def upload_delivery_template_for_customer():
    customer = (request.form.get("customer") or "").strip()
    f = request.files.get("file")
    if not customer:
        return jsonify({"error": "客户名称不能为空"}), 400
    if not f or not f.filename:
        return jsonify({"error": "请选择 Excel 模板文件"}), 400
    try:
        name = delivery_note_service.upload_template_file(normalize_upload_filename(f.filename), f.read())
        delivery_note_service.set_customer_template(customer, name)
        return jsonify({"ok": True, "customer": customer, "filename": name})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/delivery-templates", methods=["GET"])
def list_delivery_templates():
    return jsonify(delivery_note_service.list_config())


@app.route("/api/delivery-templates/customer-info", methods=["GET", "POST"])
def delivery_template_customer_info():
    if request.method == "GET":
        customer = (request.args.get("customer") or "").strip()
        if not customer:
            return jsonify({"error": "缺少客户参数"}), 400
        return jsonify(
            {
                "customer": customer,
                "info": delivery_note_service.get_customer_delivery(customer),
            }
        )
    data = request.get_json(force=True) or {}
    try:
        customer = (data.get("customer") or "").strip()
        delivery_note_service.save_customer_delivery(customer, data.get("info") or {})
        return jsonify({"ok": True, "customer": customer})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/delivery-templates/upload", methods=["POST"])
def upload_delivery_template():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "请选择文件"}), 400
    try:
        name = delivery_note_service.upload_template_file(normalize_upload_filename(f.filename), f.read())
        return jsonify({"ok": True, "filename": name})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/delivery-templates/mapping", methods=["POST", "DELETE"])
def delivery_template_mapping():
    if request.method == "DELETE":
        data = request.get_json(force=True) or {}
        try:
            delivery_note_service.remove_customer_template(data.get("customer", ""))
            return jsonify({"ok": True})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    data = request.get_json(force=True) or {}
    try:
        customer = (data.get("customer") or "").strip()
        template = (data.get("template") or "").strip()
        delivery_note_service.set_customer_template(customer, template)
        preview = delivery_note_service.preview_for_customer(customer)
        return jsonify({"ok": True, "customer": customer, "template": template, **preview})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/customer-profiles", methods=["GET"])
def list_customer_profiles():
    rows = customer_profile_service.list_rows()
    return jsonify({"ok": True, "rows": rows, "count": len(rows)})


@app.route("/api/customer-profiles/detail", methods=["GET"])
def get_customer_profile():
    customer = request.args.get("customer", "").strip()
    if not customer:
        return jsonify({"error": "请选择客户"}), 400
    return jsonify(
        {
            "ok": True,
            "customer": customer,
            "profile": customer_profile_service.get(customer),
        }
    )


@app.route("/api/customer-profiles", methods=["POST"])
def save_customer_profile():
    data = request.get_json(force=True) or {}
    customer = (data.get("customer") or "").strip()
    if not customer:
        return jsonify({"error": "客户名称不能为空"}), 400
    try:
        profile = customer_profile_service.save(customer, data.get("profile") or {})
        return jsonify({"ok": True, "customer": customer, "profile": profile})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/customer-profiles/create", methods=["POST"])
def create_customer_profile():
    data = request.get_json(force=True) or {}
    customer = (data.get("customer") or "").strip()
    if not customer:
        return jsonify({"error": "客户名称不能为空"}), 400
    try:
        profile = customer_profile_service.create(customer, data.get("profile") or {})
        return jsonify({"ok": True, "customer": customer, "profile": profile})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/customer-profiles/delete", methods=["POST"])
def delete_customer_profile():
    data = request.get_json(force=True) or {}
    customer = (data.get("customer") or "").strip()
    if not customer:
        return jsonify({"error": "客户名称不能为空"}), 400
    try:
        customer_profile_service.delete(customer)
        return jsonify({"ok": True, "customer": customer})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/supplier-profiles", methods=["GET"])
def list_supplier_profiles():
    rows = supplier_profile_service.list_rows()
    return jsonify({"ok": True, "rows": rows, "count": len(rows)})


@app.route("/api/supplier-profiles/detail", methods=["GET"])
def get_supplier_profile():
    supplier = request.args.get("supplier", "").strip()
    if not supplier:
        return jsonify({"error": "请选择供应商"}), 400
    return jsonify(
        {
            "ok": True,
            "supplier": supplier,
            "profile": supplier_profile_service.get(supplier),
        }
    )


@app.route("/api/supplier-profiles", methods=["POST"])
def save_supplier_profile():
    data = request.get_json(force=True) or {}
    supplier = (data.get("supplier") or "").strip()
    if not supplier:
        return jsonify({"error": "供应商名称不能为空"}), 400
    try:
        new_supplier = (data.get("new_supplier") or "").strip()
        profile = supplier_profile_service.save(
            supplier,
            data.get("profile") or {},
            new_supplier=new_supplier,
        )
        final_name = new_supplier or supplier
        return jsonify({"ok": True, "supplier": final_name, "profile": profile})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/supplier-profiles/create", methods=["POST"])
def create_supplier_profile():
    data = request.get_json(force=True) or {}
    supplier = (data.get("supplier") or "").strip()
    if not supplier:
        return jsonify({"error": "供应商名称不能为空"}), 400
    try:
        profile = supplier_profile_service.create(supplier, data.get("profile") or {})
        return jsonify({"ok": True, "supplier": supplier, "profile": profile})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/supplier-profiles/delete", methods=["POST"])
def delete_supplier_profile():
    data = request.get_json(force=True) or {}
    supplier = (data.get("supplier") or "").strip()
    if not supplier:
        return jsonify({"error": "供应商名称不能为空"}), 400
    try:
        supplier_profile_service.delete(supplier)
        return jsonify({"ok": True, "supplier": supplier})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/lines/<int:line_id>", methods=["DELETE"])
def delete_line(line_id: int):
    try:
        line_service.get_line(line_id)
        line_service.delete_line(line_id)
        return jsonify({"ok": True})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/lines/import/template", methods=["GET"])
def import_lines_template():
    try:
        data = build_template_bytes()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 500
    return send_file(
        io.BytesIO(data),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="WKT订单导入模板.xlsx",
    )


@app.route("/api/lines/import/preview", methods=["POST"])
def import_lines_preview():
    upload = request.files.get("file")
    if upload is None or upload.filename == "":
        return jsonify({"error": "请选择 Excel 文件（.xlsx / .csv）"}), 400
    ext = Path(upload.filename).suffix.lower()
    if ext not in (".xlsx", ".xlsm", ".csv"):
        return jsonify({"error": "仅支持 .xlsx 或 .csv 格式"}), 400
    try:
        rows, unknown = parse_excel_bytes(upload.read(), upload.filename)
        if not rows:
            return jsonify({"error": "未解析到有效数据行，请检查表头与内容"}), 400
        return jsonify(summarize_results(rows, unknown_headers=unknown or None))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


def _import_tier_from_item(item: dict) -> str:
    tier = str(item.get("review_status") or "").strip()
    if tier in ("passed", "pending", "blocked"):
        return tier
    if item.get("importable") is False:
        return "blocked"
    issues = item.get("issues") or []
    if any(i.get("level") == "warn" for i in issues):
        return "pending"
    return "passed"


@app.route("/api/lines/import/pending", methods=["GET"])
def list_import_pending():
    return jsonify({"rows": line_service.list_pending_import(), "count": len(line_service.list_pending_import())})


@app.route("/api/lines/import/stage-pending", methods=["POST"])
def stage_import_pending():
    body = request.get_json(force=True) or {}
    rows = body.get("rows") or []
    staged = []
    for item in rows:
        if _import_tier_from_item(item) != "pending":
            continue
        data = item.get("data") if isinstance(item, dict) and "data" in item else item
        if isinstance(data, dict):
            staged.append(item)
    count = line_service.stage_pending_import(staged)
    return jsonify({"staged": count})


@app.route("/api/lines/import/confirm", methods=["POST"])
def import_lines_confirm():
    body = request.get_json(force=True) or {}
    raw_rows = body.get("rows") or []
    tier = str(body.get("tier") or "passed").strip()  # passed | pending | all_importable
    if not raw_rows:
        return jsonify({"error": "没有可导入的数据"}), 400

    to_create: list = []
    skipped: list = []
    for item in raw_rows:
        data = item.get("data") if isinstance(item, dict) and "data" in item else item
        if not isinstance(data, dict):
            skipped.append({"error": "行数据格式无效"})
            continue
        item_tier = _import_tier_from_item(item)
        if tier == "passed" and item_tier != "passed":
            continue
        if tier == "pending" and item_tier != "pending":
            continue
        if tier == "all_importable" and item_tier == "blocked":
            skipped.append({"row_no": item.get("row_no"), "tier": item_tier})
            continue
        check = validate_import_row(dict(data), row_no=int(item.get("row_no", 0) or 0))
        if check.importable:
            to_create.append(check.data)
        else:
            skipped.append(
                {
                    "row_no": item.get("row_no"),
                    "issues": [i.to_dict() for i in check.issues],
                }
            )

    if not to_create:
        return jsonify({"error": "没有符合导入条件的行", "skipped": skipped, "tier": tier}), 400

    result = line_service.bulk_create_lines(to_create)
    result["tier"] = tier
    result["skipped"] = len(skipped)
    if tier == "pending":
        line_service.clear_pending_import()
    return jsonify(result), 201


@app.route("/api/feishu/config", methods=["GET", "POST"])
def feishu_config_api():
    if request.method == "GET":
        return jsonify(public_feishu_config())
    data = request.get_json(force=True) or {}
    try:
        saved = save_feishu_config(data)
        return jsonify({"ok": True, **saved})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/feishu/test", methods=["POST"])
def feishu_test_api():
    try:
        send_test_message()
        return jsonify({"ok": True})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/lines/recognize", methods=["POST"])
def recognize_lines():
    upload = request.files.get("file")
    if upload is None or upload.filename == "":
        return jsonify({"error": "请选择要上传的订单文件（PDF / 图片）"}), 400

    file_bytes = upload.read()
    filename = upload.filename
    job_id = str(uuid.uuid4())

    with _jobs_lock:
        _recognize_jobs[job_id] = {
            "status": "running",
            "progress": 0,
            "message": "任务已创建…",
        }

    def _run() -> None:
        def on_progress(pct: int, msg: str) -> None:
            with _jobs_lock:
                if job_id in _recognize_jobs:
                    _recognize_jobs[job_id].update(
                        progress=pct, message=msg, status="running"
                    )

        try:
            result = intake_service.recognize_lines(file_bytes, filename, on_progress)
            lines = result.get("lines") or []
            for ln in lines:
                ln.pop("_raw_text", None)
            archived_path, archived_error = try_archive_order_file(
                file_bytes, filename, lines, ORDERS_DIR
            )
            preview_pages = render_document_preview_pages(file_bytes, filename)
            with _jobs_lock:
                if preview_pages:
                    _recognize_previews[job_id] = preview_pages
                job_data = {
                    "status": "done",
                    "progress": 100,
                    "message": "识别完成",
                    "job_id": job_id,
                    "lines": lines,
                    "validation": result.get("validation") or {},
                    "ocr_text": result.get("ocr_text") or {},
                    "preview_pages": len(preview_pages),
                }
                if archived_path:
                    job_data["archived_path"] = archived_path
                    job_data["message"] = f"识别完成，已归档至 {archived_path}"
                if archived_error:
                    job_data["archived_error"] = archived_error
                _recognize_jobs[job_id] = job_data
        except (TextExtractionError, DeepSeekError, ValueError) as exc:
            with _jobs_lock:
                _recognize_jobs[job_id] = {
                    "status": "error",
                    "progress": 0,
                    "message": str(exc),
                    "error": str(exc),
                }

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/lines/recognize/<job_id>/preview/<int:page>")
def recognize_lines_preview_page(job_id: str, page: int):
    with _jobs_lock:
        pages = _recognize_previews.get(job_id)
    if not pages or page < 0 or page >= len(pages):
        return jsonify({"error": "预览不存在或已过期"}), 404
    return send_file(
        io.BytesIO(pages[page]),
        mimetype="image/png",
        download_name=f"preview-{job_id}-{page + 1}.png",
    )


@app.route("/api/lines/recognize/<job_id>", methods=["GET"])
def recognize_lines_status(job_id: str):
    with _jobs_lock:
        job = _recognize_jobs.get(job_id)
    if job is None:
        return jsonify({"error": "识别任务不存在或已过期"}), 404
    return jsonify(job)


@app.route("/api/orders", methods=["GET"])
def list_orders():
    orders = sorted(service.list_orders(), key=lambda o: o.created_at, reverse=True)
    return jsonify([_order_to_dict(o) for o in orders])


@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json(force=True)
    try:
        order = service.create_order(
            order_no=data["order_no"],
            customer=data["customer"],
            created_by=data.get("created_by", ""),
            order_date=data.get("order_date", ""),
            delivery_date=data.get("delivery_date", ""),
            payment_terms=data.get("payment_terms", ""),
            items=data["items"],
        )
        return jsonify(_order_to_dict(order)), 201
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/orders/<order_no>/approve", methods=["POST"])
def approve_order(order_no: str):
    data = request.get_json(force=True) or {}
    try:
        order = service.approve_order(order_no, approved_by=data.get("approved_by", "system"))
        return jsonify(_order_to_dict(order))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/orders/<order_no>/cancel", methods=["POST"])
def cancel_order(order_no: str):
    data = request.get_json(force=True) or {}
    try:
        order = service.cancel_order(order_no, operator=data.get("operator", "system"))
        return jsonify(_order_to_dict(order))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/orders/recognize", methods=["POST"])
def recognize_order():
    upload = request.files.get("file")
    if upload is None or upload.filename == "":
        return jsonify({"error": "请选择要上传的订单文件（PDF）"}), 400
    try:
        file_bytes = upload.read()
        result = intake_service.recognize(file_bytes, upload.filename)
        return jsonify(result)
    except (TextExtractionError, DeepSeekError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400



@app.route("/api/cost/options", methods=["GET"])
def cost_options():
    return jsonify(
        {
            "materials": cost_service.get_materials(),
            "processes": cost_service.get_processes(),
            "process_options": cost_service.get_process_options(),
        }
    )


@app.route("/api/cost/quote", methods=["POST"])
def cost_quote():
    data = request.get_json(force=True) or {}
    try:
        quote = cost_service.build_quote(data)
        return jsonify(cost_service.quote_to_dict(quote))
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/cost/records", methods=["GET"])
def cost_records_list():
    q = request.args.get("q", "")
    customer = request.args.get("customer", "")
    product_part_no = request.args.get("product_part_no", "")
    records = cost_record_service.list_records(
        q=q,
        customer=customer,
        product_part_no=product_part_no,
    )
    return jsonify(
        {
            "records": [cost_record_service.record_to_dict(r) for r in records],
            "total": len(records),
        }
    )


@app.route("/api/cost/records", methods=["POST"])
def cost_records_create():
    data = request.get_json(force=True) or {}
    try:
        record = cost_record_service.create_record(data)
        payload = cost_record_service.record_to_dict(record)
        return jsonify(payload), 201
    except (KeyError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/cost/bom-import/parse", methods=["POST"])
def cost_bom_import_parse():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"error": "请上传 Excel 文件"}), 400
    name = (upload.filename or "").lower()
    if not name.endswith((".xlsx", ".xlsm", ".xls")):
        return jsonify({"error": "仅支持 .xlsx / .xlsm / .xls 格式的 BOM 表单"}), 400
    try:
        parsed = parse_bom_workbook(upload.read(), filename=upload.filename or "")
        customer_names: set[str] = set()
        for name in line_service.list_master().get("customers") or []:
            if str(name).strip():
                customer_names.add(str(name).strip())
        customer_names.update(list_profile_customers())
        batch = preview_import_batch(
            parsed,
            store=cost_record_service._store,
            filename=upload.filename or "",
            customer_names=sorted(customer_names),
        )
        previews = batch["items"]
        passed = sum(1 for p in previews if p["tier"] == "passed")
        pending = sum(1 for p in previews if p["tier"] == "pending")
        blocked = sum(1 for p in previews if p["tier"] == "blocked")
        duplicate_parts = sum(1 for p in previews if p.get("duplicate_part_no"))
        return jsonify(
            {
                "ok": True,
                "total": len(previews),
                "passed": passed,
                "pending": pending,
                "blocked": blocked,
                "duplicate_parts": duplicate_parts,
                "customer_hint": batch.get("customer_hint", ""),
                "customer_resolved": batch.get("customer_resolved", ""),
                "customer_error": batch.get("customer_error", ""),
                "items": previews,
            }
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/cost/bom-import/commit", methods=["POST"])
def cost_bom_import_commit():
    data = request.get_json(force=True) or {}
    raw_items = data.get("items") or []
    if not isinstance(raw_items, list) or not raw_items:
        return jsonify({"error": "没有可导入的数据"}), 400
    payloads = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        payload = item.get("payload")
        if isinstance(payload, dict):
            payloads.append(payload)
    if not payloads:
        return jsonify({"error": "导入项缺少 payload"}), 400
    skip_supplier = bool(data.get("skip_supplier_check", True))
    overwrite = bool(data.get("overwrite", True))
    result = cost_record_service.import_bom_rows(
        payloads,
        skip_supplier_check=skip_supplier,
        overwrite=overwrite,
    )
    return jsonify({"ok": True, **result})


@app.route("/api/cost/bom-import/revalidate", methods=["POST"])
def cost_bom_import_revalidate():
    data = request.get_json(force=True) or {}
    raw_items = data.get("items") or []
    if not isinstance(raw_items, list) or not raw_items:
        return jsonify({"error": "没有可校验的数据"}), 400
    store = cost_record_service._store
    results = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        parsed = item.get("parsed")
        if not isinstance(parsed, dict):
            continue
        customer = str(item.get("customer_name") or parsed.get("customer_name") or "").strip()
        fields = item.get("fields") if isinstance(item.get("fields"), dict) else {}
        check_existing_db = bool(data.get("check_existing_db", False))
        updated = revalidate_preview_item(
            parsed,
            customer,
            store=store,
            fields=fields,
            check_existing_db=check_existing_db,
        )
        updated["index"] = item.get("index")
        if item.get("sheet_name"):
            updated["sheet_name"] = str(item.get("sheet_name") or "").strip()
        results.append(updated)
    if not results:
        return jsonify({"error": "校验项缺少 parsed"}), 400
    passed = sum(1 for p in results if p["tier"] == "passed")
    pending = sum(1 for p in results if p["tier"] == "pending")
    blocked = sum(1 for p in results if p["tier"] == "blocked")
    return jsonify(
        {
            "ok": True,
            "items": results,
            "passed": passed,
            "pending": pending,
            "blocked": blocked,
            "total": len(results),
        }
    )


@app.route("/api/cost/bom-import/sync-duplicates", methods=["POST"])
def cost_bom_import_sync_duplicates():
    data = request.get_json(force=True) or {}
    raw_items = data.get("items") or []
    if not isinstance(raw_items, list) or not raw_items:
        return jsonify({"error": "没有可同步的数据"}), 400
    items = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        parsed = item.get("parsed")
        if not isinstance(parsed, dict):
            continue
        items.append(
            {
                "index": item.get("index"),
                "parsed": dict(parsed),
                "tier": item.get("tier", "pending"),
                "issues": list(item.get("issues") or []),
                "duplicate_part_no": bool(item.get("duplicate_part_no")),
            }
        )
    if not items:
        return jsonify({"error": "同步项缺少 parsed"}), 400
    duplicate_parts = apply_batch_duplicate_part_hints(items)
    return jsonify(
        {
            "ok": True,
            "duplicate_parts": duplicate_parts,
            "items": [
                {
                    "index": it.get("index"),
                    "tier": it.get("tier"),
                    "issues": it.get("issues") or [],
                    "duplicate_part_no": bool(it.get("duplicate_part_no")),
                }
                for it in items
            ],
        }
    )


@app.route("/api/cost/records/<int:record_id>", methods=["GET"])
def cost_records_get(record_id: int):
    try:
        record = cost_record_service.get_record(record_id)
        return jsonify(cost_record_service.record_to_dict(record))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404


@app.route("/api/cost/records/<int:record_id>", methods=["PUT"])
def cost_records_update(record_id: int):
    data = request.get_json(force=True) or {}
    try:
        record = cost_record_service.update_record(record_id, data)
        payload = cost_record_service.record_to_dict(record)
        return jsonify(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/cost/records/<int:record_id>", methods=["DELETE"])
def cost_records_delete(record_id: int):
    try:
        record = cost_record_service.get_record(record_id)
        cost_record_service.delete_record(record_id)
        return jsonify({"ok": True})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404


@app.route("/api/cost/part-numbers", methods=["GET"])
def cost_part_numbers():
    q = request.args.get("q", "")
    try:
        limit = int(request.args.get("limit", "20"))
    except ValueError:
        limit = 20
    items = cost_lookup_service.suggest_part_numbers(q=q, limit=limit)
    return jsonify({"items": items, "total": len(items)})


@app.route("/api/cost/customers", methods=["GET"])
def cost_customers():
    q = request.args.get("q", "")
    try:
        limit = int(request.args.get("limit", "20"))
    except ValueError:
        limit = 20
    items = cost_lookup_service.suggest_customers(q=q, limit=limit)
    return jsonify({"items": items, "total": len(items)})


@app.route("/api/cost/lookup", methods=["GET"])
def cost_lookup():
    product_part_no = request.args.get("product_part_no", "")
    try:
        return jsonify(cost_lookup_service.lookup_by_part_no(product_part_no))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


@app.route("/api/cost/missing-suppliers", methods=["GET"])
def cost_missing_suppliers():
    return jsonify(cost_record_service.list_missing_bom_suppliers())


@app.route("/api/reconciliation/config", methods=["GET"])
def reconciliation_config():
    return jsonify({"ok": True, **reconciliation_service.get_config()})


@app.route("/api/reconciliation/due-months", methods=["GET"])
def reconciliation_due_months():
    return jsonify({"ok": True, "months": reconciliation_service.list_due_months()})


@app.route("/api/reconciliation/customer-months", methods=["GET"])
def reconciliation_customer_months():
    q = request.args.get("q", "")
    due_month = request.args.get("due_month", "")
    ship_month = request.args.get("ship_month", "")
    collection_month = request.args.get("collection_month", "")
    rows = reconciliation_service.summarize_by_customer_month(
        q=q,
        due_month=due_month,
        ship_month=ship_month,
        collection_month=collection_month,
    )
    total = sum(float(r.get("total_amount") or 0) for r in rows)
    return jsonify({"ok": True, "rows": rows, "count": len(rows), "total_amount": f"{total:.2f}"})


@app.route("/api/reconciliation/lines", methods=["GET"])
def reconciliation_lines():
    q = request.args.get("q", "")
    customer = request.args.get("customer", "")
    due_month = request.args.get("due_month", "")
    ship_month = request.args.get("ship_month", "")
    collection_month = request.args.get("collection_month", "")
    rows = reconciliation_service.list_lines(
        q=q,
        customer=customer,
        due_month=due_month,
        ship_month=ship_month,
        collection_month=collection_month,
    )
    return jsonify({"ok": True, "lines": rows, "count": len(rows)})


@app.route("/api/reconciliation/summary", methods=["GET"])
def reconciliation_summary():
    q = request.args.get("q", "")
    customer = request.args.get("customer", "")
    due_month = request.args.get("due_month", "")
    ship_month = request.args.get("ship_month", "")
    collection_month = request.args.get("collection_month", "")
    rows = reconciliation_service.summarize_by_customer(
        q=q,
        customer=customer,
        due_month=due_month,
        ship_month=ship_month,
        collection_month=collection_month,
    )
    total = sum(float(r.get("total_amount") or 0) for r in rows)
    return jsonify({"ok": True, "customers": rows, "total_amount": f"{total:.2f}"})


@app.route("/api/reconciliation/due-outlook", methods=["GET"])
def reconciliation_due_outlook():
    data = reconciliation_service.due_outlook()
    return jsonify({"ok": True, **data})


@app.route("/api/payable/config", methods=["GET"])
def payable_config():
    return jsonify({"ok": True, **payable_service.get_config()})


@app.route("/api/payable/settlement-months", methods=["GET"])
def payable_settlement_months():
    return jsonify({"ok": True, "months": payable_service.list_settlement_months()})


@app.route("/api/payable/payment-months", methods=["GET"])
def payable_payment_months():
    return jsonify({"ok": True, "months": payable_service.list_payment_months()})


@app.route("/api/payable/supplier-months", methods=["GET"])
def payable_supplier_months():
    q = request.args.get("q", "")
    settlement_month = request.args.get("settlement_month", "")
    payment_month = request.args.get("payment_month", "")
    rows = payable_service.summarize_by_supplier_month(
        q=q,
        settlement_month=settlement_month,
        payment_month=payment_month,
    )
    total = sum(float(r.get("total_amount") or 0) for r in rows)
    return jsonify({"ok": True, "rows": rows, "count": len(rows), "total_amount": f"{total:.2f}"})


@app.route("/api/payable/due-outlook", methods=["GET"])
def payable_due_outlook():
    data = payable_service.due_outlook()
    return jsonify({"ok": True, **data})


@app.route("/api/payable/lines", methods=["GET"])
def payable_lines():
    q = request.args.get("q", "")
    supplier = request.args.get("supplier", "")
    settlement_month = request.args.get("settlement_month", "")
    payment_month = request.args.get("payment_month", "")
    receive_from = request.args.get("receive_from", "")
    receive_to = request.args.get("receive_to", "")
    rows = payable_service.list_lines(
        q=q,
        supplier=supplier,
        settlement_month=settlement_month,
        payment_month=payment_month,
        receive_from=receive_from,
        receive_to=receive_to,
    )
    return jsonify({"ok": True, "lines": rows, "count": len(rows)})


@app.route("/api/ai/status", methods=["GET"])
def ai_status():
    client = DeepSeekChatClient()
    return jsonify(
        {
            "ok": True,
            "configured": db_assistant.is_configured(),
            "model": client.assistant_model,
            "db_path": str(line_service.db_path),
        }
    )


@app.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    data = request.get_json(force=True) or {}
    try:
        result = db_assistant.ask(
            str(data.get("message") or ""),
            data.get("history") if isinstance(data.get("history"), list) else None,
        )
        return jsonify({"ok": True, **result})
    except DatabaseAssistantError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/ai/memory", methods=["GET"])
def ai_memory_get():
    return jsonify({"ok": True, **memory_to_api_dict()})


@app.route("/api/ai/memory", methods=["POST"])
def ai_memory_save():
    data = request.get_json(force=True) or {}
    try:
        current = load_memory()
        if "business_rules" in data and isinstance(data["business_rules"], list):
            current["business_rules"] = [
                str(x).strip() for x in data["business_rules"] if str(x).strip()
            ]
        if "glossary" in data and isinstance(data["glossary"], dict):
            current["glossary"] = {
                str(k).strip(): str(v).strip()
                for k, v in data["glossary"].items()
                if str(k).strip() and str(v).strip()
            }
        if "query_examples" in data and isinstance(data["query_examples"], list):
            current["query_examples"] = data["query_examples"]
        if "custom_prompt" in data:
            current["custom_prompt"] = str(data.get("custom_prompt") or "").strip()
        path = save_memory(current)
        return jsonify({"ok": True, **memory_to_api_dict(current), "saved_to": str(path)})
    except (ValueError, OSError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/api/ai/memory/remember", methods=["POST"])
def ai_memory_remember():
    """追加一条业务记忆（规则 / 术语 / 问法示例）。"""
    data = request.get_json(force=True) or {}
    kind = str(data.get("type") or "rule").strip().lower()
    try:
        if kind == "glossary":
            memory = append_glossary(
                str(data.get("term") or ""),
                str(data.get("meaning") or data.get("text") or ""),
            )
        elif kind == "example":
            memory = append_query_example(
                str(data.get("question") or data.get("text") or ""),
                str(data.get("note") or ""),
            )
        else:
            text = str(data.get("text") or data.get("rule") or "").strip()
            if text.startswith("记住：") or text.startswith("记住:"):
                text = text.split("：", 1)[-1].split(":", 1)[-1].strip()
            memory = append_business_rule(text)
        return jsonify({"ok": True, **memory_to_api_dict(memory)})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


if __name__ == "__main__":
    import os

    port = int(os.environ.get("WKT_PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"

    url = f"http://127.0.0.1:{port}"
    print("=" * 50)
    print("WKT 销售管理系统 Web 演示")
    print(f"请在浏览器打开: {url}")
    print(f"订单数据库: {line_service.db_path}")
    print(f"当前订单行数: {line_service.count_lines()}")
    print(f"设计库预览: {url}/design-gallery")
    print(f"主题切换:   {url}/themes")
    print("数据已保存到本地 SQLite，重启服务后仍会保留")
    print("注意: 本窗口必须保持运行，关闭或 Ctrl+C 后页面将无法访问")
    print("=" * 50)
    # Windows + Cursor 调试时关闭 reloader，避免双进程占端口导致打不开
    app.run(host="127.0.0.1", port=port, debug=debug, use_reloader=False)
