from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from decimal import Decimal

from test_impl.common.money import round_qty, serialize_qty, to_decimal

from .line_models import CustomerMaster, OrderLine, PartMapping, normalize_line_fields
from .line_store import CLOSURE_FORCED, LineStore, default_db_path
from .shipment_models import SHIP_SOURCE_OPEN, ShipmentEvent


class DuplicateLineError(ValueError):
    """同一客户+订单号+品名规格已存在。"""

    def __init__(self, line_id: int, message: str) -> None:
        self.line_id = line_id
        super().__init__(message)


class OrderLineService:
    """料号行录入服务（SQLite 持久化）。"""

    def __init__(self, db_path: Optional[str | Path] = None, store: Optional[LineStore] = None) -> None:
        self._store = store or LineStore(db_path)
        self._import_pending: List[dict] = []

    @property
    def db_path(self) -> str:
        return self._store.db_path

    def _all_customer_names(self) -> List[str]:
        names = {c.name for c in self._store.list_customers()}
        for name in self._store.distinct_customers_from_lines():
            if name:
                names.add(name)
        return sorted(names, key=lambda x: (x.casefold(), x))

    def list_master(self) -> dict:
        return {
            "customers": self._all_customer_names(),
            "parts": [
                {"product_spec": p.product_spec, "customer_part_no": p.customer_part_no}
                for p in self._store.list_parts()
            ],
        }

    def _ensure_customer(self, name: str) -> None:
        n = (name or "").strip()
        if n:
            self.add_customer(n)

    def add_customer(self, name: str) -> CustomerMaster:
        name = (name or "").strip()
        if not name:
            raise ValueError("客户名称不能为空")
        return self._store.upsert_customer(name)

    def resolve_customer(self, ocr_name: str) -> Optional[CustomerMaster]:
        """OCR 客户名匹配主数据（精确 → 忽略大小写 → 包含关系）。"""
        name = (ocr_name or "").strip()
        if not name:
            return None
        customers = self._store.list_customers()
        for c in customers:
            if c.name == name:
                return c
        lower = name.lower()
        for c in customers:
            if c.name.lower() == lower:
                return c
        best: Optional[CustomerMaster] = None
        for c in customers:
            cl = c.name.lower()
            if cl in lower or lower in cl:
                if best is None or len(c.name) > len(best.name):
                    best = c
        return best

    def enrich_line_dict(self, row: dict) -> dict:
        out = dict(row)
        if not str(out.get("customer_part_no") or "").strip() and out.get("product_spec"):
            out["customer_part_no"] = self.lookup_customer_part(str(out.get("product_spec")))
        matched = self.resolve_customer(str(out.get("customer") or ""))
        if matched and (
            not str(out.get("customer") or "").strip() or out.get("customer") != matched.name
        ):
            out["customer"] = matched.name
        return out

    def enrich_recognized_lines(self, lines: List[dict]) -> List[dict]:
        return [self.enrich_line_dict(ln) for ln in lines]

    def add_part(self, product_spec: str, customer_part_no: str) -> dict:
        part = self._store.upsert_part(product_spec, customer_part_no)
        return {"product_spec": part.product_spec, "customer_part_no": part.customer_part_no}

    def lookup_customer_part(self, product_spec: str) -> str:
        return self._store.lookup_part_no(product_spec)

    def create_line(self, data: dict) -> OrderLine:
        fields = normalize_line_fields(self.enrich_line_dict(data))
        self._ensure_customer(fields["customer"])
        dup = self._store.find_duplicate_line(
            fields["customer"], fields["order_no"], fields["product_spec"]
        )
        if dup is not None:
            raise DuplicateLineError(
                dup.id,
                f"该料号行已存在（客户「{fields['customer']}」· 订单号「{fields['order_no']}」· 品名「{fields['product_spec']}」），请使用「修改」更新原记录",
            )
        spec = fields.get("product_spec", "")
        cpn = fields.get("customer_part_no", "")
        if spec and cpn:
            self._store.upsert_part(spec, cpn)
        line = self._store.insert_line(fields)
        line.validate()
        return line

    def stage_pending_import(self, rows: List[dict]) -> int:
        self._import_pending = list(rows)
        return len(self._import_pending)

    def list_pending_import(self) -> List[dict]:
        return list(self._import_pending)

    def clear_pending_import(self) -> None:
        self._import_pending = []

    def bulk_create_lines(self, rows: List[dict]) -> dict:
        from test_impl.integrations.feishu import feishu_notifier

        imported: List[OrderLine] = []
        failed: List[dict] = []
        with feishu_notifier.suppress():
            for idx, data in enumerate(rows, start=1):
                try:
                    imported.append(self.create_line(data))
                except DuplicateLineError as exc:
                    failed.append(
                        {
                            "index": idx,
                            "error": str(exc),
                            "duplicate_id": exc.line_id,
                            "data": data,
                        }
                    )
                except ValueError as exc:
                    failed.append({"index": idx, "error": str(exc), "data": data})
        return {
            "imported": len(imported),
            "line_ids": [ln.id for ln in imported],
            "failed": len(failed),
            "errors": failed,
            "skipped_duplicates": sum(
                1 for e in failed if e.get("duplicate_id") is not None
            ),
        }

    def ship_line(self, line_id: int, ship_qty, delivery_note: Optional[dict] = None):
        """未结订单出货：累加已出货，未结 = PO − 已出货。返回 (更新后的订单行, 出货记录)。"""
        import json

        from test_impl.order_management.delivery_note.wkt_document import (
            apply_document_overrides,
            build_draft_document,
            document_to_dict,
            finalize_doc_no,
        )

        line = self.get_line(line_id)
        delta = round_qty(to_decimal(ship_qty, field="本次出货"))
        if delta <= 0:
            raise ValueError("本次出货数量必须大于 0")
        open_before = line.open_qty()
        if delta > open_before:
            raise ValueError(
                f"本次出货 {serialize_qty(delta)} 不能超过未结数量 {serialize_qty(open_before)}"
            )
        new_shipped = round_qty(line.shipped_qty + delta)
        updated = self._store.update_shipped_qty(line_id, str(new_shipped))
        updated.validate()
        event = self._store.insert_shipment_event(line_id, str(delta), source=SHIP_SOURCE_OPEN)
        if delivery_note is not None:
            doc = build_draft_document(line, delta)
            apply_document_overrides(doc, delivery_note)
            doc.lines[0].qty = serialize_qty(delta)
            doc.total_qty = doc.lines[0].qty
            monthly_seq = self._store.count_shipment_events_in_calendar_month(event.shipped_at)
            finalize_doc_no(doc, event.id, event.shipped_at, monthly_seq)
            snap = json.dumps(document_to_dict(doc), ensure_ascii=False)
            self._store.save_shipment_delivery_note(event.id, snap)
        return updated, event

    def ship_lines_batch(self, items: List[dict], delivery_note: Optional[dict] = None):
        """同一客户多条料号合并出货：共用一张送货单。返回 (更新行列表, 出货记录列表)。"""
        import json

        from test_impl.order_management.delivery_note.wkt_document import (
            apply_document_overrides,
            build_batch_draft_document,
            document_to_dict,
            finalize_doc_no,
        )

        if not items or len(items) < 2:
            raise ValueError("合并出货至少需要两条料号")
        parsed: List[tuple[OrderLine, Decimal]] = []
        customer: Optional[str] = None
        for raw in items:
            if not isinstance(raw, dict):
                raise ValueError("出货项格式无效")
            line_id = int(raw.get("line_id") or 0)
            if line_id <= 0:
                raise ValueError("缺少有效的 line_id")
            line = self.get_line(line_id)
            delta = round_qty(
                to_decimal(
                    raw.get("qty") if raw.get("qty") is not None else raw.get("ship_qty"),
                    field="本次出货",
                )
            )
            if delta <= 0:
                raise ValueError("本次出货数量必须大于 0")
            open_before = line.open_qty()
            if delta > open_before:
                raise ValueError(
                    f"料号 {line.product_spec or line.order_no} 本次出货 {serialize_qty(delta)} "
                    f"不能超过未结数量 {serialize_qty(open_before)}"
                )
            cust = (line.customer or "").strip()
            if not cust:
                raise ValueError("客户名称不能为空")
            if customer is None:
                customer = cust
            elif cust != customer:
                raise ValueError(f"合并出货须为同一客户，当前包含「{customer}」与「{cust}」")
            parsed.append((line, delta))

        monthly_seq = None
        if delivery_note is not None:
            monthly_seq = self._store.count_shipment_events_in_calendar_month(
                datetime.now(timezone.utc)
            ) + 1

        updated_lines: List[OrderLine] = []
        events: List[ShipmentEvent] = []
        ship_pairs: List[tuple[OrderLine, Decimal]] = []
        for line, delta in parsed:
            new_shipped = round_qty(line.shipped_qty + delta)
            updated = self._store.update_shipped_qty(line.id, str(new_shipped))
            updated.validate()
            event = self._store.insert_shipment_event(line.id, str(delta), source=SHIP_SOURCE_OPEN)
            updated_lines.append(updated)
            events.append(event)
            ship_pairs.append((line, delta))

        if delivery_note is not None and events:
            doc = build_batch_draft_document(ship_pairs)
            apply_document_overrides(doc, delivery_note)
            if monthly_seq is not None:
                finalize_doc_no(doc, events[0].id, events[0].shipped_at, monthly_seq)
            snap = json.dumps(document_to_dict(doc), ensure_ascii=False)
            for event in events:
                self._store.save_shipment_delivery_note(event.id, snap)

        return updated_lines, events

    def force_close_line(self, line_id: int) -> OrderLine:
        """未结订单强制结案：不记出货、不纳入对账，归入强制结案列表。"""
        line = self.get_line(line_id)
        if (line.closure_type or "").strip() == CLOSURE_FORCED:
            raise ValueError("该料号已强制结案")
        if line.open_qty() <= 0:
            raise ValueError("未结已为 0，请查看正常结案订单")
        return self._store.set_force_closed(line_id)

    def get_shipment_event(self, event_id: int):
        return self._store.get_shipment_event(event_id)

    def list_shipment_events(self, q: str = "", customer: str = "") -> List[ShipmentEvent]:
        return self._store.list_shipment_events(q=q, customer=customer)

    def get_last_shipment_info_for_lines(self, line_ids: List[int]) -> dict[int, tuple[str, str]]:
        return self._store.get_last_shipment_info_for_lines(line_ids)

    def update_line(self, line_id: int, data: dict) -> OrderLine:
        line = self.get_line(line_id)
        merged = {**self._line_to_dict(line), **data}
        fields = normalize_line_fields(self.enrich_line_dict(merged))
        dup = self._store.find_duplicate_line(
            fields["customer"], fields["order_no"], fields["product_spec"], exclude_id=line_id
        )
        if dup is not None:
            raise DuplicateLineError(
                dup.id,
                f"修改后将与其他行重复（客户·订单号·品名规格相同），请核对",
            )
        self._ensure_customer(fields["customer"])
        spec = fields.get("product_spec", "")
        cpn = fields.get("customer_part_no", "")
        if spec and cpn:
            self._store.upsert_part(spec, cpn)
        updated = self._store.update_line(line_id, fields)
        updated.validate()
        return updated

    def delete_line(self, line_id: int) -> None:
        self._store.delete_line(line_id)

    def get_line(self, line_id: int) -> OrderLine:
        return self._store.get_line(line_id)

    def list_lines(self, q: str = "", customer: str = "", view: str = "all") -> List[OrderLine]:
        return self._store.list_lines(q=q, customer=customer, view=view)

    def count_lines(self) -> int:
        return self._store.count_lines()

    @staticmethod
    def _line_to_dict(line: OrderLine) -> dict:
        return {
            "customer": line.customer,
            "order_date": line.order_date,
            "delivery_date": line.delivery_date,
            "order_no": line.order_no,
            "product_spec": line.product_spec,
            "customer_part_no": line.customer_part_no,
            "unit_weight_g": str(line.unit_weight_g),
            "material": line.material,
            "po_qty": str(line.po_qty),
            "shipped_qty": str(line.shipped_qty),
            "unit": line.unit,
            "tax_rate": str(line.tax_rate),
            "rmb_tax_incl_price": str(line.rmb_tax_incl_price),
            "payment_terms": line.payment_terms,
        }
