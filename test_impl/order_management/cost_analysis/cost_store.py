"""成本录入记录 SQLite 持久化。"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from test_impl.order_management.order_entry.line_store import default_db_path

# Excel 未填产品料号时的占位显示（可导入，后续人工补录）
UNFILLED_PART_NO = "/"


def is_unfilled_part_no(part: str) -> bool:
    s = normalize_part_no(part)
    return s == UNFILLED_PART_NO


def normalize_part_no(part: str) -> str:
    """料号规范化：去空格、统一连字符（OCR/手工录入差异）。"""
    s = str(part or "").strip()
    for ch in (
        "\u2010",
        "\u2011",
        "\u2012",
        "\u2013",
        "\u2014",
        "\u2212",
        "\uff0d",
        "\u00ad",
        "\u2015",
    ):
        s = s.replace(ch, "-")
    return s.replace(" ", "")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS cost_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL DEFAULT '',
    product_name TEXT NOT NULL DEFAULT '',
    mold_no TEXT NOT NULL DEFAULT '',
    product_part_no TEXT NOT NULL DEFAULT '',
    cavity TEXT NOT NULL DEFAULT '',
    unit_weight_g TEXT NOT NULL DEFAULT '',
    material TEXT NOT NULL DEFAULT '',
    machine_tonnage TEXT NOT NULL DEFAULT '',
    material_unit_price TEXT NOT NULL DEFAULT '0',
    process_prices_json TEXT NOT NULL DEFAULT '{}',
    material_cost TEXT NOT NULL DEFAULT '0',
    process_total TEXT NOT NULL DEFAULT '0',
    unit_cost TEXT NOT NULL DEFAULT '0',
    quote_price TEXT NOT NULL DEFAULT '0',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_cost_records_customer ON cost_records(customer_name);
CREATE INDEX IF NOT EXISTS idx_cost_records_part ON cost_records(product_part_no);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CostRecordRow:
    id: int
    customer_name: str
    product_name: str
    mold_no: str
    product_part_no: str
    cavity: str
    unit_weight_g: str
    material: str
    machine_tonnage: str
    material_unit_price: str
    process_prices: dict
    material_cost: str
    process_total: str
    unit_cost: str
    quote_price: str
    created_at: str
    updated_at: str
    is_demo: bool = False


def _row_to_record(row: sqlite3.Row) -> CostRecordRow:
    try:
        processes = json.loads(row["process_prices_json"] or "{}")
        if not isinstance(processes, dict):
            processes = {}
    except json.JSONDecodeError:
        processes = {}
    return CostRecordRow(
        id=int(row["id"]),
        customer_name=str(row["customer_name"] or ""),
        product_name=str(row["product_name"] or ""),
        mold_no=str(row["mold_no"] or ""),
        product_part_no=str(row["product_part_no"] or ""),
        cavity=str(row["cavity"] or ""),
        unit_weight_g=str(row["unit_weight_g"] or ""),
        material=str(row["material"] or ""),
        machine_tonnage=str(row["machine_tonnage"] or ""),
        material_unit_price=str(row["material_unit_price"] or "0"),
        process_prices={str(k): v for k, v in processes.items()},
        material_cost=str(row["material_cost"] or "0"),
        process_total=str(row["process_total"] or "0"),
        unit_cost=str(row["unit_cost"] or "0"),
        quote_price=str(row["quote_price"] or "0"),
        created_at=str(row["created_at"] or ""),
        updated_at=str(row["updated_at"] or ""),
        is_demo=bool(row["is_demo"]) if "is_demo" in row.keys() else False,
    )


class CostStore:
    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        path = str(db_path) if db_path is not None else str(default_db_path())
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=60000")
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(_SCHEMA)
        cols = {r[1] for r in self._conn.execute("PRAGMA table_info(cost_records)")}
        if "is_demo" not in cols:
            self._conn.execute(
                "ALTER TABLE cost_records ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0"
            )
        self._conn.commit()
        self._migrate_process_catalog_v32()

    def _migrate_process_catalog_v32(self) -> None:
        """铝挤插入 32 后，旧 32–36 工艺编号顺延为 33–37（仅执行一次）。"""
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cost_schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            )
            """
        )
        row = self._conn.execute(
            "SELECT value FROM cost_schema_meta WHERE key = 'process_catalog_v32'"
        ).fetchone()
        if row and str(row[0]) == "1":
            return
        remap_dict = {"36": "37", "35": "36", "34": "35", "33": "34", "32": "33"}
        rows = self._conn.execute(
            "SELECT id, process_prices_json FROM cost_records"
        ).fetchall()
        for rec_id, raw_json in rows:
            try:
                data = json.loads(raw_json or "{}")
                if not isinstance(data, dict):
                    continue
            except json.JSONDecodeError:
                continue
            order = data.get("__order__")
            new_data: dict = {}
            for key, val in data.items():
                if key == "__order__":
                    continue
                new_data[remap_dict.get(str(key), str(key))] = val
            if isinstance(order, list):
                new_order = []
                for code in order:
                    s = str(code).strip()
                    mapped = remap_dict.get(s, s)
                    if mapped not in new_order:
                        new_order.append(mapped)
                new_data["__order__"] = new_order
            self._conn.execute(
                "UPDATE cost_records SET process_prices_json = ? WHERE id = ?",
                (json.dumps(new_data, ensure_ascii=False), rec_id),
            )
        self._conn.execute(
            """
            INSERT INTO cost_schema_meta(key, value) VALUES('process_catalog_v32', '1')
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """
        )
        self._conn.commit()

    def insert(self, data: dict) -> CostRecordRow:
        now = _utc_now()
        cur = self._conn.execute(
            """
            INSERT INTO cost_records (
                customer_name, product_name, mold_no, product_part_no, cavity,
                unit_weight_g, material, machine_tonnage, material_unit_price,
                process_prices_json, material_cost, process_total, unit_cost, quote_price,
                is_demo, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["customer_name"],
                data["product_name"],
                data["mold_no"],
                data["product_part_no"],
                data["cavity"],
                data["unit_weight_g"],
                data["material"],
                data["machine_tonnage"],
                data["material_unit_price"],
                data["process_prices_json"],
                data["material_cost"],
                data["process_total"],
                data["unit_cost"],
                data["quote_price"],
                1 if data.get("is_demo") else 0,
                now,
                now,
            ),
        )
        self._conn.commit()
        return self.get(int(cur.lastrowid))

    def get(self, record_id: int) -> CostRecordRow:
        row = self._conn.execute(
            "SELECT * FROM cost_records WHERE id = ?", (record_id,)
        ).fetchone()
        if row is None:
            raise ValueError("成本记录不存在")
        return _row_to_record(row)

    def list_records(
        self,
        *,
        q: str = "",
        customer: str = "",
        product_part_no: str = "",
    ) -> List[CostRecordRow]:
        sql = "SELECT * FROM cost_records WHERE 1=1"
        params: list = []
        if customer:
            sql += " AND customer_name LIKE ?"
            params.append(f"%{customer.strip()}%")
        if product_part_no:
            sql += " AND product_part_no LIKE ?"
            params.append(f"%{product_part_no.strip()}%")
        if q:
            kw = f"%{q.strip().lower()}%"
            sql += """ AND (
                LOWER(customer_name) LIKE ? OR LOWER(product_name) LIKE ?
                OR LOWER(product_part_no) LIKE ? OR LOWER(mold_no) LIKE ?
                OR LOWER(material) LIKE ?
            )"""
            params.extend([kw, kw, kw, kw, kw])
        sql += " ORDER BY updated_at DESC, id DESC"
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_record(r) for r in rows]

    def find_latest_by_part_no(
        self,
        product_part_no: str,
        *,
        customer_name: str = "",
    ) -> Optional[CostRecordRow]:
        part_no = normalize_part_no(product_part_no)
        if not part_no:
            return None
        sql = """
            SELECT * FROM cost_records
            WHERE LOWER(TRIM(product_part_no)) = LOWER(?)
        """
        params: list = [part_no]
        customer = (customer_name or "").strip()
        if customer:
            sql += " AND customer_name = ?"
            params.append(customer)
        sql += " ORDER BY updated_at DESC, id DESC LIMIT 1"
        row = self._conn.execute(sql, params).fetchone()
        if row:
            return _row_to_record(row)
        want = part_no.casefold()
        for raw in self._conn.execute(
            """
            SELECT * FROM cost_records
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall():
            if normalize_part_no(str(raw["product_part_no"] or "")).casefold() == want:
                return _row_to_record(raw)
        return None

    def find_latest_by_product_name(self, product_name: str) -> Optional[CostRecordRow]:
        name = (product_name or "").strip()
        if not name:
            return None
        row = self._conn.execute(
            """
            SELECT * FROM cost_records
            WHERE LOWER(TRIM(product_name)) = LOWER(?)
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """,
            (name,),
        ).fetchone()
        return _row_to_record(row) if row else None

    def search_part_numbers(self, q: str = "", limit: int = 20) -> List[dict]:
        """BOM 料号联想（仅 cost_records）。"""
        limit = max(1, min(int(limit), 50))
        q = (q or "").strip().lower()
        params: list = []
        sql = """
            SELECT product_part_no, customer_name, product_name, unit_weight_g, updated_at
            FROM cost_records
            WHERE TRIM(product_part_no) <> ''
        """
        if q:
            sql += """
                AND (
                    LOWER(product_part_no) LIKE ?
                    OR LOWER(product_name) LIKE ?
                    OR LOWER(customer_name) LIKE ?
                )
            """
            kw = f"%{q}%"
            params.extend([kw, kw, kw])
        sql += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit * 4)

        rows = self._conn.execute(sql, params).fetchall()
        results: List[dict] = []
        seen: set = set()
        for row in rows:
            part_no = str(row["product_part_no"] or "").strip()
            if not part_no:
                continue
            key = part_no.casefold()
            if key in seen:
                continue
            seen.add(key)
            results.append(
                {
                    "product_part_no": part_no,
                    "customer_name": str(row["customer_name"] or "").strip(),
                    "product_name": str(row["product_name"] or "").strip(),
                    "unit_weight_g": str(row["unit_weight_g"] or "").strip(),
                    "source": "bom",
                }
            )
            if len(results) >= limit:
                break
        return results

    def search_customers(self, q: str = "", limit: int = 20) -> List[str]:
        """BOM 客户名称联想（去重）。"""
        limit = max(1, min(int(limit), 50))
        kw = (q or "").strip().lower()
        sql = """
            SELECT DISTINCT customer_name FROM cost_records
            WHERE TRIM(customer_name) <> ''
        """
        params: list = []
        if kw:
            sql += " AND LOWER(customer_name) LIKE ?"
            params.append(f"%{kw}%")
        sql += " ORDER BY customer_name LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(sql, params).fetchall()
        return [str(r["customer_name"] or "").strip() for r in rows if str(r["customer_name"] or "").strip()]

    def get_part_binding(
        self,
        product_part_no: str,
        *,
        exclude_record_id: Optional[int] = None,
    ) -> Optional[dict]:
        from test_impl.order_management.customer_name import dedupe_customer_names

        part_no = normalize_part_no(product_part_no)
        if not part_no:
            return None

        sql = """
            SELECT DISTINCT customer_name FROM cost_records
            WHERE LOWER(TRIM(product_part_no)) = LOWER(?)
        """
        params: list = [part_no]
        if exclude_record_id is not None:
            sql += " AND id <> ?"
            params.append(int(exclude_record_id))
        customer_rows = self._conn.execute(sql, params).fetchall()
        customers = dedupe_customer_names(
            str(r["customer_name"] or "").strip()
            for r in customer_rows
            if str(r["customer_name"] or "").strip()
        )
        if not customers:
            row = self.find_latest_by_part_no(part_no)
            if row is None:
                return None
            return {
                "conflict": False,
                "product_part_no": part_no,
                "customer_name": str(row.customer_name or "").strip(),
                "product_name": str(row.product_name or "").strip(),
                "material": str(row.material or "").strip(),
                "unit_weight_g": str(row.unit_weight_g or "").strip(),
                "source": "bom",
            }
        if len(customers) > 1:
            return {
                "conflict": True,
                "product_part_no": part_no,
                "customers": customers,
            }

        row = self.find_latest_by_part_no(part_no)
        if row is None:
            return None
        return {
            "conflict": False,
            "product_part_no": part_no,
            "customer_name": str(row.customer_name or "").strip(),
            "product_name": str(row.product_name or "").strip(),
            "material": str(row.material or "").strip(),
            "unit_weight_g": str(row.unit_weight_g or "").strip(),
            "source": "bom",
        }

    def list_master_parts(self) -> List[dict]:
        rows = self._conn.execute(
            """
            SELECT product_part_no, product_name, customer_name, updated_at
            FROM cost_records
            WHERE TRIM(product_part_no) <> ''
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()
        out: List[dict] = []
        seen: set = set()
        for row in rows:
            part_no = str(row["product_part_no"] or "").strip()
            if not part_no:
                continue
            key = part_no.casefold()
            if key in seen:
                continue
            seen.add(key)
            product_name = str(row["product_name"] or "").strip()
            out.append(
                {
                    "product_spec": product_name or part_no,
                    "customer_part_no": part_no,
                    "customer_name": str(row["customer_name"] or "").strip(),
                }
            )
        out.sort(key=lambda item: (item["product_spec"].casefold(), item["customer_part_no"].casefold()))
        return out

    def update(self, record_id: int, data: dict) -> CostRecordRow:
        existing = self.get(record_id)
        now = _utc_now()
        self._conn.execute(
            """
            UPDATE cost_records SET
                customer_name = ?, product_name = ?, mold_no = ?, product_part_no = ?,
                cavity = ?, unit_weight_g = ?, material = ?, machine_tonnage = ?,
                material_unit_price = ?, process_prices_json = ?,
                material_cost = ?, process_total = ?, unit_cost = ?, quote_price = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                data["customer_name"],
                data["product_name"],
                data["mold_no"],
                data["product_part_no"],
                data["cavity"],
                data["unit_weight_g"],
                data["material"],
                data["machine_tonnage"],
                data["material_unit_price"],
                data["process_prices_json"],
                data["material_cost"],
                data["process_total"],
                data["unit_cost"],
                data["quote_price"],
                now,
                record_id,
            ),
        )
        self._conn.commit()
        return self.get(record_id)

    def list_ids_by_part_no(self, product_part_no: str) -> List[int]:
        """同料号所有 BOM 记录 id（最新 updated 在前）。"""
        part_no = normalize_part_no(product_part_no)
        if not part_no:
            return []
        rows = self._conn.execute(
            """
            SELECT id FROM cost_records
            WHERE LOWER(TRIM(product_part_no)) = LOWER(?)
            ORDER BY updated_at DESC, id DESC
            """,
            (part_no,),
        ).fetchall()
        return [int(r["id"]) for r in rows]

    def delete(self, record_id: int) -> None:
        cur = self._conn.execute("DELETE FROM cost_records WHERE id = ?", (record_id,))
        self._conn.commit()
        if cur.rowcount == 0:
            raise ValueError("成本记录不存在")
