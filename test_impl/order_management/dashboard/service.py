"""订单模块首页：汇总统计与可视化数据。"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List

from test_impl.common.money import round_amount, round_qty, serialize_amount, serialize_qty, to_decimal
from test_impl.order_management.order_entry.line_service import OrderLineService
from test_impl.order_management.order_entry.line_store import CLOSURE_FORCED

NOT_FORCED = "(closure_type IS NULL OR closure_type = '' OR closure_type <> ?)"
OPEN_EXPR = "ROUND(CAST(po_qty AS REAL) - CAST(shipped_qty AS REAL), 1)"


class OrderDashboardService:
    def __init__(self, line_service: OrderLineService) -> None:
        self._lines = line_service

    def build_overview(self) -> Dict[str, Any]:
        store = self._lines._store
        conn = store._conn
        today = date.today()
        warn_end = today + timedelta(days=10)

        total_lines = int(conn.execute("SELECT COUNT(*) FROM order_lines").fetchone()[0])
        open_lines = int(
            conn.execute(
                f"SELECT COUNT(*) FROM order_lines WHERE {OPEN_EXPR} > 0 AND {NOT_FORCED}",
                (CLOSURE_FORCED,),
            ).fetchone()[0]
        )
        forced_lines = int(
            conn.execute(
                "SELECT COUNT(*) FROM order_lines WHERE closure_type = ?",
                (CLOSURE_FORCED,),
            ).fetchone()[0]
        )
        closed_lines = max(0, total_lines - open_lines - forced_lines)

        open_qty_row = conn.execute(
            f"""
            SELECT COALESCE(SUM({OPEN_EXPR}), 0),
                   COALESCE(SUM({OPEN_EXPR} * CAST(rmb_tax_incl_price AS REAL)), 0)
            FROM order_lines
            WHERE {OPEN_EXPR} > 0 AND {NOT_FORCED}
            """,
            (CLOSURE_FORCED,),
        ).fetchone()
        open_qty = serialize_qty(round_qty(to_decimal(open_qty_row[0] or 0)))
        open_amount = serialize_amount(round_amount(to_decimal(open_qty_row[1] or 0)))

        shipment_events = int(conn.execute("SELECT COUNT(*) FROM shipment_events").fetchone()[0])
        month_prefix = today.strftime("%Y-%m")
        shipments_this_month = int(
            conn.execute(
                "SELECT COUNT(*) FROM shipment_events WHERE strftime('%Y-%m', shipped_at) = ?",
                (month_prefix,),
            ).fetchone()[0]
        )
        customers = int(
            conn.execute(
                "SELECT COUNT(DISTINCT customer) FROM order_lines WHERE TRIM(customer) <> ''"
            ).fetchone()[0]
        )

        overdue_lines = int(
            conn.execute(
                f"""
                SELECT COUNT(*) FROM order_lines
                WHERE {OPEN_EXPR} > 0 AND {NOT_FORCED}
                  AND TRIM(delivery_date) <> ''
                  AND date(substr(delivery_date, 1, 10)) < date(?)
                """,
                (CLOSURE_FORCED, today.isoformat()),
            ).fetchone()[0]
        )
        due_soon_lines = int(
            conn.execute(
                f"""
                SELECT COUNT(*) FROM order_lines
                WHERE {OPEN_EXPR} > 0 AND {NOT_FORCED}
                  AND TRIM(delivery_date) <> ''
                  AND date(substr(delivery_date, 1, 10)) >= date(?)
                  AND date(substr(delivery_date, 1, 10)) <= date(?)
                """,
                (CLOSURE_FORCED, today.isoformat(), warn_end.isoformat()),
            ).fetchone()[0]
        )

        status_distribution = [
            {"key": "open", "label": "未结", "count": open_lines},
            {"key": "closed", "label": "正常结案", "count": closed_lines},
            {"key": "forced", "label": "强制结案", "count": forced_lines},
        ]

        top_open_customers = self._top_open_customers(conn, limit=8)
        monthly_shipments = self._monthly_shipments(conn, months=6)
        shipment_sources = self._shipment_sources(conn)

        return {
            "ok": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "kpis": {
                "total_lines": total_lines,
                "open_lines": open_lines,
                "closed_lines": closed_lines,
                "forced_closed_lines": forced_lines,
                "open_qty": open_qty,
                "open_amount": open_amount,
                "shipment_events": shipment_events,
                "shipments_this_month": shipments_this_month,
                "customers": customers,
                "overdue_lines": overdue_lines,
                "due_soon_lines": due_soon_lines,
            },
            "status_distribution": status_distribution,
            "top_open_customers": top_open_customers,
            "monthly_shipments": monthly_shipments,
            "shipment_sources": shipment_sources,
        }

    def _top_open_customers(self, conn, *, limit: int) -> List[Dict[str, Any]]:
        rows = conn.execute(
            f"""
            SELECT customer,
                   COUNT(*) AS line_count,
                   SUM({OPEN_EXPR}) AS open_qty,
                   SUM({OPEN_EXPR} * CAST(rmb_tax_incl_price AS REAL)) AS open_amount
            FROM order_lines
            WHERE {OPEN_EXPR} > 0 AND {NOT_FORCED}
            GROUP BY customer
            ORDER BY open_qty DESC, line_count DESC, customer COLLATE NOCASE
            LIMIT ?
            """,
            (CLOSURE_FORCED, limit),
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "customer": row["customer"] or "",
                    "lines": int(row["line_count"] or 0),
                    "open_qty": serialize_qty(round_qty(to_decimal(row["open_qty"] or 0))),
                    "open_amount": serialize_amount(round_amount(to_decimal(row["open_amount"] or 0))),
                }
            )
        return out

    def _monthly_shipments(self, conn, *, months: int) -> List[Dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT strftime('%Y-%m', shipped_at) AS ym,
                   COUNT(*) AS cnt,
                   COALESCE(SUM(CAST(ship_qty AS REAL)), 0) AS qty
            FROM shipment_events
            WHERE shipped_at IS NOT NULL
            GROUP BY ym
            ORDER BY ym DESC
            LIMIT ?
            """,
            (months,),
        ).fetchall()
        items = [
            {
                "month": row["ym"] or "",
                "label": row["ym"] or "",
                "count": int(row["cnt"] or 0),
                "qty": serialize_qty(round_qty(to_decimal(row["qty"] or 0))),
            }
            for row in reversed(list(rows))
        ]
        return items

    def _shipment_sources(self, conn) -> List[Dict[str, Any]]:
        from test_impl.order_management.order_entry.shipment_models import SOURCE_LABELS

        rows = conn.execute(
            """
            SELECT source, COUNT(*) AS cnt
            FROM shipment_events
            GROUP BY source
            ORDER BY cnt DESC
            """
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for row in rows:
            key = row["source"] or ""
            out.append(
                {
                    "key": key,
                    "label": SOURCE_LABELS.get(key, key or "其他"),
                    "count": int(row["cnt"] or 0),
                }
            )
        return out
