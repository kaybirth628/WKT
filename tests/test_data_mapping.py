import unittest

from test_impl.order_management.data_mapping.service import DataMappingService


class TestDataMappingService(unittest.TestCase):
    def test_build_report_shape(self) -> None:
        report = DataMappingService().build_report()
        self.assertIn("customer_matrix", report)
        self.assertIn("parts_matrix", report)
        self.assertIn("summary", report)
        self.assertIn("stats", report)
        self.assertIn("order_lines", report["stats"])
        self.assertIsInstance(report["customer_matrix"], list)
        if report["customer_matrix"]:
            row = report["customer_matrix"][0]
            for key in (
                "customer",
                "order_lines",
                "has_profile",
                "has_delivery",
                "status",
            ):
                self.assertIn(key, row)


if __name__ == "__main__":
    unittest.main()
