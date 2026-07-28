"""库存业务：按 BOM 工序路线管理半成品/成品。

规则（CL-0163 统一入库/出库）：
- **入库**：首道 +本道场内；非首道 -本道在途 +本道场内；末道 -本道在途 +成品
- **出库**：-上道场内 +下道在途（外发下道带供应商）；成品出库 -成品
- 库内状态码 `outsource` 页面展示为「在途」
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from test_impl.common.money import round_qty, to_decimal
from test_impl.order_management.cost_analysis import CostRecordService
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.cost_analysis.models import (
    PROCESS_BY_CODE,
    is_inhouse_process,
    is_inhouse_supplier,
)

from .store import (
    PROCESS_FINISHED,
    STATUS_FINISHED,
    STATUS_INHOUSE,
    STATUS_OUTSOURCE,
    STATUS_REPAIR,
    InventoryStore,
)

ACTION_INBOUND = "inbound"
ACTION_OUTBOUND = "outbound"
ACTION_SKIP_OUTBOUND = "skip_outbound"
ACTION_REPAIR_OUT = "repair_out"
ACTION_REPAIR_IN = "repair_in"
ACTION_COMPLETE = "complete"
ACTION_OUT_SEND = "outsource_send"
ACTION_OUT_RECV = "outsource_receive"
ACTION_SHIP = "ship_finished"
ACTION_ADJUST = "balance_adjust"

ACTION_LABELS = {
    ACTION_INBOUND: "入库",
    ACTION_OUTBOUND: "出库",
    ACTION_SKIP_OUTBOUND: "跳序出库",
    ACTION_REPAIR_OUT: "返修",
    ACTION_REPAIR_IN: "返修入库",
    ACTION_COMPLETE: "入库",
    ACTION_OUT_SEND: "出库",
    ACTION_OUT_RECV: "入库",
    ACTION_SHIP: "出库",
    ACTION_ADJUST: "库存校正",
}

# 进出单号前缀：动作-YYYYMMDD-当日序号
DOC_PREFIX = {
    ACTION_INBOUND: "RK",
    ACTION_OUTBOUND: "CK",
    ACTION_SKIP_OUTBOUND: "TK",
    ACTION_REPAIR_OUT: "FX",
    ACTION_REPAIR_IN: "FR",
    ACTION_COMPLETE: "RK",
    ACTION_OUT_SEND: "CK",
    ACTION_OUT_RECV: "RK",
    ACTION_SHIP: "CK",
    ACTION_ADJUST: "TZ",
}


class InventoryService:
    def __init__(
        self,
        store: Optional[InventoryStore] = None,
        cost_store: Optional[CostStore] = None,
        record_service: Optional[CostRecordService] = None,
    ) -> None:
        self._store = store or InventoryStore()
        self._cost = cost_store or CostStore(self._store.db_path)
        self._records = record_service or CostRecordService(store=self._cost)

    @property
    def store(self) -> InventoryStore:
        return self._store

    def _resolve_doc_no(self, action_type: str, doc_no: str = "") -> str:
        manual = (doc_no or "").strip()
        if manual:
            return manual
        prefix = DOC_PREFIX.get(action_type)
        if not prefix:
            return ""
        return self._store.next_movement_doc_no(prefix)

    @staticmethod
    def _normalize_doc_no_display(doc_no: str) -> str:
        """历史单号前缀 WG/FC/CP 在界面统一显示为 RK/CK。"""
        raw = (doc_no or "").strip()
        if not raw:
            return raw
        parts = raw.split("-", 2)
        if len(parts) < 2:
            return raw
        legacy = {"WG": "RK", "FC": "CK", "CP": "CK"}
        head = parts[0].upper()
        if head in legacy:
            parts[0] = legacy[head]
            return "-".join(parts)
        return raw

    def get_route(self, product_part_no: str) -> List[dict]:
        part = (product_part_no or "").strip()
        if not part:
            raise ValueError("产品料号不能为空")
        row = self._cost.find_latest_by_part_no(part)
        if row is None:
            raise ValueError(f"料号「{part}」未在 BOM 中建档，请先 BOM 录入")
        data = self._records.record_to_dict(row)
        selections = data.get("process_selections") or []
        if not selections:
            raise ValueError(f"料号「{part}」BOM 未勾选工序")
        out = []
        for item in selections:
            code = str(item.get("code") or "").strip()
            supplier = str(item.get("supplier") or "").strip()
            inhouse = (
                bool(item.get("inhouse"))
                or is_inhouse_process(code)
                or is_inhouse_supplier(supplier)
            )
            out.append(
                {
                    "code": code,
                    "name": str(item.get("name") or PROCESS_BY_CODE.get(code, code)),
                    "supplier": supplier,
                    "inhouse": inhouse,
                    "is_outsource": not inhouse,
                }
            )
        return out

    def list_balances(self, *, product_part_no: str = "") -> List[dict]:
        return [self._enrich_balance(r) for r in self._store.list_balances(product_part_no=product_part_no)]

    def list_movements(
        self, *, product_part_no: str = "", on_date: str = "", limit: int = 200, customer_name: str = ""
    ) -> List[dict]:
        bom_cache: dict[str, tuple[str, str]] = {}
        items = [
            self._enrich_movement(r, bom_cache=bom_cache)
            for r in self._store.list_movements(
                product_part_no=product_part_no, on_date=on_date, limit=limit
            )
        ]
        cust_q = (customer_name or "").strip()
        if cust_q:
            items = [r for r in items if self._customer_matches(r.get("customer_name", ""), cust_q)]
        return items

    def board(self, *, product_part_no: str = "", customer_name: str = "") -> List[dict]:
        """按料号汇总：成品 + 各工序场内/外发；可按客户名称模糊筛选。"""
        route_cache: dict[str, List[dict]] = {}
        balances = self.list_balances(product_part_no=product_part_no)
        parts = sorted({b["product_part_no"] for b in balances})
        if product_part_no.strip() and product_part_no.strip() not in parts:
            # 仍返回空路线看板，方便查询无库存料号
            try:
                route = self.get_route(product_part_no.strip())
                row = self._empty_board_row(product_part_no.strip(), route)
                if self._customer_matches(row.get("customer_name", ""), customer_name):
                    return [row]
                return []
            except ValueError:
                return []

        result = []
        for part in parts:
            try:
                route = route_cache.setdefault(part, self.get_route(part))
            except ValueError:
                route = []
            row = self._empty_board_row(part, route)
            for b in balances:
                if b["product_part_no"] != part:
                    continue
                qty = to_decimal(b["qty"])
                if b["status"] == STATUS_FINISHED:
                    row["finished_qty"] = str(round_qty(to_decimal(row["finished_qty"]) + qty))
                    continue
                if b["status"] == STATUS_REPAIR and b["process_code"] == PROCESS_FINISHED:
                    row["finished_repair_qty"] = str(
                        round_qty(to_decimal(row.get("finished_repair_qty", "0")) + qty)
                    )
                    continue
                for stage in row["stages"]:
                    if stage["process_code"] != b["process_code"]:
                        continue
                    if b["status"] == STATUS_INHOUSE:
                        stage["inhouse_qty"] = str(round_qty(to_decimal(stage["inhouse_qty"]) + qty))
                    elif b["status"] == STATUS_OUTSOURCE:
                        stage["outsource_qty"] = str(
                            round_qty(to_decimal(stage["outsource_qty"]) + qty)
                        )
                        if b["supplier_name"]:
                            stage["suppliers"].append(
                                {"supplier_name": b["supplier_name"], "qty": b["qty"]}
                            )
                    elif b["status"] == STATUS_REPAIR:
                        stage["repair_qty"] = str(
                            round_qty(to_decimal(stage.get("repair_qty", "0")) + qty)
                        )
            result.append(row)
        cust_q = (customer_name or "").strip()
        if cust_q:
            result = [r for r in result if self._customer_matches(r.get("customer_name", ""), cust_q)]
        return result

    def inbound(
        self,
        product_part_no: str,
        process_code: str,
        qty,
        *,
        supplier_name: str = "",
        doc_no: str = "",
        note: str = "",
    ) -> dict:
        """入库：首道加场内；非首道在途→场内；末道在途→成品。"""
        part = product_part_no.strip()
        code = process_code.strip()
        amount = round_qty(qty)
        route = self.get_route(part)
        step = self._find(route, code)
        idx = route.index(step)
        is_first = idx == 0
        is_last = idx == len(route) - 1
        supplier = (supplier_name or "").strip()

        if is_first:
            return self._store.record_movement(
                product_part_no=part,
                action_type=ACTION_INBOUND,
                qty=amount,
                process_code=code,
                to_process_code=code,
                to_status=STATUS_INHOUSE,
                doc_no=self._resolve_doc_no(ACTION_INBOUND, doc_no),
                note=note or f"入库 {step['name']}",
                deltas=[(code, STATUS_INHOUSE, "", amount)],
            )

        if is_last:
            have = self._store.get_qty(part, code, STATUS_OUTSOURCE, "")
            if have < amount:
                raise ValueError(
                    f"「{code} {step['name']}」在途仅有 {round_qty(have)}，无法入库 {amount}"
                )
            return self._store.record_movement(
                product_part_no=part,
                action_type=ACTION_INBOUND,
                qty=amount,
                process_code=code,
                from_process_code=code,
                from_status=STATUS_OUTSOURCE,
                to_process_code=PROCESS_FINISHED,
                to_status=STATUS_FINISHED,
                doc_no=self._resolve_doc_no(ACTION_INBOUND, doc_no),
                note=note or "入库成品",
                deltas=[
                    (code, STATUS_OUTSOURCE, "", -amount),
                    (PROCESS_FINISHED, STATUS_FINISHED, "", amount),
                ],
            )

        if step["is_outsource"]:
            if not supplier:
                supplier = step.get("supplier") or ""
            if not supplier:
                raise ValueError("外发工序入库须选择供应商")
            have = self._store.get_qty(part, code, STATUS_OUTSOURCE, supplier)
            transit_supplier = supplier
        else:
            have = self._store.get_qty(part, code, STATUS_OUTSOURCE, "")
            transit_supplier = ""
        if have < amount:
            raise ValueError(
                f"「{code} {step['name']}」在途仅有 {round_qty(have)}，无法入库 {amount}"
            )
        return self._store.record_movement(
            product_part_no=part,
            action_type=ACTION_INBOUND,
            qty=amount,
            process_code=code,
            from_process_code=code,
            from_status=STATUS_OUTSOURCE,
            from_supplier=transit_supplier if step["is_outsource"] else "",
            to_process_code=code,
            to_status=STATUS_INHOUSE,
            doc_no=self._resolve_doc_no(ACTION_INBOUND, doc_no),
            note=note or f"入库 {step['name']}",
            deltas=[
                (code, STATUS_OUTSOURCE, transit_supplier, -amount),
                (code, STATUS_INHOUSE, "", amount),
            ],
        )

    def outbound(
        self,
        product_part_no: str,
        from_process_code: str,
        to_process_code: str,
        qty,
        *,
        supplier_name: str = "",
        doc_no: str = "",
        note: str = "",
    ) -> dict:
        """出库：上道场内→下道在途；from=FIN 且无 to 时为成品出库。"""
        part = product_part_no.strip()
        from_code = from_process_code.strip()
        to_code = (to_process_code or "").strip()
        amount = round_qty(qty)
        if from_code == PROCESS_FINISHED and not to_code:
            return self.ship_finished(part, amount, doc_no=doc_no, note=note)

        route = self.get_route(part)
        from_step = self._find(route, from_code)
        to_step = self._find(route, to_code)
        from_idx = route.index(from_step)
        to_idx = route.index(to_step)
        if to_idx != from_idx + 1:
            raise ValueError("出库须按工艺顺序：从一道工序发往下道相邻工序")

        have = self._store.get_qty(part, from_code, STATUS_INHOUSE, "")
        if have < amount:
            raise ValueError(
                f"「{from_code} {from_step['name']}」场内仅有 {round_qty(have)}，无法出库 {amount}"
            )

        supplier = (supplier_name or "").strip()
        if to_step["is_outsource"]:
            if not supplier:
                supplier = to_step.get("supplier") or ""
            if not supplier:
                raise ValueError("发往外发工序须选择供应商")
        to_supplier = supplier if to_step["is_outsource"] else ""

        return self._store.record_movement(
            product_part_no=part,
            action_type=ACTION_OUTBOUND,
            qty=amount,
            process_code=to_code,
            from_process_code=from_code,
            from_status=STATUS_INHOUSE,
            to_process_code=to_code,
            to_status=STATUS_OUTSOURCE,
            to_supplier=to_supplier,
            doc_no=self._resolve_doc_no(ACTION_OUTBOUND, doc_no),
            note=note or f"出库 {from_code}→{to_code}",
            deltas=[
                (from_code, STATUS_INHOUSE, "", -amount),
                (to_code, STATUS_OUTSOURCE, to_supplier, amount),
            ],
        )

    def skip_outbound(
        self,
        product_part_no: str,
        from_process_code: str,
        to_process_code: str,
        qty,
        *,
        supplier_name: str = "",
        doc_no: str = "",
        note: str = "",
    ) -> dict:
        """跳序出库：任意工序场内 → 任意工序在途（可跨道、可逆向，不记欠账表）。"""
        part = product_part_no.strip()
        from_code = from_process_code.strip()
        to_code = to_process_code.strip()
        amount = round_qty(qty)
        if not from_code or not to_code:
            raise ValueError("跳序出库须选择从工序与到工序")
        if from_code == to_code:
            raise ValueError("跳序出库的起止工序不能相同")
        if from_code == PROCESS_FINISHED:
            raise ValueError("成品请使用「出库 → 成品（出库给客户）」")
        if to_code == PROCESS_FINISHED:
            raise ValueError("跳序目标须为某道工序在途，成品请先末道入库")

        route = self.get_route(part)
        from_step = self._find(route, from_code)
        to_step = self._find(route, to_code)

        have = self._store.get_qty(part, from_code, STATUS_INHOUSE, "")
        if have < amount:
            raise ValueError(
                f"「{from_code} {from_step['name']}」场内仅有 {round_qty(have)}，无法跳序出库 {amount}"
            )

        supplier = (supplier_name or "").strip()
        if to_step["is_outsource"]:
            if not supplier:
                supplier = to_step.get("supplier") or ""
            if not supplier:
                raise ValueError("发往外发工序须选择供应商")
        to_supplier = supplier if to_step["is_outsource"] else ""

        note_text = (note or "").strip() or f"跳序 {from_code}→{to_code}"
        return self._store.record_movement(
            product_part_no=part,
            action_type=ACTION_SKIP_OUTBOUND,
            qty=amount,
            process_code=to_code,
            from_process_code=from_code,
            from_status=STATUS_INHOUSE,
            to_process_code=to_code,
            to_status=STATUS_OUTSOURCE,
            to_supplier=to_supplier,
            doc_no=self._resolve_doc_no(ACTION_SKIP_OUTBOUND, doc_no),
            note=note_text,
            deltas=[
                (from_code, STATUS_INHOUSE, "", -amount),
                (to_code, STATUS_OUTSOURCE, to_supplier, amount),
            ],
        )

    def complete(
        self,
        product_part_no: str,
        process_code: str,
        qty,
        *,
        doc_no: str = "",
        note: str = "",
    ) -> dict:
        """兼容旧 API：等价于 outbound+inbound（中间道）或 inbound（首/末道）。"""
        part = product_part_no.strip()
        code = process_code.strip()
        route = self.get_route(part)
        step = self._find(route, code)
        idx = route.index(step)
        if idx == 0 or idx == len(route) - 1:
            return self.inbound(part, code, qty, doc_no=doc_no, note=note)
        prev = route[idx - 1]
        self.outbound(part, prev["code"], code, qty, doc_no=doc_no, note=note)
        return self.inbound(part, code, qty, doc_no=doc_no, note=note)

    def outsource_send(
        self,
        product_part_no: str,
        process_code: str,
        supplier_name: str,
        qty,
        *,
        doc_no: str = "",
        note: str = "",
    ) -> dict:
        """兼容旧 API：等价于 outbound(上道→本道)。"""
        part = product_part_no.strip()
        code = process_code.strip()
        route = self.get_route(part)
        step = self._find(route, code)
        idx = route.index(step)
        if idx == 0:
            raise ValueError("首道工序不能外发出库，请先入库")
        prev = route[idx - 1]
        return self.outbound(
            part,
            prev["code"],
            code,
            qty,
            supplier_name=supplier_name,
            doc_no=doc_no,
            note=note,
        )

    def outsource_receive(
        self,
        product_part_no: str,
        process_code: str,
        supplier_name: str,
        qty,
        *,
        doc_no: str = "",
        note: str = "",
    ) -> dict:
        """兼容旧 API：等价于 inbound(本道)。"""
        return self.inbound(
            product_part_no,
            process_code,
            qty,
            supplier_name=supplier_name,
            doc_no=doc_no,
            note=note,
        )

    def ship_finished(
        self,
        product_part_no: str,
        qty,
        *,
        doc_no: str = "",
        note: str = "",
    ) -> dict:
        part = product_part_no.strip()
        amount = round_qty(qty)
        self.get_route(part)  # 校验 BOM 存在
        have = self.finished_qty(part)
        if have < amount:
            raise ValueError(
                f"成品库存不足：{part} 成品仓仅有 {round_qty(have)}，无法出库 {round_qty(amount)}"
            )
        return self._store.record_movement(
            product_part_no=part,
            action_type=ACTION_OUTBOUND,
            qty=amount,
            process_code=PROCESS_FINISHED,
            from_process_code=PROCESS_FINISHED,
            from_status=STATUS_FINISHED,
            to_process_code="",
            to_status="",
            doc_no=self._resolve_doc_no(ACTION_OUTBOUND, doc_no),
            note=note or "成品出库",
            deltas=[(PROCESS_FINISHED, STATUS_FINISHED, "", -amount)],
        )

    def adjust_balance(
        self,
        product_part_no: str,
        *,
        target_qty,
        process_code: str = "",
        status: str = "",
        supplier_name: str = "",
        note: str = "",
    ) -> dict:
        """按目标数量校正库存（差额记流水）。用于期初/盘点发现余额本身有误。"""
        part = product_part_no.strip()
        if not part:
            raise ValueError("产品料号不能为空")
        self.get_route(part)
        st = (status or "").strip()
        code = (process_code or "").strip()
        supplier = (supplier_name or "").strip()
        if st == STATUS_FINISHED:
            code = PROCESS_FINISHED
        elif not code or not st:
            raise ValueError("须指定工序与库存状态")
        if st == STATUS_OUTSOURCE and not supplier:
            raise ValueError("在途校正须选择供应商")
        target = round_qty(target_qty)
        if target < 0:
            raise ValueError("目标数量不能为负")
        current = self._store.get_qty(part, code, st, supplier)
        delta = round_qty(target - current)
        if delta == 0:
            raise ValueError(f"当前已是 {round_qty(current)}，无需校正")
        amount = abs(delta)
        label = f"{current}→{target}"
        base_note = f"库存校正 {label}"
        full_note = f"{base_note}；{note}" if note else base_note
        if delta > 0:
            return self._store.record_movement(
                product_part_no=part,
                action_type=ACTION_ADJUST,
                qty=amount,
                process_code=code,
                to_process_code=code,
                to_status=st,
                to_supplier=supplier if st == STATUS_OUTSOURCE else "",
                doc_no=self._resolve_doc_no(ACTION_ADJUST),
                note=full_note,
                deltas=[(code, st, supplier if st == STATUS_OUTSOURCE else "", delta)],
            )
        return self._store.record_movement(
            product_part_no=part,
            action_type=ACTION_ADJUST,
            qty=amount,
            process_code=code,
            from_process_code=code,
            from_status=st,
            from_supplier=supplier if st == STATUS_OUTSOURCE else "",
            doc_no=self._resolve_doc_no(ACTION_ADJUST),
            note=full_note,
            deltas=[(code, st, supplier if st == STATUS_OUTSOURCE else "", delta)],
        )

    def repair_out(
        self,
        product_part_no: str,
        qty,
        *,
        process_code: str = "",
        note: str = "",
        doc_no: str = "",
    ) -> dict:
        """返修：半成品场内或成品 → 返修在途（同工序/成品桶）。"""
        part = product_part_no.strip()
        code = (process_code or "").strip()
        amount = round_qty(qty)
        if amount <= 0:
            raise ValueError("返修数量必须大于 0")
        route = self.get_route(part)
        if code == PROCESS_FINISHED:
            have = self.finished_qty(part)
            if have < amount:
                raise ValueError(
                    f"成品库存不足：仅有 {round_qty(have)}，无法返修 {amount}"
                )
            label = "成品"
            return self._store.record_movement(
                product_part_no=part,
                action_type=ACTION_REPAIR_OUT,
                qty=amount,
                process_code=PROCESS_FINISHED,
                from_process_code=PROCESS_FINISHED,
                from_status=STATUS_FINISHED,
                to_process_code=PROCESS_FINISHED,
                to_status=STATUS_REPAIR,
                doc_no=self._resolve_doc_no(ACTION_REPAIR_OUT, doc_no),
                note=note or f"返修 {label}",
                deltas=[
                    (PROCESS_FINISHED, STATUS_FINISHED, "", -amount),
                    (PROCESS_FINISHED, STATUS_REPAIR, "", amount),
                ],
            )
        if not code:
            raise ValueError("返修须指定工序或成品")
        step = self._find(route, code)
        have = self._store.get_qty(part, code, STATUS_INHOUSE, "")
        if have < amount:
            raise ValueError(
                f"「{code} {step['name']}」场内仅有 {round_qty(have)}，无法返修 {amount}"
            )
        return self._store.record_movement(
            product_part_no=part,
            action_type=ACTION_REPAIR_OUT,
            qty=amount,
            process_code=code,
            from_process_code=code,
            from_status=STATUS_INHOUSE,
            to_process_code=code,
            to_status=STATUS_REPAIR,
            doc_no=self._resolve_doc_no(ACTION_REPAIR_OUT, doc_no),
            note=note or f"返修 {code} {step['name']}",
            deltas=[
                (code, STATUS_INHOUSE, "", -amount),
                (code, STATUS_REPAIR, "", amount),
            ],
        )

    def repair_in(
        self,
        product_part_no: str,
        qty,
        *,
        process_code: str = "",
        note: str = "",
        doc_no: str = "",
    ) -> dict:
        """返修入库：返修在途 → 恢复场内或成品库存。"""
        part = product_part_no.strip()
        code = (process_code or "").strip()
        amount = round_qty(qty)
        if amount <= 0:
            raise ValueError("返修入库数量必须大于 0")
        route = self.get_route(part)
        if code == PROCESS_FINISHED:
            have = self._store.get_qty(part, PROCESS_FINISHED, STATUS_REPAIR, "")
            if have < amount:
                raise ValueError(
                    f"成品返修在途仅有 {round_qty(have)}，无法返修入库 {amount}"
                )
            return self._store.record_movement(
                product_part_no=part,
                action_type=ACTION_REPAIR_IN,
                qty=amount,
                process_code=PROCESS_FINISHED,
                from_process_code=PROCESS_FINISHED,
                from_status=STATUS_REPAIR,
                to_process_code=PROCESS_FINISHED,
                to_status=STATUS_FINISHED,
                doc_no=self._resolve_doc_no(ACTION_REPAIR_IN, doc_no),
                note=note or "返修入库 成品",
                deltas=[
                    (PROCESS_FINISHED, STATUS_REPAIR, "", -amount),
                    (PROCESS_FINISHED, STATUS_FINISHED, "", amount),
                ],
            )
        if not code:
            raise ValueError("返修入库须指定工序或成品")
        step = self._find(route, code)
        have = self._store.get_qty(part, code, STATUS_REPAIR, "")
        if have < amount:
            raise ValueError(
                f"「{code} {step['name']}」返修在途仅有 {round_qty(have)}，无法返修入库 {amount}"
            )
        return self._store.record_movement(
            product_part_no=part,
            action_type=ACTION_REPAIR_IN,
            qty=amount,
            process_code=code,
            from_process_code=code,
            from_status=STATUS_REPAIR,
            to_process_code=code,
            to_status=STATUS_INHOUSE,
            doc_no=self._resolve_doc_no(ACTION_REPAIR_IN, doc_no),
            note=note or f"返修入库 {code} {step['name']}",
            deltas=[
                (code, STATUS_REPAIR, "", -amount),
                (code, STATUS_INHOUSE, "", amount),
            ],
        )

    def finished_qty(self, product_part_no: str) -> Decimal:
        part = (product_part_no or "").strip()
        if not part:
            return Decimal("0")
        return self._store.get_qty(part, PROCESS_FINISHED, STATUS_FINISHED)

    def ensure_finished_available(self, product_part_no: str, qty) -> None:
        """出货前校验：须有 BOM，且成品仓数量足够。"""
        part = (product_part_no or "").strip()
        if not part:
            raise ValueError("产品料号不能为空")
        amount = round_qty(qty)
        if amount <= 0:
            raise ValueError("数量必须大于 0")
        self.get_route(part)
        have = self.finished_qty(part)
        if have < amount:
            raise ValueError(
                f"成品库存不足：{part} 成品仓仅有 {round_qty(have)}，无法出货 {round_qty(amount)}"
            )

    def create_replenish(
        self,
        *,
        product_part_no: str,
        qty,
        sales_order_no: str = "",
        line_id: Optional[int] = None,
        note: str = "",
    ) -> dict:
        part = (product_part_no or "").strip()
        if not part:
            raise ValueError("产品料号不能为空")
        amount = round_qty(qty)
        if amount <= 0:
            raise ValueError("补产数量必须大于 0")
        self.get_route(part)
        doc_no = self._store.next_replenish_doc_no()
        return self._store.insert_replenish(
            doc_no=doc_no,
            product_part_no=part,
            qty=str(amount),
            sales_order_no=sales_order_no,
            line_id=line_id,
            note=note,
        )

    def list_replenish(self, *, limit: int = 100, status: str = "") -> List[dict]:
        rows = self._store.list_replenish(limit=limit, status=status)
        return [
            {
                **r,
                "qty": str(round_qty(r.get("qty"))),
                "line_id": r.get("line_id"),
            }
            for r in rows
        ]

    def inject_balances(self, product_part_no: str, buckets: list[dict], *, note: str = "演示注入") -> None:
        """测试/演示：直接写入余额（不校验扣减路径）。buckets: process_code,status,supplier_name,qty"""
        from datetime import datetime, timezone

        part = product_part_no.strip()
        now = datetime.now(timezone.utc).isoformat()
        amount_total = Decimal("0")
        for b in buckets:
            qty = round_qty(b.get("qty") or "0")
            if qty <= 0:
                continue
            amount_total += qty
            self._store.apply_delta(
                product_part_no=part,
                process_code=str(b.get("process_code") or PROCESS_FINISHED),
                status=str(b.get("status") or STATUS_FINISHED),
                supplier_name=str(b.get("supplier_name") or ""),
                delta=qty,
                now=now,
            )
        self._store._conn.commit()
        if amount_total > 0:
            self._store._conn.execute(
                """
                INSERT INTO inventory_movements (
                    product_part_no, action_type, process_code,
                    from_process_code, from_status, from_supplier,
                    to_process_code, to_status, to_supplier,
                    qty, doc_no, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    part,
                    "demo_inject",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    str(round_qty(amount_total)),
                    "DEMO-INJ",
                    note,
                    now,
                ),
            )
            self._store._conn.commit()

    def seed_demo_flow(self, product_part_no: str) -> dict:
        """演示：首道入库→出库外发→外发入库→逐道出库/入库→末道入成品→成品出库。"""
        part = product_part_no.strip()
        route = self.get_route(part)
        if len(route) < 2:
            raise ValueError("演示数据需要至少 2 道工序的 BOM 路线")
        first = route[0]
        outsource = next((s for s in route if s["is_outsource"]), None)
        if outsource is None:
            raise ValueError("演示数据需要至少一道外发工序（带供应商）")
        supplier = outsource["supplier"] or "演示供应商"
        out_idx = route.index(outsource)

        self.inbound(part, first["code"], "500", doc_no="DEMO-RK-01", note=f"演示：{first['name']}入库")
        self.outbound(
            part,
            first["code"],
            outsource["code"],
            "200",
            supplier_name=supplier,
            doc_no="DEMO-CK-01",
            note=f"演示：出库至{outsource['name']}",
        )
        self.inbound(
            part,
            outsource["code"],
            "200",
            supplier_name=supplier,
            doc_no="DEMO-RK-02",
            note=f"演示：{outsource['name']}入库",
        )
        prev = outsource
        for step in route[out_idx + 1 :]:
            self.outbound(
                part,
                prev["code"],
                step["code"],
                "200",
                doc_no=f"DEMO-CK-{step['code']}",
                note=f"演示：出库 {prev['code']}→{step['code']}",
            )
            self.inbound(
                part,
                step["code"],
                "200",
                doc_no=f"DEMO-RK-{step['code']}",
                note=f"演示：{step['name']}入库",
            )
            prev = step
        self.ship_finished(part, "50", doc_no="DEMO-CK-SHIP", note="演示：成品出库")
        self._store.set_part_demo(part, True)
        return {
            "product_part_no": part,
            "board": self.board(product_part_no=part),
            "movements": self.list_movements(product_part_no=part, limit=20),
        }

    def _clear_balances(self, product_part_no: str) -> None:
        from datetime import datetime, timezone

        part = product_part_no.strip()
        now = datetime.now(timezone.utc).isoformat()
        for row in list(self._store.list_balances(product_part_no=part)):
            qty = to_decimal(row["qty"])
            if qty == 0:
                continue
            self._store.apply_delta(
                product_part_no=part,
                process_code=row["process_code"],
                status=row["status"],
                supplier_name=row.get("supplier_name") or "",
                delta=-qty,
                now=now,
            )
        self._store._conn.commit()

    @staticmethod
    def _board_demo_route(index: int) -> dict:
        """按序号轮换几套工艺（含外发与场内）。"""
        supplier = "苏州麦凯良金属制品厂"
        variants = [
            {
                "01": "0",
                "02": {"price": "0", "supplier": supplier},
                "28": {"price": "0", "supplier": "场内自制"},
                "34": {"price": "0", "supplier": "场内自制"},
            },
            {
                "01": "0",
                "13": {"price": "0", "supplier": supplier},
                "18": {"price": "0", "supplier": supplier},
                "28": {"price": "0", "supplier": "场内自制"},
                "34": {"price": "0", "supplier": "场内自制"},
            },
            {
                "01": "0",
                "02": {"price": "0", "supplier": supplier},
                "11": {"price": "0", "supplier": supplier},
                "28": {"price": "0", "supplier": "场内自制"},
                "34": {"price": "0", "supplier": "场内自制"},
            },
            {
                "01": "0",
                "06": {"price": "0", "supplier": supplier},
                "12": {"price": "0", "supplier": supplier},
                "28": {"price": "0", "supplier": "场内自制"},
                "34": {"price": "0", "supplier": "场内自制"},
            },
            {
                "01": "0",
                "05": {"price": "0", "supplier": supplier},
                "24": {"price": "0", "supplier": supplier},
                "28": {"price": "0", "supplier": "场内自制"},
                "34": {"price": "0", "supplier": "场内自制"},
            },
        ]
        return variants[index % len(variants)]

    def _pick_parts_from_orders(self, limit: int = 10) -> list[dict]:
        rows = self._store._conn.execute(
            """
            SELECT customer_part_no, product_spec, customer
            FROM order_lines
            WHERE TRIM(IFNULL(customer_part_no, '')) != ''
            ORDER BY id DESC
            """
        ).fetchall()
        seen: set[str] = set()
        out: list[dict] = []
        for raw_part, spec, customer in rows:
            part = "".join(ch for ch in str(raw_part or "") if ch >= " ").strip()
            if not part or part in seen or len(part) > 48:
                continue
            name = " ".join(str(spec or "").replace("\n", " ").replace("\r", " ").split()) or f"演示品-{part}"
            if len(name) > 40:
                name = name[:40]
            cust = str(customer or "").strip() or "演示库存客户"
            seen.add(part)
            out.append(
                {
                    "product_part_no": part,
                    "product_name": name,
                    "customer_name": cust,
                }
            )
            if len(out) >= limit:
                break
        return out

    def seed_board_demo(
        self,
        cost_record_service: CostRecordService,
        *,
        parts: Optional[list[dict]] = None,
        limit: int = 10,
    ) -> dict:
        """写入多料号 BOM（若不存在）+ 各工序场内/外发/成品库存，供总览看板演示。"""
        from unittest.mock import patch

        supplier = "苏州麦凯良金属制品厂"
        selected = list(parts) if parts else self._pick_parts_from_orders(limit)
        while len(selected) < limit:
            i = len(selected) + 1
            selected.append(
                {
                    "product_part_no": f"BOARD-DEMO-{i:02d}",
                    "product_name": f"看板演示品{i}",
                    "customer_name": "演示库存客户",
                }
            )
        selected = selected[:limit]

        created = []
        with patch(
            "test_impl.order_management.cost_analysis.record_service.list_profile_suppliers",
            return_value=[supplier],
        ):
            for idx, item in enumerate(selected):
                part = str(item.get("product_part_no") or "").strip()
                if not part:
                    continue
                try:
                    self.get_route(part)
                except ValueError:
                    cost_record_service.create_record(
                        {
                            "customer_name": str(item.get("customer_name") or "演示库存客户"),
                            "product_name": str(item.get("product_name") or f"演示品-{part}"),
                            "mold_no": f"M-{part}"[:32],
                            "product_part_no": part,
                            "cavity": "1*1",
                            "unit_weight_g": str(80 + idx * 7),
                            "material": "ADC12",
                            "machine_tonnage": "280T",
                            "material_unit_price": "0",
                            "process_prices": self._board_demo_route(idx),
                        }
                    )
                    created.append(part)

                self._clear_balances(part)
                route = self.get_route(part)
                buckets = [
                    {
                        "process_code": PROCESS_FINISHED,
                        "status": STATUS_FINISHED,
                        "qty": str(80 + idx * 35),
                    }
                ]
                for stage_i, step in enumerate(route):
                    buckets.append(
                        {
                            "process_code": step["code"],
                            "status": STATUS_INHOUSE,
                            "qty": str(120 + idx * 15 + stage_i * 25),
                        }
                    )
                    if step["is_outsource"]:
                        buckets.append(
                            {
                                "process_code": step["code"],
                                "status": STATUS_OUTSOURCE,
                                "supplier_name": step["supplier"] or supplier,
                                "qty": str(40 + idx * 8 + stage_i * 10),
                            }
                        )
                self.inject_balances(part, buckets, note=f"看板演示库存 {part}")
                self._store.set_part_demo(part, True)

        board = self.board()
        demo_parts = {str(p.get("product_part_no") or "").strip() for p in selected}
        items = [r for r in board if r["product_part_no"] in demo_parts]
        return {
            "ok": True,
            "count": len(selected),
            "created_bom": created,
            "product_part_nos": [str(p.get("product_part_no") or "").strip() for p in selected],
            "items": items,
        }

    def _find(self, route: List[dict], process_code: str) -> dict:
        code = process_code.strip()
        for step in route:
            if step["code"] == code:
                return step
        raise ValueError(f"工序「{code}」不在该料号 BOM 路线中")

    def _empty_board_row(self, part: str, route: List[dict], *, product_name: str = "") -> dict:
        demo = self._store.is_part_demo(part)
        name = (product_name or "").strip()
        customer = ""
        bom = self._cost.find_latest_by_part_no(part)
        if bom:
            if not name:
                name = str(bom.product_name or "").strip()
            customer = str(bom.customer_name or "").strip()
        return {
            "product_part_no": part,
            "product_name": name,
            "customer_name": customer,
            "is_demo": demo,
            "data_tag": "测" if demo else "实",
            "finished_qty": "0",
            "finished_repair_qty": "0",
            "stages": [
                {
                    "process_code": s["code"],
                    "process_name": s["name"],
                    "is_outsource": s["is_outsource"],
                    "inhouse_qty": "0",
                    "outsource_qty": "0",
                    "repair_qty": "0",
                    "suppliers": [],
                }
                for s in route
            ],
        }

    @staticmethod
    def _customer_matches(record_customer: str, query: str) -> bool:
        q = (query or "").strip().lower()
        if not q:
            return True
        return q in (record_customer or "").strip().lower()

    def _enrich_balance(self, row: dict) -> dict:
        code = str(row.get("process_code") or "")
        status = str(row.get("status") or "")
        return {
            **row,
            "process_name": (
                "成品"
                if code == PROCESS_FINISHED
                else PROCESS_BY_CODE.get(code, code)
            ),
            "status_label": {
                STATUS_INHOUSE: "场内",
                STATUS_OUTSOURCE: "在途",
                STATUS_FINISHED: "成品",
                STATUS_REPAIR: "返修在途",
            }.get(status, status),
            "qty": str(round_qty(row.get("qty"))),
        }

    def correct_movement(self, movement_id: int, *, qty, note: str = "") -> dict:
        row = self._store.get_movement(movement_id)
        if not row:
            raise ValueError("出入库流水不存在")
        self._ensure_movement_editable(row)
        updated = self._store.correct_movement(
            movement_id,
            new_qty=round_qty(qty),
            new_note=str(note or "").strip(),
        )
        return self._enrich_movement(updated)

    @staticmethod
    def _ensure_movement_editable(row: dict) -> None:
        action = str(row.get("action_type") or "")
        if action == "demo_inject":
            raise ValueError("演示数据流水不可修改")
        if action == ACTION_ADJUST:
            raise ValueError("库存校正流水请用「校正库存」重新设定目标数量")
        note = str(row.get("note") or "")
        if "订单出货" in note:
            raise ValueError("订单出货产生的流水请从出货明细处理，不可在此修改")

    @staticmethod
    def _movement_editable(row: dict) -> bool:
        action = str(row.get("action_type") or "")
        if action == "demo_inject":
            return False
        if action == ACTION_ADJUST:
            return False
        if "订单出货" in str(row.get("note") or ""):
            return False
        return action in (
            ACTION_INBOUND,
            ACTION_OUTBOUND,
            ACTION_SKIP_OUTBOUND,
            ACTION_REPAIR_OUT,
            ACTION_REPAIR_IN,
            ACTION_COMPLETE,
            ACTION_OUT_SEND,
            ACTION_OUT_RECV,
            ACTION_SHIP,
        )

    @staticmethod
    def _process_display(code: str) -> str:
        c = (code or "").strip()
        if not c:
            return ""
        if c == PROCESS_FINISHED:
            return "成品"
        name = PROCESS_BY_CODE.get(c, "")
        return f"{c} {name}".strip() if name else c

    def _movement_route_display(self, row: dict) -> str:
        action = str(row.get("action_type") or "")
        from_code = str(row.get("from_process_code") or "").strip()
        to_code = str(row.get("to_process_code") or "").strip()
        code = str(row.get("process_code") or "").strip()
        if action in (ACTION_OUTBOUND, ACTION_SKIP_OUTBOUND, ACTION_OUT_SEND, ACTION_SHIP):
            if from_code == PROCESS_FINISHED:
                return "成品出库"
            if from_code and to_code:
                arrow = "⇢" if action == ACTION_SKIP_OUTBOUND else "→"
                return f"{self._process_display(from_code)} {arrow} {self._process_display(to_code)}"
        if action == ACTION_REPAIR_OUT:
            if from_code == PROCESS_FINISHED or code == PROCESS_FINISHED:
                return "成品 → 返修在途"
            if from_code:
                return f"返修 · {self._process_display(from_code)}"
        if action == ACTION_REPAIR_IN:
            if to_code == PROCESS_FINISHED or code == PROCESS_FINISHED:
                return "返修入库 · 成品"
            if to_code:
                return f"返修入库 · {self._process_display(to_code)}"
        if action in (ACTION_INBOUND, ACTION_OUT_RECV, ACTION_COMPLETE):
            if to_code == PROCESS_FINISHED:
                return f"入库成品 · {self._process_display(code)}"
            if code:
                return f"入库 · {self._process_display(code)}"
        if code:
            return self._process_display(code)
        return "—"

    def _enrich_movement(self, row: dict, *, bom_cache: dict | None = None) -> dict:
        part = str(row.get("product_part_no") or "").strip()
        product_name = ""
        customer_name = ""
        if part:
            if bom_cache is not None:
                if part not in bom_cache:
                    bom = self._cost.find_latest_by_part_no(part)
                    bom_cache[part] = (
                        str(bom.product_name or "").strip() if bom else "",
                        str(bom.customer_name or "").strip() if bom else "",
                    )
                product_name, customer_name = bom_cache[part]
            else:
                bom = self._cost.find_latest_by_part_no(part)
                if bom:
                    product_name = str(bom.product_name or "").strip()
                    customer_name = str(bom.customer_name or "").strip()
        code = str(row.get("process_code") or "").strip()
        from_code = str(row.get("from_process_code") or "").strip()
        process_name = (
            "成品"
            if code == PROCESS_FINISHED
            else PROCESS_BY_CODE.get(code, "")
        )
        from_process_name = (
            "成品"
            if from_code == PROCESS_FINISHED
            else PROCESS_BY_CODE.get(from_code, from_code)
        )
        route_display = self._movement_route_display(row)
        doc_no = self._normalize_doc_no_display(str(row.get("doc_no") or ""))
        return {
            **row,
            "doc_no": doc_no,
            "product_name": product_name,
            "customer_name": customer_name,
            "process_name": process_name,
            "from_process_name": from_process_name,
            "route_display": route_display,
            "action_label": ACTION_LABELS.get(str(row.get("action_type") or ""), row.get("action_type")),
            "qty": str(round_qty(row.get("qty"))),
            "editable": self._movement_editable(row),
        }
