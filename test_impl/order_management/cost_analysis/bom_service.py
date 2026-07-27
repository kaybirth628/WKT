"""BOM 主数据：以 cost_records 为料号权威来源，订单引用 BOM。"""
from __future__ import annotations

from typing import List, Optional

from test_impl.order_management.customer_name import customer_names_match

from .cost_store import CostRecordRow, CostStore, normalize_part_no
from .record_service import CostRecordService


def _meaningful_unit_weight(value: str) -> bool:
    raw = str(value or "").strip()
    if not raw:
        return False
    try:
        return float(raw) > 0
    except ValueError:
        return True


class BomNotFoundError(ValueError):
    """料号未在 BOM 中建档。"""


class BomService:
    def __init__(
        self,
        cost_store: Optional[CostStore] = None,
        record_service: Optional[CostRecordService] = None,
    ) -> None:
        self._store = cost_store or CostStore()
        self._records = record_service or CostRecordService(store=self._store)

    @property
    def store(self) -> CostStore:
        return self._store

    def suggest_part_numbers(self, q: str = "", limit: int = 20) -> List[dict]:
        return self._store.search_part_numbers(q=q, limit=limit)

    def get_binding(self, product_part_no: str, *, exclude_record_id: Optional[int] = None) -> Optional[dict]:
        return self._store.get_part_binding(product_part_no, exclude_record_id=exclude_record_id)

    def lookup_part_no_by_product_name(self, product_name: str) -> str:
        row = self._store.find_latest_by_product_name(product_name)
        return str(row.product_part_no or "").strip() if row else ""

    def list_parts_for_master(self) -> List[dict]:
        return self._store.list_master_parts()

    def lookup_for_order(self, customer_part_no: str) -> Optional[dict]:
        """订单录入：按客户料号查 BOM，返回可填充字段。"""
        part_no = normalize_part_no(customer_part_no)
        if not part_no:
            return None
        binding = self.get_binding(part_no)
        if not binding or binding.get("conflict"):
            return None
        row = self._store.find_latest_by_part_no(part_no)
        if row is None:
            return None
        return {
            "customer_part_no": part_no,
            "customer_name": row.customer_name,
            "product_spec": row.product_name,
            "product_name": row.product_name,
            "material": row.material,
            "unit_weight_g": row.unit_weight_g,
        }

    def require_for_order(self, customer_part_no: str, customer: str) -> CostRecordRow:
        part_no = normalize_part_no(customer_part_no)
        cust = (customer or "").strip()
        if not part_no:
            raise ValueError("客户料号不能为空，请填写或在 BOM 录入中维护")
        binding = self.get_binding(part_no)
        if binding is None:
            raise BomNotFoundError(
                f"料号「{part_no}」未在 BOM 中建档，请先在「BOM 录入」中维护"
                f"（产品料号须与订单客户料号完全一致）"
            )
        if binding.get("conflict"):
            joined = "、".join(binding.get("customers") or [])
            raise ValueError(f"料号「{part_no}」在 BOM 中存在多个客户（{joined}），请先修正 BOM 数据")
        owner = str(binding.get("customer_name") or "").strip()
        if owner and cust and not customer_names_match(owner, cust):
            raise ValueError(
                f"料号「{part_no}」BOM 绑定客户为「{owner}」，与订单客户「{cust}」不一致"
            )
        row = self._store.find_latest_by_part_no(part_no)
        if row is None:
            raise BomNotFoundError(
                f"料号「{part_no}」未在 BOM 中建档，请先在「BOM 录入」中维护"
            )
        return row

    def enrich_order_fields(self, fields: dict) -> dict:
        out = dict(fields)
        cpn = str(out.get("customer_part_no") or "").strip()
        spec = str(out.get("product_spec") or "").strip()
        if not cpn and spec:
            cpn = self.lookup_part_no_by_product_name(spec)
            if cpn:
                out["customer_part_no"] = cpn
        if not cpn:
            return out
        info = self.lookup_for_order(cpn)
        if not info:
            return out
        if not spec:
            out["product_spec"] = info.get("product_spec") or info.get("product_name") or ""
        if not str(out.get("material") or "").strip() and info.get("material"):
            out["material"] = info["material"]
        weight = str(info.get("unit_weight_g") or "").strip()
        if not str(out.get("unit_weight_g") or "").strip() and _meaningful_unit_weight(weight):
            out["unit_weight_g"] = weight
        return out

    def lookup_by_part_no_for_entry(self, product_part_no: str) -> dict:
        """BOM 录入页：仅查 BOM 主数据。"""
        part_no = (product_part_no or "").strip()
        if not part_no:
            raise ValueError("产品料号不能为空")

        binding = self.get_binding(part_no)
        if binding and binding.get("conflict"):
            joined = "、".join(binding.get("customers") or [])
            raise ValueError(f"料号「{part_no}」在 BOM 中存在多个客户（{joined}），请先修正 BOM 数据")

        row = self._store.find_latest_by_part_no(part_no)
        if row is None:
            return {
                "found": False,
                "product_part_no": part_no,
                "customer_name": "",
                "suggested": {"product_part_no": part_no},
                "auto_filled": [],
                "from_bom": False,
            }

        cost_dict = self._records.record_to_dict(row)
        suggested: dict = {"product_part_no": part_no}
        for key in (
            "customer_name",
            "product_name",
            "mold_no",
            "cavity",
            "material",
            "machine_tonnage",
            "material_unit_price",
        ):
            value = str(cost_dict.get(key, "") or "").strip()
            if value:
                suggested[key] = value
        weight = str(cost_dict.get("unit_weight_g") or "").strip()
        if _meaningful_unit_weight(weight):
            suggested["unit_weight_g"] = weight
        suggested["process_prices"] = cost_dict.get("process_prices") or {}
        suggested["process_selections"] = cost_dict.get("process_selections") or []

        auto_filled: list[str] = []
        for key in ("customer_name", "product_name", "unit_weight_g", "material"):
            if suggested.get(key):
                auto_filled.append(key)

        return {
            "found": True,
            "product_part_no": part_no,
            "customer_name": suggested.get("customer_name", ""),
            "suggested": suggested,
            "auto_filled": auto_filled,
            "from_bom": True,
            "from_order_line": False,
            "from_cost_record": True,
        }
