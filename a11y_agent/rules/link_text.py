"""Rule: non-descriptive link text ("click here", "read more", ...).

What it catches that plain linters don't:
    eslint-plugin-jsx-a11y's `anchor-has-content` and axe-core's
    `link-name` check only verify that a link has *some* accessible name at
    all (text, aria-label, image alt, etc.) - an empty <a></a> is the bug
    they look for. A link that says "click here" or "read more" already
    satisfies those checks completely: it has non-empty text. But that text
    is meaningless out of context - screen reader users often navigate a
    page via a list of all links, where every "click here" looks identical.

Heuristic and known risks:
    * False positives: a link whose *only* content is legitimately the
      word "more" (e.g. a paginator control that has an aria-label anyway)
      is exempted only if aria-label/title is present; a bare "More" link
      with no aria-label will still be flagged even if surrounding page
      structure makes it clear in practice - this rule can't see layout.
    * False negatives: longer-but-still-vague phrases ("check this out",
      "go here now") aren't on the blocklist and won't be caught; the
      blocklist is intentionally small and easy to extend.
    * The rule only inspects the anchor's own text/aria-label/title, not
      of surrounding sibling elements (e.g. a preceding heading that gives
      context) - a genuinely common, accessible pattern is a heading
      immediately followed by a "read more" link, which some style guides
      accept. This rule will still flag it; treat findings as prompts for
      human review, not absolute violations.
"""

import re

from ..findings import Finding
from ..parser import find_with_content, get_line_snippet

RULE_ID = "non-descriptive-link-text"

VAGUE_PHRASES = {
    "click here",
    "read more",
    "here",
    "link",
    "more",
    "learn more",
    "this link",
    "click",
}

_TRAILING_PUNCT_RE = re.compile(r"[.,!?;:…]+$")


def _normalize(s: str) -> str:
    s = s.strip().lower()
    s = _TRAILING_PUNCT_RE.sub("", s)
    s = re.sub(r"\s+", " ", s)
    return s


def slug_to_words(href: str) -> str:
    if not href:
        return ""
    # drop query/hash, take the last path segment
    href = href.split("#")[0].split("?")[0]
    segment = href.rstrip("/").split("/")[-1]
    segment = re.sub(r"\.(html?|jsx?|tsx?|php)$", "", segment, flags=re.IGNORECASE)
    words = re.split(r"[-_]+", segment)
    words = [w for w in words if w]
    return " ".join(words)


def check(text: str, filepath: str):
    findings = []
    for anchor in find_with_content(text, "a"):
        visible_text = _normalize(anchor.text)
        if visible_text not in VAGUE_PHRASES:
            continue

        aria_label = anchor.attrs.get("aria-label", "").strip()
        title = anchor.attrs.get("title", "").strip()
        if (aria_label and not aria_label.startswith("{")) or (
            title and not title.startswith("{")
        ):
            # Has a real descriptive label/title alongside the vague
            # visible text - assistive tech will announce the label, not
            # the raw text, so this is acceptable.
            continue

        snippet = get_line_snippet(text, anchor.line) or anchor.raw.strip()
        href = anchor.attrs.get("href", "")
        hint = f" (href suggests: \"{slug_to_words(href)}\")" if slug_to_words(href) else ""
        findings.append(
            Finding(
                file=filepath,
                rule_id=RULE_ID,
                severity="warning",
                message=(
                    f"link text \"{anchor.text.strip()}\" is not descriptive "
                    f"out of context, and has no aria-label/title to "
                    f"compensate{hint}."
                ),
                line=anchor.line,
                snippet=snippet,
            )
        )
    return findings
