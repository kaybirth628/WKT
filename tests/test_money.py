import unittest
from decimal import Decimal

from test_impl.common.money import (
    to_decimal,
    round_amount,
    round_qty,
    round_weight,
    round_price,
    round_rate,
    fmt_amount,
    fmt_qty,
    fmt_price,
    serialize_qty,
    serialize_amount,
    transport,
    rmb_upper,
)


class TestRounding(unittest.TestCase):
    def test_round_amount_half_up(self) -> None:
        self.assertEqual(round_amount("12.345"), Decimal("12.35"))
        self.assertEqual(round_amount("12.344"), Decimal("12.34"))
        self.assertEqual(round_amount("2.5"), Decimal("2.50"))
        self.assertEqual(round_amount(""), Decimal("0.00"))

    def test_round_price_4dp(self) -> None:
        self.assertEqual(round_price("1.23456"), Decimal("1.2346"))
        self.assertEqual(round_price("2.5"), Decimal("2.5000"))

    def test_round_qty_1dp(self) -> None:
        self.assertEqual(round_qty("100.15"), Decimal("100.2"))
        self.assertEqual(round_qty("2996.94"), Decimal("2996.9"))

    def test_round_weight_2dp(self) -> None:
        self.assertEqual(round_weight("120.456"), Decimal("120.46"))
        self.assertEqual(round_weight("45"), Decimal("45.00"))

    def test_round_rate_6dp(self) -> None:
        self.assertEqual(round_rate("7.1234565"), Decimal("7.123457"))

    def test_no_float_pollution(self) -> None:
        # 0.1 + 0.2 经 Decimal 应精确
        self.assertEqual(round_amount(to_decimal("0.1") + to_decimal("0.2")), Decimal("0.30"))


class TestFormat(unittest.TestCase):
    def test_fmt_amount_thousands(self) -> None:
        self.assertEqual(fmt_amount("12345.6"), "12,345.6")
        self.assertEqual(fmt_amount("5000"), "5,000")
        self.assertEqual(fmt_amount("-12345.67"), "-12,345.67")

    def test_fmt_price_4dp(self) -> None:
        self.assertEqual(fmt_price("1234.5"), "1,234.5")
        self.assertEqual(fmt_price("1234.5678"), "1,234.5678")

    def test_fmt_qty_1dp(self) -> None:
        self.assertEqual(fmt_qty("1407510"), "1,407,510")
        self.assertEqual(fmt_qty("2996.9"), "2,996.9")

    def test_serialize_plain(self) -> None:
        self.assertEqual(serialize_qty("1407510"), "1407510")
        self.assertEqual(serialize_qty("2996.9"), "2996.9")
        self.assertEqual(serialize_amount("352300"), "352300")
        self.assertEqual(serialize_amount("352300.5"), "352300.5")

    def test_transport_plain(self) -> None:
        self.assertEqual(transport("12345.67", 2), "12345.67")
        self.assertEqual(transport("2.5", 4), "2.5000")
        self.assertNotIn(",", transport("1234567.89", 2))


class TestRmbUpper(unittest.TestCase):
    def test_examples(self) -> None:
        self.assertEqual(rmb_upper("12345.67"), "人民币壹万贰仟叁佰肆拾伍元陆角柒分")
        self.assertEqual(rmb_upper("10000.00"), "人民币壹万元整")
        self.assertEqual(rmb_upper("0"), "人民币零元整")
        self.assertEqual(rmb_upper("100.05"), "人民币壹佰元零伍分")
        self.assertEqual(rmb_upper("10050"), "人民币壹万零伍拾元整")
        self.assertEqual(rmb_upper("0.67"), "人民币陆角柒分")


if __name__ == "__main__":
    unittest.main()
