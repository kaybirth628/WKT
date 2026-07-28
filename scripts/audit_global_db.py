#!/usr/bin/env python3
"""Audit WKT global SQLite database (data/wkt_orders.db) for integrity and consistency."""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "wkt_orders.db"

EXPECTED_TABLES = {
    "order_lines",
    "shipment_events",
    "customers",
    "parts",
    "cost_records",
    "cost_schema_meta",
    "inventory_balances",
    "inventory_movements",
    "inventory_part_tags",
    "production_replenish_orders",
    "users",
    "audit_log",
}

VALID_INV_STATUS = {"inhouse", "outsource", "finished", "repair"}


def audit(db_path: Path) -> int:
    if not db_path.is_file():
        print(f"ERROR: database not found: {db_path}")
        return 1

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    issues: list[dict] = []
    warns: list[dict] = []
    stats: dict = {}

    def issue(severity: str, category: str, message: str, detail: str | None = None) -> None:
        issues.append(
            {"severity": severity, "category": category, "message": message, "detail": detail}
        )

    def warn(category: str, message: str, detail: str | None = None) -> None:
        warns.append({"category": category, "message": message, "detail": detail})

    # 1. Integrity
    for row in conn.execute("PRAGMA integrity_check"):
        if row[0] != "ok":
            issue("CRITICAL", "integrity", f"PRAGMA integrity_check: {row[0]}")

    fk_rows = list(conn.execute("PRAGMA foreign_key_check"))
    for row in fk_rows:
        issue("CRITICAL", "foreign_key", f"FK violation: {dict(row)}")

    # 2. Schema
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]
    stats["tables"] = tables
    missing = EXPECTED_TABLES - set(tables)
    extra = set(tables) - EXPECTED_TABLES - {"sqlite_sequence"}
    if missing:
        issue("HIGH", "schema", f"Missing tables: {sorted(missing)}")
    if extra:
        warn("schema", f"Extra tables: {sorted(extra)}")

    for t in sorted(set(tables) - {"sqlite_sequence"}):
        stats[f"count_{t}"] = conn.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]

    # 3. Orphan shipments
    for r in conn.execute(
        """
        SELECT se.id, se.line_id, se.ship_qty
        FROM shipment_events se
        LEFT JOIN order_lines ol ON ol.id = se.line_id
        WHERE ol.id IS NULL
        """
    ):
        issue(
            "HIGH",
            "shipment",
            f"Orphan shipment_events id={r[0]} line_id={r[1]} qty={r[2]}",
        )

    # 4. shipped_qty vs event sum
    ship_sums: dict[int, Decimal] = defaultdict(lambda: Decimal("0"))
    for r in conn.execute("SELECT line_id, ship_qty FROM shipment_events"):
        try:
            ship_sums[int(r[0])] += Decimal(str(r[1] or "0"))
        except InvalidOperation:
            issue("HIGH", "shipment", f"Invalid ship_qty for line_id={r[0]}")

    lines = conn.execute(
        """
        SELECT id, customer, customer_part_no, po_qty, shipped_qty, closure_type, is_demo
        FROM order_lines
        """
    ).fetchall()

    mismatch_ship = 0
    over_ship = 0
    for ln in lines:
        lid = int(ln["id"])
        try:
            po = Decimal(str(ln["po_qty"] or "0"))
            shipped = Decimal(str(ln["shipped_qty"] or "0"))
        except InvalidOperation:
            issue("HIGH", "order_lines", f"Invalid qty on line id={lid}")
            continue
        ev_sum = ship_sums.get(lid, Decimal("0"))
        if shipped != ev_sum:
            mismatch_ship += 1
            if mismatch_ship <= 15:
                issue(
                    "MEDIUM",
                    "shipment",
                    f"line {lid} shipped_qty={shipped} != sum(events)={ev_sum}",
                    f"{ln['customer']} {ln['customer_part_no']}",
                )
        if shipped > po and not (ln["closure_type"] or "").strip():
            over_ship += 1
            if over_ship <= 10:
                issue(
                    "MEDIUM",
                    "order_lines",
                    f"line {lid} shipped_qty > po_qty ({shipped} > {po})",
                    f"{ln['customer']} {ln['customer_part_no']}",
                )

    if mismatch_ship > 15:
        issue(
            "MEDIUM",
            "shipment",
            f"{mismatch_ship} total lines where shipped_qty != sum(shipment_events)",
        )
    if over_ship > 10:
        warn("order_lines", f"{over_ship} lines with shipped_qty > po_qty")

    # 5. Part no multi-customer (non-demo order lines)
    part_owners: dict[str, set[str]] = defaultdict(set)
    for r in conn.execute(
        """
        SELECT customer, customer_part_no, is_demo
        FROM order_lines
        WHERE TRIM(customer_part_no) != ''
        """
    ):
        if r["is_demo"]:
            continue
        part_owners[r["customer_part_no"].strip().upper()].add(r["customer"])
    dup_parts = {p: cs for p, cs in part_owners.items() if len(cs) > 1}
    stats["dup_part_customers"] = len(dup_parts)
    for p, cs in list(dup_parts.items())[:10]:
        issue(
            "HIGH",
            "order_lines",
            f"Part {p} used by multiple customers: {sorted(cs)}",
        )
    if len(dup_parts) > 10:
        warn("order_lines", f"{len(dup_parts)} part numbers bound to multiple customers")

    # 6. cost_records
    bad_json = 0
    empty_part = 0
    dup_cost: dict[tuple[str, str], list[int]] = defaultdict(list)
    for r in conn.execute(
        "SELECT id, customer_name, product_part_no, process_prices_json FROM cost_records"
    ):
        pid = (r["product_part_no"] or "").strip()
        if not pid:
            empty_part += 1
        key = (r["customer_name"].strip(), pid.upper())
        dup_cost[key].append(int(r["id"]))
        try:
            data = json.loads(r["process_prices_json"] or "{}")
            if not isinstance(data, dict):
                bad_json += 1
        except json.JSONDecodeError:
            bad_json += 1

    if bad_json:
        issue("HIGH", "cost_records", f"{bad_json} rows with invalid process_prices_json")
    if empty_part:
        warn("cost_records", f"{empty_part} rows with empty product_part_no")

    cost_dups = {k: v for k, v in dup_cost.items() if len(v) > 1 and k[1]}
    stats["cost_dup_keys"] = len(cost_dups)
    for k, ids in list(cost_dups.items())[:8]:
        issue(
            "MEDIUM",
            "cost_records",
            f"Duplicate BOM key customer={k[0]!r} part={k[1]!r} ids={ids}",
        )

    # 7. Inventory
    for r in conn.execute(
        """
        SELECT id, product_part_no, process_code, status, qty
        FROM inventory_balances
        WHERE CAST(qty AS REAL) < -0.0001
        """
    ):
        issue(
            "HIGH",
            "inventory",
            f"Negative balance id={r[0]} {r[1]} {r[2]}/{r[3]} qty={r[4]}",
        )

    for r in conn.execute("SELECT DISTINCT status FROM inventory_balances"):
        if r[0] not in VALID_INV_STATUS:
            issue("HIGH", "inventory", f"Unknown inventory status: {r[0]!r}")

    for r in conn.execute(
        """
        SELECT pr.id, pr.line_id, pr.doc_no
        FROM production_replenish_orders pr
        LEFT JOIN order_lines ol ON ol.id = pr.line_id
        WHERE pr.line_id IS NOT NULL AND ol.id IS NULL
        """
    ):
        issue(
            "MEDIUM",
            "inventory",
            f"Orphan replenish order id={r[0]} line_id={r[1]} doc={r[2]}",
        )

    # 8. audit_log orphan users
    for r in conn.execute(
        """
        SELECT al.id, al.user_id
        FROM audit_log al
        LEFT JOIN users u ON u.id = al.user_id
        WHERE al.user_id IS NOT NULL AND u.id IS NULL
        """
    ):
        warn("audit_log", f"audit_log id={r[0]} references missing user_id={r[1]}")

    # 9. Empty customer
    empty_customer = conn.execute(
        "SELECT COUNT(*) FROM order_lines WHERE TRIM(customer) = ''"
    ).fetchone()[0]
    if empty_customer:
        issue("HIGH", "order_lines", f"{empty_customer} order lines with empty customer")

    stats["demo_lines"] = conn.execute(
        "SELECT COUNT(*) FROM order_lines WHERE is_demo = 1"
    ).fetchone()[0]
    stats["demo_cost"] = conn.execute(
        "SELECT COUNT(*) FROM cost_records WHERE is_demo = 1"
    ).fetchone()[0]

    wal = db_path.with_suffix(".db-wal")
    stats["wal_bytes"] = wal.stat().st_size if wal.exists() else 0

    # Report
    print("=" * 60)
    print(f"WKT Global DB Audit: {db_path}")
    print("=" * 60)
    print("Tables:", ", ".join(tables))
    print("Row counts:")
    for t in sorted(set(tables) - {"sqlite_sequence"}):
        print(f"  {t}: {stats.get('count_' + t, '?')}")
    print()
    print(f"Demo rows: order_lines={stats['demo_lines']}, cost_records={stats['demo_cost']}")
    print(f"Part-no multi-customer conflicts: {stats.get('dup_part_customers', 0)}")
    print(f"Cost duplicate keys: {stats.get('cost_dup_keys', 0)}")
    print(f"WAL size: {stats['wal_bytes']} bytes")
    print()

    sev_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    by_sev: dict[str, list] = defaultdict(list)
    for i in issues:
        by_sev[i["severity"]].append(i)

    print(f"ISSUES: {len(issues)} | WARNINGS: {len(warns)}")
    for s in sev_order:
        if by_sev[s]:
            print(f"\n--- {s} ({len(by_sev[s])}) ---")
            for i in by_sev[s][:25]:
                print(f"  [{i['category']}] {i['message']}")
                if i.get("detail"):
                    print(f"    -> {i['detail']}")
            if len(by_sev[s]) > 25:
                print(f"  ... +{len(by_sev[s]) - 25} more")

    if warns:
        print(f"\n--- WARNINGS ({len(warns)}) ---")
        for w in warns[:20]:
            print(f"  [{w['category']}] {w['message']}")
        if len(warns) > 20:
            print(f"  ... +{len(warns) - 20} more")

    conn.close()
    return 1 if any(i["severity"] in ("CRITICAL", "HIGH") for i in issues) else 0


