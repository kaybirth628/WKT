"""排产对照：未结订单行 × 成品/半成品库存 → 缺口。"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from test_impl.common.money import round_qty, to_decimal
from test_impl.order_management.order_entry.line_service import OrderLineService

from .service import InventoryService
from .store import PROCESS_FINISHED, STATUS_FINISHED, STATUS_INHOUSE, STATUS_OUTSOURCE


class PlanningService:
    STOCK_WARN_OK = "ok"
    STOCK_WARN_NO_PART = "no_part"
    STOCK_WARN_SHORT_SHIP = "short_ship"
    STOCK_WARN_SHORT_COVER = "short_cover"

    def __init__(
        self,
        line_service: OrderLineService,
        inventory: InventoryService,
    ) -> None:
        self._lines = line_service
        self._inv = inventory

    @staticmethod
    def stock_warn_level(part: str, gap_ship: Decimal, gap_cover: Decimal) -> str:
        if not (part or "").strip():
            return PlanningService.STOCK_WARN_NO_PART
        if gap_ship > 0:
            return PlanningService.STOCK_WARN_SHORT_SHIP
        if gap_cover > 0:
            return PlanningService.STOCK_WARN_SHORT_COVER
        return PlanningService.STOCK_WARN_OK

    def stock_by_part(self, product_part_no: str) -> dict:
        part = (product_part_no or "").strip()
        finished = Decimal("0")
        inhouse = Decimal("0")
        outsource = Decimal("0")
        stages: list[dict] = []
        if not part:
            return self._empty_stock("")
        for row in self._inv.list_balances(product_part_no=part):
            qty = to_decimal(row["qty"])
            if row["status"] == STATUS_FINISHED or row["process_code"] == PROCESS_FINISHED:
                finished += qty
            elif row["status"] == STATUS_OUTSOURCE:
                outsource += qty
                stages.append(
                    {
                        "process_code": row["process_code"],
                        "process_name": row.get("process_name") or row["process_code"],
                        "status": "outsource",
                        "status_label": "在途",
                        "supplier_name": row.get("supplier_name") or "",
                        "qty": row["qty"],
                    }
                )
            elif row["status"] == STATUS_INHOUSE:
                inhouse += qty
                stages.append(
                    {
                        "process_code": row["process_code"],
                        "process_name": row.get("process_name") or row["process_code"],
                        "status": "inhouse",
                        "status_label": "场内",
                        "supplier_name": "",
                        "qty": row["qty"],
                    }
                )
        semi = inhouse + outsource
        return {
            "product_part_no": part,
            "finished_qty": str(round_qty(finished)),
            "inhouse_qty": str(round_qty(inhouse)),
            "outsource_qty": str(round_qty(outsource)),
            "semifinished_qty": str(round_qty(semi)),
            "stages": stages,
        }

    @staticmethod
    def _empty_stock(part: str) -> dict:
        return {
            "product_part_no": part,
            "finished_qty": "0",
            "inhouse_qty": "0",
            "outsource_qty": "0",
            "semifinished_qty": "0",
            "stages": [],
        }

    def compare_open_lines(self, *, customer: str = "", q: str = "") -> List[dict]:
        """未结订单：一行一条，附库存与缺口（库存按料号共用，未按单预留）。"""
        lines = self._lines.list_lines(q=q, customer=customer, view="open")
        cache: dict[str, dict] = {}
        rows = []
        for line in lines:
            part = (line.customer_part_no or "").strip()
            if part not in cache:
                cache[part] = self.stock_by_part(part) if part else self._empty_stock("")
            stock = cache[part]
            demand = round_qty(line.open_qty())
            finished = to_decimal(stock["finished_qty"])
            semi = to_decimal(stock["semifinished_qty"])
            gap_ship = round_qty(max(Decimal("0"), demand - finished))
            gap_cover = round_qty(max(Decimal("0"), demand - finished - semi))
            warn = self.stock_warn_level(part, gap_ship, gap_cover)
            rows.append(
                {
                    "line_id": line.id,
                    "customer": line.customer,
                    "order_no": line.order_no,
                    "order_date": line.order_date,
                    "delivery_date": line.delivery_date,
                    "product_spec": line.product_spec,
                    "customer_part_no": part,
                    "po_qty": str(round_qty(line.po_qty)),
                    "shipped_qty": str(round_qty(line.shipped_qty)),
                    "open_qty": str(demand),
                    "finished_qty": stock["finished_qty"],
                    "inhouse_qty": stock["inhouse_qty"],
                    "outsource_qty": stock["outsource_qty"],
                    "semifinished_qty": stock["semifinished_qty"],
                    "gap_ship": str(gap_ship),
                    "gap_cover": str(gap_cover),
                    "suggest_qty": str(gap_cover),
                    "stock_warn_level": warn,
                    "stages": stock["stages"],
                }
            )
        return rows

    def seed_planning_demo(self, cost_record_service) -> dict:
        """写入 A/B/C 三料号 BOM + 未结订单各 1000 + 库存 500/600/700。"""
        from unittest.mock import patch

        from test_impl.order_management.inventory.store import (
            PROCESS_FINISHED,
            STATUS_FINISHED,
            STATUS_INHOUSE,
            STATUS_OUTSOURCE,
        )

        supplier = "苏州麦凯良金属制品厂"
        specs = [
            ("PLAN-A", "演示料号A", "200", "250", "50", "500"),
            ("PLAN-B", "演示料号B", "400", "150", "50", "600"),
            ("PLAN-C", "演示料号C", "500", "150", "50", "700"),
        ]
        # finished + inhouse + outsource = total SF+FG
        created_lines = []
        with patch(
            "test_impl.order_management.cost_analysis.record_service.list_profile_suppliers",
            return_value=[supplier],
        ):
            for part, name, fin, ih, os_qty, _total in specs:
                try:
                    self._inv.get_route(part)
                except ValueError:
                    cost_record_service.create_record(
                        {
                            "customer_name": "演示客户",
                            "product_name": name,
                            "mold_no": f"M-{part}",
                            "product_part_no": part,
                            "cavity": "1*1",
                            "unit_weight_g": "100",
                            "material": "ADC12",
                            "machine_tonnage": "280T",
                            "material_unit_price": "0",
                            "process_prices": {
                                "01": "0",
                                "02": {"price": "0", "supplier": supplier},
                                "28": {"price": "0", "supplier": "场内自制"},
                                "34": {"price": "0", "supplier": "场内自制"},
                            },
                        }
                    )
                # 清空该料号旧余额（演示覆盖）
                for row in list(self._inv.store.list_balances(product_part_no=part)):
                    self._inv.store.apply_delta(
                        product_part_no=part,
                        process_code=row["process_code"],
                        status=row["status"],
                        supplier_name=row.get("supplier_name") or "",
                        delta=-to_decimal(row["qty"]),
                        now=__import__("datetime").datetime.now(
                            __import__("datetime").timezone.utc
                        ).isoformat(),
                    )
                self._inv.store._conn.commit()
                self._inv.inject_balances(
                    part,
                    [
                        {
                            "process_code": PROCESS_FINISHED,
                            "status": STATUS_FINISHED,
                            "qty": fin,
                        },
                        {"process_code": "28", "status": STATUS_INHOUSE, "qty": ih},
                        {
                            "process_code": "02",
                            "status": STATUS_OUTSOURCE,
                            "supplier_name": supplier,
                            "qty": os_qty,
                        },
                    ],
                    note=f"排产演示库存 {part}",
                )
                # 若已有同订单号演示行则跳过新建
                existing = [
                    ln
                    for ln in self._lines.list_lines(view="open")
                    if ln.customer_part_no == part and ln.order_no.startswith("PO-PLAN-")
                ]
                if existing:
                    created_lines.append(existing[0].id)
                    continue
                line = self._lines.create_line(
                    {
                        "customer": "演示客户",
                        "order_date": "2026-07-20",
                        "delivery_date": "2026-08-20",
                        "order_no": f"PO-PLAN-{part}",
                        "product_spec": name,
                        "customer_part_no": part,
                        "po_qty": "1000",
                        "shipped_qty": "0",
                        "unit": "PCS",
                    }
                )
                created_lines.append(line.id)

        rows = self.compare_open_lines(customer="演示客户")
        demo_rows = [r for r in rows if r["customer_part_no"] in ("PLAN-A", "PLAN-B", "PLAN-C")]
        return {"ok": True, "line_ids": created_lines, "items": demo_rows}
