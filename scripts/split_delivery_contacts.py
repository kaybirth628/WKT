#!/usr/bin/env python3
"""将 customer_delivery.json 中合并的「联系人+电话」拆分为独立字段。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_impl.order_management.delivery_note.wkt_document import (  # noqa: E402
    _CUSTOMER_FILE,
    load_customer_delivery_config,
    split_receiver_contact,
)


def main() -> None:
    all_cfg = load_customer_delivery_config()
    updated = 0
    for name, row in all_cfg.items():
        if not isinstance(row, dict):
            continue
        contact = (row.get("receiver_contact") or "").strip()
        phone = (row.get("receiver_phone") or "").strip()
        if not contact or phone:
            continue
        c, p = split_receiver_contact(contact)
        if not p:
            continue
        row["receiver_contact"] = c
        row["receiver_phone"] = p
        updated += 1
        print(f"  已拆分: {name} -> {c} | {p}")

    if updated:
        _CUSTOMER_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CUSTOMER_FILE.write_text(
            json.dumps(all_cfg, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    print(f"完成，共更新 {updated} 条收货联系人。")


if __name__ == "__main__":
    main()
