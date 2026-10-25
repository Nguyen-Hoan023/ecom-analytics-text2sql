from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from text2sql.output import render_table, write_csv


class TextToSQLOutputTests(unittest.TestCase):
    def test_render_table_formats_nulls_and_clips_long_cells(self) -> None:
        rendered = render_table(
            ("product_name", "total_profit", "active"),
            (("Sản phẩm thử nghiệm rất dài để xem cách cắt", Decimal("-12.50"), True),),
            max_column_width=16,
        )

        self.assertIn("product_name", rendered)
        self.assertIn("…", rendered)
        self.assertIn("-12.50", rendered)
        self.assertIn("true", rendered)

    def test_render_table_handles_empty_results(self) -> None:
        rendered = render_table(("country", "total_sales"), ())

        self.assertIn("No rows returned.", rendered)
        self.assertIn("country", rendered)

    def test_write_csv_preserves_values_and_escapes_formula_like_text(self) -> None:
        result = SimpleNamespace(
            columns=("product_name", "snapshot_date", "profit", "missing"),
            rows=(("=HYPERLINK(\"https://example.test\")", date(2024, 1, 1), Decimal("-1.25"), None),),
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "result.csv"
            saved_path = write_csv(result, path)

            with saved_path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle))

        self.assertEqual(rows[0], list(result.columns))
        self.assertEqual(
            rows[1],
            ["'=HYPERLINK(\"https://example.test\")", "2024-01-01", "-1.25", "NULL"],
        )

    def test_write_csv_refuses_to_overwrite(self) -> None:
        result = SimpleNamespace(columns=("value",), rows=((1,),))
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "result.csv"
            path.write_text("keep this file", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                write_csv(result, path)

            self.assertEqual(path.read_text(encoding="utf-8"), "keep this file")


if __name__ == "__main__":
    unittest.main()
