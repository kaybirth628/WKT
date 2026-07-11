from __future__ import annotations

from typing import Any, Dict, List

from .store import EMPTY_PROFILE, delete_profile, get_profile, list_profile_suppliers, save_profile
from .store import profile_with_labels as _profile_with_labels


class SupplierProfileService:
    def _supplier_names(self) -> List[str]:
        return list_profile_suppliers()

    def list_rows(self) -> List[Dict[str, Any]]:
        rows = []
        for name in self._supplier_names():
            info = get_profile(name)
            rows.append({"supplier": name, **_profile_with_labels(info)})
        return rows

    def get(self, supplier: str) -> Dict[str, str]:
        return get_profile(supplier)

    def save(self, supplier: str, info: dict) -> Dict[str, str]:
        return save_profile(supplier, info)

    def create(self, supplier: str, info: dict) -> Dict[str, str]:
        supplier = (supplier or "").strip()
        if not supplier:
            raise ValueError("供应商名称不能为空")
        existing = {n.casefold(): n for n in self._supplier_names()}
        if supplier.casefold() in existing:
            dup = existing[supplier.casefold()]
            raise ValueError(f"供应商「{dup}」已存在")
        return self.save(supplier, info)

    def delete(self, supplier: str) -> None:
        delete_profile(supplier)

    def empty_profile(self) -> Dict[str, str]:
        return dict(EMPTY_PROFILE)
