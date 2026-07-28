from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from decimal import Decimal

from test_impl.common.money import round_qty, serialize_qty, to_decimal

from test_impl.order_management.customer_name import (
    customer_names_match,
    dedupe_customer_names,
    normalize_customer_name,
    pick_canonical_customer_name,
)

from .line_models import CustomerMaster, OrderLine, PartMapping, normalize_line_fields
from .line_store import CLOSURE_FORCED, DuplicatePartNoError, LineStore, default_db_path
from .shipment_models import SHIP_SOURCE_OPEN, ShipmentEvent


class DuplicateLineError(ValueError):
    """同一客户+订单号+品名规格已存在。"""

    def __init__(self, line_id: int, message: str) -> None:
        self.line_id = line_id
        super().__init__(message)


class OrderLineService:
    """料号行录入服务（SQLite 持久化）。"""

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        store: Optional[LineStore] = None,
        bom_service=None,
        inventory_service=None,
    ) -> None:
        from test_impl.order_management.cost_analysis.bom_service import BomService
        from test_impl.order_management.cost_analysis.cost_store import CostStore

        self._store = store or LineStore(db_path)
        self._import_pending: List[dict] = []
        self._bom = bom_service or BomService(
            cost_store=CostStore(self._store.db_path),
        )
        self._inventory = inventory_service

    def set_inventory_service(self, inventory_service) -> None:
        """Flask 启动后注入库存服务，出货时扣成品仓。"""
        self._inventory = inventory_service

    def _check_finished_for_ship(self, line: OrderLine, delta: Decimal) -> None:
        if self._inventory is None:
            return
        part = (line.customer_part_no or "").strip()
        if not part:
            return
        self._inventory.ensure_finished_available(part, delta)

    def _deduct_finished_for_ship(
        self, line: OrderLine, delta: Decimal, *, doc_no: str = ""
    ) -> None:
        if self._inventory is None:
            return
        part = (line.customer_part_no or "").strip()
        if not part:
            return
        self._inventory.ship_finished(
            part,
            delta,
            doc_no=doc_no or (line.order_no or ""),
            note=f"订单出货 {line.order_no}",
        )

    @property
    def db_path(self) -> str:
        return self._store.db_path

    def list_master(self) -> dict:
        return {
            "customers": self._all_customer_names(),
            "parts": self._bom.list_parts_for_master(),
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

    def count_lines_for_customer(self, customer: str) -> int:
        return self._store.count_lines_for_customer(customer)

    def delete_customer_master(self, name: str) -> None:
        self._store.delete_customer_master(name)

    def resolve_customer(self, ocr_name: str) -> Optional[CustomerMaster]:
        """OCR 客户名匹配主数据（精确 → 规范化 → 包含关系）。"""
        name = (ocr_name or "").strip()
        if not name:
            return None
        customers = self._store.list_customers()
        for c in customers:
            if customer_names_match(c.name, name):
                canonical = pick_canonical_customer_name([c.name, name])
                return CustomerMaster(name=canonical)
        lower = name.lower()
        matches: List[CustomerMaster] = []
        for c in customers:
            cl = c.name.lower()
            if cl in lower or lower in cl:
                matches.append(c)
        if matches:
            canonical = pick_canonical_customer_name([m.name for m in matches] + [name])
            return CustomerMaster(name=canonical)
        return None

    def enrich_line_dict(self, row: dict) -> dict:
        out = dict(row)
        ocr_customer = str(out.get("customer") or "").strip()
        cpn = str(out.get("customer_part_no") or "").strip()
        if not cpn and out.get("product_spec"):
            cpn = self.lookup_customer_part(str(out.get("product_spec")))
            if cpn:
                out["customer_part_no"] = cpn

        bom_info = self._bom.lookup_for_order(cpn) if cpn else None
        if bom_info:
            bom_customer = str(bom_info.get("customer_name") or "").strip()
            if not str(out.get("product_spec") or "").strip():
                out["product_spec"] = (
                    bom_info.get("product_spec") or bom_info.get("product_name") or ""
                )
            if not str(out.get("material") or "").strip() and bom_info.get("material"):
                out["material"] = bom_info["material"]
            weight = str(bom_info.get("unit_weight_g") or "").strip()
            if not str(out.get("unit_weight_g") or "").strip() and weight:
                try:
                    if float(weight) > 0:
                        out["unit_weight_g"] = weight
                except ValueError:
                    if weight:
                        out["unit_weight_g"] = weight
            if bom_customer:
                out["_bom_customer_name"] = bom_customer
                if not ocr_customer:
                    out["customer"] = bom_customer
                elif not customer_names_match(ocr_customer, bom_customer):
                    out["_customer_bom_mismatch"] = True
                else:
                    out["customer"] = pick_canonical_customer_name([bom_customer, ocr_customer])
        else:
            out = self._bom.enrich_order_fields(out)

        if not out.get("_customer_bom_mismatch"):
            matched = self.resolve_customer(str(out.get("customer") or ""))
            if matched and (
                not str(out.get("customer") or "").strip()
                or out.get("customer") != matched.name
            ):
                out["customer"] = matched.name
        if not str(out.get("customer_part_no") or "").strip() and out.get("product_spec"):
            out["customer_part_no"] = self.lookup_customer_part(str(out.get("product_spec")))
        return out

    def enrich_recognized_lines(self, lines: List[dict]) -> List[dict]:
        return [self.enrich_line_dict(ln) for ln in lines]

    def add_part(self, product_spec: str, customer_part_no: str) -> dict:
        part = self._store.upsert_part(product_spec, customer_part_no)
        return {"product_spec": part.product_spec, "customer_part_no": part.customer_part_no}

    def _all_customer_names(self) -> List[str]:
        names = {c.name for c in self._store.list_customers()}
        for name in self._store.distinct_customers_from_lines():
            if name:
                names.add(name)
        return dedupe_customer_names(names)

    def lookup_customer_part(self, product_spec: str) -> str:
        return self._bom.lookup_part_no_by_product_name(product_spec) or self._store.lookup_part_no(
            product_spec
        )

    def _validate_part_no_assignment(
        self,
        customer_part_no: str,
        customer: str,
        *,
        exclude_line_id: Optional[int] = None,
    ) -> None:
        part_no = (customer_part_no or "").strip()
        if not part_no:
            return
        self._store.validate_part_no_assignment(
            part_no,
            customer,
            exclude_line_id=exclude_line_id,
        )

    def create_line(self, data: dict) -> OrderLine:
        fields = normalize_line_fields(self.enrich_line_dict(data))
        if data.get("is_demo"):
            fields["is_demo"] = True
        self._ensure_customer(fields["customer"])
        dup = self._store.find_duplicate_line(
            fields["customer"], fields["order_no"], fields["product_spec"]
        )
        if dup is not None:
            raise DuplicateLineError(
                dup.id,
                f"该料号行已存在（客户「{fields['customer']}」· 订单号「{fields['order_no']}」· 品名「{fields['product_spec']}」），请使用「修改」更新原记录",
            )
        cpn = fields.get("customer_part_no", "")
        if str(cpn or "").strip():
            bom_row = self._bom.require_for_order(str(cpn).strip(), fields["customer"])
            if not str(fields.get("product_spec") or "").strip():
                fields["product_spec"] = bom_row.product_name
            if not str(fields.get("material") or "").strip():
                fields["material"] = bom_row.material
            if not str(fields.get("unit_weight_g") or "").strip() and bom_row.unit_weight_g:
                fields["unit_weight_g"] = bom_row.unit_weight_g
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
                except (DuplicatePartNoError, ValueError) as exc:
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
        self._check_finished_for_ship(line, delta)
        prev_shipped = line.shipped_qty
        new_shipped = round_qty(line.shipped_qty + delta)
        updated = self._store.update_shipped_qty(line_id, str(new_shipped))
        updated.validate()
        try:
            self._deduct_finished_for_ship(updated, delta, doc_no=line.order_no or "")
        except Exception:
            self._store.update_shipped_qty(line_id, str(prev_shipped))
            raise
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
            enforce_document_quantities,
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

        for line, delta in parsed:
            self._check_finished_for_ship(line, delta)

        monthly_seq = None
        if delivery_note is not None:
            monthly_seq = self._store.count_shipment_events_in_calendar_month(
                datetime.now(timezone.utc)
            ) + 1

        updated_lines: List[OrderLine] = []
        events: List[ShipmentEvent] = []
        ship_pairs: List[tuple[OrderLine, Decimal]] = []
        for line, delta in parsed:
            prev_shipped = line.shipped_qty
            new_shipped = round_qty(line.shipped_qty + delta)
            updated = self._store.update_shipped_qty(line.id, str(new_shipped))
            updated.validate()
            try:
                self._deduct_finished_for_ship(updated, delta, doc_no=line.order_no or "")
            except Exception:
                self._store.update_shipped_qty(line.id, str(prev_shipped))
                raise
            event = self._store.insert_shipment_event(line.id, str(delta), source=SHIP_SOURCE_OPEN)
            updated_lines.append(updated)
            events.append(event)
            ship_pairs.append((line, delta))

        if delivery_note is not None and events:
            doc = build_batch_draft_document(ship_pairs)
            apply_document_overrides(doc, delivery_note)
            enforce_document_quantities(doc, [delta for _, delta in ship_pairs])
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

    def reverse_shipment_event(self, event_id: int) -> tuple[OrderLine, int]:
        """撤销出货明细：扣减已出货、删除记录，料号回到未结订单。"""
        from decimal import Decimal

        from test_impl.common.money import round_qty, serialize_qty, to_decimal

        event = self.get_shipment_event(event_id)
        line = self.get_line(event.line_id)

        delta = round_qty(to_decimal(event.ship_qty, field="本次出货"))
        if delta <= 0:
            raise ValueError("出货数量无效")

        current = round_qty(line.shipped_qty)
        new_shipped = round_qty(max(Decimal("0"), current - delta))
        updated = self._store.update_shipped_qty(line.id, str(new_shipped))
        updated.validate()
        self._store.delete_shipment_event(event_id)
        return updated, event_id

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
        cpn = fields.get("customer_part_no", "")
        if str(cpn or "").strip():
            bom_row = self._bom.require_for_order(str(cpn).strip(), fields["customer"])
            if not str(fields.get("product_spec") or "").strip():
                fields["product_spec"] = bom_row.product_name
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
