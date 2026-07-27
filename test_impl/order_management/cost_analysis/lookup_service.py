"""BOM 录入：按产品料号从 BOM 主数据联想填充。"""
from __future__ import annotations

from typing import List, Optional

from .bom_service import BomService
from .cost_store import CostStore
from .record_service import CostRecordService


class CostLookupService:
    def __init__(
        self,
        line_store=None,
        cost_store: Optional[CostStore] = None,
        record_service: Optional[CostRecordService] = None,
        bom_service: Optional[BomService] = None,
    ) -> None:
        store = cost_store or CostStore()
        records = record_service or CostRecordService(store=store, line_store=line_store)
        self._bom = bom_service or BomService(cost_store=store, record_service=records)

    def suggest_part_numbers(self, q: str = "", limit: int = 20) -> List[dict]:
        return self._bom.suggest_part_numbers(q=q, limit=limit)

    def suggest_customers(self, q: str = "", limit: int = 20) -> List[str]:
        return self._bom.store.search_customers(q=q, limit=limit)

    def lookup_by_part_no(self, product_part_no: str) -> dict:
        return self._bom.lookup_by_part_no_for_entry(product_part_no)
