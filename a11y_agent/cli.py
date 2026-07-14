"""Command-line interface: python -m a11y_agent scan <path> [options]."""

import argparse
import sys

from .walker import find_source_files
from .rules import run_all_rules
from .report import generate_report
from .suggest import suggest_fix


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="a11y-agent",
        description=(
            "Context-aware accessibility smell scanner for HTML/JSX/TSX. "
            "Finds issues that require semantic judgement (generic alt "
            "text, vague link text, color-only meaning, heading skips) "
            "that structural linters like axe-core / eslint-plugin-jsx-a11y "
            "typically miss."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan a file or directory")
    scan_parser.add_argument("path", help="File or directory to scan")
    scan_parser.add_argument(
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
        help="Output format (default: text)",
    )
    scan_parser.add_argument(
        "--suggest-fix",
        action="store_true",
        help=(
            "Include heuristic fix suggestions as a diff-style preview. "
            "Never modifies source files."
        ),
    )
    return parser


def run_scan(path: str, fmt: str, suggest: bool) -> int:
    all_findings = []
    file_texts = {}

    files = list(find_source_files(path))
    if not files:
        print(f"No .html/.htm/.jsx/.tsx files found under {path}", file=sys.stderr)

    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            print(f"warning: could not read {filepath}: {exc}", file=sys.stderr)
            continue

        file_texts[filepath] = text
        findings = run_all_rules(text, filepath)
        all_findings.extend(findings)

    if suggest:
        for finding in all_findings:
            finding.suggestion = suggest_fix(finding, file_texts[finding.file])

    print(generate_report(all_findings, fmt))

    # non-zero exit if any error-severity findings, useful for CI gating
    return 1 if any(f.severity == "error" for f in all_findings) else 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "scan":
        return run_scan(args.path, args.format, args.suggest_fix)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
