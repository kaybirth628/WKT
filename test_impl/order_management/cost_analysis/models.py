from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple

# ============================================================
# 原材选项（下拉菜单）。如需增减，在此维护即可。
# ============================================================
RAW_MATERIALS: List[str] = [
    "ADC12",
    "A380",
    "ZN-05",
]

# ============================================================
# 工艺目录：两位编号 + 显示名称。
# 压铸类（压铸/埋轴/下料/精冲）合并为 01 压铸，录入与查询只显示一项。
# ============================================================
PROCESS_CATALOG: List[Tuple[str, str]] = [
    ("01", "压铸"),
    ("02", "去毛边"),
    ("03", "抛光"),
    ("04", "过砂"),
    ("05", "打磨"),
    ("06", "喷砂"),
    ("07", "补土"),
    ("08", "抛丸"),
    ("09", "震研"),
    ("10", "磁力研磨"),
    ("11", "钻孔攻牙"),
    ("12", "车加工"),
    ("13", "CNC"),
    ("14", "铆合"),
    ("15", "皮模钝化"),
    ("16", "洗白"),
    ("17", "超声波清洗"),
    ("18", "电镀"),
    ("19", "化镍"),
    ("20", "电泳"),
    ("21", "烤漆"),
    ("22", "喷粉"),
    ("23", "阳极"),
    ("24", "镭雕"),
    ("25", "整形"),
    ("26", "剥漆"),
    ("27", "包胶"),
    ("28", "全检"),
    ("29", "外购磁铁"),
    ("30", "外购销钉"),
    ("31", "外购轴套"),
    ("32", "制程损耗"),
    ("33", "包装"),
    ("34", "运输"),
    ("35", "管销"),
    ("36", "利润"),
]

# 已并入 01 压铸的旧工艺名（兼容历史数据）
LEGACY_PROCESS_ALIASES: Dict[str, str] = {
    "埋轴": "01",
    "下料": "01",
    "精冲": "01",
}

PROCESS_LIST: List[str] = [name for _, name in PROCESS_CATALOG]
PROCESS_BY_CODE: Dict[str, str] = {code: name for code, name in PROCESS_CATALOG}
PROCESS_CODE_BY_NAME: Dict[str, str] = {name: code for code, name in PROCESS_CATALOG}


@dataclass
class ProcessOption:
    code: str
    name: str

    def to_dict(self) -> dict:
        return {"code": self.code, "name": self.name}


def list_process_options() -> List[ProcessOption]:
    return [ProcessOption(code, name) for code, name in PROCESS_CATALOG]


def resolve_process_key(key: str) -> Tuple[str, str]:
    """将工艺编号或名称解析为 (code, name)。"""
    raw = str(key).strip()
    if not raw:
        raise ValueError("工艺不能为空")
    if raw in PROCESS_BY_CODE:
        return raw, PROCESS_BY_CODE[raw]
    if raw in PROCESS_CODE_BY_NAME:
        return PROCESS_CODE_BY_NAME[raw], raw
    if raw in LEGACY_PROCESS_ALIASES:
        code = LEGACY_PROCESS_ALIASES[raw]
        return code, PROCESS_BY_CODE[code]
    raise ValueError(f"未知工艺: {key}")


def process_prices_to_names(prices: Dict[str, str]) -> Dict[str, str]:
    """编号键 -> 名称键（报价计算用）。"""
    out: Dict[str, str] = {}
    for key, price in prices.items():
        code, name = resolve_process_key(key)
        out[name] = price
    return out


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

    def validate(self, *, strict_material: bool = True) -> None:
        if strict_material and self.material_code not in RAW_MATERIALS:
            raise ValueError(f"未知原材: {self.material_code}")
        if not (self.material_code or "").strip():
            raise ValueError("材质不能为空")
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
