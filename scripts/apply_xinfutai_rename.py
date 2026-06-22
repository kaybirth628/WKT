"""鑫福泰订单客户：改为「苏州鑫福泰电子科技有限公司-尾缀」，档案/送货单继承母公司。"""
from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "wkt_orders.db"
PROFILES = ROOT / "data" / "customer_profiles.json"
DELIVERY = ROOT / "data" / "delivery_templates" / "customer_delivery.json"

PARENT = "苏州鑫福泰电子科技有限公司"
OLD_PREFIX = "鑫福泰-"


def new_customer_name(old: str) -> str | None:
    old = (old or "").strip()
    if not old.startswith(OLD_PREFIX):
        return None
    suffix = old[len(OLD_PREFIX) :]
    if not suffix:
        return None
    return f"{PARENT}-{suffix}"


def delivery_from_profile(profile: dict, customer_name: str) -> dict:
    return {
        "receiver_company": customer_name,
        "receiver_address": profile.get("address", ""),
        "receiver_contact": profile.get("contact", ""),
        "doc_no_prefix": "",
    }


def main() -> None:
    profiles = json.loads(PROFILES.read_text(encoding="utf-8"))
    parent_profile = profiles.get(PARENT)
    if not parent_profile:
        raise SystemExit(f"缺少母公司档案：{PARENT}")

    delivery = {}
    if DELIVERY.is_file():
        delivery = json.loads(DELIVERY.read_text(encoding="utf-8"))

    backup = DB.with_suffix(f".db.bak-xinfutai-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
    shutil.copy2(DB, backup)
    print(f"DB backup -> {backup}")

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()
    renames: list[tuple[str, str, int]] = []

    try:
        old_names = [
            r["customer"]
            for r in conn.execute(
                "SELECT DISTINCT customer FROM order_lines WHERE customer LIKE ? ORDER BY customer",
                (OLD_PREFIX + "%",),
            ).fetchall()
        ]
        if not old_names:
            print("No 鑫福泰-* customers in order_lines.")
            return

        for old in old_names:
            new = new_customer_name(old)
            if not new:
                print(f"Skip: {old}")
                continue
            cur = conn.execute(
                "UPDATE order_lines SET customer = ?, updated_at = ? WHERE customer = ?",
                (new, now, old),
            )
            n = cur.rowcount
            renames.append((old, new, n))
            print(f"  {old} -> {new}: {n} rows")

            conn.execute("INSERT OR IGNORE INTO customers (name) VALUES (?)", (new,))
            if conn.execute("SELECT COUNT(*) FROM order_lines WHERE customer = ?", (old,)).fetchone()[0] == 0:
                conn.execute("DELETE FROM customers WHERE name = ?", (old,))

            profiles[new] = dict(parent_profile)
            delivery[new] = delivery_from_profile(parent_profile, new)

        conn.commit()
    finally:
        conn.close()

    if PARENT not in delivery:
        delivery[PARENT] = delivery_from_profile(parent_profile, PARENT)

    PROFILES.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")
    DELIVERY.write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Updated profiles: {len(renames)} variant keys (+ parent template kept)")
    print(f"Updated delivery: {len(renames)} variant keys")
    print("Done.")


if __name__ == "__main__":
    main()
