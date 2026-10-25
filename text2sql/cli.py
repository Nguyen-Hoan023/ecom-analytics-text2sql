"""Small local CLI for inspecting prompts and trying Text-to-SQL requests."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from text2sql.nl_service import NaturalLanguageQueryService, build_generation_payload
from text2sql.output import render_table, write_csv


def _result_payload(result: Any) -> list[dict[str, Any]]:
    return [
        {column: value for column, value in zip(result.columns, row)}
        for row in result.rows
    ]


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")

    parser = argparse.ArgumentParser(description="Ask a read-only question over Xom E-Com Gold marts.")
    parser.add_argument("question", nargs="+", help="A question in Vietnamese or English.")
    parser.add_argument(
        "--show-prompt",
        action="store_true",
        help="Print the system instructions and allowlisted metadata locally; do not call Gemini.",
    )
    parser.add_argument(
        "--output-format",
        choices=("table", "json"),
        default="table",
        help="Format query results for the terminal (default: table).",
    )
    parser.add_argument(
        "--export-csv",
        type=Path,
        metavar="PATH",
        help="Also save query rows as UTF-8 CSV; refuses to overwrite an existing file.",
    )
    args = parser.parse_args(argv)
    question = " ".join(args.question)

    if args.show_prompt:
        try:
            system_instruction, payload = build_generation_payload(question)
        except Exception as exc:
            print(f"Could not build prompt ({type(exc).__name__}).", file=sys.stderr)
            return 2
        print("SYSTEM INSTRUCTION\n")
        print(system_instruction)
        print("\nMODEL INPUT JSON\n")
        print(json.dumps(json.loads(payload), ensure_ascii=False, indent=2, default=str))
        return 0

    service = None
    try:
        service = NaturalLanguageQueryService()
        response = service.ask(question)
    except Exception as exc:
        print(f"Text-to-SQL could not start ({type(exc).__name__}).", file=sys.stderr)
        return 2
    finally:
        if service is not None:
            service.close()

    print(f"Status: {response.status}")
    print(response.message)
    if response.sql:
        print("\nValidated SQL:\n")
        print(response.sql)
    if response.result is not None:
        print("\nResult:\n")
        if args.output_format == "json":
            print(
                json.dumps(
                    _result_payload(response.result),
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            )
        else:
            print(render_table(response.result.columns, response.result.rows))
        print(
            f"\nrows={response.result.row_count}, "
            f"truncated={response.result.truncated}, "
            f"duration_ms={response.result.duration_ms}"
        )
        if args.export_csv is not None:
            try:
                saved_path = write_csv(response.result, args.export_csv)
            except FileExistsError:
                print("CSV export failed: the destination file already exists.", file=sys.stderr)
                return 2
            except (OSError, ValueError) as exc:
                print(f"CSV export failed ({type(exc).__name__}).", file=sys.stderr)
                return 2
            print(f"CSV saved: {saved_path}")
    elif args.export_csv is not None:
        print("CSV export skipped: this response has no query result.", file=sys.stderr)
    return 0 if response.status == "answered" else 1


if __name__ == "__main__":
    raise SystemExit(main())
