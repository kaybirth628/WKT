"""出货明细：单次出货记录（来自未结订单出货或历史导入）。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

SHIP_SOURCE_OPEN = "open_ship"
SHIP_SOURCE_IMPORT = "import"

SOURCE_LABELS = {
    SHIP_SOURCE_OPEN: "未结出货",
    SHIP_SOURCE_IMPORT: "历史导入",
}


@dataclass
class ShipmentEvent:
    id: int
    line_id: int
    ship_qty: Decimal
    source: str
    shipped_at: datetime
    customer: str = ""
    order_date: str = ""
    order_no: str = ""
    product_spec: str = ""
    customer_part_no: str = ""
    po_qty: Decimal = Decimal("0")
    shipped_qty_after: Decimal = Decimal("0")
    open_qty_after: Decimal = Decimal("0")
    delivery_note_json: str = ""

    @property
    def source_label(self) -> str:
        return SOURCE_LABELS.get(self.source, self.source)
