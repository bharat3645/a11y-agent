"""Heuristic (and optionally LLM-backed) fix suggestions.

Nothing in this module ever writes to disk. `suggest_fix` and
`suggest_fix_with_llm` both return strings meant for a diff-style preview
in the report; the CLI's --suggest-fix flag only ever *displays* these,
it never rewrites source files.
"""

import os
import re
from typing import Optional

from .findings import Finding
from .parser import find_headings, get_line_snippet
from .rules import generic_alt, link_text as link_text_rule

_HEADING_RE = re.compile(r"<h[1-6][^>]*>(.*?)</h[1-6]\s*>", re.IGNORECASE | re.DOTALL)
_FIGCAPTION_RE = re.compile(r"<figcaption[^>]*>(.*?)</figcaption>", re.IGNORECASE | re.DOTALL)


def _strip(html: str) -> str:
    return re.sub(r"<[^>]*>", " ", html).strip()


def _nearest_heading_before(file_text: str, line: int) -> Optional[str]:
    best = None
    for heading in find_headings(file_text):
        if heading.line <= line:
            best = heading.text.strip()
        else:
            break
    return best or None


def _nearby_figcaption(file_text: str, line: int, window_lines: int = 6) -> Optional[str]:
    lines = file_text.splitlines()
    lo = max(0, line - 1 - window_lines)
    hi = min(len(lines), line + window_lines)
    nearby_text = "\n".join(lines[lo:hi])
    m = _FIGCAPTION_RE.search(nearby_text)
    if m:
        return _strip(m.group(1))
    return None


def _propose_alt_text(file_text: str, finding: Finding) -> str:
    line = finding.line or 1
    figcaption = _nearby_figcaption(file_text, line)
    if figcaption:
        return figcaption
    heading = _nearest_heading_before(file_text, line)
    if heading:
        return f"{heading} (image)"
    return "TODO: describe what this image shows"


def _propose_link_text(href: str, original_text: str) -> str:
    slug = link_text_rule.slug_to_words(href)
    if slug:
        return f"{original_text.strip()} — {slug}".strip(" —")
    return f"{original_text.strip()} (describe the destination, e.g. section/page name)"


def _diff_preview(before: str, after: str) -> str:
    return f"- {before}\n+ {after}"


def suggest_fix(finding: Finding, file_text: str) -> str:
    """Return a diff-style suggestion string for a single finding.

    `file_text` is the full source of the file the finding came from, so
    nearby headings/figcaptions can be used as context.
    """
    if finding.rule_id in (generic_alt.RULE_ID, generic_alt.RULE_ID_EMPTY):
        proposed_alt = _propose_alt_text(file_text, finding)
        before = finding.snippet
        after = re.sub(r'alt=(["\']).*?\1', f'alt="{proposed_alt}"', before, count=1)
        if after == before:
            after = before + f'  <!-- suggested alt: "{proposed_alt}" -->'
        return _diff_preview(before, after)

    if finding.rule_id == link_text_rule.RULE_ID:
        href_match = re.search(r'href=(["\'])(.*?)\1', finding.snippet)
        href = href_match.group(2) if href_match else ""
        text_match = re.search(r">([^<]*)</a>", finding.snippet, re.IGNORECASE)
        original_text = text_match.group(1) if text_match else ""
        proposed = _propose_link_text(href, original_text)
        before = finding.snippet
        if text_match:
            after = before.replace(f">{original_text}</a>", f">{proposed}</a>")
        else:
            after = before + f"  <!-- suggested text: \"{proposed}\" -->"
        return _diff_preview(before, after)

    return "No automatic suggestion available for this rule; manual review recommended."


def _deterministic_llm_fallback(finding: Finding, surrounding_context: str) -> str:
    """Template-only suggestion used when no LLM/API key is available.

    Works off a plain context string (not necessarily the whole file), so
    it degrades gracefully to a generic TODO when no useful context is in
    range.
    """
    if finding.rule_id in (generic_alt.RULE_ID, generic_alt.RULE_ID_EMPTY):
        context_stripped = _strip(surrounding_context)
        proposed = context_stripped[:80] if context_stripped else "TODO: describe what this image shows"
        return f"Suggested alt text (template, no LLM): \"{proposed}\""

    if finding.rule_id == link_text_rule.RULE_ID:
        href_match = re.search(r'href=(["\'])(.*?)\1', finding.snippet)
        href = href_match.group(2) if href_match else ""
        slug = link_text_rule.slug_to_words(href)
        proposed = slug if slug else "TODO: name the destination of this link"
        return f"Suggested link text (template, no LLM): \"{proposed}\""

    return "No automatic suggestion available for this rule; manual review recommended."


def _build_llm_prompt(finding: Finding, surrounding_context: str) -> str:
    return (
        "You are helping fix a web accessibility issue. "
        f"Rule violated: {finding.rule_id}. Message: {finding.message}. "
        f"Offending snippet: {finding.snippet!r}. "
        f"Surrounding context: {surrounding_context!r}. "
        "Reply with ONLY the concrete replacement text/attribute value to "
        "use, no extra commentary."
    )


def suggest_fix_with_llm(finding: Finding, surrounding_context: str, llm_client=None) -> str:
    """Draft a fix suggestion, optionally via the real Anthropic API.

    Resolution order:
      1. If `llm_client` is passed in explicitly, use it (useful for tests/
         dependency injection).
      2. Else if `ANTHROPIC_API_KEY` is set in the environment, lazily
         construct an `anthropic.Anthropic()` client and call it.
      3. Else fall back to a deterministic, template-based suggestion that
         needs no network access and no dependency on the `anthropic`
         package - this is the path exercised by the test suite.

    This function never raises just because no key is configured; it only
    raises if a key *is* configured but the `anthropic` package can't be
    imported, since that indicates a real misconfiguration rather than
    "LLM mode simply isn't enabled".
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if llm_client is None and not api_key:
        return _deterministic_llm_fallback(finding, surrounding_context)

    client = llm_client
    if client is None:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is set but the 'anthropic' package is not "
                "installed. Install it with `pip install anthropic` or pass "
                "an explicit llm_client to use the LLM suggestion path."
            ) from exc
        client = anthropic.Anthropic(api_key=api_key)

    prompt = _build_llm_prompt(finding, surrounding_context)
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()
