from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from test_impl.common.money import round_amount


class OrderStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    PARTIALLY_SHIPPED = "partially_shipped"
    SHIPPED = "shipped"
    RECONCILED = "reconciled"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass
class SalesOrderItem:
    """订单明细行，字段对应上传/录入表头。"""

    item_no: int                                   # 行号
    product_spec: str                              # 品名/规格
    customer_part_no: str = ""                     # 客户料号
    unit_weight_g: Decimal = Decimal("0")          # 单重未含损耗g
    material: str = ""                             # 材质
    po_qty: Decimal = Decimal("0")                 # PO数量
    shipped_qty: Decimal = Decimal("0")            # 已出货数量
    unit: str = ""                                 # 单位
    tax_rate: Decimal = Decimal("0")               # 税率
    rmb_tax_incl_price: Decimal = Decimal("0")     # 人民币含税单价

    def open_qty(self) -> Decimal:
        """未结数量 = PO数量 - 已出货数量。"""
        return self.po_qty - self.shipped_qty

    def validate(self) -> None:
        if not self.product_spec:
            raise ValueError("品名/规格不能为空")
        if self.po_qty <= 0:
            raise ValueError("PO数量必须大于 0")
        if self.shipped_qty < 0 or self.shipped_qty > self.po_qty:
            raise ValueError("已出货数量需在 0 ~ PO数量 之间")
        if self.unit_weight_g < 0:
            raise ValueError("单重不能为负")
        if self.tax_rate < 0 or self.tax_rate > 1:
            raise ValueError("税率需在 0 ~ 1 之间")
        if self.rmb_tax_incl_price < 0:
            raise ValueError("人民币含税单价不能为负")

    def amount(self) -> Decimal:
        """行含税金额 = PO数量 × 人民币含税单价（财务四舍五入，2 位小数）。"""
        self.validate()
        return round_amount(self.po_qty * self.rmb_tax_incl_price)


@dataclass
class SalesOrder:
    order_no: str                                  # 订单号
    customer: str                                  # 客户
    created_by: str                                # 录入人
    order_date: str = ""                           # 接单日期
    delivery_date: str = ""                        # 客户交期
    payment_terms: str = ""                        # 账期
    status: OrderStatus = OrderStatus.DRAFT
    items: List[SalesOrderItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None

    def total_amount(self) -> Decimal:
        if not self.items:
            return Decimal("0.00")
        return round_amount(sum((item.amount() for item in self.items), Decimal("0")))
