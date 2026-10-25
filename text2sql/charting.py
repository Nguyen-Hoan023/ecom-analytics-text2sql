"""Deterministic chart suggestions for bounded Text-to-SQL result tables."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Sequence


_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ].*)?$")
_MEASURE_PREFERENCE = (
    "total_sales",
    "total_profit",
    "units_sold",
    "customer_count",
    "sales_line_count",
    "order_count",
    "loss_making_order_count",
    "average_discount",
    "avg_discount",
    "profit_margin",
    "sales_share_of_segment",
    "support",
    "confidence",
    "lift",
)
_DIMENSION_PREFERENCE = (
    "sales_month",
    "product_name",
    "category",
    "segment",
    "country",
    "market",
    "occupation",
    "gender",
    "discount_band",
    "product_code",
)


@dataclass(frozen=True)
class ChartSuggestion:
    """Chart columns that can be shown without changing query semantics."""

    dimensions: tuple[str, ...]
    measures: tuple[str, ...]
    default_dimension: str
    default_measure: str
    chart_type: str


def _number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, Decimal)):
        result = float(value)
        return result if result == result and abs(result) != float("inf") else None
    if isinstance(value, str):
        try:
            return float(Decimal(value.strip()))
        except (InvalidOperation, ValueError):
            return None
    return None


def _is_date_column(values: Sequence[Any]) -> bool:
    if not values or any(value is None for value in values):
        return False
    for value in values:
        if isinstance(value, (date, datetime)):
            continue
        if not isinstance(value, str) or not _ISO_DATE.match(value):
            return False
        try:
            date.fromisoformat(value[:10])
        except ValueError:
            return False
    return True


def _preferred(candidates: Sequence[str], names: Sequence[str]) -> str:
    by_casefold = {candidate.casefold(): candidate for candidate in candidates}
    for name in names:
        if name.casefold() in by_casefold:
            return by_casefold[name.casefold()]
    return candidates[0]


def suggest_chart(
    columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    max_chart_rows: int = 60,
) -> ChartSuggestion | None:
    """Suggest a line/bar chart only for bounded, multi-row result shapes.

    Results with no rows, one row, too many rows, or no dimension/measure pair
    remain tabular/KPI outputs. The suggestion never runs SQL or aggregates data.
    """
    if not columns or len(rows) < 2 or len(rows) > max_chart_rows:
        return None
    if any(len(row) != len(columns) for row in rows):
        return None

    measures: list[str] = []
    dimensions: list[str] = []
    date_dimensions: list[str] = []
    for index, column in enumerate(columns):
        values = [row[index] for row in rows]
        numeric_values = [_number(value) for value in values]
        if all(value is not None for value in numeric_values):
            measures.append(column)
        elif len({str(value) for value in values}) > 1:
            dimensions.append(column)
            if _is_date_column(values):
                date_dimensions.append(column)

    if not dimensions or not measures:
        return None
    default_dimension = (
        date_dimensions[0]
        if date_dimensions
        else _preferred(dimensions, _DIMENSION_PREFERENCE)
    )
    default_measure = _preferred(measures, _MEASURE_PREFERENCE)
    return ChartSuggestion(
        dimensions=tuple(dimensions),
        measures=tuple(measures),
        default_dimension=default_dimension,
        default_measure=default_measure,
        chart_type="line" if default_dimension in date_dimensions else "bar",
    )
