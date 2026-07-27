"""SOP 正式测试用：清空业务 SQLite 数据并写入带「测」标注的演示数据集。"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

from test_impl.order_management.cost_analysis import CostRecordService
from test_impl.order_management.inventory.service import InventoryService
from test_impl.order_management.order_entry.line_service import OrderLineService
from test_impl.order_management.order_entry.line_store import LineStore
from test_impl.order_management.cost_analysis.cost_store import CostStore
from test_impl.order_management.inventory.store import InventoryStore

DEMO_PART_PREFIX = "TST-PL-"
DEMO_ORDER_PREFIX = "TST-PO-"
DEMO_PAYMENT_NOTE = "【测试数据】"
DEFAULT_SUPPLIER = "苏州麦凯良金属制品厂"
DEFAULT_COUNT = 15


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_json_profiles(name: str) -> Dict[str, dict]:
    path = _project_root() / "data" / name
    if not path.is_file():
        alt = path.with_name(name.replace(".json", ".example.json"))
        path = alt if alt.is_file() else path
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _share_sqlite_connection(store: LineStore, cost_store: CostStore, inv_store: InventoryStore) -> None:
    """种子脚本内共用一个连接，避免 Windows 下多连接锁库。"""
    main = store._conn
    for extra in (cost_store, inv_store):
        try:
            extra._conn.close()
        except Exception:
            pass
        extra._conn = main


def clear_operational_data(store: LineStore) -> None:
    """删除 SQLite 业务数据；不改动 data/*.json 客商档案。"""
    tables = [
        "shipment_events",
        "production_replenish_orders",
        "inventory_movements",
        "inventory_balances",
        "inventory_part_tags",
        "order_lines",
        "cost_records",
        "parts",
        "customers",
    ]
    conn = store._conn
    conn.execute("PRAGMA busy_timeout = 60000")
    conn.execute("PRAGMA foreign_keys = OFF")
    for table in tables:
        conn.execute(f"DELETE FROM {table}")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()


def _demo_route(idx: int, supplier: str) -> dict:
    """外发工序带单价，供应付模块演示。"""
    price = f"{2.0 + (idx % 5) * 0.5:.2f}"
    variants = [
        {
            "01": "1.20",
            "02": {"price": price, "supplier": supplier},
            "28": {"price": "0.80", "supplier": "场内自制"},
            "34": {"price": "1.50", "supplier": "场内自制"},
        },
        {
            "01": "1.00",
            "13": {"price": price, "supplier": supplier},
            "28": {"price": "0.90", "supplier": "场内自制"},
            "34": {"price": "1.40", "supplier": "场内自制"},
        },
        {
            "01": "1.10",
            "02": {"price": price, "supplier": supplier},
            "11": {"price": "3.20", "supplier": supplier},
            "28": {"price": "0.85", "supplier": "场内自制"},
            "34": {"price": "1.55", "supplier": "场内自制"},
        },
    ]
    return variants[idx % len(variants)]


def _part_no(i: int) -> str:
    return f"{DEMO_PART_PREFIX}{i:03d}"


def _order_no(i: int) -> str:
    return f"{DEMO_ORDER_PREFIX}{i:04d}"


def _iso_ship(days_ago: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.replace(hour=10, minute=0, second=0, microsecond=0).isoformat()


def seed_sop_test_data(*, count: int = DEFAULT_COUNT) -> Dict[str, Any]:
    """写入各模块测试数据（默认 15 条/类）。"""
    count = max(10, min(20, int(count)))
    customers = list(_load_json_profiles("customer_profiles.json").keys())
    suppliers = list(_load_json_profiles("supplier_profiles.json").keys())
    if not customers:
        customers = ["演示客户A", "演示客户B", "演示客户C"]
    if DEFAULT_SUPPLIER not in suppliers:
        suppliers = [DEFAULT_SUPPLIER] + suppliers

    lines = OrderLineService()
    store: LineStore = lines._store
    db_path = store.db_path
    cost_store = CostStore(db_path)
    inv_store = InventoryStore(db_path)
    _share_sqlite_connection(store, cost_store, inv_store)
    clear_operational_data(store)
    records = CostRecordService(store=cost_store, line_store=store)
    inv = InventoryService(store=inv_store, cost_store=cost_store, record_service=records)

    bom_created: List[str] = []
    order_ids: List[int] = []
    shipment_ids: List[int] = []
    inv_parts: List[str] = []

    supplier = DEFAULT_SUPPLIER if DEFAULT_SUPPLIER in suppliers else suppliers[0]

    with patch(
        "test_impl.order_management.cost_analysis.record_service.list_profile_suppliers",
        return_value=suppliers[:20],
    ):
        # --- BOM（cost_records）---
        for i in range(1, count + 1):
            part = _part_no(i)
            cust = customers[(i - 1) % len(customers)]
            records.create_record(
                {
                    "customer_name": cust,
                    "product_name": f"【测】培训样件-{i:02d}",
                    "mold_no": f"TST-MJ-{i:04d}",
                    "product_part_no": part,
                    "cavity": "1*2",
                    "unit_weight_g": str(80 + i * 3),
                    "material": "ADC12",
                    "machine_tonnage": "280T",
                    "material_unit_price": "0.02",
                    "process_prices": _demo_route(i, supplier),
                    "is_demo": True,
                }
            )
            bom_created.append(part)

        store._conn.commit()

        # --- 库存 + 外发回货（应付）---
        from test_impl.order_management.inventory.store import (
            PROCESS_FINISHED,
            STATUS_FINISHED,
            STATUS_INHOUSE,
            STATUS_OUTSOURCE,
        )

        for i in range(1, count + 1):
            part = _part_no(i)
            route = inv.get_route(part)
            fin_qty = 1500 + i * 50
            buckets = [
                {
                    "process_code": PROCESS_FINISHED,
                    "status": STATUS_FINISHED,
                    "qty": str(fin_qty),
                }
            ]
            for stage_i, step in enumerate(route):
                buckets.append(
                    {
                        "process_code": step["code"],
                        "status": STATUS_INHOUSE,
                        "qty": str(200 + stage_i * 30 + i * 5),
                    }
                )
                if step["is_outsource"]:
                    os_qty = str(60 + i * 4)
                    buckets.append(
                        {
                            "process_code": step["code"],
                            "status": STATUS_OUTSOURCE,
                            "supplier_name": step["supplier"] or supplier,
                            "qty": os_qty,
                        }
                    )
            inv.inject_balances(part, buckets, note=f"{DEMO_PAYMENT_NOTE} 初始库存")
            inv._store.set_part_demo(part, True)
            inv_parts.append(part)

            # 回货流水（应付）：对外发在途做部分回货
            if i <= max(10, count - 2):
                for step in route:
                    if not step["is_outsource"]:
                        continue
                    sup = step["supplier"] or supplier
                    try:
                        recv_qty = min(40 + i * 2, 200)
                        inv.outsource_receive(
                            part,
                            step["code"],
                            sup,
                            recv_qty,
                            doc_no=f"RK-TST-{i:03d}",
                            note=f"{DEMO_PAYMENT_NOTE} 外协回货",
                        )
                        recv_days = 30 + (i % 45)
                        recv_at = _iso_ship(recv_days)
                        store._conn.execute(
                            """
                            UPDATE inventory_movements
                            SET created_at = ?
                            WHERE id = (
                                SELECT id FROM inventory_movements
                                WHERE product_part_no = ? AND action_type = 'outsource_receive'
                                ORDER BY id DESC LIMIT 1
                            )
                            """,
                            (recv_at, part),
                        )
                    except ValueError:
                        pass
                    break

        store._conn.commit()

        # --- 订单行 ---
        today = datetime.now().date()
        for i in range(1, count + 1):
            part = _part_no(i)
            cust = customers[(i - 1) % len(customers)]
            profile = _load_json_profiles("customer_profiles.json").get(cust, {})
            terms = (profile.get("payment_terms") or "月结90天").strip()
            order_date = (today - timedelta(days=60 + i * 3)).isoformat()
            delivery = (today + timedelta(days=15 + i)).isoformat()
            ln = lines.create_line(
                {
                    "customer": cust,
                    "order_date": order_date,
                    "delivery_date": delivery,
                    "order_no": _order_no(i),
                    "product_spec": f"【测】培训样件-{i:02d}",
                    "customer_part_no": part,
                    "unit_weight_g": str(80 + i * 3),
                    "material": "ADC12",
                    "po_qty": "1000",
                    "shipped_qty": "0",
                    "unit": "PCS",
                    "tax_rate": "13",
                    "rmb_tax_incl_price": f"{12.5 + (i % 7) * 0.8:.4f}",
                    "payment_terms": f"{terms} {DEMO_PAYMENT_NOTE}",
                    "is_demo": True,
                }
            )
            order_ids.append(ln.id)

        store._conn.commit()

        # --- 出货 / 出货明细 / 应收 ---
        # 6~10：部分出货 400；11~13：出完；1~5 保持未结
        for idx, line_id in enumerate(order_ids, start=1):
            if 6 <= idx <= 10:
                qty = 400
                days_ago = 75 - idx * 3
            elif 11 <= idx <= 13:
                qty = 1000
                days_ago = 45 - (idx - 11) * 5
            else:
                continue
            updated, ev = lines.ship_line(line_id, qty)
            shipment_ids.append(ev.id)
            ship_at = _iso_ship(max(1, days_ago))
            store._conn.execute(
                "UPDATE shipment_events SET shipped_at = ? WHERE id = ?",
                (ship_at, ev.id),
            )

        store._conn.commit()

        # --- 强制结案 2 条（14~15）---
        forced_ids: List[int] = []
        for line_id in order_ids[13:15]:
            if line_id in order_ids[: count]:
                try:
                    lines.force_close_line(line_id)
                    forced_ids.append(line_id)
                except ValueError:
                    pass

    store._conn.commit()

    summary = {
        "ok": True,
        "count": count,
        "cleared": True,
        "profiles_preserved": True,
        "demo_tag": "测",
        "bom_records": len(bom_created),
        "order_lines": len(order_ids),
        "shipment_events": len(shipment_ids),
        "inventory_parts": len(inv_parts),
        "forced_closed": len(forced_ids),
        "part_prefix": DEMO_PART_PREFIX,
        "order_prefix": DEMO_ORDER_PREFIX,
        "open_orders": 5,
        "partial_orders": 5,
        "closed_orders": 3,
        "note": DEMO_PAYMENT_NOTE,
    }
    return summary
