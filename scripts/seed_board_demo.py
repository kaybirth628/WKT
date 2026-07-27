"""一次性：向本地库写入 10 料号看板演示数据。"""
from __future__ import annotations

from test_impl.order_management.cost_analysis import CostRecordService
from test_impl.order_management.inventory import InventoryService
from test_impl.order_management.order_entry.line_service import OrderLineService


def main() -> None:
    lines = OrderLineService()
    records = CostRecordService(line_store=lines._store)
    inv = InventoryService(
        cost_store=records._store,
        record_service=records,
    )
    result = inv.seed_board_demo(records, limit=10)
    print("count", result["count"])
    print("created_bom", result["created_bom"])
    print("parts", result["product_part_nos"])
    for row in result["items"]:
        stages = ", ".join(
            f"{s['process_code']}场内{s['inhouse_qty']}/外发{s['outsource_qty']}"
            for s in row["stages"]
        )
        print(row["product_part_no"], "成品", row["finished_qty"], "|", stages)


if __name__ == "__main__":
    main()
