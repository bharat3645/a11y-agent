"""Report generation: human-readable text/Markdown and machine-readable JSON."""

import json
from typing import List

from .findings import Finding

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def _sort_key(f: Finding):
    return (f.file, f.line or 0, SEVERITY_ORDER.get(f.severity, 3), f.rule_id)


def to_json(findings: List[Finding]) -> str:
    return json.dumps([f.to_dict() for f in findings], indent=2)


def to_text(findings: List[Finding]) -> str:
    if not findings:
        return "No context-dependent accessibility smells found."

    lines = []
    findings_sorted = sorted(findings, key=_sort_key)
    current_file = None
    for f in findings_sorted:
        if f.file != current_file:
            lines.append(f"\n{f.file}")
            current_file = f.file
        loc = f"line {f.line}" if f.line else "line ?"
        lines.append(f"  [{f.severity.upper():7}] {f.rule_id} ({loc})")
        lines.append(f"      {f.message}")
        if f.snippet:
            lines.append(f"      > {f.snippet}")
        if f.suggestion:
            lines.append(f"      suggestion: {f.suggestion}")

    counts = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
    lines.append(f"\n{len(findings)} finding(s) across "
                 f"{len(set(f.file for f in findings))} file(s) ({summary})")
    return "\n".join(lines).strip("\n")


def to_markdown(findings: List[Finding]) -> str:
    if not findings:
        return "## a11y-agent report\n\nNo context-dependent accessibility smells found.\n"

    lines = ["## a11y-agent report", ""]
    findings_sorted = sorted(findings, key=_sort_key)
    current_file = None
    for f in findings_sorted:
        if f.file != current_file:
            lines.append(f"\n### `{f.file}`\n")
            current_file = f.file
        loc = f"line {f.line}" if f.line else "line ?"
        lines.append(f"- **[{f.severity.upper()}] {f.rule_id}** ({loc}): {f.message}")
        if f.snippet:
            lines.append(f"  ```\n  {f.snippet}\n  ```")
        if f.suggestion:
            lines.append(f"  - suggestion: {f.suggestion}")

    counts = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
    lines.append(f"\n**Total:** {len(findings)} finding(s) across "
                 f"{len(set(f.file for f in findings))} file(s) ({summary})")
    return "\n".join(lines)


def generate_report(findings: List[Finding], fmt: str = "text") -> str:
    if fmt == "json":
        return to_json(findings)
    if fmt == "markdown":
        return to_markdown(findings)
    return to_text(findings)
