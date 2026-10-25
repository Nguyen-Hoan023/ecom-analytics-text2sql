"""Human-friendly and portable renderers for bounded Text-to-SQL results."""

from __future__ import annotations

import csv
import unicodedata
from pathlib import Path
from typing import Any, Sequence


def _value_text(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if hasattr(value, "isoformat") and callable(value.isoformat):
        return value.isoformat()
    return str(value)


def _display_width(value: str) -> int:
    return sum(
        0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
        for char in value
    )


def _fit_cell(value: str, width: int) -> str:
    if _display_width(value) <= width:
        return value + (" " * (width - _display_width(value)))

    ellipsis = "…"
    available = max(0, width - _display_width(ellipsis))
    clipped: list[str] = []
    used = 0
    for char in value:
        char_width = 0 if unicodedata.combining(char) else 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
        if used + char_width > available:
            break
        clipped.append(char)
        used += char_width
    shortened = "".join(clipped) + ellipsis
    return shortened + (" " * max(0, width - _display_width(shortened)))


def render_table(
    columns: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    max_column_width: int = 36,
) -> str:
    """Render a bounded result for terminal reading; long cells are visually clipped."""
    if not columns:
        return "(no columns)"
    if max_column_width < 4:
        raise ValueError("max_column_width must be at least 4.")

    rendered_rows = [[_value_text(value) for value in row] for row in rows]
    if any(len(row) != len(columns) for row in rendered_rows):
        raise ValueError("Each result row must have the same number of values as columns.")

    widths = [
        min(
            max_column_width,
            max(
                _display_width(str(column)),
                max((_display_width(row[index]) for row in rendered_rows), default=0),
            ),
        )
        for index, column in enumerate(columns)
    ]

    def line(values: Sequence[str]) -> str:
        return "| " + " | ".join(_fit_cell(value, widths[index]) for index, value in enumerate(values)) + " |"

    separator = "+-" + "-+-".join("-" * width for width in widths) + "-+"
    output = [separator, line([str(column) for column in columns]), separator]
    output.extend(line(row) for row in rendered_rows)
    output.append(separator)
    if not rendered_rows:
        output.append("No rows returned.")
    return "\n".join(output)


def _csv_cell(value: Any) -> str:
    text = _value_text(value)
    if isinstance(value, str) and text.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def write_csv(result: Any, path: str | Path) -> Path:
    """Write a result as Excel-friendly UTF-8 CSV without overwriting an existing file."""
    output_path = Path(path).expanduser()
    with output_path.open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(result.columns)
        writer.writerows([_csv_cell(value) for value in row] for row in result.rows)
    return output_path.resolve()
