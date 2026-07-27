"""测试用：快速写入 BOM 主数据（cost_records）。"""
from __future__ import annotations

import json

from test_impl.order_management.cost_analysis import CostRecordService
from test_impl.order_management.cost_analysis.cost_store import CostStore


def bom_payload(**overrides) -> dict:
    base = {
        "customer_name": "测试客户",
        "product_name": "测试品名",
        "mold_no": "M-TEST-001",
        "product_part_no": "CPN-TEST",
        "cavity": "1*2",
        "unit_weight_g": "100",
        "material": "ADC12",
        "machine_tonnage": "280T",
        "material_unit_price": "0.02",
        "process_prices": {"01": "1.5"},
    }
    base.update(overrides)
    return base


def seed_bom(record_service: CostRecordService, **overrides):
    return record_service.create_record(bom_payload(**overrides))


def seed_bom_conflict(
    cost_store: CostStore,
    product_part_no: str,
    *,
    customers: list[tuple[str, str]],
) -> None:
    """同一料号写入多条 BOM（绕过录入校验，用于冲突场景测试）。"""
    part_no = (product_part_no or "").strip()
    for customer_name, product_name in customers:
        cost_store.insert(
            {
                "customer_name": customer_name,
                "product_name": product_name,
                "mold_no": "M-TEST-001",
                "product_part_no": part_no,
                "cavity": "1*2",
                "unit_weight_g": "88",
                "material": "ADC12",
                "machine_tonnage": "280T",
                "material_unit_price": "0.02",
                "process_prices_json": json.dumps({"01": "1.0"}, ensure_ascii=False),
                "material_cost": "1.76",
                "process_total": "1.0",
                "unit_cost": "2.76",
                "quote_price": "0",
            }
        )
