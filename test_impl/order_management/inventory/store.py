"""库存：成品/半成品余额与出入库流水。"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from test_impl.common.money import round_qty, to_decimal
from test_impl.order_management.order_entry.line_store import default_db_path

STATUS_INHOUSE = "inhouse"
STATUS_OUTSOURCE = "outsource"
STATUS_FINISHED = "finished"
STATUS_REPAIR = "repair"
PROCESS_FINISHED = "FIN"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS inventory_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_part_no TEXT NOT NULL,
    process_code TEXT NOT NULL,
    status TEXT NOT NULL,
    supplier_name TEXT NOT NULL DEFAULT '',
    qty TEXT NOT NULL DEFAULT '0',
    updated_at TEXT NOT NULL DEFAULT ''
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_inv_balances_bucket
    ON inventory_balances(product_part_no, process_code, status, supplier_name);

CREATE TABLE IF NOT EXISTS inventory_movements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_part_no TEXT NOT NULL,
    action_type TEXT NOT NULL,
    process_code TEXT NOT NULL DEFAULT '',
    from_process_code TEXT NOT NULL DEFAULT '',
    from_status TEXT NOT NULL DEFAULT '',
    from_supplier TEXT NOT NULL DEFAULT '',
    to_process_code TEXT NOT NULL DEFAULT '',
    to_status TEXT NOT NULL DEFAULT '',
    to_supplier TEXT NOT NULL DEFAULT '',
    qty TEXT NOT NULL,
    doc_no TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_inv_movements_part ON inventory_movements(product_part_no);
CREATE INDEX IF NOT EXISTS idx_inv_movements_created ON inventory_movements(created_at);

CREATE TABLE IF NOT EXISTS inventory_part_tags (
    product_part_no TEXT PRIMARY KEY,
    is_demo INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS production_replenish_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_no TEXT NOT NULL UNIQUE,
    product_part_no TEXT NOT NULL,
    qty TEXT NOT NULL,
    sales_order_no TEXT NOT NULL DEFAULT '',
    line_id INTEGER,
    status TEXT NOT NULL DEFAULT 'open',
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_replenish_part ON production_replenish_orders(product_part_no);
CREATE INDEX IF NOT EXISTS idx_replenish_created ON production_replenish_orders(created_at);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class InventoryStore:
    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        path = str(db_path) if db_path is not None else str(default_db_path())
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=60000")
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._backfill_demo_tags()

    def _backfill_demo_tags(self) -> None:
        """把已有演示流水/演示料号标成测（只补缺，不覆盖已标实）。"""
        now = _utc_now()
        self._conn.execute(
            """
            INSERT OR IGNORE INTO inventory_part_tags (product_part_no, is_demo, updated_at)
            SELECT DISTINCT product_part_no, 1, ?
            FROM inventory_movements
            WHERE action_type = 'demo_inject'
               OR note LIKE '%演示%'
               OR note LIKE '%看板演示%'
               OR doc_no LIKE 'DEMO-%'
            """,
            (now,),
        )
        self._conn.execute(
            """
            INSERT OR IGNORE INTO inventory_part_tags (product_part_no, is_demo, updated_at)
            SELECT DISTINCT product_part_no, 1, ?
            FROM inventory_balances
            WHERE product_part_no LIKE 'PLAN-%'
               OR product_part_no LIKE 'BOARD-DEMO-%'
            """,
            (now,),
        )
        try:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO inventory_part_tags (product_part_no, is_demo, updated_at)
                SELECT DISTINCT product_part_no, 1, ?
                FROM cost_records
                WHERE TRIM(IFNULL(product_part_no, '')) != ''
                  AND (
                    customer_name LIKE '%演示%'
                    OR product_name LIKE '%演示%'
                    OR product_name LIKE '%看板演示%'
                  )
                """,
                (now,),
            )
        except sqlite3.OperationalError:
            pass
        self._conn.commit()

    def set_part_demo(self, product_part_no: str, is_demo: bool = True) -> None:
        part = (product_part_no or "").strip()
        if not part:
            return
        now = _utc_now()
        self._conn.execute(
            """
            INSERT INTO inventory_part_tags (product_part_no, is_demo, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(product_part_no) DO UPDATE SET
                is_demo = excluded.is_demo,
                updated_at = excluded.updated_at
            """,
            (part, 1 if is_demo else 0, now),
        )
        self._conn.commit()

    def is_part_demo(self, product_part_no: str) -> bool:
        part = (product_part_no or "").strip()
        if not part:
            return False
        row = self._conn.execute(
            "SELECT is_demo FROM inventory_part_tags WHERE LOWER(TRIM(product_part_no)) = LOWER(?)",
            (part,),
        ).fetchone()
        return bool(row and int(row["is_demo"] or 0) == 1)

    def close(self) -> None:
        self._conn.close()

    def get_qty(
        self,
        product_part_no: str,
        process_code: str,
        status: str,
        supplier_name: str = "",
    ) -> Decimal:
        row = self._conn.execute(
            """
            SELECT qty FROM inventory_balances
            WHERE LOWER(TRIM(product_part_no)) = LOWER(?)
              AND process_code = ?
              AND status = ?
              AND supplier_name = ?
            """,
            (
                product_part_no.strip(),
                process_code.strip(),
                status.strip(),
                (supplier_name or "").strip(),
            ),
        ).fetchone()
        return to_decimal(row["qty"]) if row else Decimal("0")

    def list_balances(self, *, product_part_no: str = "") -> List[dict]:
        sql = """
            SELECT product_part_no, process_code, status, supplier_name, qty, updated_at
            FROM inventory_balances
            WHERE CAST(qty AS REAL) > 0
        """
        params: list = []
        if product_part_no.strip():
            sql += " AND LOWER(TRIM(product_part_no)) = LOWER(?)"
            params.append(product_part_no.strip())
        sql += " ORDER BY product_part_no, process_code, status, supplier_name"
        return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def list_movements(
        self, *, product_part_no: str = "", on_date: str = "", limit: int = 200
    ) -> List[dict]:
        sql = "SELECT * FROM inventory_movements WHERE 1=1"
        params: list = []
        if product_part_no.strip():
            sql += " AND LOWER(TRIM(product_part_no)) = LOWER(?)"
            params.append(product_part_no.strip())
        day = on_date.strip()
        if day:
            # created_at 为 UTC ISO；按本机时区日历日筛选「当天」
            sql += " AND date(created_at, 'localtime') = date(?)"
            params.append(day)
        sql += " ORDER BY datetime(created_at) DESC, id DESC LIMIT ?"
        params.append(int(limit))
        return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def list_movements_chronological(self, *, product_part_no: str) -> List[dict]:
        part = (product_part_no or "").strip()
        if not part:
            return []
        sql = """
            SELECT * FROM inventory_movements
            WHERE LOWER(TRIM(product_part_no)) = LOWER(?)
            ORDER BY datetime(created_at) ASC, id ASC
        """
        return [dict(r) for r in self._conn.execute(sql, (part,)).fetchall()]

    def distinct_movement_parts(self) -> List[str]:
        rows = self._conn.execute(
            """
            SELECT DISTINCT TRIM(product_part_no) AS part
            FROM inventory_movements
            WHERE TRIM(product_part_no) != ''
            ORDER BY part
            """
        ).fetchall()
        return [str(r["part"]) for r in rows if r["part"]]

    def update_movement_note(self, movement_id: int, note: str) -> None:
        self._conn.execute(
            "UPDATE inventory_movements SET note = ? WHERE id = ?",
            (str(note or "").strip(), int(movement_id)),
        )
        self._conn.commit()

    def get_movement(self, movement_id: int) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM inventory_movements WHERE id = ?",
            (int(movement_id),),
        ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def deltas_from_movement(row: dict) -> List[tuple[str, str, str, Decimal]]:
        """从流水记录还原库存桶变动（process, status, supplier, delta）。"""
        qty = round_qty(row.get("qty"))
        from_code = str(row.get("from_process_code") or "").strip()
        from_status = str(row.get("from_status") or "").strip()
        from_supplier = str(row.get("from_supplier") or "").strip()
        to_code = str(row.get("to_process_code") or "").strip()
        to_status = str(row.get("to_status") or "").strip()
        to_supplier = str(row.get("to_supplier") or "").strip()
        deltas: list[tuple[str, str, str, Decimal]] = []
        if from_code and from_status:
            deltas.append((from_code, from_status, from_supplier, -qty))
        if to_code and to_status:
            deltas.append((to_code, to_status, to_supplier, qty))
        return deltas

    def correct_movement(self, movement_id: int, *, new_qty: Decimal, new_note: str) -> dict:
        row = self.get_movement(movement_id)
        if not row:
            raise ValueError("出入库流水不存在")
        old_qty = round_qty(row.get("qty"))
        qty = round_qty(new_qty)
        if qty <= 0:
            raise ValueError("数量必须大于 0")
        note = str(new_note or "").strip()
        now = _utc_now()
        part = str(row.get("product_part_no") or "").strip()
        cur = self._conn.cursor()
        try:
            if old_qty != qty:
                for code, status, supplier, delta in self.deltas_from_movement(row):
                    self.apply_delta(
                        product_part_no=part,
                        process_code=code,
                        status=status,
                        supplier_name=supplier,
                        delta=-delta,
                        now=now,
                        cur=cur,
                    )
                patched = dict(row)
                patched["qty"] = str(qty)
                for code, status, supplier, delta in self.deltas_from_movement(patched):
                    self.apply_delta(
                        product_part_no=part,
                        process_code=code,
                        status=status,
                        supplier_name=supplier,
                        delta=delta,
                        now=now,
                        cur=cur,
                    )
                cur.execute(
                    "UPDATE inventory_movements SET qty = ?, note = ? WHERE id = ?",
                    (str(qty), note, int(movement_id)),
                )
            else:
                cur.execute(
                    "UPDATE inventory_movements SET note = ? WHERE id = ?",
                    (note, int(movement_id)),
                )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        updated = self.get_movement(movement_id)
        if updated is None:
            raise ValueError("出入库流水不存在")
        return updated

    def apply_delta(
        self,
        *,
        product_part_no: str,
        process_code: str,
        status: str,
        supplier_name: str,
        delta: Decimal,
        now: str,
        cur: Optional[sqlite3.Cursor] = None,
    ) -> None:
        cursor = cur or self._conn.cursor()
        part = product_part_no.strip()
        code = process_code.strip()
        st = status.strip()
        supplier = (supplier_name or "").strip()
        current = self.get_qty(part, code, st, supplier)
        new_qty = round_qty(current + delta)
        if new_qty < 0:
            label = f"{code}/{st}"
            if supplier:
                label += f"/{supplier}"
            raise ValueError(f"库存不足：{part} 在「{label}」仅有 {current}，无法变动 {delta}")
        row = cursor.execute(
            """
            SELECT id FROM inventory_balances
            WHERE LOWER(TRIM(product_part_no)) = LOWER(?)
              AND process_code = ? AND status = ? AND supplier_name = ?
            """,
            (part, code, st, supplier),
        ).fetchone()
        if new_qty == 0:
            if row is not None:
                cursor.execute("DELETE FROM inventory_balances WHERE id = ?", (int(row["id"]),))
            return
        if row is None:
            cursor.execute(
                """
                INSERT INTO inventory_balances (
                    product_part_no, process_code, status, supplier_name, qty, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (part, code, st, supplier, str(new_qty), now),
            )
        else:
            cursor.execute(
                "UPDATE inventory_balances SET qty = ?, updated_at = ? WHERE id = ?",
                (str(new_qty), now, int(row["id"])),
            )

    def record_movement(
        self,
        *,
        product_part_no: str,
        action_type: str,
        qty: Decimal,
        process_code: str = "",
        from_process_code: str = "",
        from_status: str = "",
        from_supplier: str = "",
        to_process_code: str = "",
        to_status: str = "",
        to_supplier: str = "",
        doc_no: str = "",
        note: str = "",
        deltas: list[tuple[str, str, str, str, Decimal]],
    ) -> dict:
        """deltas: list of (process_code, status, supplier, delta)."""
        part = product_part_no.strip()
        amount = round_qty(qty)
        if amount <= 0:
            raise ValueError("数量必须大于 0")
        now = _utc_now()
        cur = self._conn.cursor()
        try:
            for code, status, supplier, delta in deltas:
                self.apply_delta(
                    product_part_no=part,
                    process_code=code,
                    status=status,
                    supplier_name=supplier,
                    delta=delta,
                    now=now,
                    cur=cur,
                )
            cur.execute(
                """
                INSERT INTO inventory_movements (
                    product_part_no, action_type, process_code,
                    from_process_code, from_status, from_supplier,
                    to_process_code, to_status, to_supplier,
                    qty, doc_no, note, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    part,
                    action_type,
                    process_code,
                    from_process_code,
                    from_status,
                    (from_supplier or "").strip(),
                    to_process_code,
                    to_status,
                    (to_supplier or "").strip(),
                    str(amount),
                    (doc_no or "").strip(),
                    (note or "").strip(),
                    now,
                ),
            )
            mov_id = int(cur.lastrowid)
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        return {
            "id": mov_id,
            "product_part_no": part,
            "action_type": action_type,
            "process_code": process_code,
            "from_process_code": from_process_code,
            "from_status": from_status,
            "from_supplier": (from_supplier or "").strip(),
            "to_process_code": to_process_code,
            "to_status": to_status,
            "to_supplier": (to_supplier or "").strip(),
            "qty": str(amount),
            "doc_no": doc_no,
            "note": (note or "").strip(),
            "created_at": now,
        }

    def next_movement_doc_no(self, action_prefix: str = "", day: Optional[str] = None) -> str:
        """WKT+YYYYMMDD+三位序号，如 WKT20260729001（当日递增）。"""
        _ = action_prefix  # 历史参数保留，统一 WKT 前缀
        stamp = day or datetime.now().strftime("%Y%m%d")
        head = f"WKT{stamp}"
        row = self._conn.execute(
            """
            SELECT doc_no FROM inventory_movements
            WHERE doc_no LIKE ?
            ORDER BY id DESC LIMIT 1
            """,
            (f"{head}%",),
        ).fetchone()
        seq = 0
        if row and row["doc_no"]:
            tail = str(row["doc_no"])[len(head) :]
            try:
                seq = int(tail)
            except ValueError:
                pass
        return f"{head}{seq + 1:03d}"

    def next_replenish_doc_no(self, day: Optional[str] = None) -> str:
        """BC-YYYYMMDD-序号（当日递增）。"""
        stamp = day or datetime.now().strftime("%Y%m%d")
        prefix = f"BC-{stamp}-"
        row = self._conn.execute(
            """
            SELECT doc_no FROM production_replenish_orders
            WHERE doc_no LIKE ?
            ORDER BY id DESC LIMIT 1
            """,
            (prefix + "%",),
        ).fetchone()
        seq = 1
        if row and row["doc_no"]:
            tail = str(row["doc_no"]).rsplit("-", 1)[-1]
            try:
                seq = int(tail) + 1
            except ValueError:
                seq = 1
        return f"{prefix}{seq:03d}"

    def insert_replenish(
        self,
        *,
        doc_no: str,
        product_part_no: str,
        qty: str,
        sales_order_no: str = "",
        line_id: Optional[int] = None,
        note: str = "",
        status: str = "open",
    ) -> dict:
        now = _utc_now()
        cur = self._conn.execute(
            """
            INSERT INTO production_replenish_orders (
                doc_no, product_part_no, qty, sales_order_no, line_id, status, note, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_no.strip(),
                product_part_no.strip(),
                str(round_qty(qty)),
                (sales_order_no or "").strip(),
                line_id,
                (status or "open").strip() or "open",
                (note or "").strip(),
                now,
            ),
        )
        self._conn.commit()
        return self.get_replenish(int(cur.lastrowid))

    def get_replenish(self, replenish_id: int) -> dict:
        row = self._conn.execute(
            "SELECT * FROM production_replenish_orders WHERE id = ?",
            (int(replenish_id),),
        ).fetchone()
        if row is None:
            raise ValueError(f"补产单不存在：{replenish_id}")
        return dict(row)

    def list_replenish(self, *, limit: int = 100, status: str = "") -> List[dict]:
        sql = "SELECT * FROM production_replenish_orders WHERE 1=1"
        params: list = []
        if status.strip():
            sql += " AND status = ?"
            params.append(status.strip())
        sql += " ORDER BY datetime(created_at) DESC, id DESC LIMIT ?"
        params.append(int(limit))
        return [dict(r) for r in self._conn.execute(sql, params).fetchall()]
