import json
import unittest
from decimal import Decimal

from test_impl.order_management.delivery_note.wkt_document import (
    build_batch_draft_document,
    document_to_dict,
)
from test_impl.order_management.order_entry.line_models import OrderLine
from test_impl.order_management.order_entry.line_service import OrderLineService


def _fake_line(
    id: int,
    customer: str,
    order_no: str,
    product_spec: str,
    po_qty: str,
    shipped_qty: str,
) -> OrderLine:
    from datetime import datetime, timezone

    return OrderLine(
        id=id,
        customer=customer,
        order_date="2026-05-01",
        delivery_date="2026-06-01",
        order_no=order_no,
        product_spec=product_spec,
        customer_part_no="P-" + order_no,
        unit_weight_g=Decimal("1"),
        material="ADC12",
        po_qty=Decimal(po_qty),
        shipped_qty=Decimal(shipped_qty),
        unit="PCS",
        tax_rate=Decimal("0.13"),
        rmb_tax_incl_price=Decimal("1"),
        payment_terms="月结",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestBatchShip(unittest.TestCase):
    def test_batch_draft_multiple_lines(self) -> None:
        a = _fake_line(1, "怡利", "PO-001", "散热器A", "100", "0")
        b = _fake_line(2, "怡利", "PO-002", "散热器B", "200", "50")
        doc = build_batch_draft_document([(a, Decimal("30")), (b, Decimal("20"))])
        d = document_to_dict(doc)
        self.assertEqual(len(d["lines"]), 2)
        self.assertEqual(d["lines"][0]["order_no"], "PO-001")
        self.assertEqual(d["lines"][1]["order_no"], "PO-002")
        self.assertEqual(d["total_qty"], "50")

    def test_batch_draft_rejects_mixed_customer(self) -> None:
        a = _fake_line(1, "怡利", "PO-001", "散热器A", "100", "0")
        b = _fake_line(2, "其他客", "PO-002", "散热器B", "200", "0")
        with self.assertRaises(ValueError):
            build_batch_draft_document([(a, Decimal("10")), (b, Decimal("10"))])

    def test_ship_lines_batch_uses_actual_qty_not_delivery_note_override(self) -> None:
        lines = OrderLineService(db_path=":memory:")
        a = lines.create_line(
            {
                "customer": "怡利",
                "order_no": "PO-001",
                "customer_part_no": "P-001",
                "product_spec": "散热器A",
                "po_qty": "100",
                "unit": "PCS",
            }
        )
        b = lines.create_line(
            {
                "customer": "怡利",
                "order_no": "PO-002",
                "customer_part_no": "P-002",
                "product_spec": "散热器B",
                "po_qty": "200",
                "unit": "PCS",
            }
        )
        bad_dn = {
            "lines": [
                {"qty": "100", "order_no": "PO-001"},
                {"qty": "200", "order_no": "PO-002"},
            ],
            "total_qty": "300",
        }
        items = [{"line_id": a.id, "qty": "10"}, {"line_id": b.id, "qty": "20"}]
        _, events = lines.ship_lines_batch(items, delivery_note=bad_dn)
        raw = lines._store.get_shipment_delivery_note_json(events[0].id)
        snap = json.loads(raw)
        self.assertEqual(snap["lines"][0]["qty"], "10")
        self.assertEqual(snap["lines"][1]["qty"], "20")
        self.assertEqual(snap["total_qty"], "30")


if __name__ == "__main__":
    unittest.main()
