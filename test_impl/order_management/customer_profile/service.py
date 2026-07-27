from __future__ import annotations

from typing import Any, Dict, List, Optional

from test_impl.order_management.order_entry.line_service import OrderLineService

from .store import (
    EMPTY_PROFILE,
    delete_profile,
    get_profile,
    is_delivery_enabled,
    list_profile_customers,
    load_all_profiles,
    save_profile,
    sort_names_by_created_at,
)
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
        return sort_names_by_created_at(names)

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

    def _all_known_customer_names(self) -> set[str]:
        names: set[str] = set()
        try:
            for name in self._lines.list_master().get("customers") or []:
                if str(name).strip():
                    names.add(str(name).strip())
        except Exception:
            pass
        names.update(list_profile_customers())
        from test_impl.order_management.delivery_note.template_store import DeliveryTemplateStore
        from test_impl.order_management.delivery_note.wkt_document import load_customer_delivery_config

        names.update(load_customer_delivery_config().keys())
        names.update(DeliveryTemplateStore().load_mapping().keys())
        return names

    def _resolve_customer_name(self, customer: str) -> str | None:
        target = (customer or "").strip().casefold()
        if not target:
            return None
        for name in self._all_known_customer_names():
            if str(name).strip().casefold() == target:
                return str(name).strip()
        return None

    def delete(self, customer: str) -> None:
        customer = (customer or "").strip()
        if not customer:
            raise ValueError("客户名称不能为空")
        actual = self._resolve_customer_name(customer)
        if not actual:
            raise ValueError(f"客户「{customer}」不存在")

        if self._lines.count_lines_for_customer(actual) > 0:
            raise ValueError(f"客户「{actual}」已有订单，无法删除")

        profiles = load_all_profiles()
        profile_key = next((k for k in profiles if k.casefold() == actual.casefold()), None)
        if profile_key:
            delete_profile(profile_key)

        from test_impl.order_management.delivery_note.template_store import DeliveryTemplateStore
        from test_impl.order_management.delivery_note.wkt_document import remove_customer_delivery_info

        DeliveryTemplateStore().remove_customer_mapping(actual)
        remove_customer_delivery_info(actual)
        self._lines.delete_customer_master(actual)

    def empty_profile(self) -> Dict[str, str]:
        return dict(EMPTY_PROFILE)
