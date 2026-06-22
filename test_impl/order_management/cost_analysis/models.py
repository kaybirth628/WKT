from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List

# ============================================================
# 原材选项（下拉菜单）。如需增减，在此维护即可。
# ============================================================
RAW_MATERIALS: List[str] = [
    "ADC12",
    "A380",
    "ZN-05",
]

# ============================================================
# 工艺清单（除原材外的所有项）。
# 注意：以下名称由图片识别得到，部分字可能需要核对修正。
# 维护方式：直接增删本列表即可，前端会自动同步。
# ============================================================
PROCESS_LIST: List[str] = [
    "压铸",
    "埋轴",
    "下料",
    "精冲",
    "去毛边",
    "抛光",
    "过砂",
    "打磨",
    "喷砂",
    "补土",
    "抛丸",
    "震研",
    "磁力研磨",
    "钻孔攻牙",
    "车加工",
    "CNC",
    "铆合",
    "皮模钝化",
    "洗白",
    "超声波清洗",
    "电镀",
    "化镍",
    "电泳",
    "烤漆",
    "喷粉",
    "阳极",
    "镭雕",
    "整形",
    "剥漆",
    "包胶",
    "全检",
    "外购磁铁",
    "外购销钉",
    "外购轴套",
    "制程损耗",
    "包装",
    "运输",
    "管销",
    "利润",
]


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


@dataclass
class CostQuote:
    """一张成本报价单：选定原材 + 各工艺单价 -> 生成客户报价。"""

    material_code: str
    material_unit_price: Decimal = Decimal("0")
    material_weight: Decimal = Decimal("0")
    process_prices: Dict[str, Decimal] = field(default_factory=dict)
    quantity: Decimal = Decimal("1")
    markup_rate: Decimal = Decimal("0")

    def validate(self) -> None:
        if self.material_code not in RAW_MATERIALS:
            raise ValueError(f"未知原材: {self.material_code}")
        if self.material_unit_price < 0:
            raise ValueError("原材单价不能为负")
        if self.material_weight < 0:
            raise ValueError("原材重量不能为负")
        if self.quantity <= 0:
            raise ValueError("数量必须大于 0")
        if self.markup_rate < 0:
            raise ValueError("利润率不能为负")
        for name, price in self.process_prices.items():
            if name not in PROCESS_LIST:
                raise ValueError(f"未知工艺: {name}")
            if price < 0:
                raise ValueError(f"工艺单价不能为负: {name}")

    def material_cost(self) -> Decimal:
        return quantize_money(self.material_unit_price * self.material_weight)

    def process_total(self) -> Decimal:
        total = sum(self.process_prices.values(), Decimal("0"))
        return quantize_money(total)

    def unit_cost(self) -> Decimal:
        return quantize_money(self.material_cost() + self.process_total())

    def total_cost(self) -> Decimal:
        return quantize_money(self.unit_cost() * self.quantity)

    def quote_price(self) -> Decimal:
        return quantize_money(self.total_cost() * (Decimal("1") + self.markup_rate))
