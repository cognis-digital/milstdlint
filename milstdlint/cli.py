"""Command-line interface for MILSTDLINT.

Usage:
    milstdlint lint FILE [FILE ...] [--format {table,json}] [--strict]
    milstdlint --version

Exit codes:
    0  all files passed (no ERROR-severity findings)
    1  one or more files had ERROR-severity findings
    2  usage / IO error
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import TOOL_NAME, TOOL_VERSION
from .core import lint_file, LintResult


def _render_table(results: List[LintResult]) -> str:
    out: List[str] = []
    for res in results:
        status = "PASS" if res.ok else "FAIL"
        banner = res.declared_banner or "-"
        derived = res.derived_banner or "-"
        out.append(f"== {res.path}  [{status}]  banner={banner} derived={derived}")
        if not res.findings:
            out.append("   (no findings)")
        for f in res.findings:
            loc = f"L{f.line}" if f.line else "doc"
            line = f"   {f.severity.value.upper():7} {loc:>6}  {f.rule:<24} {f.message}"
            out.append(line)
            if f.excerpt:
                out.append(f"            > {f.excerpt}")
        out.append(
            f"   -- {res.error_count} error(s), {res.warning_count} warning(s)"
        )
    return "\n".join(out)


def _render_json(results: List[LintResult]) -> str:
    payload = {
        "tool": TOOL_NAME,
        "version": TOOL_VERSION,
        "files": [r.to_dict() for r in results],
        "summary": {
            "files": len(results),
            "failed": sum(1 for r in results if not r.ok),
            "total_errors": sum(r.error_count for r in results),
            "total_warnings": sum(r.warning_count for r in results),
        },
    }
    return json.dumps(payload, indent=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Lint documents against MIL-STD / DoD formatting and "
                    "classification-marking rules (static analysis only).",
    )
    parser.add_argument(
        "--version", action="version",
        version=f"{TOOL_NAME} {TOOL_VERSION}",
    )
    sub = parser.add_subparsers(dest="command")

    lint = sub.add_parser("lint", help="Lint one or more document files.")
    lint.add_argument("files", nargs="+", help="Document file(s) to lint.")
    lint.add_argument(
        "--format", choices=["table", "json"], default="table",
        help="Output format (default: table).",
    )
    lint.add_argument(
        "--strict", action="store_true",
        help="Treat formatting warnings as errors (affects exit code).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command != "lint":
        parser.print_help()
        return 2

    results: List[LintResult] = []
    for path in args.files:
        try:
            results.append(lint_file(path, strict=args.strict))
        except FileNotFoundError:
            print(f"{TOOL_NAME}: file not found: {path}", file=sys.stderr)
            return 2
        except PermissionError as exc:
            print(f"{TOOL_NAME}: permission denied: {path}: {exc}", file=sys.stderr)
            return 2
        except OSError as exc:
            print(f"{TOOL_NAME}: cannot read {path}: {exc}", file=sys.stderr)
            return 2
        except ValueError as exc:
            # e.g. file too large
            print(f"{TOOL_NAME}: {exc}", file=sys.stderr)
            return 2

    if not results:
        # Defensive: argparse nargs="+" guarantees at least one file, but
        # guard against programmatic callers passing an empty list.
        print(f"{TOOL_NAME}: no files to lint", file=sys.stderr)
        return 2

    try:
        if args.format == "json":
            print(_render_json(results))
        else:
            print(_render_table(results))
    except (OSError, BrokenPipeError) as exc:
        print(f"{TOOL_NAME}: output error: {exc}", file=sys.stderr)
        return 2

    failed = any(not r.ok for r in results)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
