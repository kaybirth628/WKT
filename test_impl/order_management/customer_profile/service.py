from __future__ import annotations

from typing import Any, Dict, List, Optional

from test_impl.order_management.order_entry.line_service import OrderLineService

from .store import EMPTY_PROFILE, get_profile, is_delivery_enabled, list_profile_customers, save_profile
from .store import profile_with_labels as _profile_with_labels


class CustomerProfileService:
    def __init__(self, line_service: Optional[OrderLineService] = None) -> None:
        self._lines = line_service or OrderLineService()

    def _customer_names(self) -> List[str]:
        names: set[str] = set()
        try:
            for name in self._lines.list_master().get("customers") or []:
                if str(name).strip():
                    names.add(str(name).strip())
        except Exception:
            pass
        names.update(list_profile_customers())
        return sorted(names, key=lambda x: (x.casefold(), x))

    def list_rows(self) -> List[Dict[str, Any]]:
        rows = []
        for name in self._customer_names():
            info = get_profile(name)
            rows.append(
                {
                    "customer": name,
                    **_profile_with_labels(info),
                    "delivery_enabled": is_delivery_enabled(info),
                }
            )
        return rows

    def get(self, customer: str) -> Dict[str, str]:
        return get_profile(customer)

    def save(self, customer: str, info: dict) -> Dict[str, str]:
        row = save_profile(customer, info)
        if is_delivery_enabled(row):
            from .delivery_sync import sync_delivery_from_profile

            sync_delivery_from_profile(customer, row, only_if_empty=True)
        return row

    def create(self, customer: str, info: dict) -> Dict[str, str]:
        customer = (customer or "").strip()
        if not customer:
            raise ValueError("客户名称不能为空")
        existing = {n.casefold(): n for n in self._customer_names()}
        if customer.casefold() in existing:
            dup = existing[customer.casefold()]
            raise ValueError(f"客户「{dup}」已存在")
        self._lines.add_customer(customer)
        return self.save(customer, info)

    def empty_profile(self) -> Dict[str, str]:
        return dict(EMPTY_PROFILE)
