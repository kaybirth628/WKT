"""一次性：导入客户档案并统一订单客户全称（鑫福泰系列保留简称）。"""
from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = ROOT / "data" / "customer_import_proposal.json"
DB = ROOT / "data" / "wkt_orders.db"
PROFILES = ROOT / "data" / "customer_profiles.json"
DELIVERY = ROOT / "data" / "delivery_templates" / "customer_delivery.json"
SKIP_PREFIX = "鑫福泰"


def main() -> None:
    proposal = json.loads(PROPOSAL.read_text(encoding="utf-8"))
    profiles_raw = proposal["profiles"]
    profiles_out: dict[str, dict] = {}
    for p in profiles_raw:
        name = p["canonical_name"]
        profiles_out[name] = {
            "address": p["address"],
            "contact": p["contact"],
            "phone": p["phone"],
            "email": p.get("email", ""),
            "payment_terms": p["payment_terms"],
            "reconciliation_period": p.get("reconciliation_period") or "month_21_20",
        }
    PROFILES.write_text(
        json.dumps(profiles_out, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(profiles_out)} profiles -> {PROFILES}")

    renames = [
        r for r in proposal["order_renames"]
        if not str(r["from"]).startswith(SKIP_PREFIX)
    ]
    skipped = [
        r for r in proposal["order_renames"]
        if str(r["from"]).startswith(SKIP_PREFIX)
    ]
    print(f"Order renames: {len(renames)} groups; skipped 鑫福泰: {len(skipped)}")

    backup = DB.with_suffix(f".db.bak-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(DB, backup)
    print(f"DB backup -> {backup}")

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    total_updated = 0
    try:
        for r in renames:
            old, new = r["from"], r["to"]
            cur = conn.execute(
                "UPDATE order_lines SET customer = ?, updated_at = ? WHERE customer = ?",
                (new, now, old),
            )
            n = cur.rowcount
            total_updated += n
            print(f"  {old} -> {new}: {n} rows")
            conn.execute("INSERT OR IGNORE INTO customers (name) VALUES (?)", (new,))

        old_names = [r["from"] for r in renames]
        for old in old_names:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM order_lines WHERE customer = ?", (old,)
            ).fetchone()
            if int(row["c"]) == 0:
                conn.execute("DELETE FROM customers WHERE name = ?", (old,))

        conn.commit()
    finally:
        conn.close()

    print(f"Total order_lines updated: {total_updated}")

    if DELIVERY.exists():
        delivery = json.loads(DELIVERY.read_text(encoding="utf-8"))
        for r in proposal.get("delivery_template_renames", []):
            old, new = r["from"], r["to"]
            if old in delivery:
                delivery[new] = delivery.pop(old)
                addr = profiles_out.get(new, {}).get("address", "")
                if addr:
                    delivery[new]["receiver_address"] = addr
        DELIVERY.write_text(
            json.dumps(delivery, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Updated delivery template keys -> {DELIVERY}")

    proposal["status"] = "已执行 — 鑫福泰订单简称保留"
    proposal["executed_at"] = datetime.now(timezone.utc).isoformat()
    proposal["executed_renames"] = len(renames)
    proposal["skipped_renames"] = [r["from"] for r in skipped]
    PROPOSAL.write_text(
        json.dumps(proposal, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
