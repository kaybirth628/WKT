#!/usr/bin/env python3
"""将 customer_profiles.json 中的地址/联系人同步到 customer_delivery.json（仅填充空字段）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_impl.order_management.customer_profile.delivery_sync import (  # noqa: E402
    sync_delivery_from_profile,
)
from test_impl.order_management.customer_profile.store import load_all_profiles  # noqa: E402


def main() -> None:
    profiles = load_all_profiles()
    updated = 0
    for name, profile in sorted(profiles.items()):
        if sync_delivery_from_profile(name, profile, only_if_empty=True):
            updated += 1
            print(f"  已同步: {name}")
    print(f"完成，共更新 {updated} 个客户的送货收货信息。")


if __name__ == "__main__":
    main()
