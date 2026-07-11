import unittest
from decimal import Decimal

from test_impl.order_management.cost_analysis import CostAnalysisService, RAW_MATERIALS


class TestCostAnalysisService(unittest.TestCase):
    def setUp(self) -> None:
        self.service = CostAnalysisService()

    def test_materials_dropdown(self) -> None:
        materials = self.service.get_materials()
        self.assertEqual(materials, ["ADC12", "A380", "ZN-05"])
        self.assertEqual(materials, RAW_MATERIALS)

    def test_processes_match_corrected_list(self) -> None:
        processes = self.service.get_processes()
        for name in ["压铸", "去毛边", "抛光", "铆合", "皮模钝化", "化镍", "喷粉", "镭雕", "剥漆", "外购磁铁", "外购销钉", "外购轴套", "管销", "利润"]:
            self.assertIn(name, processes)
        for merged in ["埋轴", "下料", "精冲"]:
            self.assertNotIn(merged, processes)
        for old in ["理料", "锚铜", "铝合", "皮模化料", "管制"]:
            self.assertNotIn(old, processes)
        self.assertEqual(len(processes), 36)

    def test_process_options_have_codes(self) -> None:
        options = self.service.get_process_options()
        self.assertEqual(len(options), 36)
        self.assertEqual(options[0], {"code": "01", "name": "压铸"})
        self.assertEqual(options[-1]["code"], "36")

    def test_build_quote_and_total(self) -> None:
        quote = self.service.build_quote(
            {
                "material_code": "ADC12",
                "material_unit_price": "0.02",
                "material_weight": "150",
                "process_prices": {"压铸": "1.5", "CNC": "3.2", "电镀": "0.8"},
                "quantity": "100",
                "markup_rate": "0.15",
            }
        )
        # 原材成本 = 0.02 * 150 = 3.0000
        self.assertEqual(quote.material_cost(), Decimal("3.0000"))
        # 工艺合计 = 1.5 + 3.2 + 0.8 = 5.5000
        self.assertEqual(quote.process_total(), Decimal("5.5000"))
        # 单件成本 = 3 + 5.5 = 8.5000
        self.assertEqual(quote.unit_cost(), Decimal("8.5000"))
        # 总成本 = 8.5 * 100 = 850.0000
        self.assertEqual(quote.total_cost(), Decimal("850.0000"))
        # 报价 = 850 * 1.15 = 977.5000
        self.assertEqual(quote.quote_price(), Decimal("977.5000"))

    def test_reject_unknown_material(self) -> None:
        with self.assertRaisesRegex(ValueError, "未知原材"):
            self.service.build_quote({"material_code": "UNKNOWN"})

    def test_reject_unknown_process(self) -> None:
        with self.assertRaisesRegex(ValueError, "未知工艺"):
            self.service.build_quote(
                {
                    "material_code": "A380",
                    "process_prices": {"不存在的工艺": "1"},
                }
            )

    def test_empty_process_prices_ignored(self) -> None:
        quote = self.service.build_quote(
            {
                "material_code": "ZN-05",
                "process_prices": {"压铸": "", "CNC": None, "打磨": "2"},
            }
        )
        self.assertEqual(quote.process_total(), Decimal("2.0000"))


if __name__ == "__main__":
    unittest.main()