def detail_report(db_path: Path) -> None:
    """Extra detail for audit handoff (stdout)."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    print("\n=== Detail: duplicate BOM ===")
    for r in conn.execute(
        """
        SELECT customer_name, product_part_no, GROUP_CONCAT(id) AS ids, COUNT(*) AS c
        FROM cost_records
        WHERE TRIM(product_part_no) != ''
        GROUP BY customer_name, UPPER(TRIM(product_part_no))
        HAVING c > 1
        """
    ):
        print(f"  {r['customer_name']} | {r['product_part_no']} | ids={r['ids']}")

    print("\n=== Detail: cost_records by customer ===")
    for r in conn.execute(
        """
        SELECT customer_name, COUNT(*) AS c,
               SUM(CASE WHEN is_demo = 1 THEN 1 ELSE 0 END) AS demo
        FROM cost_records GROUP BY customer_name ORDER BY c DESC
        """
    ):
        print(f"  {r['customer_name']}: total={r['c']} demo={r['demo']}")

    print("\n=== Detail: inventory by status ===")
    for r in conn.execute(
        """
        SELECT status, COUNT(*) AS rows, ROUND(SUM(CAST(qty AS REAL)), 2) AS total_qty
        FROM inventory_balances GROUP BY status
        """
    ):
        print(f"  {r['status']}: rows={r['rows']} qty={r['total_qty']}")

    fk = sqlite3.connect(str(db_path)).execute("PRAGMA foreign_keys").fetchone()[0]
    print(f"\n=== Code note: SQLite foreign_keys default = {fk} (LineStore does not enable) ===")

    conn.close()


def write_detail_file(db_path: Path, out_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    lines: list[str] = []
    lines.append("# WKT DB Audit Detail\n")
    lines.append("## Duplicate BOM (same customer + part_no)\n")
    for r in conn.execute(
        """
        SELECT customer_name, product_part_no, GROUP_CONCAT(id) AS ids
        FROM cost_records
        WHERE TRIM(product_part_no) != ''
        GROUP BY customer_name, UPPER(TRIM(product_part_no))
        HAVING COUNT(*) > 1
        """
    ):
        lines.append(f"- {r['customer_name']} | {r['product_part_no']} | ids={r['ids']}")
        for rid in str(r["ids"]).split(","):
            row = conn.execute(
                "SELECT id, created_at, updated_at, is_demo FROM cost_records WHERE id = ?",
                (int(rid),),
            ).fetchone()
            if row:
                lines.append(f"  - id={row['id']} created={row['created_at']} demo={row['is_demo']}")
    lines.append("\n## All tables row count\n")
    for t in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence' ORDER BY name"
    ):
        name = t[0]
        c = conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
        lines.append(f"- {name}: {c}")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    conn.close()


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Audit WKT global SQLite database")
    parser.add_argument("db", nargs="?", default=str(DEFAULT_DB), help="Path to wkt_orders.db")
    parser.add_argument("--detail", action="store_true", help="Print extended detail")
    parser.add_argument("--out", default="", help="Write detail markdown to path")
    args = parser.parse_args()
    db = Path(args.db)
    rc = audit(db)
    if args.detail:
        detail_report(db)
    if args.out:
        write_detail_file(db, Path(args.out))
        print(f"\nDetail written: {args.out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
