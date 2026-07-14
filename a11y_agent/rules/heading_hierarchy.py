"""Rule: heading hierarchy skips (h1 -> h3, h2 -> h5, etc.).

What it catches that plain linters don't:
    eslint-plugin-jsx-a11y and axe-core mostly check individual elements in
    isolation. Heading order is a *document-level* / cross-element concern:
    WCAG 2.4.6 and general screen-reader navigation guidance both call for
    heading levels to increase by at most one at a time, because screen
    reader users frequently navigate a page by jumping between headings and
    rely on the level to infer document structure. A jump from <h1> straight
    to <h4> is invisible to per-element linting but breaks that navigation
    model.

Heuristic and known risks:
    * The extractor (see parser.py) finds headings via regex over raw
      source. It does not understand conditional rendering, so headings
      inside a JSX branch that never actually renders together will still
      be compared as if they appear in the same document flow -> possible
      false positive.
    * Only levels present in the *same file* are tracked. Multi-file
      documents (e.g. a layout component that renders an <h1> and a page
      component that renders an <h3> assuming the layout's h1/h2 already
      exist) are common in modern component-based frontends and are
      invisible to a per-file static scan -> false negative by design.
    * A document that never starts at h1 (e.g. a reusable card component
      that starts at h3 because it's always embedded under an h2) is not
      flagged by itself; only *jumps between consecutive headings within
      the file* are checked, not the absolute starting level.
"""

from ..findings import Finding
from ..parser import find_headings, get_line_snippet

RULE_ID = "heading-hierarchy-skip"


def check(text: str, filepath: str):
    findings = []
    headings = find_headings(text)
    headings.sort(key=lambda h: h.line)

    last_level = None
    last_text = None
    for heading in headings:
        level = int(heading.tag[1])
        if last_level is not None and level - last_level > 1:
            snippet = get_line_snippet(text, heading.line) or heading.raw.strip()
            findings.append(
                Finding(
                    file=filepath,
                    rule_id=RULE_ID,
                    severity="warning",
                    message=(
                        f"heading level jumps from h{last_level} "
                        f"(\"{(last_text or '').strip()[:40]}\") straight to "
                        f"h{level} (\"{heading.text.strip()[:40]}\") - skips "
                        f"{level - last_level - 1} level(s)."
                    ),
                    line=heading.line,
                    snippet=snippet,
                )
            )
        last_level = level
        last_text = heading.text
    return findings
