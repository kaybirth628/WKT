"""成本录入记录业务逻辑。"""
from __future__ import annotations

import json
from typing import List, Optional

from test_impl.order_management.order_entry.line_store import LineStore

from .cost_store import CostRecordRow, CostStore
from .models import process_prices_to_names, resolve_process_key
from .service import CostAnalysisService


_REQUIRED_BASIC = (
    "customer_name",
    "product_name",
    "mold_no",
    "product_part_no",
    "cavity",
    "unit_weight_g",
    "material",
    "machine_tonnage",
)


class CostRecordService:
    def __init__(
        self,
        store: Optional[CostStore] = None,
        quote_service: Optional[CostAnalysisService] = None,
        line_store: Optional[LineStore] = None,
    ) -> None:
        self._store = store or CostStore()
        self._quote = quote_service or CostAnalysisService()
        self._lines = line_store or LineStore()

    @property
    def db_path(self) -> str:
        return self._store.db_path

    def create_record(self, payload: dict) -> CostRecordRow:
        basic = self._validate_basic(payload)
        self._validate_part_no_customer(basic["product_part_no"], basic["customer_name"])
        process_prices = self._normalize_process_prices(payload.get("process_prices") or {})
        if not process_prices:
            raise ValueError("请至少选择一道工序")

        material_unit_price = str(payload.get("material_unit_price", "0") or "0")
        named_prices = process_prices_to_names(process_prices)
        quote = self._quote.build_quote(
            {
                "material_code": basic["material"],
                "material_unit_price": material_unit_price,
                "material_weight": basic["unit_weight_g"],
                "process_prices": named_prices,
                "quantity": "1",
                "markup_rate": "0",
            },
            strict_material=False,
        )

        return self._store.insert(self._build_store_payload(basic, material_unit_price, process_prices, quote))

    def update_record(self, record_id: int, payload: dict) -> CostRecordRow:
        self.get_record(record_id)
        basic = self._validate_basic(payload)
        self._validate_part_no_customer(basic["product_part_no"], basic["customer_name"])
        process_prices = self._normalize_process_prices(payload.get("process_prices") or {})
        if not process_prices:
            raise ValueError("请至少选择一道工序")

        material_unit_price = str(payload.get("material_unit_price", "0") or "0")
        named_prices = process_prices_to_names(process_prices)
        quote = self._quote.build_quote(
            {
                "material_code": basic["material"],
                "material_unit_price": material_unit_price,
                "material_weight": basic["unit_weight_g"],
                "process_prices": named_prices,
                "quantity": "1",
                "markup_rate": "0",
            },
            strict_material=False,
        )
        return self._store.update(
            record_id,
            self._build_store_payload(basic, material_unit_price, process_prices, quote),
        )

    def delete_record(self, record_id: int) -> None:
        self._store.delete(record_id)

    def _build_store_payload(self, basic: dict, material_unit_price: str, process_prices: dict, quote) -> dict:
        return {
            **basic,
            "material_unit_price": material_unit_price,
            "process_prices_json": json.dumps(process_prices, ensure_ascii=False),
            "material_cost": str(quote.material_cost()),
            "process_total": str(quote.process_total()),
            "unit_cost": str(quote.unit_cost()),
            "quote_price": str(quote.quote_price()),
        }

    def list_records(
        self,
        *,
        q: str = "",
        customer: str = "",
        product_part_no: str = "",
    ) -> List[CostRecordRow]:
        return self._store.list_records(
            q=q,
            customer=customer,
            product_part_no=product_part_no,
        )

    def get_record(self, record_id: int) -> CostRecordRow:
        return self._store.get(record_id)

    def record_to_dict(self, record: CostRecordRow) -> dict:
        selections = self._build_process_selections(record.process_prices)
        return {
            "id": record.id,
            "customer_name": record.customer_name,
            "product_name": record.product_name,
            "mold_no": record.mold_no,
            "product_part_no": record.product_part_no,
            "cavity": record.cavity,
            "unit_weight_g": record.unit_weight_g,
            "material": record.material,
            "machine_tonnage": record.machine_tonnage,
            "material_unit_price": record.material_unit_price,
            "process_prices": {s["code"]: s["price"] for s in selections},
            "process_selections": selections,
            "selected_processes": [s["name"] for s in selections],
            "selected_process_codes": [s["code"] for s in selections],
            "material_cost": record.material_cost,
            "process_total": record.process_total,
            "unit_cost": record.unit_cost,
            "quote_price": record.quote_price,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

    def _build_process_selections(self, raw_prices: dict) -> list:
        selections = []
        for key, price in raw_prices.items():
            code, name = resolve_process_key(key)
            selections.append({"code": code, "name": name, "price": str(price)})
        selections.sort(key=lambda item: item["code"])
        return selections

    def _validate_basic(self, payload: dict) -> dict:
        out: dict = {}
        for key in _REQUIRED_BASIC:
            value = str(payload.get(key, "") or "").strip()
            if not value:
                label = {
                    "customer_name": "客户名称",
                    "product_name": "产品名称",
                    "mold_no": "模具编号",
                    "product_part_no": "产品料号",
                    "cavity": "模穴",
                    "unit_weight_g": "产品单重",
                    "material": "材质",
                    "machine_tonnage": "机台吨位",
                }[key]
                raise ValueError(f"{label}不能为空")
            out[key] = value
        return out

    def _validate_part_no_customer(self, product_part_no: str, customer_name: str) -> None:
        part_no = (product_part_no or "").strip()
        customer = (customer_name or "").strip()
        if not part_no:
            return
        binding = self._lines.get_part_no_binding(part_no)
        if binding and binding.get("conflict"):
            joined = "、".join(binding.get("customers") or [])
            raise ValueError(f"料号「{part_no}」在订单中存在多个客户（{joined}），请先修正订单数据")
        if binding and binding.get("customer_name") and binding["customer_name"] != customer:
            raise ValueError(
                f"料号「{part_no}」已绑定客户「{binding['customer_name']}」，与所选客户不一致"
            )

    def _normalize_process_prices(self, raw: dict) -> dict:
        out: dict = {}
        for name, price in raw.items():
            key = str(name).strip()
            if not key:
                continue
            try:
                code, _ = resolve_process_key(key)
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
            if price in (None, ""):
                out[code] = "0"
            else:
                out[code] = str(price)
        return out
