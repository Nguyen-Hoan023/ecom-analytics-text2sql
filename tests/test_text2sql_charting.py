from __future__ import annotations

import unittest
from datetime import date
from decimal import Decimal

from text2sql.charting import suggest_chart
from text2sql.executor import QueryResult
from text2sql.nl_service import TextToSQLResponse
from text2sql.web_app import _response_payload


class ChartSuggestionTests(unittest.TestCase):
    def test_suggests_a_bar_chart_for_segment_sales(self) -> None:
        spec = suggest_chart(
            ("segment", "order_count", "total_sales"),
            (("Corporate", 7724, Decimal("3840707.00")), ("Consumer", 13291, Decimal("2146780.00"))),
        )
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.chart_type, "bar")
        self.assertEqual(spec.default_dimension, "segment")
        self.assertEqual(spec.default_measure, "total_sales")

    def test_suggests_a_line_chart_for_monthly_sales(self) -> None:
        spec = suggest_chart(
            ("sales_month", "total_sales"),
            ((date(2023, 1, 1), Decimal("100.00")), (date(2023, 2, 1), Decimal("125.00"))),
        )
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.chart_type, "line")
        self.assertEqual(spec.default_dimension, "sales_month")

    def test_does_not_suggest_chart_for_empty_or_single_row_results(self) -> None:
        self.assertIsNone(suggest_chart(("total_sales",), ()))
        self.assertIsNone(suggest_chart(("total_sales", "total_profit"), ((10, 2),)))

    def test_does_not_suggest_chart_for_malformed_rows(self) -> None:
        self.assertIsNone(suggest_chart(("segment", "sales"), (("Consumer",), ("Corporate", 2))))


class WebResponsePayloadTests(unittest.TestCase):
    def test_payload_serializes_decimal_and_dates_and_suggests_chart(self) -> None:
        result = QueryResult(
            columns=("sales_month", "total_sales"),
            rows=((date(2023, 1, 1), Decimal("100.00")), (date(2023, 2, 1), Decimal("125.00"))),
            row_count=2,
            row_limit=500,
            truncated=False,
            duration_ms=12,
            relation="analytics_gold.mart_monthly_sales",
            model_name="mart_monthly_sales",
            role="analyst",
        )
        payload = _response_payload(TextToSQLResponse("answered", "ok", result=result))
        self.assertEqual(payload["result"]["rows"][0], ["2023-01-01", "100.00"])
        self.assertEqual(payload["result"]["chart"]["chart_type"], "line")


if __name__ == "__main__":
    unittest.main()
