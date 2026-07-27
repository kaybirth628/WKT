from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import List

from test_impl.common.money import round_price, round_qty, round_weight, serialize_weight, to_decimal


@dataclass
class CustomerMaster:
    """客户主数据（仅名称，用于下拉与 OCR 名称归一）。"""

    name: str


@dataclass
class PartMapping:
    """品名规格 ↔ 客户料号（全局一对一，可扩展）。"""

    product_spec: str
    customer_part_no: str


@dataclass
class OrderLine:
    """一个料号 = 一条订单行记录（字段对齐附件2）。"""

    id: int
    customer: str                    # 客户
    order_date: str                  # 接单日期
    delivery_date: str               # 客户交期
    order_no: str                    # 订单号
    product_spec: str                # 品名规格
    customer_part_no: str            # 客户料号
    unit_weight_g: str               # 单重（不含损耗）g；可为数字或备注如「外购件」
    material: str                    # 材质
    po_qty: Decimal                  # PO数量
    shipped_qty: Decimal             # 已出货
    unit: str                        # 单位
    tax_rate: Decimal                # 税率 0~1
    rmb_tax_incl_price: Decimal      # 人民币单价（含税）
    payment_terms: str               # 账期
    closure_type: str = ""            # 结案方式：空=未强制；forced=强制结案
    is_demo: bool = False             # 测试数据标注（测）
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def open_qty(self) -> Decimal:
        """未结数量 = PO数量 − 已出货（1 位小数）。"""
        return round_qty(self.po_qty - self.shipped_qty)

    def amount(self) -> Decimal:
        """行含税金额（展示用）= PO数量 × 人民币含税单价。"""
        from test_impl.common.money import round_amount
        return round_amount(self.po_qty * self.rmb_tax_incl_price)

    def validate(self) -> None:
        if not self.customer:
            raise ValueError("客户不能为空")
        if not self.order_no:
            raise ValueError("订单号不能为空")
        if not self.product_spec:
            raise ValueError("品名规格不能为空")
        if self.po_qty <= 0:
            raise ValueError("PO数量必须大于 0")
        if self.shipped_qty < 0 or self.shipped_qty > self.po_qty:
            raise ValueError("已出货数量需在 0 ~ PO数量 之间")
        try:
            if to_decimal(self.unit_weight_g) < 0:
                raise ValueError("单重不能为负")
        except ValueError:
            pass  # 非数字备注（如外购件）允许保留原文
        if self.tax_rate < 0 or self.tax_rate > 1:
            raise ValueError("税率需在 0 ~ 1 之间")
        if self.rmb_tax_incl_price < 0:
            raise ValueError("人民币含税单价不能为负")


def _normalize_unit_weight_g(value) -> str:
    """数字则规范化；文字备注（如「外购件」）原样保留。"""
    s = str(value or "").strip()
    if not s:
        return "0"
    try:
        d = to_decimal(s.replace(",", ""))
        if d < 0:
            raise ValueError("单重不能为负")
        return serialize_weight(d)
    except (ValueError, InvalidOperation):
        return s[:80]


def _normalize_tax_rate(value) -> Decimal:
    if value is None or str(value).strip() == "":
        return Decimal("0")
    s = str(value).strip()
    has_pct = "%" in s
    try:
        num = to_decimal(s.replace("%", ""), field="税率")
    except ValueError:
        raise ValueError(f"税率不是有效数字：{value!r}") from None
    if has_pct or num > 1:
        num = num / Decimal("100")
    return num


def normalize_line_fields(data: dict) -> dict:
    """把请求字段规范化为 OrderLine 构造参数。"""
    return {
        "customer": str(data.get("customer", "")).strip(),
        "order_date": str(data.get("order_date", "")).strip(),
        "delivery_date": str(data.get("delivery_date", "")).strip(),
        "order_no": str(data.get("order_no", "")).strip(),
        "product_spec": str(data.get("product_spec", "")).strip(),
        "customer_part_no": str(data.get("customer_part_no", "")).strip(),
        "unit_weight_g": _normalize_unit_weight_g(data.get("unit_weight_g", "0")),
        "material": str(data.get("material", "")).strip(),
        "po_qty": round_qty(to_decimal(data.get("po_qty"), field="PO数量")),
        "shipped_qty": round_qty(to_decimal(data.get("shipped_qty", "0"), field="已出货")),
        "unit": str(data.get("unit", "")).strip(),
        "tax_rate": _normalize_tax_rate(data.get("tax_rate")),
        "rmb_tax_incl_price": round_price(
            to_decimal(data.get("rmb_tax_incl_price", "0"), field="人民币单价（含税）")
        ),
        "payment_terms": str(data.get("payment_terms", "")).strip(),
    }
