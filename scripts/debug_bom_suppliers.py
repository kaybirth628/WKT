"""Debug BOM process supplier names vs supplier profiles."""
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from test_impl.order_management.supplier_profile.store import (
    list_profile_suppliers,
    resolve_supplier_name,
)

db = ROOT / "data" / "wkt_orders.db"
if not db.exists():
    db = ROOT / "data.local" / "wkt_orders.db"
print("DB:", db)

conn = sqlite3.connect(db)
conn.row_factory = sqlite3.Row

profiles = list_profile_suppliers()
profile_set = {p.casefold() for p in profiles}
print("Supplier profiles count:", len(profiles))
print("Sample profiles:", profiles[:8])

all_names: Counter[str] = Counter()
unmatched: Counter[str] = Counter()
matched_short: list[tuple[str, str]] = []

rows = conn.execute("SELECT id, product_part_no, product_name, process_prices_json FROM cost_records").fetchall()
for r in rows:
    try:
        pp = json.loads(r["process_prices_json"] or "{}")
    except json.JSONDecodeError:
        continue
    for k, v in pp.items():
        if k == "__order__" or not isinstance(v, dict):
            continue
        names = []
        if v.get("supplier"):
            names.append(str(v["supplier"]).strip())
        for s in v.get("suppliers") or []:
            s = str(s or "").strip()
            if s:
                names.append(s)
        for name in names:
            if not name or name == "场内自制":
                continue
            all_names[name] += 1
            if name.casefold() not in profile_set:
                resolved, note = resolve_supplier_name(name)
                if resolved and resolved.casefold() in profile_set and resolved != name:
                    matched_short.append((name, resolved))
                else:
                    unmatched[name] += 1

print("\nDistinct supplier strings in BOM:", len(all_names))
print("\nTop BOM supplier values:")
for name, cnt in all_names.most_common(25):
    in_profile = "OK" if name.casefold() in profile_set else "MISSING"
    resolved, _ = resolve_supplier_name(name)
    resolve_hint = f" -> {resolved}" if resolved != name else ""
    print(f"  [{in_profile}] {name!r} x{cnt}{resolve_hint}")

print("\nCould resolve but DB still has short name:")
for short, full in matched_short[:20]:
    print(f"  {short!r} -> {full!r}")
print("Total resolvable short names in DB:", len(matched_short))

print("\nUnmatched (resolve failed or not in profile):")
for name, cnt in unmatched.most_common(20):
    resolved, note = resolve_supplier_name(name)
    print(f"  {name!r} x{cnt} resolve={resolved!r} note={note!r}")

# 810 related sample
print("\n--- 810 BOM sample ---")
for r in conn.execute(
    """
    SELECT id, product_part_no, product_name, process_prices_json
    FROM cost_records WHERE LOWER(product_name) LIKE '%810%'
    LIMIT 3
    """
):
    print(r["product_part_no"], "|", r["product_name"])
    pp = json.loads(r["process_prices_json"] or "{}")
    for k, v in sorted(pp.items()):
        if k == "__order__" or not isinstance(v, dict):
            continue
        sup = v.get("supplier") or ""
        if sup and sup != "场内自制":
            resolved, note = resolve_supplier_name(sup)
            print(f"  {k}: stored={sup!r} resolved={resolved!r}")

conn.close()
