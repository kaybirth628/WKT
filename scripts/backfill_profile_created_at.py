#!/usr/bin/env python3
"""回填 customer_profiles / supplier_profiles 缺失的 created_at。

来源优先级：
1. 已有 created_at（跳过）
2. audit_log 新建记录（supplier.create / customer.create）
3. 客户：order_lines 首单 created_at
4. 供应商：cost_records BOM 工序供应商首次出现时间
5. 供应商：inventory_movements 外发/回货首次出现时间
6. 兜底：JSON 键顺序 → 2026-07-11 客商维护上线批次（相对先后）
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "wkt_orders.db"
CUSTOMER_FILE = ROOT / "data" / "customer_profiles.json"
SUPPLIER_FILE = ROOT / "data" / "supplier_profiles.json"
LEGACY_BASE = datetime(2026, 7, 11, 8, 0, 0, tzinfo=timezone.utc)


def _fold(name: str) -> str:
    return str(name or "").strip().casefold()


def _resolve_key(keys: Iterable[str], name: str) -> Optional[str]:
    target = _fold(name)
    if not target:
        return None
    for key in keys:
        if _fold(key) == target:
            return key
    return None


def _load_json(path: Path) -> Dict[str, dict]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _audit_creates(conn: sqlite3.Connection) -> Tuple[Dict[str, str], Dict[str, str]]:
    suppliers: Dict[str, str] = {}
    customers: Dict[str, str] = {}
    rows = conn.execute(
        """
        SELECT action, summary, created_at FROM audit_log
        WHERE action IN ('supplier.create', 'customer.create')
        ORDER BY created_at ASC
        """
    ).fetchall()
    for action, summary, created_at in rows:
        summary = str(summary or "").strip()
        ts = str(created_at or "").strip()
        if not ts:
            continue
        if action == "supplier.create":
            name = summary.replace("新建供应商", "").replace("新建供应商档案", "").strip()
            if name and _fold(name) not in {_fold(k) for k in suppliers}:
                suppliers[name] = ts
        elif action == "customer.create":
            name = summary.replace("新建客户", "").replace("新建客户档案", "").strip()
            if name and _fold(name) not in {_fold(k) for k in customers}:
                customers[name] = ts
    return suppliers, customers


def _customer_first_orders(conn: sqlite3.Connection) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for customer, first_at in conn.execute(
        "SELECT customer, MIN(created_at) FROM order_lines WHERE TRIM(customer) != '' GROUP BY customer"
    ):
        key = _fold(customer)
        if key and first_at and key not in out:
            out[key] = str(first_at)
    return out


def _extract_suppliers_from_process_json(raw: str) -> List[str]:
    names: List[str] = []
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return names
    if not isinstance(data, dict):
        return names
    for val in data.values():
        if isinstance(val, dict):
            s = str(val.get("supplier") or "").strip()
            if s:
                names.append(s)
            for item in val.get("suppliers") or []:
                s = str(item).strip()
                if s:
                    names.append(s)
    return names


def _supplier_first_from_bom(conn: sqlite3.Connection) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for raw_json, created_at in conn.execute(
        "SELECT process_prices_json, created_at FROM cost_records WHERE TRIM(process_prices_json) NOT IN ('', '{}')"
    ):
        ts = str(created_at or "").strip()
        if not ts:
            continue
        for name in _extract_suppliers_from_process_json(raw_json):
            key = _fold(name)
            if not key:
                continue
            if key not in out or ts < out[key]:
                out[key] = ts
    return out


def _supplier_first_from_inventory(conn: sqlite3.Connection) -> Dict[str, str]:
    out: Dict[str, str] = {}
    try:
        rows = conn.execute(
            """
            SELECT created_at, from_supplier, to_supplier FROM inventory_movements
            WHERE TRIM(from_supplier) != '' OR TRIM(to_supplier) != ''
            """
        ).fetchall()
    except sqlite3.OperationalError:
        return out
    for created_at, from_sup, to_sup in rows:
        ts = str(created_at or "").strip()
        if not ts:
            continue
        for name in (from_sup, to_sup):
            key = _fold(name)
            if not key:
                continue
            if key not in out or ts < out[key]:
                out[key] = ts
    return out


def _legacy_json_ts(index: int) -> str:
    return (LEGACY_BASE + timedelta(minutes=index)).replace(microsecond=0).isoformat()


def backfill_profiles(*, apply: bool) -> dict:
    customers = _load_json(CUSTOMER_FILE)
    suppliers = _load_json(SUPPLIER_FILE)
    conn = sqlite3.connect(DB_PATH) if DB_PATH.is_file() else None

    audit_sup: Dict[str, str] = {}
    audit_cust: Dict[str, str] = {}
    cust_orders: Dict[str, str] = {}
    bom_sup: Dict[str, str] = {}
    inv_sup: Dict[str, str] = {}
    if conn:
        audit_sup, audit_cust = _audit_creates(conn)
        cust_orders = _customer_first_orders(conn)
        bom_sup = _supplier_first_from_bom(conn)
        inv_sup = _supplier_first_from_inventory(conn)
        conn.close()

    stats: Dict[str, int] = defaultdict(int)
    report: List[str] = []

    def pick_ts(
        name: str,
        *,
        audit_map: Dict[str, str],
        order_map: Dict[str, str] | None = None,
        bom_map: Dict[str, str] | None = None,
        inv_map: Dict[str, str] | None = None,
        json_index: int,
    ) -> Tuple[str, str]:
        resolved_audit = _resolve_key(audit_map.keys(), name)
        if resolved_audit:
            return audit_map[resolved_audit], "audit"
        key = _fold(name)
        if order_map and key in order_map:
            return order_map[key], "order_first"
        if bom_map and key in bom_map:
            return bom_map[key], "bom_first"
        if inv_map and key in inv_map:
            return inv_map[key], "inventory_first"
        return _legacy_json_ts(json_index), "legacy_json_order"

    for idx, (name, row) in enumerate(customers.items()):
        if not isinstance(row, dict):
            continue
        if str(row.get("created_at") or "").strip():
            stats["customer_skip_existing"] += 1
            continue
        ts, src = pick_ts(name, audit_map=audit_cust, order_map=cust_orders, json_index=idx)
        row["created_at"] = ts
        stats[f"customer_{src}"] += 1
        report.append(f"客户 | {src:16} | {ts[:19]} | {name}")

    for idx, (name, row) in enumerate(suppliers.items()):
        if not isinstance(row, dict):
            continue
        if str(row.get("created_at") or "").strip():
            stats["supplier_skip_existing"] += 1
            continue
        ts, src = pick_ts(
            name,
            audit_map=audit_sup,
            bom_map=bom_sup,
            inv_map=inv_sup,
            json_index=idx,
        )
        row["created_at"] = ts
        stats[f"supplier_{src}"] += 1
        report.append(f"供应商 | {src:16} | {ts[:19]} | {name}")

    if apply:
        CUSTOMER_FILE.write_text(
            json.dumps(customers, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        SUPPLIER_FILE.write_text(
            json.dumps(suppliers, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return {"stats": dict(stats), "report": report}


def main() -> None:
    parser = argparse.ArgumentParser(description="回填客商档案 created_at")
    parser.add_argument("--apply", action="store_true", help="写回 JSON（默认仅预览）")
    parser.add_argument("--limit", type=int, default=20, help="预览条数")
    args = parser.parse_args()
    result = backfill_profiles(apply=args.apply)
    stats = result["stats"]
    print("=== 回填统计 ===")
    for k in sorted(stats):
        print(f"  {k}: {stats[k]}")
    print(f"\n=== 预览（前 {args.limit} 条）===")
    for line in result["report"][: args.limit]:
        print(line)
    if len(result["report"]) > args.limit:
        print(f"... 共 {len(result['report'])} 条")
    if not args.apply:
        print("\n加 --apply 写回 data/customer_profiles.json 与 supplier_profiles.json")


if __name__ == "__main__":
    main()
