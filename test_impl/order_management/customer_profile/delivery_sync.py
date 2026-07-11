"""将客户档案中的地址、联系人默认同步到送货单收货信息。"""
from __future__ import annotations

from typing import Dict

from test_impl.order_management.customer_profile.store import get_profile, is_delivery_enabled
from test_impl.order_management.delivery_note.wkt_document import (
    get_raw_customer_delivery_info,
    save_customer_delivery_info,
)


def format_receiver_contact(profile: Dict[str, str]) -> str:
    contact = (profile.get("contact") or "").strip()
    phone = (profile.get("phone") or "").strip()
    if contact and phone:
        return f"{contact} {phone}"
    return contact or phone


def sync_delivery_from_profile(
    customer: str,
    profile: Dict[str, str] | None = None,
    *,
    only_if_empty: bool = True,
) -> bool:
    """将档案地址/联系人写入 customer_delivery.json；only_if_empty 时不覆盖已有送货信息。"""
    customer = (customer or "").strip()
    if not customer:
        return False
    profile = profile if profile is not None else get_profile(customer)
    if not is_delivery_enabled(profile):
        return False
    address = (profile.get("address") or "").strip()
    contact = (profile.get("contact") or "").strip()
    phone = (profile.get("phone") or "").strip()
    if not address and not contact and not phone:
        return False

    raw = get_raw_customer_delivery_info(customer)
    updated = {
        "receiver_company": (raw.get("receiver_company") or "").strip(),
        "receiver_address": (raw.get("receiver_address") or "").strip(),
        "receiver_contact": (raw.get("receiver_contact") or "").strip(),
        "receiver_phone": (raw.get("receiver_phone") or "").strip(),
        "doc_no_prefix": (raw.get("doc_no_prefix") or "").strip(),
    }
    if not updated["receiver_company"]:
        updated["receiver_company"] = customer

    changed = False
    if address:
        if only_if_empty:
            if not updated["receiver_address"]:
                updated["receiver_address"] = address
                changed = True
        elif updated["receiver_address"] != address:
            updated["receiver_address"] = address
            changed = True

    if contact:
        if only_if_empty:
            if not updated["receiver_contact"]:
                updated["receiver_contact"] = contact
                changed = True
        elif updated["receiver_contact"] != contact:
            updated["receiver_contact"] = contact
            changed = True

    if phone:
        if only_if_empty:
            if not updated["receiver_phone"]:
                updated["receiver_phone"] = phone
                changed = True
        elif updated["receiver_phone"] != phone:
            updated["receiver_phone"] = phone
            changed = True

    if changed:
        save_customer_delivery_info(customer, updated)
    return changed
