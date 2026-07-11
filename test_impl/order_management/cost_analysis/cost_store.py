"""成本录入记录 SQLite 持久化。"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from test_impl.order_management.order_entry.line_store import default_db_path

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
        process_prices={str(k): str(v) for k, v in processes.items()},
        material_cost=str(row["material_cost"] or "0"),
        process_total=str(row["process_total"] or "0"),
        unit_cost=str(row["unit_cost"] or "0"),
        quote_price=str(row["quote_price"] or "0"),
        created_at=str(row["created_at"] or ""),
        updated_at=str(row["updated_at"] or ""),
    )


class CostStore:
    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        path = str(db_path) if db_path is not None else str(default_db_path())
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def insert(self, data: dict) -> CostRecordRow:
        now = _utc_now()
        cur = self._conn.execute(
            """
            INSERT INTO cost_records (
                customer_name, product_name, mold_no, product_part_no, cavity,
                unit_weight_g, material, machine_tonnage, material_unit_price,
                process_prices_json, material_cost, process_total, unit_cost, quote_price,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            sql += " AND customer_name = ?"
            params.append(customer.strip())
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
        sql += " ORDER BY datetime(created_at) DESC, id DESC"
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_record(r) for r in rows]

    def find_latest_by_part_no(
        self,
        product_part_no: str,
        *,
        customer_name: str = "",
    ) -> Optional[CostRecordRow]:
        part_no = (product_part_no or "").strip()
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
        sql += " ORDER BY datetime(updated_at) DESC, id DESC LIMIT 1"
        row = self._conn.execute(sql, params).fetchone()
        return _row_to_record(row) if row else None

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

    def delete(self, record_id: int) -> None:
        cur = self._conn.execute("DELETE FROM cost_records WHERE id = ?", (record_id,))
        self._conn.commit()
        if cur.rowcount == 0:
            raise ValueError("成本记录不存在")
