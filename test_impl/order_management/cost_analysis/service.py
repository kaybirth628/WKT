from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from .models import PROCESS_LIST, RAW_MATERIALS, CostQuote


class CostAnalysisService:
    """成本分析服务：提供原材/工艺清单，并根据录入生成客户报价。"""

    def get_materials(self) -> List[str]:
        return list(RAW_MATERIALS)

    def get_processes(self) -> List[str]:
        return list(PROCESS_LIST)

    def build_quote(self, payload: dict) -> CostQuote:
        raw_prices = payload.get("process_prices", {}) or {}
        process_prices: Dict[str, Decimal] = {}
        for name, price in raw_prices.items():
            if price in (None, ""):
                continue
            process_prices[str(name)] = Decimal(str(price))

        quote = CostQuote(
            material_code=str(payload["material_code"]),
            material_unit_price=Decimal(str(payload.get("material_unit_price", "0") or "0")),
            material_weight=Decimal(str(payload.get("material_weight", "0") or "0")),
            process_prices=process_prices,
            quantity=Decimal(str(payload.get("quantity", "1") or "1")),
            markup_rate=Decimal(str(payload.get("markup_rate", "0") or "0")),
        )
        quote.validate()
        return quote

    def quote_to_dict(self, quote: CostQuote) -> dict:
        return {
            "material_code": quote.material_code,
            "material_unit_price": str(quote.material_unit_price),
            "material_weight": str(quote.material_weight),
            "material_cost": str(quote.material_cost()),
            "process_prices": {k: str(v) for k, v in quote.process_prices.items()},
            "process_total": str(quote.process_total()),
            "quantity": str(quote.quantity),
            "unit_cost": str(quote.unit_cost()),
            "total_cost": str(quote.total_cost()),
            "markup_rate": str(quote.markup_rate),
            "quote_price": str(quote.quote_price()),
        }
