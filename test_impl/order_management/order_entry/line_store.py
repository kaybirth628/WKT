"""订单行 SQLite 持久化（本地库 data/wkt_orders.db）。"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from test_impl.common.money import round_qty

from .line_models import CustomerMaster, OrderLine, PartMapping
from .shipment_models import SHIP_SOURCE_OPEN, ShipmentEvent

CLOSURE_FORCED = "forced"

_DEFAULT_DB = Path(__file__).resolve().parents[3] / "data" / "wkt_orders.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS parts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_spec TEXT NOT NULL UNIQUE,
    customer_part_no TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS order_lines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT NOT NULL,
    order_date TEXT NOT NULL DEFAULT '',
    delivery_date TEXT NOT NULL DEFAULT '',
    order_no TEXT NOT NULL,
    product_spec TEXT NOT NULL,
    customer_part_no TEXT NOT NULL DEFAULT '',
    unit_weight_g TEXT NOT NULL DEFAULT '0',
    material TEXT NOT NULL DEFAULT '',
    po_qty TEXT NOT NULL,
    shipped_qty TEXT NOT NULL DEFAULT '0',
    unit TEXT NOT NULL DEFAULT '',
    tax_rate TEXT NOT NULL DEFAULT '0',
    rmb_tax_incl_price TEXT NOT NULL DEFAULT '0',
    payment_terms TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lines_customer ON order_lines(customer);
CREATE INDEX IF NOT EXISTS idx_lines_order_date ON order_lines(order_date);
CREATE INDEX IF NOT EXISTS idx_lines_part_no ON order_lines(customer_part_no);
CREATE TABLE IF NOT EXISTS shipment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id INTEGER NOT NULL,
    ship_qty TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'open_ship',
    shipped_at TEXT NOT NULL,
    FOREIGN KEY (line_id) REFERENCES order_lines(id)
);
CREATE INDEX IF NOT EXISTS idx_shipment_line ON shipment_events(line_id);
CREATE INDEX IF NOT EXISTS idx_shipment_at ON shipment_events(shipped_at);
"""


def default_db_path() -> Path:
    env = os.environ.get("WKT_DB_PATH", "").strip()
    if env:
        return Path(env)
    return _DEFAULT_DB


class DuplicatePartNoError(ValueError):
    """料号已绑定其他客户。"""

    def __init__(self, part_no: str, owner_customer: str) -> None:
        self.part_no = part_no
        self.owner_customer = owner_customer
        super().__init__(f"料号「{part_no}」已绑定客户「{owner_customer}」，不能分配给其他客户")


def _meaningful_unit_weight(value: str) -> bool:
    raw = str(value or "").strip()
    if not raw:
        return False
    try:
        return float(raw) > 0
    except ValueError:
        return True


def _parse_dt(value: str) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def _row_to_line(row: sqlite3.Row) -> OrderLine:
    return OrderLine(
        id=int(row["id"]),
        customer=row["customer"],
        order_date=row["order_date"] or "",
        delivery_date=row["delivery_date"] or "",
        order_no=row["order_no"],
        product_spec=row["product_spec"],
        customer_part_no=row["customer_part_no"] or "",
        unit_weight_g=row["unit_weight_g"] or "0",
        material=row["material"] or "",
        po_qty=Decimal(row["po_qty"]),
        shipped_qty=Decimal(row["shipped_qty"] or "0"),
        unit=row["unit"] or "",
        tax_rate=Decimal(row["tax_rate"] or "0"),
        rmb_tax_incl_price=Decimal(row["rmb_tax_incl_price"] or "0"),
        payment_terms=row["payment_terms"] or "",
        created_at=_parse_dt(row["created_at"] if "created_at" in row.keys() else row["updated_at"]),
        updated_at=_parse_dt(row["updated_at"]),
        closure_type=str(row["closure_type"] or "") if "closure_type" in row.keys() else "",
    )


