"""将 BOM 工序供应商简称回写为 supplier_profiles 全称（仅可唯一匹配的）。"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from test_impl.order_management.cost_analysis.models import INHOUSE_SUPPLIER_LABEL
from test_impl.order_management.supplier_profile.store import (
    list_profile_suppliers,
    resolve_supplier_name,
)


def _default_db() -> Path:
    for rel in ("data/wkt_orders.db", "data.local/wkt_orders.db"):
        p = ROOT / rel
        if p.is_file():
            return p
    return ROOT / "data/wkt_orders.db"


def _normalize_supplier_field(raw: str, profile_set: set[str]) -> tuple[str, bool]:
    s = str(raw or "").strip()
    if not s or s in (INHOUSE_SUPPLIER_LABEL, "场内自制"):
        return s, False
    if s.casefold() in profile_set:
        return s, False
    resolved, _note = resolve_supplier_name(s)
    if resolved and resolved != s and resolved.casefold() in profile_set:
        return resolved, True
    return s, False


def backfill(db_path: Path, *, dry_run: bool = True) -> dict:
    profiles = list_profile_suppliers()
    profile_set = {p.casefold() for p in profiles}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, product_part_no, product_name, process_prices_json FROM cost_records"
    ).fetchall()

    replacements: Counter[tuple[str, str]] = Counter()
    records_touched = 0
    fields_changed = 0
    pending_updates: list[tuple[str, int]] = []

    for row in rows:
        raw_json = row["process_prices_json"] or "{}"
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue

        changed = False
        for key, value in data.items():
            if key == "__order__" or not isinstance(value, dict):
                continue
            primary = value.get("supplier")
            if primary is not None:
                new_primary, did = _normalize_supplier_field(str(primary), profile_set)
                if did:
                    value["supplier"] = new_primary
                    replacements[(str(primary).strip(), new_primary)] += 1
                    fields_changed += 1
                    changed = True
            suppliers = value.get("suppliers")
            if isinstance(suppliers, list):
                new_list: list[str] = []
                list_changed = False
                for item in suppliers:
                    old = str(item or "").strip()
                    new, did = _normalize_supplier_field(old, profile_set)
                    if did:
                        replacements[(old, new)] += 1
                        fields_changed += 1
                        list_changed = True
                    new_list.append(new)
                if list_changed:
                    value["suppliers"] = new_list
                    changed = True

        if changed:
            records_touched += 1
            new_json = json.dumps(data, ensure_ascii=False)
            pending_updates.append((new_json, int(row["id"])))

    if not dry_run and pending_updates:
        conn.executemany(
            "UPDATE cost_records SET process_prices_json = ? WHERE id = ?",
            pending_updates,
        )
        conn.commit()

    conn.close()
    return {
        "dry_run": dry_run,
        "db": str(db_path),
        "records_scanned": len(rows),
        "records_updated": records_touched,
        "fields_changed": fields_changed,
        "replacements": dict(replacements),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=None, help="SQLite path")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="写入数据库（默认仅预览）",
    )
    args = parser.parse_args()
    db_path = args.db or _default_db()
    if not db_path.is_file():
        raise SystemExit(f"数据库不存在: {db_path}")

    result = backfill(db_path, dry_run=not args.apply)
    print(f"DB: {result['db']}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"Records scanned: {result['records_scanned']}")
    print(f"Records updated: {result['records_updated']}")
    print(f"Supplier fields changed: {result['fields_changed']}")
    if result["replacements"]:
        print("\nReplacements:")
        for (old, new), cnt in sorted(
            result["replacements"].items(),
            key=lambda x: (-x[1], x[0][0]),
        ):
            print(f"  {old!r} -> {new!r}  x{cnt}")
    if not args.apply and result["records_updated"]:
        print("\nRun with --apply to persist changes.")


if __name__ == "__main__":
    main()
