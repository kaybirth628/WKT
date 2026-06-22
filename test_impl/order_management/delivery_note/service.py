"""送货单：威可特统一版式（HTML 打印 + Excel 下载）。"""
from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from test_impl.common.money import serialize_qty
from test_impl.order_management.order_entry.line_service import OrderLineService
from test_impl.order_management.order_entry.shipment_models import ShipmentEvent

from .template_store import BUILTIN_HTML, DeliveryTemplateStore, WKT_STANDARD
from .wkt_document import (
    _gen_doc_no,
    build_document_from_event,
    build_draft_document,
    build_sample_document,
    document_from_dict,
    document_to_dict,
    get_customer_delivery_info,
    load_company_config,
    load_customer_delivery_config,
    save_customer_delivery_info,
    split_receiver_contact,
)
from .wkt_xlsx import build_xlsx_bytes

try:
    from openpyxl import load_workbook
except ImportError:
    load_workbook = None  # type: ignore

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def _fmt_dt_local(dt: datetime) -> str:
    if dt.tzinfo is not None:
        local = dt.astimezone()
    else:
        local = dt.replace(tzinfo=timezone.utc).astimezone()
    return local.strftime("%Y-%m-%d %H:%M")


def _fmt_date(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    if "T" in s:
        return s.split("T", 1)[0]
    return s[:10] if len(s) >= 10 else s


def _fmt_date_dot(s: str) -> str:
    base = _fmt_date(s)
    if not base:
        return ""
    parts = base.split("-")
    if len(parts) == 3:
        y, m, d = parts
        return f"{y}.{int(m)}.{int(d)}"
    return base


def _split_contact_phone(text: str) -> tuple[str, str]:
    contact, phone = split_receiver_contact(text or "")
    return contact, phone


class DeliveryNoteService:
    def __init__(
        self,
        line_service: OrderLineService,
        template_store: Optional[DeliveryTemplateStore] = None,
    ) -> None:
        self._lines = line_service
        self._templates = template_store or DeliveryTemplateStore()

    def get_event(self, event_id: int) -> ShipmentEvent:
        return self._lines.get_shipment_event(event_id)

    def build_context(self, event: ShipmentEvent) -> Dict[str, str]:
        line = self._lines.get_line(event.line_id)
        ship_qty = serialize_qty(event.ship_qty)
        po = serialize_qty(event.po_qty)
        shipped_after = serialize_qty(event.shipped_qty_after)
        open_after = serialize_qty(event.open_qty_after)
        shipped_at = _fmt_dt_local(event.shipped_at)
        ctx = {
            "customer": event.customer or line.customer,
            "order_no": event.order_no or line.order_no,
            "product_spec": event.product_spec or line.product_spec,
            "customer_part_no": event.customer_part_no or line.customer_part_no,
            "material": line.material or "",
            "unit": line.unit or "",
            "po_qty": po,
            "ship_qty": ship_qty,
            "shipped_qty_after": shipped_after,
            "open_qty_after": open_after,
            "order_date": _fmt_date(event.order_date or line.order_date),
            "delivery_date": _fmt_date(line.delivery_date),
            "shipped_at": shipped_at,
            "payment_terms": line.payment_terms or "",
            "客户": event.customer or line.customer,
            "订单号": event.order_no or line.order_no,
            "品名规格": event.product_spec or line.product_spec,
            "客户料号": event.customer_part_no or line.customer_part_no,
            "材质": line.material or "",
            "单位": line.unit or "",
            "PO数量": po,
            "本次出货": ship_qty,
            "出货数量": ship_qty,
            "累计已出货": shipped_after,
            "未结数量": open_after,
            "接单日期": _fmt_date(event.order_date or line.order_date),
            "客户交期": _fmt_date(line.delivery_date),
            "出货日期": shipped_at.split(" ")[0] if shipped_at else "",
            "出货时间": shipped_at,
            "账期": line.payment_terms or "",
        }
        return self._enrich_custom_template_context(
            ctx,
            (event.customer or line.customer or "").strip(),
            event=event,
            event_id=event.id,
        )

    def _enrich_custom_template_context(
        self,
        ctx: Dict[str, str],
        customer: str,
        *,
        event: Optional[ShipmentEvent] = None,
        event_id: Optional[int] = None,
    ) -> Dict[str, str]:
        company = load_company_config()
        delivery = get_customer_delivery_info(customer)
        recv_contact = (delivery.get("receiver_contact") or "").strip()
        recv_phone = (delivery.get("receiver_phone") or "").strip()
        if recv_contact and not recv_phone:
            recv_contact, recv_phone = _split_contact_phone(recv_contact)

        prefix = (delivery.get("doc_no_prefix") or "").strip() or company.get("doc_no_prefix", "WKT")
        ship_dt = event.shipped_at if event else datetime.now(timezone.utc)
        monthly_seq = 1
        if event is not None:
            eid = event_id if event_id is not None else getattr(event, "id", None)
            if eid:
                try:
                    monthly_seq = self._lines._store.monthly_sequence_for_shipment(eid, event.shipped_at)
                except Exception:
                    monthly_seq = 1

        order_date = ctx.get("接单日期") or ctx.get("order_date") or ""
        ship_date = ctx.get("出货日期") or order_date
        ship_dot = _fmt_date_dot(ship_date)

        ctx.update(
            {
                "送货单号": _gen_doc_no(prefix, ship_dt, monthly_seq),
                "制单日期": _fmt_date_dot(order_date),
                "发货日期": ship_dot,
                "仓库库位": "",
                "供应商名称": company.get("supplier_name", ""),
                "供应商地址": company.get("supplier_address", ""),
                "供应商联系人": company.get("supplier_contact", ""),
                "供应商电话": company.get("supplier_phone", ""),
                "收货公司": (delivery.get("receiver_company") or "").strip() or customer,
                "收货地址": delivery.get("receiver_address", ""),
                "收货联系人": recv_contact,
                "收货电话": recv_phone,
                "序号": "1",
                "供应商货号": ctx.get("材质") or ctx.get("客户料号") or "",
                "产品描述": ctx.get("品名规格") or "",
                "合计": ctx.get("本次出货") or "",
                "附注": "",
                "发货人": "",
                "检验": "",
                "检验日期": ship_dot,
                "财务": "",
                "财务日期": "",
                "承运人": "",
                "承运日期": "",
                "收货人": "",
                "收货日期": "",
                "备注": "",
            }
        )
        return ctx

    def build_wkt_document(self, event_id: int):
        snap = self._get_saved_delivery_note(event_id)
        if snap:
            return document_from_dict(snap)
        event = self.get_event(event_id)
        line = self._lines.get_line(event.line_id)
        monthly_seq = self._lines._store.monthly_sequence_for_shipment(event_id, event.shipped_at)
        return build_document_from_event(event, line, monthly_seq=monthly_seq)

    def build_wkt_document_dict(self, event_id: int) -> dict:
        return document_to_dict(self.build_wkt_document(event_id))

    def _get_saved_delivery_note(self, event_id: int) -> Optional[dict]:
        import json

        try:
            raw = self._lines._store.get_shipment_delivery_note_json(event_id)
        except ValueError:
            return None
        if not raw or not str(raw).strip():
            return None
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    def build_ship_draft(self, line_id: int, ship_qty: str) -> dict:
        line = self._lines.get_line(line_id)
        from test_impl.common.money import to_decimal

        qty = to_decimal(ship_qty, field="本次出货")
        doc = build_draft_document(line, qty)
        d = document_to_dict(doc)
        d["ship_qty"] = serialize_qty(qty)
        d["open_qty"] = serialize_qty(line.open_qty())
        d["customer"] = line.customer
        d["product_spec"] = line.product_spec
        return d

    def build_batch_ship_draft(self, items: List[dict]) -> dict:
        from test_impl.common.money import to_decimal
        from test_impl.order_management.delivery_note.wkt_document import build_batch_draft_document

        pairs: List[tuple] = []
        for raw in items:
            if not isinstance(raw, dict):
                raise ValueError("出货项格式无效")
            line_id = int(raw.get("line_id") or 0)
            if line_id <= 0:
                raise ValueError("缺少有效的 line_id")
            line = self._lines.get_line(line_id)
            qty = to_decimal(
                raw.get("qty") if raw.get("qty") is not None else raw.get("ship_qty"),
                field="本次出货",
            )
            pairs.append((line, qty))
        doc = build_batch_draft_document(pairs)
        d = document_to_dict(doc)
        d["customer"] = pairs[0][0].customer
        d["batch_items"] = [
            {"line_id": ln.id, "ship_qty": serialize_qty(q), "order_no": ln.order_no or ""}
            for ln, q in pairs
        ]
        return d

    def template_info(self, customer: str) -> dict:
        customer = (customer or "").strip()
        meta = self._templates.template_status(customer)
        return {"customer": customer, **meta, "is_excel": meta["is_custom_excel"], "is_builtin": False}

    def _replace_placeholders(self, text: str, ctx: Dict[str, str]) -> str:
        if not text or "{{" not in text:
            return text

        def repl(m: re.Match) -> str:
            key = m.group(1).strip()
            return ctx.get(key, m.group(0))

        return _PLACEHOLDER_RE.sub(repl, str(text))

    def fill_excel_bytes(self, template_path: Path, ctx: Dict[str, str]) -> bytes:
        if load_workbook is None:
            raise ValueError("openpyxl 未安装，无法生成 Excel 送货单")
        wb = load_workbook(template_path)
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    val = cell.value
                    if isinstance(val, str) and "{{" in val:
                        cell.value = self._replace_placeholders(val, ctx)
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def render_for_event(self, event_id: int) -> Tuple[str, Any]:
        event = self.get_event(event_id)
        line = self._lines.get_line(event.line_id)
        customer = (event.customer or line.customer or "").strip()
        custom_path = self._templates.resolve_template_path(customer)
        if custom_path:
            ctx = self.build_context(event)
            data = self.fill_excel_bytes(custom_path, ctx)
            fname = f"送货单_{_safe_file_part(customer)}_{event_id}.xlsx"
            return "xlsx", (data, fname)
        doc = self.build_wkt_document(event_id)
        data = build_xlsx_bytes(doc)
        fname = f"送货单_{_safe_file_part(event.customer)}_{event_id}.xlsx"
        return "xlsx", (data, fname)

    def build_sample_context(self, customer: str) -> Dict[str, str]:
        """维护页预览用示例数据（非真实出货）。"""
        customer = (customer or "").strip()
        now = datetime.now(timezone.utc).astimezone()
        shipped_at = now.strftime("%Y-%m-%d %H:%M")
        ship_date = now.strftime("%Y-%m-%d")
        return {
            "customer": customer,
            "order_no": "PO-预览-001",
            "product_spec": "（示例品名规格）",
            "customer_part_no": "（示例料号）",
            "material": "（示例材质）",
            "unit": "PCS",
            "po_qty": "1000",
            "ship_qty": "100",
            "shipped_qty_after": "100",
            "open_qty_after": "900",
            "order_date": ship_date,
            "delivery_date": ship_date,
            "shipped_at": shipped_at,
            "payment_terms": "（示例账期）",
            "客户": customer,
            "订单号": "PO-预览-001",
            "品名规格": "（示例品名规格）",
            "客户料号": "（示例料号）",
            "材质": "（示例材质）",
            "单位": "PCS",
            "PO数量": "1000",
            "本次出货": "100",
            "出货数量": "100",
            "累计已出货": "100",
            "未结数量": "900",
            "接单日期": ship_date,
            "客户交期": ship_date,
            "出货日期": ship_date,
            "出货时间": shipped_at,
            "账期": "（示例账期）",
        }
        return self._enrich_custom_template_context(ctx, customer)

    def preview_for_customer(self, customer: str) -> dict:
        customer = (customer or "").strip()
        if not customer:
            raise ValueError("请选择客户")
        from urllib.parse import quote

        q = quote(customer)
        info = get_customer_delivery_info(customer)
        meta = self._templates.template_status(customer)
        out = {
            "customer": customer,
            **meta,
            "is_excel": meta["is_custom_excel"],
            "is_builtin": False,
            "preview_download_url": f"/api/delivery-templates/preview-download?customer={q}",
            "sample_context": self.build_sample_context(customer),
            "delivery_info": info,
        }
        if meta["is_wkt_standard"]:
            out["preview_html_url"] = f"/delivery-note/preview-sample?customer={q}"
            out["template_label"] = "威可特统一送货单"
        else:
            out["preview_html_url"] = ""
            label = meta["template_file"] or "专用 Excel 模板"
            if meta["template_missing"]:
                label += "（文件缺失，请上传）"
            out["template_label"] = f"专用模板 · {label}"
        return out

    def render_sample_for_customer(self, customer: str) -> Tuple[str, Any]:
        customer = (customer or "").strip()
        custom_path = self._templates.resolve_template_path(customer)
        if custom_path:
            ctx = self.build_sample_context(customer)
            data = self.fill_excel_bytes(custom_path, ctx)
            fname = f"送货单预览_{_safe_file_part(customer)}.xlsx"
            return "xlsx", (data, fname)
        doc = build_sample_document(customer)
        data = build_xlsx_bytes(doc)
        fname = f"送货单预览_{_safe_file_part(customer)}.xlsx"
        return "xlsx", (data, fname)

    def render_sample_html_doc(self, customer: str) -> dict:
        return document_to_dict(build_sample_document(customer))

    def list_config(self) -> dict:
        customer_names: set[str] = set()
        try:
            for name in self._lines.list_master().get("customers") or []:
                if str(name).strip():
                    customer_names.add(str(name).strip())
        except Exception:
            pass
        delivery_cfg = load_company_config()
        all_delivery = load_customer_delivery_config()
        mapping = self._templates.load_mapping()
        customer_names.update(all_delivery.keys())
        customer_names.update(mapping.keys())
        rows = []
        for name in sorted(customer_names, key=lambda x: x.lower()):
            info = get_customer_delivery_info(name)
            meta = self._templates.template_status(name)
            if meta["is_wkt_standard"]:
                template_display = "威可特统一模板"
            elif meta["template_missing"]:
                template_display = f"专用 · {meta['template_file']}（待上传）"
            else:
                template_display = f"专用 · {meta['template_file']}"
            rows.append(
                {
                    "customer": name,
                    "template": meta["template"],
                    "template_display": template_display,
                    "template_file": meta.get("template_file", ""),
                    "is_builtin": False,
                    "is_excel": meta["is_custom_excel"],
                    "is_wkt_standard": meta["is_wkt_standard"],
                    "is_custom_excel": meta["is_custom_excel"],
                    "template_missing": meta["template_missing"],
                    "receiver_address": info.get("receiver_address", ""),
                    "receiver_contact": info.get("receiver_contact", ""),
                    "doc_no_prefix": info.get("doc_no_prefix", ""),
                }
            )
        return {
            "template": WKT_STANDARD,
            "supplier": delivery_cfg,
            "builtin": BUILTIN_HTML,
            "mapping": mapping,
            "special_customers": list(mapping.keys()),
            "template_files": self._templates.list_template_files(),
            "placeholder_help": list(_wkt_field_help()),
            "custom_placeholder_help": list(_custom_field_help()),
            "customer_rows": rows,
        }

    def get_customer_delivery(self, customer: str) -> dict:
        return get_customer_delivery_info(customer)

    def save_customer_delivery(self, customer: str, info: dict) -> None:
        save_customer_delivery_info(customer, info)

    def upload_template_file(self, filename: str, data: bytes) -> str:
        return self._templates.save_upload(filename, data)

    def set_customer_template(self, customer: str, template: str) -> None:
        self._templates.set_customer_template(customer, template)

    def remove_customer_template(self, customer: str) -> None:
        self._templates.remove_customer_mapping(customer)


def _safe_file_part(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", (s or "").strip())[:40] or "customer"


def _wkt_field_help() -> tuple[str, ...]:
    return (
        "全公司统一送货单版式（抬头为收货公司，供应商为威可特）。",
        "表格列：订单号、客户物料编码、物料名称、规格型号、单位、数量、生产批号、箱数、备注。",
        "每客户可维护：收货地点、联系人及电话、送货单号前缀（如 ABL）。",
        "出货后自动带出订单号、料号、品名、材质、单位、本次出货数量。",
    )


def _custom_field_help() -> tuple[str, ...]:
    return (
        "在 Excel 单元格写入占位符，出货时自动替换。常用：",
        "{{送货单号}} {{发货日期}} {{出货日期}} {{订单号}} {{客户料号}} {{品名规格}} {{产品描述}} {{材质}} {{本次出货}} {{合计}}",
        "{{供应商名称}} {{供应商地址}} {{收货公司}} {{收货地址}} {{收货联系人}} {{收货电话}}",
        "{{备注}} 留空时可出货后在 Excel 里手工填写。",
    )
