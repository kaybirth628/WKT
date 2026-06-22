"""跨 SQLite 与 JSON 配置的数据映射汇总（只读）。"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

from test_impl.order_management.customer_profile.store import load_all_profiles
from test_impl.order_management.delivery_note.wkt_document import load_customer_delivery_config
from test_impl.order_management.order_entry.line_store import default_db_path

ROOT = Path(__file__).resolve().parents[3]
PROFILE_FIELDS = ("address", "contact", "phone", "email", "payment_terms", "reconciliation_cycle")
DELIVERY_FIELDS = ("receiver_company", "receiver_address", "receiver_contact", "doc_no_prefix")


def _count_filled(row: dict, fields: tuple[str, ...]) -> int:
    return sum(1 for k in fields if str(row.get(k) or "").strip())


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


class DataMappingService:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or default_db_path())

    def build_report(self) -> Dict[str, Any]:
        profiles = load_all_profiles()
        delivery_cfg = load_customer_delivery_config()
        wkt_company = _load_json(ROOT / "data" / "delivery_templates" / "wkt_company.json")
        reconcile_cfg = _load_json(ROOT / "data" / "reconciliation_config.json")

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            table_counts = self._table_counts(conn)
            master_customers = self._column_list(conn, "SELECT name FROM customers ORDER BY name")
            order_by_customer = self._count_map(
                conn, "SELECT customer, COUNT(*) AS c FROM order_lines GROUP BY customer"
            )
            ship_by_customer = self._count_map(
                conn,
                """
                SELECT l.customer, COUNT(*) AS c
                FROM shipment_events e
                INNER JOIN order_lines l ON l.id = e.line_id
                GROUP BY l.customer
                """,
            )
            parts_rows = conn.execute(
                "SELECT product_spec, customer_part_no FROM parts ORDER BY product_spec"
            ).fetchall()
            spec_line_counts = self._count_map(
                conn,
                "SELECT product_spec, COUNT(*) AS c FROM order_lines GROUP BY product_spec",
            )
            specs_without_master = conn.execute(
                """
                SELECT DISTINCT product_spec FROM order_lines
                WHERE TRIM(product_spec) != ''
                  AND product_spec NOT IN (SELECT product_spec FROM parts)
                ORDER BY product_spec
                """
            ).fetchall()
        finally:
            conn.close()

        all_customers: Set[str] = set()
        all_customers.update(master_customers)
        all_customers.update(order_by_customer.keys())
        all_customers.update(profiles.keys())
        all_customers.update(delivery_cfg.keys())

        customer_matrix: List[Dict[str, Any]] = []
        complete = partial = profile_only = delivery_only = 0

        for name in sorted(all_customers, key=lambda x: (x.casefold(), x)):
            if not name:
                continue
            in_master = name in master_customers
            order_lines = int(order_by_customer.get(name, 0))
            shipments = int(ship_by_customer.get(name, 0))
            profile = profiles.get(name, {})
            delivery = delivery_cfg.get(name, {})
            profile_filled = _count_filled(profile, PROFILE_FIELDS)
            delivery_filled = _count_filled(delivery, DELIVERY_FIELDS)
            has_profile = profile_filled > 0
            has_delivery = delivery_filled > 0
            has_orders = order_lines > 0

            issues: List[str] = []
            if has_orders and not has_profile:
                issues.append("有订单但缺客户档案")
            if has_orders and not has_delivery:
                issues.append("有订单但缺送货单配置")
            if has_profile and not has_orders:
                issues.append("有档案但无订单")
            if has_delivery and not has_orders:
                issues.append("有送货单配置但无订单")
            if not in_master and has_orders:
                issues.append("有订单但未在 customers 主数据表")

            if has_orders and has_profile and has_delivery:
                status = "complete"
                complete += 1
            elif has_orders:
                status = "partial"
                partial += 1
            elif has_profile and not has_delivery:
                status = "profile_only"
                profile_only += 1
            elif has_delivery:
                status = "delivery_only"
                delivery_only += 1
            else:
                status = "master_only"

            customer_matrix.append(
                {
                    "customer": name,
                    "in_master": in_master,
                    "order_lines": order_lines,
                    "shipments": shipments,
                    "has_profile": has_profile,
                    "profile_filled": profile_filled,
                    "profile_total": len(PROFILE_FIELDS),
                    "has_delivery": has_delivery,
                    "delivery_filled": delivery_filled,
                    "delivery_total": len(DELIVERY_FIELDS),
                    "status": status,
                    "issues": issues,
                }
            )

        order_customer_set = set(order_by_customer.keys())
        orphan_profiles = sorted(set(profiles.keys()) - order_customer_set)
        orphan_delivery = sorted(set(delivery_cfg.keys()) - order_customer_set)
        missing_profiles = sorted(
            n for n in order_customer_set if _count_filled(profiles.get(n, {}), PROFILE_FIELDS) == 0
        )
        missing_delivery = sorted(
            n for n in order_customer_set if _count_filled(delivery_cfg.get(n, {}), DELIVERY_FIELDS) == 0
        )

        parts_matrix = [
            {
                "product_spec": str(r["product_spec"]),
                "customer_part_no": str(r["customer_part_no"] or ""),
                "order_line_refs": int(spec_line_counts.get(str(r["product_spec"]), 0)),
                "in_master": True,
            }
            for r in parts_rows
        ]
        for row in specs_without_master:
            spec = str(row["product_spec"])
            parts_matrix.append(
                {
                    "product_spec": spec,
                    "customer_part_no": "",
                    "order_line_refs": int(spec_line_counts.get(spec, 0)),
                    "in_master": False,
                }
            )
        parts_matrix.sort(key=lambda x: (-x["order_line_refs"], x["product_spec"].casefold()))

        json_files = [
            {
                "id": "customer_profiles",
                "label": "客户档案",
                "path": "data/customer_profiles.json",
                "key_count": len(profiles),
                "exists": (ROOT / "data" / "customer_profiles.json").is_file(),
            },
            {
                "id": "customer_delivery",
                "label": "送货单收货",
                "path": "data/delivery_templates/customer_delivery.json",
                "key_count": len(delivery_cfg),
                "exists": (ROOT / "data" / "delivery_templates" / "customer_delivery.json").is_file(),
            },
            {
                "id": "wkt_company",
                "label": "威可特抬头",
                "path": "data/delivery_templates/wkt_company.json",
                "key_count": len(wkt_company),
                "exists": (ROOT / "data" / "delivery_templates" / "wkt_company.json").is_file(),
            },
            {
                "id": "reconciliation_config",
                "label": "对账规则",
                "path": "data/reconciliation_config.json",
                "key_count": len(reconcile_cfg),
                "exists": (ROOT / "data" / "reconciliation_config.json").is_file(),
            },
        ]

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "db_path": str(self.db_path),
            "stats": table_counts,
            "json_files": json_files,
            "global_config": {
                "wkt_company_filled": _count_filled(
                    wkt_company,
                    ("supplier_name", "supplier_address", "supplier_phone", "footer_note", "doc_no_prefix"),
                ),
                "reconciliation_terms": str(reconcile_cfg.get("terms_label") or reconcile_cfg.get("description") or ""),
            },
            "customer_matrix": customer_matrix,
            "orphan_keys": {
                "profiles_without_orders": orphan_profiles,
                "delivery_without_orders": orphan_delivery,
            },
            "gaps": {
                "orders_missing_profile": missing_profiles,
                "orders_missing_delivery": missing_delivery,
                "specs_not_in_parts_master": [str(r["product_spec"]) for r in specs_without_master],
            },
            "parts_matrix": parts_matrix,
            "summary": {
                "customers_total": len(customer_matrix),
                "customers_with_orders": len(order_customer_set),
                "customers_complete": complete,
                "customers_partial": partial,
                "customers_profile_only": profile_only,
                "customers_delivery_only": delivery_only,
                "orphan_profile_keys": len(orphan_profiles),
                "orphan_delivery_keys": len(orphan_delivery),
                "parts_master_count": len(parts_rows),
                "specs_only_in_orders": len(specs_without_master),
            },
            "join_key": "客户名称（order_lines.customer = customers.name = JSON 键名）",
        }

    @staticmethod
    def _table_counts(conn: sqlite3.Connection) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for table in ("customers", "parts", "order_lines", "shipment_events"):
            row = conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()
            out[table] = int(row["c"])
        return out

    @staticmethod
    def _column_list(conn: sqlite3.Connection, sql: str) -> List[str]:
        return [str(r[0]).strip() for r in conn.execute(sql).fetchall() if str(r[0]).strip()]

    @staticmethod
    def _count_map(conn: sqlite3.Connection, sql: str) -> Dict[str, int]:
        return {str(r[0]): int(r[1]) for r in conn.execute(sql).fetchall()}
