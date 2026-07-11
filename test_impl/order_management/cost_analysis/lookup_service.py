"""成本录入：按产品料号从订单/历史成本记录联想填充。"""
from __future__ import annotations

from typing import List, Optional

from test_impl.order_management.order_entry.line_store import LineStore, _meaningful_unit_weight

from .cost_store import CostStore
from .record_service import CostRecordService


class CostLookupService:
    def __init__(
        self,
        line_store: Optional[LineStore] = None,
        cost_store: Optional[CostStore] = None,
        record_service: Optional[CostRecordService] = None,
    ) -> None:
        self._lines = line_store or LineStore()
        self._cost = cost_store or CostStore()
        self._records = record_service or CostRecordService(
            store=self._cost,
            line_store=self._lines,
        )

    def suggest_part_numbers(self, q: str = "", limit: int = 20) -> List[dict]:
        return self._lines.search_part_numbers(q=q, limit=limit)

    def lookup_by_part_no(self, product_part_no: str) -> dict:
        part_no = (product_part_no or "").strip()
        if not part_no:
            raise ValueError("产品料号不能为空")

        order_binding = self._lines.get_part_no_binding(part_no)
        if order_binding and order_binding.get("conflict"):
            joined = "、".join(order_binding.get("customers") or [])
            raise ValueError(f"料号「{part_no}」在订单中存在多个客户（{joined}），请先修正订单数据")

        cost_row = self._cost.find_latest_by_part_no(part_no)
        if cost_row and order_binding:
            owner = order_binding["customer_name"]
            if cost_row.customer_name and cost_row.customer_name != owner:
                raise ValueError(
                    f"料号「{part_no}」已绑定客户「{owner}」，与历史成本记录客户不一致"
                )

        suggested: dict = {"product_part_no": part_no}
        if order_binding:
            suggested.update(
                {
                    "customer_name": order_binding["customer_name"],
                    "product_name": order_binding["product_name"],
                    "material": order_binding["material"],
                }
            )
            weight = str(order_binding.get("unit_weight_g") or "").strip()
            if _meaningful_unit_weight(weight):
                suggested["unit_weight_g"] = weight
        elif cost_row:
            suggested["customer_name"] = cost_row.customer_name

        if cost_row:
            cost_dict = self._records.record_to_dict(cost_row)
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
            cost_weight = str(cost_dict.get("unit_weight_g") or "").strip()
            if _meaningful_unit_weight(cost_weight):
                suggested["unit_weight_g"] = cost_weight
            suggested["process_prices"] = cost_dict.get("process_prices") or {}
            suggested["process_selections"] = cost_dict.get("process_selections") or []

        auto_filled: list[str] = []
        if suggested.get("customer_name"):
            auto_filled.append("customer_name")
        if suggested.get("product_name"):
            auto_filled.append("product_name")
        if suggested.get("unit_weight_g"):
            auto_filled.append("unit_weight_g")
        if suggested.get("material"):
            auto_filled.append("material")

        for key in ("customer_name", "product_name", "unit_weight_g", "material"):
            value = str(suggested.get(key, "") or "").strip()
            if value:
                suggested[key] = value
            else:
                suggested.pop(key, None)

        return {
            "found": bool(order_binding or cost_row),
            "product_part_no": part_no,
            "customer_name": suggested.get("customer_name", ""),
            "suggested": suggested,
            "auto_filled": auto_filled,
            "from_order_line": order_binding is not None,
            "from_cost_record": cost_row is not None,
        }
