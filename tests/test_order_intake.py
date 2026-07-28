import unittest

from test_impl.order_management.order_intake import normalize_extraction, normalize_order
from test_impl.order_management.order_intake.intake_service import _to_number_str, _to_tax_rate
from test_impl.order_management.order_intake.part_no_fill import fill_part_no_from_raw_text
from test_impl.order_management.order_intake.text_extract import (
    TextExtractionError,
    extract_text,
)


class TestNumberCleaning(unittest.TestCase):
    def test_number_strip_commas_units(self) -> None:
        self.assertEqual(_to_number_str("1,000"), "1000")
        self.assertEqual(_to_number_str("120 g"), "120")
        self.assertEqual(_to_number_str("¥2.50"), "2.50")
        self.assertEqual(_to_number_str(""), "0")
        self.assertEqual(_to_number_str(None), "0")

    def test_tax_rate_normalization(self) -> None:
        self.assertEqual(_to_tax_rate("13%"), "0.13")
        self.assertEqual(_to_tax_rate("13"), "0.13")
        self.assertEqual(_to_tax_rate("0.13"), "0.13")
        self.assertEqual(_to_tax_rate(""), "0")


class TestNormalizeOrder(unittest.TestCase):
    def test_normalize_full(self) -> None:
        raw = {
            "customer": "华东精密 ",
            "order_no": "PO-2026-888",
            "order_date": "2026-05-30",
            "delivery_date": "2026-06-20",
            "payment_terms": "月结30天",
            "items": [
                {
                    "product_spec": "壳体/Φ50",
                    "customer_part_no": "CPN-1",
                    "material": "ADC12",
                    "unit_weight_g": "120 g",
                    "po_qty": "1,000",
                    "shipped_qty": "",
                    "unit": "PCS",
                    "tax_rate": "13%",
                    "rmb_tax_incl_price": "¥2.50",
                }
            ],
        }
        out = normalize_order(raw)
        self.assertEqual(out["customer"], "华东精密")
        self.assertEqual(out["order_no"], "PO-2026-888")
        self.assertEqual(len(out["items"]), 1)
        it = out["items"][0]
        self.assertEqual(it["item_no"], 1)
        self.assertEqual(it["unit_weight_g"], "120")
        self.assertEqual(it["po_qty"], "1000")
        self.assertEqual(it["shipped_qty"], "0")
        self.assertEqual(it["tax_rate"], "0.13")
        self.assertEqual(it["rmb_tax_incl_price"], "2.50")

    def test_normalize_single_item_dict(self) -> None:
        out = normalize_order({"items": {"product_spec": "件A", "po_qty": "5"}})
        self.assertEqual(len(out["items"]), 1)
        self.assertEqual(out["items"][0]["po_qty"], "5")


class TestNormalizeExtraction(unittest.TestCase):
    def test_multiple_orders(self) -> None:
        raw = {
            "orders": [
                {"order_no": "A1", "customer": "甲", "items": [{"product_spec": "件A", "po_qty": "10"}]},
                {"order_no": "B2", "customer": "乙", "items": [{"product_spec": "件B", "po_qty": "20"}]},
            ]
        }
        out = normalize_extraction(raw)
        self.assertEqual(len(out["orders"]), 2)
        self.assertEqual(out["orders"][0]["order_no"], "A1")
        self.assertEqual(out["orders"][1]["items"][0]["po_qty"], "20")

    def test_single_order_legacy_format(self) -> None:
        # 兼容：DeepSeek 直接返回单张订单（无 orders 包裹）
        raw = {"order_no": "X9", "customer": "丙", "items": [{"product_spec": "件C", "po_qty": "3"}]}
        out = normalize_extraction(raw)
        self.assertEqual(len(out["orders"]), 1)
        self.assertEqual(out["orders"][0]["order_no"], "X9")

    def test_normalize_empty(self) -> None:
        out = normalize_extraction({})
        self.assertEqual(out["orders"], [])


class TestPartNoFill(unittest.TestCase):
    def test_fill_dawo_material_code_by_product_spec(self) -> None:
        raw_text = (
            "1 1-000797 大沃款-扳手 W2808吊环压板 材料：ADC12 2500 pcs 3.800\n"
            "2 1-000796 大沃款-扳手 W2808端盖 材料：ADC12 2500 pcs 12.990\n"
        )
        orders = normalize_extraction(
            {
                "orders": [
                    {
                        "customer": "苏州大沃",
                        "items": [
                            {"product_spec": "大沃款-扳手 W2808吊环压板", "customer_part_no": ""},
                            {"product_spec": "大沃款-扳手 W2808端盖", "customer_part_no": ""},
                        ],
                    }
                ]
            }
        )
        fill_part_no_from_raw_text(orders, raw_text)
        items = orders["orders"][0]["items"]
        self.assertEqual(items[0]["customer_part_no"], "1-000797")
        self.assertEqual(items[1]["customer_part_no"], "1-000796")

    def test_fill_sequential_when_spec_missing(self) -> None:
        raw_text = "1-000797\n1-000796\n"
        orders = normalize_extraction(
            {
                "orders": [
                    {
                        "items": [
                            {"product_spec": "", "customer_part_no": ""},
                            {"product_spec": "", "customer_part_no": ""},
                        ]
                    }
                ]
            }
        )
        fill_part_no_from_raw_text(orders, raw_text)
        items = orders["orders"][0]["items"]
        self.assertEqual(items[0]["customer_part_no"], "1-000797")
        self.assertEqual(items[1]["customer_part_no"], "1-000796")


class TestTextExtract(unittest.TestCase):
    def test_unsupported_type(self) -> None:
        with self.assertRaisesRegex(TextExtractionError, "不支持的文件类型"):
            extract_text(b"x", "order.docx")


if __name__ == "__main__":
    unittest.main()