class LineStore:
    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        path = str(db_path) if db_path is not None else str(default_db_path())
        self.db_path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(_SCHEMA)
        self._migrate_schema()
        self._conn.commit()

    def _migrate_schema(self) -> None:
        cols = {r[1] for r in self._conn.execute("PRAGMA table_info(order_lines)")}
        if "created_at" not in cols:
            self._conn.execute(
                "ALTER TABLE order_lines ADD COLUMN created_at TEXT NOT NULL DEFAULT ''"
            )
            self._conn.execute(
                "UPDATE order_lines SET created_at = updated_at WHERE TRIM(created_at) = ''"
            )
        tables = {
            r[0]
            for r in self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "shipment_events" not in tables:
            self._conn.execute(
                """
                CREATE TABLE shipment_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    line_id INTEGER NOT NULL,
                    ship_qty TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'open_ship',
                    shipped_at TEXT NOT NULL,
                    FOREIGN KEY (line_id) REFERENCES order_lines(id)
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_shipment_line ON shipment_events(line_id)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_shipment_at ON shipment_events(shipped_at)"
            )
        ship_cols = {r[1] for r in self._conn.execute("PRAGMA table_info(shipment_events)")}
        if "delivery_note_json" not in ship_cols:
            self._conn.execute(
                "ALTER TABLE shipment_events ADD COLUMN delivery_note_json TEXT NOT NULL DEFAULT ''"
            )
        ship_cols = {r[1] for r in self._conn.execute("PRAGMA table_info(shipment_events)")}
        if "delivery_note_attachment" not in ship_cols:
            self._conn.execute(
                "ALTER TABLE shipment_events ADD COLUMN delivery_note_attachment TEXT NOT NULL DEFAULT ''"
            )
        line_cols = {r[1] for r in self._conn.execute("PRAGMA table_info(order_lines)")}
        if "closure_type" not in line_cols:
            self._conn.execute(
                "ALTER TABLE order_lines ADD COLUMN closure_type TEXT NOT NULL DEFAULT ''"
            )

    def close(self) -> None:
        self._conn.close()

    def count_lines(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS c FROM order_lines").fetchone()
        return int(row["c"])

    def list_customers(self) -> List[CustomerMaster]:
        rows = self._conn.execute("SELECT name FROM customers ORDER BY name COLLATE NOCASE").fetchall()
        return [CustomerMaster(name=r["name"]) for r in rows]

    def upsert_customer(self, name: str) -> CustomerMaster:
        name = (name or "").strip()
        self._conn.execute(
            "INSERT OR IGNORE INTO customers (name) VALUES (?)",
            (name,),
        )
        self._conn.commit()
        return CustomerMaster(name=name)

    def list_parts(self) -> List[PartMapping]:
        rows = self._conn.execute(
            "SELECT product_spec, customer_part_no FROM parts ORDER BY product_spec COLLATE NOCASE"
        ).fetchall()
        return [PartMapping(r["product_spec"], r["customer_part_no"] or "") for r in rows]

    def upsert_part(self, product_spec: str, customer_part_no: str) -> PartMapping:
        spec = (product_spec or "").strip()
        cpn = (customer_part_no or "").strip()
        existing = self._conn.execute(
            "SELECT id FROM parts WHERE product_spec = ?", (spec,)
        ).fetchone()
        if existing:
            self._conn.execute(
                "UPDATE parts SET customer_part_no = ? WHERE product_spec = ?",
                (cpn, spec),
            )
        else:
            self._conn.execute(
                "INSERT INTO parts (product_spec, customer_part_no) VALUES (?, ?)",
                (spec, cpn),
            )
        self._conn.commit()
        return PartMapping(spec, cpn)

    def lookup_part_no(self, product_spec: str) -> str:
        spec = (product_spec or "").strip()
        row = self._conn.execute(
            "SELECT customer_part_no FROM parts WHERE product_spec = ?", (spec,)
        ).fetchone()
        return row["customer_part_no"] if row else ""

    def insert_line(self, fields: dict) -> OrderLine:
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            """
            INSERT INTO order_lines (
                customer, order_date, delivery_date, order_no, product_spec,
                customer_part_no, unit_weight_g, material, po_qty, shipped_qty,
                unit, tax_rate, rmb_tax_incl_price, payment_terms, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                fields["customer"],
                fields.get("order_date", ""),
                fields.get("delivery_date", ""),
                fields["order_no"],
                fields["product_spec"],
                fields.get("customer_part_no", ""),
                str(fields.get("unit_weight_g", "0")),
                fields.get("material", ""),
                str(fields["po_qty"]),
                str(fields.get("shipped_qty", "0")),
                fields.get("unit", ""),
                str(fields.get("tax_rate", "0")),
                str(fields.get("rmb_tax_incl_price", "0")),
                fields.get("payment_terms", ""),
                now,
                now,
            ),
        )
        self._conn.commit()
        line_id = int(cur.lastrowid)
        row = self._conn.execute("SELECT * FROM order_lines WHERE id = ?", (line_id,)).fetchone()
        return _row_to_line(row)

    def update_shipped_qty(self, line_id: int, shipped_qty: str) -> OrderLine:
        """仅更新已出货数量（出货登记用，不做重复料号校验）。"""
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            "UPDATE order_lines SET shipped_qty=?, updated_at=? WHERE id=?",
            (str(shipped_qty), now, line_id),
        )
        self._conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"记录不存在: {line_id}")
        return self.get_line(line_id)

    def set_force_closed(self, line_id: int) -> OrderLine:
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            "UPDATE order_lines SET closure_type = ?, updated_at = ? WHERE id = ?",
            (CLOSURE_FORCED, now, line_id),
        )
        self._conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"记录不存在: {line_id}")
        return self.get_line(line_id)

    def update_line(self, line_id: int, fields: dict) -> OrderLine:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            UPDATE order_lines SET
                customer=?, order_date=?, delivery_date=?, order_no=?,
                product_spec=?, customer_part_no=?, unit_weight_g=?, material=?,
                po_qty=?, shipped_qty=?, unit=?, tax_rate=?,
                rmb_tax_incl_price=?, payment_terms=?, updated_at=?
            WHERE id=?
            """,
            (
                fields["customer"],
                fields.get("order_date", ""),
                fields.get("delivery_date", ""),
                fields["order_no"],
                fields["product_spec"],
                fields.get("customer_part_no", ""),
                str(fields.get("unit_weight_g", "0")),
                fields.get("material", ""),
                str(fields["po_qty"]),
                str(fields.get("shipped_qty", "0")),
                fields.get("unit", ""),
                str(fields.get("tax_rate", "0")),
                str(fields.get("rmb_tax_incl_price", "0")),
                fields.get("payment_terms", ""),
                now,
                line_id,
            ),
        )
        self._conn.commit()
        row = self._conn.execute("SELECT * FROM order_lines WHERE id = ?", (line_id,)).fetchone()
        if row is None:
            raise ValueError(f"记录不存在: {line_id}")
        return _row_to_line(row)

    def delete_line(self, line_id: int) -> None:
        cur = self._conn.execute("DELETE FROM order_lines WHERE id = ?", (line_id,))
        self._conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"记录不存在: {line_id}")

    def get_line(self, line_id: int) -> OrderLine:
        row = self._conn.execute("SELECT * FROM order_lines WHERE id = ?", (line_id,)).fetchone()
        if row is None:
            raise ValueError(f"记录不存在: {line_id}")
        return _row_to_line(row)

    def find_duplicate_line(
        self,
        customer: str,
        order_no: str,
        product_spec: str,
        exclude_id: Optional[int] = None,
    ) -> Optional[OrderLine]:
        customer = (customer or "").strip()
        order_no = (order_no or "").strip()
        product_spec = (product_spec or "").strip()
        if not customer or not order_no or not product_spec:
            return None
        sql = """
            SELECT * FROM order_lines
            WHERE customer = ? AND order_no = ? AND product_spec = ?
        """
        params: list = [customer, order_no, product_spec]
        if exclude_id is not None:
            sql += " AND id <> ?"
            params.append(exclude_id)
        sql += " ORDER BY id ASC LIMIT 1"
        row = self._conn.execute(sql, params).fetchone()
        return _row_to_line(row) if row else None

    def insert_shipment_event(
        self,
        line_id: int,
        ship_qty: str,
        source: str = SHIP_SOURCE_OPEN,
        shipped_at: Optional[str] = None,
        delivery_note_json: str = "",
    ) -> ShipmentEvent:
        now = shipped_at or datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            """
            INSERT INTO shipment_events (line_id, ship_qty, source, shipped_at, delivery_note_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                line_id,
                str(ship_qty),
                (source or SHIP_SOURCE_OPEN).strip(),
                now,
                delivery_note_json or "",
            ),
        )
        self._conn.commit()
        event_id = int(cur.lastrowid)
        rows = self.list_shipment_events()
        for ev in rows:
            if ev.id == event_id:
                return ev
        raise ValueError(f"出货记录写入失败: {event_id}")

    def _calendar_month_bounds_local(self, dt: datetime) -> tuple[datetime, datetime]:
        local = dt.astimezone() if dt.tzinfo else dt.replace(tzinfo=timezone.utc).astimezone()
        tz = local.tzinfo
        year, month = local.year, local.month
        start = datetime(year, month, 1, tzinfo=tz)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=tz)
        else:
            end = datetime(year, month + 1, 1, tzinfo=tz)
        return start, end

    def count_shipment_events_in_calendar_month(self, shipped_at: datetime) -> int:
        if not isinstance(shipped_at, datetime):
            shipped_at = _parse_dt(str(shipped_at))
        start, end = self._calendar_month_bounds_local(shipped_at)
        start_iso = start.astimezone(timezone.utc).isoformat()
        end_iso = end.astimezone(timezone.utc).isoformat()
        row = self._conn.execute(
            "SELECT COUNT(*) AS c FROM shipment_events WHERE shipped_at >= ? AND shipped_at < ?",
            (start_iso, end_iso),
        ).fetchone()
        return int(row["c"] or 0)

    def monthly_sequence_for_shipment(self, event_id: int, shipped_at: datetime) -> int:
        if not isinstance(shipped_at, datetime):
            shipped_at = _parse_dt(str(shipped_at))
        start, end = self._calendar_month_bounds_local(shipped_at)
        start_iso = start.astimezone(timezone.utc).isoformat()
        end_iso = end.astimezone(timezone.utc).isoformat()
        rows = self._conn.execute(
            "SELECT id FROM shipment_events WHERE shipped_at >= ? AND shipped_at < ? ORDER BY id ASC",
            (start_iso, end_iso),
        ).fetchall()
        for i, row in enumerate(rows, 1):
            if int(row["id"]) == event_id:
                return i
        return max(1, len(rows))

    def get_last_shipment_info_for_lines(self, line_ids: List[int]) -> Dict[int, tuple[str, str]]:
        if not line_ids:
            return {}
        placeholders = ",".join("?" * len(line_ids))
        rows = self._conn.execute(
            f"""
            SELECT se.line_id, se.shipped_at, se.delivery_note_json
            FROM shipment_events se
            INNER JOIN (
                SELECT line_id, MAX(id) AS max_id
                FROM shipment_events
                WHERE line_id IN ({placeholders})
                GROUP BY line_id
            ) t ON se.id = t.max_id
            """,
            line_ids,
        ).fetchall()
        out: Dict[int, tuple[str, str]] = {}
        for row in rows:
            doc_no = ""
            raw = str(row["delivery_note_json"] or "").strip()
            if raw:
                try:
                    data = json.loads(raw)
                    if isinstance(data, dict):
                        doc_no = str(data.get("doc_no", "") or "").strip()
                except json.JSONDecodeError:
                    pass
            line_id = int(row["line_id"])
            out[line_id] = (str(row["shipped_at"] or ""), doc_no)
        return out

    def save_shipment_delivery_note(self, event_id: int, delivery_note_json: str) -> None:
        self._conn.execute(
            "UPDATE shipment_events SET delivery_note_json = ? WHERE id = ?",
            (delivery_note_json or "", event_id),
        )
        self._conn.commit()

    def get_shipment_delivery_note_json(self, event_id: int) -> str:
        row = self._conn.execute(
            "SELECT delivery_note_json FROM shipment_events WHERE id = ?",
            (event_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"出货记录不存在: {event_id}")
        return str(row["delivery_note_json"] or "")

    def delete_shipment_event(self, event_id: int) -> None:
        cur = self._conn.execute("DELETE FROM shipment_events WHERE id = ?", (event_id,))
        self._conn.commit()
        if cur.rowcount == 0:
            raise ValueError(f"出货记录不存在: {event_id}")

    def save_shipment_attachment(self, event_id: int, rel_path: str) -> None:
        self._conn.execute(
            "UPDATE shipment_events SET delivery_note_attachment = ? WHERE id = ?",
            ((rel_path or "").strip(), event_id),
        )
        self._conn.commit()

    def save_shipment_attachment_batch(self, event_ids: List[int], rel_path: str) -> None:
        rel = (rel_path or "").strip()
        for eid in event_ids:
            if int(eid) > 0:
                self.save_shipment_attachment(int(eid), rel)

    def get_shipment_attachment(self, event_id: int) -> str:
        row = self._conn.execute(
            "SELECT delivery_note_attachment FROM shipment_events WHERE id = ?",
            (event_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"出货记录不存在: {event_id}")
        return str(row["delivery_note_attachment"] or "").strip()

    def get_shipment_event(self, event_id: int) -> ShipmentEvent:
        sql = """
            SELECT e.id, e.line_id, e.ship_qty, e.source, e.shipped_at,
                   l.customer, l.order_date, l.order_no, l.product_spec,
                   l.customer_part_no, l.po_qty, l.shipped_qty
            FROM shipment_events e
            INNER JOIN order_lines l ON l.id = e.line_id
            WHERE e.id = ?
        """
        row = self._conn.execute(sql, (event_id,)).fetchone()
        if row is None:
            raise ValueError(f"出货记录不存在: {event_id}")
        po = Decimal(row["po_qty"])
        sh = Decimal(row["shipped_qty"] or "0")
        return ShipmentEvent(
            id=int(row["id"]),
            line_id=int(row["line_id"]),
            ship_qty=Decimal(row["ship_qty"]),
            source=row["source"] or SHIP_SOURCE_OPEN,
            shipped_at=_parse_dt(row["shipped_at"]),
            customer=row["customer"] or "",
            order_date=row["order_date"] or "",
            order_no=row["order_no"] or "",
            product_spec=row["product_spec"] or "",
            customer_part_no=row["customer_part_no"] or "",
            po_qty=po,
            shipped_qty_after=sh,
            open_qty_after=round_qty(po - sh),
        )

    def list_shipment_events(self, q: str = "", customer: str = "") -> List[ShipmentEvent]:
        """出货明细：仅未结出货登记与历史导入，不含订单录入时的已出货字段。"""
        sql = """
            SELECT e.id, e.line_id, e.ship_qty, e.source, e.shipped_at,
                   e.delivery_note_json,
                   l.customer, l.order_date, l.order_no, l.product_spec,
                   l.customer_part_no, l.po_qty, l.shipped_qty
            FROM shipment_events e
            INNER JOIN order_lines l ON l.id = e.line_id
            WHERE 1=1
        """
        params: list = []
        if customer:
            sql += " AND l.customer = ?"
            params.append(customer)
        if q:
            kw = f"%{q.lower()}%"
            sql += """ AND (
                LOWER(l.customer) LIKE ? OR LOWER(l.order_no) LIKE ? OR
                LOWER(l.product_spec) LIKE ? OR LOWER(l.customer_part_no) LIKE ?
            )"""
            params.extend([kw] * 4)
        sql += " ORDER BY e.shipped_at DESC, e.id DESC"
        rows = self._conn.execute(sql, params).fetchall()
        out: List[ShipmentEvent] = []
        for r in rows:
            po = Decimal(r["po_qty"])
            sh = Decimal(r["shipped_qty"] or "0")
            out.append(
                ShipmentEvent(
                    id=int(r["id"]),
                    line_id=int(r["line_id"]),
                    ship_qty=Decimal(r["ship_qty"]),
                    source=r["source"] or SHIP_SOURCE_OPEN,
                    shipped_at=_parse_dt(r["shipped_at"]),
                    customer=r["customer"] or "",
                    order_date=r["order_date"] or "",
                    order_no=r["order_no"] or "",
                    product_spec=r["product_spec"] or "",
                    customer_part_no=r["customer_part_no"] or "",
                    po_qty=po,
                    shipped_qty_after=sh,
                    open_qty_after=round_qty(po - sh),
                    delivery_note_json=str(r["delivery_note_json"] or ""),
                )
            )
        return out

    def list_shipment_reconciliation_sources(
        self, q: str = "", customer: str = ""
    ) -> List[dict]:
        """对账：出货事件 + 订单行金额字段（排除强制结案料号）。"""
        sql = """
            SELECT e.id AS event_id, e.line_id, e.ship_qty, e.source, e.shipped_at,
                   e.delivery_note_json,
                   l.customer, l.order_date, l.order_no, l.product_spec,
                   l.customer_part_no, l.rmb_tax_incl_price, l.unit, l.tax_rate,
                   l.payment_terms, l.closure_type
            FROM shipment_events e
            INNER JOIN order_lines l ON l.id = e.line_id
            WHERE (l.closure_type IS NULL OR l.closure_type = '' OR l.closure_type <> 'forced')
        """
        params: list = []
        if customer:
            sql += " AND l.customer = ?"
            params.append(customer)
        if q:
            kw = f"%{q.lower()}%"
            sql += """ AND (
                LOWER(l.customer) LIKE ? OR LOWER(l.order_no) LIKE ? OR
                LOWER(l.product_spec) LIKE ? OR LOWER(l.customer_part_no) LIKE ?
            )"""
            params.extend([kw] * 4)
        sql += " ORDER BY e.shipped_at DESC, e.id DESC"
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def list_lines(self, q: str = "", customer: str = "", view: str = "all") -> List[OrderLine]:
        """view: all | open | closed(正常结案) | closed_forced(强制结案)"""
        v = (view or "all").strip().lower()
        if v == "shipped":
            return []

        not_forced = "(closure_type IS NULL OR closure_type = '' OR closure_type <> 'forced')"

        if v == "closed_forced":
            sql = f"SELECT * FROM order_lines WHERE closure_type = 'forced'"
            params: list = []
            if customer:
                sql += " AND customer = ?"
                params.append(customer)
            if q:
                kw = f"%{q.lower()}%"
                sql += """ AND (
                    LOWER(customer) LIKE ? OR LOWER(order_no) LIKE ? OR
                    LOWER(product_spec) LIKE ? OR LOWER(customer_part_no) LIKE ? OR
                    LOWER(material) LIKE ? OR LOWER(payment_terms) LIKE ?
                )"""
                params.extend([kw] * 6)
            sql += " ORDER BY updated_at DESC, id DESC"
            rows = self._conn.execute(sql, params).fetchall()
            return [_row_to_line(r) for r in rows]

        if v == "closed":
            sql = f"""
                SELECT l.* FROM order_lines l
                LEFT JOIN (
                    SELECT line_id, MAX(id) AS max_id
                    FROM shipment_events
                    GROUP BY line_id
                ) t ON t.line_id = l.id
                LEFT JOIN shipment_events se ON se.id = t.max_id
                WHERE ROUND(CAST(l.po_qty AS REAL) - CAST(l.shipped_qty AS REAL), 1) <= 0
                AND {not_forced.replace("closure_type", "l.closure_type")}
            """
            params: list = []
            if customer:
                sql += " AND l.customer = ?"
                params.append(customer)
            if q:
                kw = f"%{q.lower()}%"
                sql += """ AND (
                    LOWER(l.customer) LIKE ? OR LOWER(l.order_no) LIKE ? OR
                    LOWER(l.product_spec) LIKE ? OR LOWER(l.customer_part_no) LIKE ? OR
                    LOWER(l.material) LIKE ? OR LOWER(l.payment_terms) LIKE ?
                )"""
                params.extend([kw] * 6)
            sql += " ORDER BY COALESCE(se.shipped_at, l.created_at) DESC, l.id DESC"
            rows = self._conn.execute(sql, params).fetchall()
            return [_row_to_line(r) for r in rows]

        sql = "SELECT * FROM order_lines WHERE 1=1"
        params: list = []
        if v == "open":
            sql += f" AND ROUND(CAST(po_qty AS REAL) - CAST(shipped_qty AS REAL), 1) > 0 AND {not_forced}"
        if customer:
            sql += " AND customer = ?"
            params.append(customer)
        if q:
            kw = f"%{q.lower()}%"
            sql += """ AND (
                LOWER(customer) LIKE ? OR LOWER(order_no) LIKE ? OR
                LOWER(product_spec) LIKE ? OR LOWER(customer_part_no) LIKE ? OR
                LOWER(material) LIKE ? OR LOWER(payment_terms) LIKE ?
            )"""
            params.extend([kw] * 6)
        sql += " ORDER BY id DESC"
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_line(r) for r in rows]

    def distinct_customers_from_lines(self) -> List[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT customer FROM order_lines WHERE TRIM(customer) <> '' ORDER BY customer COLLATE NOCASE"
        ).fetchall()
        return [r["customer"] for r in rows]

    def search_part_numbers(self, q: str = "", limit: int = 20) -> List[dict]:
        """按料号模糊搜索订单行，用于成本录入联想。"""
        limit = max(1, min(int(limit), 50))
        q = (q or "").strip()
        params: list = []
        sql = """
            SELECT customer_part_no, customer, product_spec, unit_weight_g, updated_at
            FROM order_lines
            WHERE TRIM(customer_part_no) <> ''
        """
        if q:
            sql += " AND LOWER(customer_part_no) LIKE ?"
            params.append(f"%{q.lower()}%")
        sql += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit * 4)

        rows = self._conn.execute(sql, params).fetchall()
        results: List[dict] = []
        seen: set = set()
        for row in rows:
            part_no = str(row["customer_part_no"] or "").strip()
            customer = str(row["customer"] or "").strip()
            if not part_no:
                continue
            dedupe_key = part_no.casefold()
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            results.append(
                {
                    "product_part_no": part_no,
                    "customer_name": customer,
                    "product_name": str(row["product_spec"] or "").strip(),
                    "unit_weight_g": str(row["unit_weight_g"] or "").strip(),
                    "source": "order_line",
                }
            )
            if len(results) >= limit:
                break
        return results

    def get_part_no_binding(
        self,
        product_part_no: str,
        *,
        exclude_line_id: Optional[int] = None,
    ) -> Optional[dict]:
        """返回料号绑定的唯一客户及最新订单行信息。"""
        part_no = (product_part_no or "").strip()
        if not part_no:
            return None

        sql = """
            SELECT DISTINCT customer FROM order_lines
            WHERE LOWER(TRIM(customer_part_no)) = LOWER(?)
        """
        params: list = [part_no]
        if exclude_line_id is not None:
            sql += " AND id <> ?"
            params.append(int(exclude_line_id))
        customer_rows = self._conn.execute(sql, params).fetchall()
        customers = [str(r["customer"] or "").strip() for r in customer_rows if str(r["customer"] or "").strip()]
        if not customers:
            return None
        if len(customers) > 1:
            return {
                "conflict": True,
                "product_part_no": part_no,
                "customers": customers,
            }

        row = self._conn.execute(
            """
            SELECT customer, product_spec, unit_weight_g, material, updated_at, id
            FROM order_lines
            WHERE LOWER(TRIM(customer_part_no)) = LOWER(?)
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """,
            (part_no,),
        ).fetchone()
        if row is None:
            return None
        return {
            "conflict": False,
            "product_part_no": part_no,
            "customer_name": str(row["customer"] or "").strip(),
            "product_name": str(row["product_spec"] or "").strip(),
            "unit_weight_g": self.find_unit_weight_by_part_no(part_no),
            "material": str(row["material"] or "").strip(),
            "source": "order_line",
        }

    def find_unit_weight_by_part_no(self, product_part_no: str) -> str:
        """取该料号在订单中最近一条有效单重（忽略空值与 0）。"""
        part_no = (product_part_no or "").strip()
        if not part_no:
            return ""
        rows = self._conn.execute(
            """
            SELECT unit_weight_g
            FROM order_lines
            WHERE LOWER(TRIM(customer_part_no)) = LOWER(?)
            ORDER BY updated_at DESC, id DESC
            """,
            (part_no,),
        ).fetchall()
        for row in rows:
            weight = str(row["unit_weight_g"] or "").strip()
            if _meaningful_unit_weight(weight):
                return weight
        return ""

    def validate_part_no_assignment(
        self,
        product_part_no: str,
        customer: str,
        *,
        exclude_line_id: Optional[int] = None,
    ) -> None:
        part_no = (product_part_no or "").strip()
        cust = (customer or "").strip()
        if not part_no:
            return
        binding = self.get_part_no_binding(part_no, exclude_line_id=exclude_line_id)
        if binding is None:
            return
        if binding.get("conflict"):
            joined = "、".join(binding.get("customers") or [])
            raise ValueError(f"料号「{part_no}」在订单中存在多个客户（{joined}），请先修正数据")
        owner = str(binding.get("customer_name") or "").strip()
        if owner and owner.casefold() != cust.casefold():
            raise DuplicatePartNoError(part_no, owner)

    def find_order_by_part_no(self, product_part_no: str) -> Optional[dict]:
        binding = self.get_part_no_binding(product_part_no)
        if binding is None or binding.get("conflict"):
            return None
        return binding

    @staticmethod
    def reset_database(db_path: Optional[str | Path] = None) -> Path:
        """删除库文件并重建空库。"""
        path = Path(db_path) if db_path is not None else default_db_path()
        if str(path) == ":memory:":
            raise ValueError("不能重置内存库")
        if path.exists():
            path.unlink()
        store = LineStore(path)
        store.close()
        return path
