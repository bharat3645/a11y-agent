"""Findings data model shared by all rules and the report generator."""

from dataclasses import dataclass, field, asdict
from typing import Optional


SEVERITY_LEVELS = ("info", "warning", "error")


@dataclass
class Finding:
    """A single accessibility smell detected in a file.

    Attributes:
        file: path to the file the finding was found in (as given on the CLI).
        rule_id: short machine id of the rule, e.g. "generic-alt-text".
        severity: one of "info", "warning", "error".
        message: human readable description of the problem.
        line: 1-indexed line number, if known. None when only a snippet is
            available (e.g. multi-line regex matches spanning a whole file).
        snippet: the raw source text that triggered the finding.
        suggestion: optional heuristic fix suggestion (filled in only when
            --suggest-fix is requested).
    """

    file: str
    rule_id: str
    severity: str
    message: str
    line: Optional[int] = None
    snippet: str = ""
    suggestion: Optional[str] = None

    def __post_init__(self) -> None:
        if self.severity not in SEVERITY_LEVELS:
            raise ValueError(
                f"invalid severity {self.severity!r}, expected one of {SEVERITY_LEVELS}"
            )

    def to_dict(self) -> dict:
        return asdict(self)
