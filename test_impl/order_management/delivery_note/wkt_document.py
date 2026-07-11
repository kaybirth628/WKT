"""威可特统一送货单版式（对齐爱毕黎/附件 Excel 模板）。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from test_impl.common.money import serialize_qty
from test_impl.order_management.order_entry.shipment_models import ShipmentEvent

_ROOT = Path(__file__).resolve().parents[3]
_CONFIG_DIR = _ROOT / "data" / "delivery_templates"
_COMPANY_FILE = _CONFIG_DIR / "wkt_company.json"
_CUSTOMER_FILE = _CONFIG_DIR / "customer_delivery.json"


@dataclass
class WktDeliveryLine:
    order_no: str = ""
    customer_part_no: str = ""
    product_name: str = ""
    spec: str = ""
    unit: str = ""
    qty: str = ""
    batch_no: str = ""
    box_count: str = ""
    remark: str = ""


@dataclass
class WktDeliveryDocument:
    title_company: str
    doc_no: str
    ship_date_cn: str
    receiver_company: str
    receiver_address: str
    receiver_contact: str
    supplier_name: str
    supplier_address: str
    supplier_phone: str
    lines: List[WktDeliveryLine] = field(default_factory=list)
    total_qty: str = ""
    footer_note: str = ""
    deliverer: str = ""
    warehouse_manager: str = ""
    receiver_sign: str = ""
    is_sample: bool = False


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_company_config() -> dict:
    defaults = {
        "supplier_name": "昆山威可特精密电子有限公司",
        "supplier_address": "昆山市张浦镇长顺路55号",
        "supplier_phone": "0512-50152121",
        "footer_note": "一式四联：厂商白联；仓库红联；蓝联；IQC黄联；",
        "doc_no_prefix": "WKT",
    }
    cfg = _load_json(_COMPANY_FILE)
    defaults.update({k: v for k, v in cfg.items() if not str(k).startswith("_")})
    return defaults


def load_customer_delivery_config() -> Dict[str, dict]:
    return _load_json(_CUSTOMER_FILE)


def split_receiver_contact(text: str) -> tuple[str, str]:
    import re

    text = (text or "").strip()
    if not text:
        return "", ""
    m = re.search(r"(\d{7,})", text)
    if m:
        phone = m.group(1)
        contact = text[: m.start()].strip(" ,，、")
        return contact, phone
    return text, ""


def get_raw_customer_delivery_info(customer: str) -> dict:
    customer = (customer or "").strip()
    all_cfg = load_customer_delivery_config()
    row = all_cfg.get(customer, {})
    return row if isinstance(row, dict) else {}


def get_customer_delivery_info(customer: str) -> dict:
    """读取送货收货信息；地址/联系人为空时回退到客户档案。"""
    customer = (customer or "").strip()
    if not customer:
        return {}
    raw = get_raw_customer_delivery_info(customer)
    contact = (raw.get("receiver_contact") or "").strip()
    phone = (raw.get("receiver_phone") or "").strip()
    if contact and not phone:
        contact, phone = split_receiver_contact(contact)
    out = {
        "receiver_company": (raw.get("receiver_company") or "").strip(),
        "receiver_address": (raw.get("receiver_address") or "").strip(),
        "receiver_contact": contact,
        "receiver_phone": phone,
        "doc_no_prefix": (raw.get("doc_no_prefix") or "").strip(),
    }
    if not out["receiver_company"]:
        out["receiver_company"] = customer

    from test_impl.order_management.customer_profile.store import get_profile

    profile = get_profile(customer)
    if not out["receiver_address"]:
        addr = (profile.get("address") or "").strip()
        if addr:
            out["receiver_address"] = addr
    if not out["receiver_contact"]:
        out["receiver_contact"] = (profile.get("contact") or "").strip()
    if not out["receiver_phone"]:
        out["receiver_phone"] = (profile.get("phone") or "").strip()
    return out


def delivery_doc_prefix(customer: str) -> str:
    """送货单号前缀：客户维护 doc_no_prefix，否则全公司默认 WKT。"""
    cust_cfg = get_customer_delivery_info(customer)
    company = load_company_config()
    return (cust_cfg.get("doc_no_prefix") or "").strip() or company.get("doc_no_prefix", "WKT")


def save_customer_delivery_info(customer: str, info: dict) -> None:
    customer = (customer or "").strip()
    if not customer:
        raise ValueError("客户名称不能为空")
    existing = get_raw_customer_delivery_info(customer)
    contact = (info.get("receiver_contact") if "receiver_contact" in info else existing.get("receiver_contact") or "")
    contact = str(contact or "").strip()
    phone = (info.get("receiver_phone") if "receiver_phone" in info else existing.get("receiver_phone") or "")
    phone = str(phone or "").strip()
    if contact and not phone and "receiver_phone" not in info:
        contact, phone = split_receiver_contact(contact)
    elif "receiver_contact" in info and contact and not phone:
        contact, phone = split_receiver_contact(contact)
    if "doc_no_prefix" in info:
        doc_prefix = (info.get("doc_no_prefix") or "").strip()
    else:
        doc_prefix = (existing.get("doc_no_prefix") or "").strip()
    address = info.get("receiver_address") if "receiver_address" in info else existing.get("receiver_address") or ""
    all_cfg = load_customer_delivery_config()
    all_cfg[customer] = {
        "receiver_company": (
            (info.get("receiver_company") or "").strip()
            or (existing.get("receiver_company") or "").strip()
        ),
        "receiver_address": str(address or "").strip(),
        "receiver_contact": contact,
        "receiver_phone": phone,
        "doc_no_prefix": doc_prefix,
    }
    _save_json(_CUSTOMER_FILE, all_cfg)


def _fmt_date_cn(dt: datetime) -> str:
    local = dt.astimezone() if dt.tzinfo else dt.replace(tzinfo=timezone.utc).astimezone()
    return f"{local.year}年{local.month}月{local.day}日"


def _gen_doc_no(prefix: str, dt: datetime, monthly_seq: int = 0) -> str:
    """送货单号：{前缀}{YYYYMMDD}{当月序号4位}；序号每月1日归零后按出货递增。"""
    p = (prefix or "WKT").strip() or "WKT"
    local = dt.astimezone() if dt.tzinfo else dt.replace(tzinfo=timezone.utc).astimezone()
    base = f"{p}{local.strftime('%Y%m%d')}"
    if monthly_seq > 0:
        return f"{base}{monthly_seq:04d}"
    return f"{base}01"


def _split_product(product_spec: str, material: str) -> tuple[str, str]:
    name = (product_spec or "").strip()
    spec = (material or "").strip()
    return name, spec


def build_line_from_event(event: ShipmentEvent, line) -> WktDeliveryLine:
    name, spec = _split_product(event.product_spec or line.product_spec, line.material or "")
    return WktDeliveryLine(
        order_no=event.order_no or line.order_no or "",
        customer_part_no=event.customer_part_no or line.customer_part_no or "",
        product_name=name,
        spec=spec,
        unit=line.unit or "pcs",
        qty=serialize_qty(event.ship_qty),
        batch_no="",
        box_count="",
        remark="",
    )


def build_draft_document(line, ship_qty) -> WktDeliveryDocument:
    """未出货前：按订单行与拟出货数量生成送货单草稿。"""
    from decimal import Decimal

    now = datetime.now(timezone.utc)
    qty = ship_qty if isinstance(ship_qty, Decimal) else Decimal(str(ship_qty or "0"))
    fake = ShipmentEvent(
        id=0,
        line_id=line.id,
        ship_qty=qty,
        source="open_ship",
        shipped_at=now,
        customer=line.customer or "",
        order_date=line.order_date or "",
        order_no=line.order_no or "",
        product_spec=line.product_spec or "",
        customer_part_no=line.customer_part_no or "",
        po_qty=line.po_qty,
        shipped_qty_after=line.shipped_qty,
        open_qty_after=line.open_qty(),
    )
    return build_document_from_event(fake, line, is_sample=False)


def build_batch_draft_document(items: List[tuple]) -> WktDeliveryDocument:
    """同一客户多条料号合并出货：生成多行送货单草稿。"""
    from decimal import Decimal

    if not items:
        raise ValueError("至少一条出货料号")
    first_line = items[0][0]
    customer = (first_line.customer or "").strip()
    if not customer:
        raise ValueError("客户名称不能为空")
    now = datetime.now(timezone.utc)
    company = load_company_config()
    cust_cfg = get_customer_delivery_info(customer)
    receiver_company = (cust_cfg.get("receiver_company") or "").strip() or customer
    receiver_address = (cust_cfg.get("receiver_address") or "").strip()
    receiver_contact = (cust_cfg.get("receiver_contact") or "").strip()
    prefix = delivery_doc_prefix(customer)

    doc_lines: List[WktDeliveryLine] = []
    total = Decimal("0")
    for line, qty in items:
        ln = line
        if (ln.customer or "").strip() != customer:
            raise ValueError(
                f"合并出货须为同一客户，当前包含「{customer}」与「{ln.customer}」"
            )
        q = qty if isinstance(qty, Decimal) else Decimal(str(qty or "0"))
        if q <= 0:
            raise ValueError("本次出货数量必须大于 0")
        name, spec = _split_product(ln.product_spec or "", ln.material or "")
        doc_lines.append(
            WktDeliveryLine(
                order_no=ln.order_no or "",
                customer_part_no=ln.customer_part_no or "",
                product_name=name,
                spec=spec,
                unit=ln.unit or "pcs",
                qty=serialize_qty(q),
            )
        )
        total += q

    return WktDeliveryDocument(
        title_company=receiver_company,
        doc_no=_gen_doc_no(prefix, now, 0),
        ship_date_cn=_fmt_date_cn(now),
        receiver_company=receiver_company,
        receiver_address=receiver_address,
        receiver_contact=receiver_contact,
        supplier_name=company.get("supplier_name", ""),
        supplier_address=company.get("supplier_address", ""),
        supplier_phone=company.get("supplier_phone", ""),
        lines=doc_lines,
        total_qty=serialize_qty(total),
        footer_note=company.get("footer_note", ""),
        deliverer="",
        warehouse_manager="",
        receiver_sign="",
        is_sample=False,
    )


def apply_document_overrides(doc: WktDeliveryDocument, payload: Optional[dict]) -> WktDeliveryDocument:
    """将用户确认页提交的字段合并到文档。"""
    if not payload or not isinstance(payload, dict):
        return doc
    for key in (
        "title_company",
        "doc_no",
        "ship_date_cn",
        "receiver_company",
        "receiver_address",
        "receiver_contact",
        "supplier_name",
        "supplier_address",
        "supplier_phone",
        "total_qty",
        "footer_note",
        "deliverer",
        "warehouse_manager",
        "receiver_sign",
    ):
        if key in payload and payload[key] is not None:
            setattr(doc, key, str(payload[key]).strip())
    if payload.get("receiver_company"):
        doc.title_company = str(payload["receiver_company"]).strip()
    lines_in = payload.get("lines")
    if isinstance(lines_in, list) and lines_in:
        from decimal import Decimal

        for i, row in enumerate(lines_in):
            if not isinstance(row, dict):
                continue
            if i < len(doc.lines):
                ln = doc.lines[i]
            else:
                ln = WktDeliveryLine()
                doc.lines.append(ln)
            for key in (
                "order_no",
                "customer_part_no",
                "product_name",
                "spec",
                "unit",
                "qty",
                "batch_no",
                "box_count",
                "remark",
            ):
                if key in row and row[key] is not None:
                    setattr(ln, key, str(row[key]).strip())
        if payload.get("total_qty") is not None:
            doc.total_qty = str(payload["total_qty"]).strip()
        else:
            total = Decimal("0")
            for ln in doc.lines:
                try:
                    total += Decimal(str(ln.qty or "0").replace(",", ""))
                except Exception:
                    pass
            if total > 0:
                doc.total_qty = serialize_qty(total)
    return doc


def document_from_dict(data: dict) -> WktDeliveryDocument:
    lines_raw = data.get("lines") or []
    lines: List[WktDeliveryLine] = []
    for item in lines_raw:
        if not isinstance(item, dict):
            continue
        lines.append(
            WktDeliveryLine(
                order_no=str(item.get("order_no", "")),
                customer_part_no=str(item.get("customer_part_no", "")),
                product_name=str(item.get("product_name", "")),
                spec=str(item.get("spec", "")),
                unit=str(item.get("unit", "")),
                qty=str(item.get("qty", "")),
                batch_no=str(item.get("batch_no", "")),
                box_count=str(item.get("box_count", "")),
                remark=str(item.get("remark", "")),
            )
        )
    if not lines:
        lines = [WktDeliveryLine()]
    rc = str(data.get("receiver_company", "") or data.get("title_company", ""))
    return WktDeliveryDocument(
        title_company=rc,
        doc_no=str(data.get("doc_no", "")),
        ship_date_cn=str(data.get("ship_date_cn", "")),
        receiver_company=rc,
        receiver_address=str(data.get("receiver_address", "")),
        receiver_contact=str(data.get("receiver_contact", "")),
        supplier_name=str(data.get("supplier_name", "")),
        supplier_address=str(data.get("supplier_address", "")),
        supplier_phone=str(data.get("supplier_phone", "")),
        lines=lines,
        total_qty=str(data.get("total_qty", lines[0].qty if lines else "")),
        footer_note=str(data.get("footer_note", "")),
        deliverer=str(data.get("deliverer", "")),
        warehouse_manager=str(data.get("warehouse_manager", "")),
        receiver_sign=str(data.get("receiver_sign", "")),
        is_sample=bool(data.get("is_sample")),
    )


def finalize_doc_no(
    doc: WktDeliveryDocument,
    event_id: int,
    shipped_at: datetime,
    monthly_seq: int,
) -> None:
    """出货登记后写入正式送货单号（保留用户手改的单号）。"""
    if event_id <= 0 or monthly_seq <= 0:
        return
    prefix = delivery_doc_prefix(doc.receiver_company)
    auto = _gen_doc_no(prefix, shipped_at, monthly_seq)
    current = (doc.doc_no or "").strip()
    if not current or (current.endswith("01") and event_id > 0):
        doc.doc_no = auto


def build_document_from_event(
    event: ShipmentEvent,
    line,
    *,
    is_sample: bool = False,
    monthly_seq: Optional[int] = None,
) -> WktDeliveryDocument:
    company = load_company_config()
    cust_cfg = get_customer_delivery_info(event.customer or line.customer)
    customer_key = (event.customer or line.customer or "").strip()

    receiver_company = (cust_cfg.get("receiver_company") or "").strip() or customer_key
    receiver_address = (cust_cfg.get("receiver_address") or "").strip()
    receiver_contact = (cust_cfg.get("receiver_contact") or "").strip()
    prefix = delivery_doc_prefix(customer_key)

    shipped_at = event.shipped_at
    if not isinstance(shipped_at, datetime):
        shipped_at = datetime.now(timezone.utc)

    item = build_line_from_event(event, line)
    total = item.qty
    if is_sample:
        seq = 0
    elif monthly_seq is not None and monthly_seq > 0:
        seq = monthly_seq
    else:
        seq = 0

    return WktDeliveryDocument(
        title_company=receiver_company,
        doc_no=_gen_doc_no(prefix, shipped_at, seq),
        ship_date_cn=_fmt_date_cn(shipped_at),
        receiver_company=receiver_company,
        receiver_address=receiver_address,
        receiver_contact=receiver_contact,
        supplier_name=company.get("supplier_name", ""),
        supplier_address=company.get("supplier_address", ""),
        supplier_phone=company.get("supplier_phone", ""),
        lines=[item],
        total_qty=total,
        footer_note=company.get("footer_note", ""),
        deliverer="",
        warehouse_manager="",
        receiver_sign="",
        is_sample=is_sample,
    )


def build_sample_document(customer: str) -> WktDeliveryDocument:
    from decimal import Decimal

    now = datetime.now(timezone.utc)
    fake = ShipmentEvent(
        id=0,
        line_id=0,
        ship_qty=Decimal("100"),
        source="open_ship",
        shipped_at=now,
        customer=customer,
        order_date=now.strftime("%Y-%m-%d"),
        order_no="PO-预览-001",
        product_spec="（示例）双嘴钳",
        customer_part_no="（示例料号）",
        po_qty=Decimal("1000"),
        shipped_qty_after=Decimal("100"),
        open_qty_after=Decimal("900"),
    )

    class _Line:
        material = "（示例材质）"
        unit = "pcs"

    return build_document_from_event(fake, _Line(), is_sample=True)


def document_to_dict(doc: WktDeliveryDocument) -> dict:
    return {
        "title_company": doc.title_company,
        "doc_no": doc.doc_no,
        "ship_date_cn": doc.ship_date_cn,
        "receiver_company": doc.receiver_company,
        "receiver_address": doc.receiver_address,
        "receiver_contact": doc.receiver_contact,
        "supplier_name": doc.supplier_name,
        "supplier_address": doc.supplier_address,
        "supplier_phone": doc.supplier_phone,
        "lines": [
            {
                "order_no": ln.order_no,
                "customer_part_no": ln.customer_part_no,
                "product_name": ln.product_name,
                "spec": ln.spec,
                "unit": ln.unit,
                "qty": ln.qty,
                "batch_no": ln.batch_no,
                "box_count": ln.box_count,
                "remark": ln.remark,
            }
            for ln in doc.lines
        ],
        "total_qty": doc.total_qty,
        "footer_note": doc.footer_note,
        "deliverer": doc.deliverer,
        "warehouse_manager": doc.warehouse_manager,
        "receiver_sign": doc.receiver_sign,
        "is_sample": doc.is_sample,
    }
