"""Rule registry: each rule module exposes RULE_ID and check(text, filepath)."""

from . import generic_alt, link_text, color_only, heading_hierarchy

ALL_RULES = [generic_alt, link_text, color_only, heading_hierarchy]


def run_all_rules(text: str, filepath: str):
    findings = []
    for rule in ALL_RULES:
        findings.extend(rule.check(text, filepath))
    return findings
