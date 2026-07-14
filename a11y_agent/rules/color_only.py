"""Rule: color-only meaning heuristic.

What it catches that plain linters don't:
    axe-core has a `color-contrast` rule (does foreground/background have
    enough contrast) but nothing checks whether *meaning* is conveyed by
    color alone in the copy itself, e.g. "fields shown in red are
    required" or "the red button cancels the order" with no icon, label,
    or aria-* attribute reinforcing the distinction for colorblind users
    or screen reader users (who never see color at all). This is a WCAG
    1.4.1 (Use of Color) concern that no structural linter can evaluate,
    because it requires reading prose, not markup structure.

Heuristic and known risks:
    * This is a blunt, regex-based text heuristic, not language
      understanding. It will flag "the red carpet" (false positive) as
      readily as "shown in red" (true positive) if a color+noun pattern
      matches and there's no cue word nearby.
    * False negatives: any phrasing that doesn't match one of the two
      trigger patterns ("displayed in {color}" / "the {color} {noun}")
      slips through entirely, e.g. "green means success".
    * "Nearby" is defined as the *same source line* as the match, not a
      semantic scope like "this sentence" or "this component" - a phrase
      that wraps across a line break may miss a same-sentence cue word on
      the next line (false positive), and a long single line containing
      several unrelated pieces of text sharing one cue word can suppress
      a real finding on that line (false negative).
    * Cue words are matched textually (e.g. the literal string "icon"), so
      an <IconWarning /> component reference counts as a cue even if it
      isn't actually rendered next to this text at runtime.
"""

import re

from ..findings import Finding
from ..parser import line_index

RULE_ID = "color-only-meaning"

_COLORS = r"red|green|blue|yellow|orange|purple|pink"

_PATTERNS = [
    re.compile(
        r"\b(?:shown|marked|highlighted|displayed|indicated|colou?red)\s+in\s+(" + _COLORS + r")\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bthe\s+(" + _COLORS + r")\s+(button|text|label|indicator|icon|dot|badge|status|field|banner)\b",
        re.IGNORECASE,
    ),
]

_CUE_WORD_RE = re.compile(
    r"icon|label|aria-|aria_|title=|alt=|role=|\basterisk\b|\*\s*required|"
    r"\bbold\b|\bunderline\b|\bstrikethrough\b|\bshape\b|\bpattern\b|\btext[- ]?says\b",
    re.IGNORECASE,
)

_TEXT_NODE_RE = re.compile(r">([^<>{}]+)<")



def check(text: str, filepath: str):
    """Scan text nodes for color-only meaning phrases.

    The "nearby" window used for the cue-word check is deliberately scoped
    to the *same source line* as the match (rather than a fixed character
    radius spanning the whole file) so that unrelated markup several lines
    away - e.g. an aria-label on a link earlier in the document - doesn't
    accidentally suppress a real finding. This still lets a same-line
    sibling element's cue (e.g. `<span class="icon-warning">` right next
    to the flagged phrase) count, which is the common real-world pattern.
    The trade-off (documented in the module docstring/README) is that a
    cue placed on an *adjacent* line to a long-wrapped sentence will not be
    picked up.
    """
    findings = []
    offset_to_line = line_index(text)
    lines = text.splitlines()

    for node_match in _TEXT_NODE_RE.finditer(text):
        segment = node_match.group(1)
        seg_start, seg_end = node_match.span(1)
        if not segment.strip():
            continue

        for pattern in _PATTERNS:
            for m in pattern.finditer(segment):
                abs_start = seg_start + m.start()
                line = offset_to_line(abs_start)
                line_text = lines[line - 1] if 1 <= line <= len(lines) else segment
                if _CUE_WORD_RE.search(line_text):
                    continue
                findings.append(
                    Finding(
                        file=filepath,
                        rule_id=RULE_ID,
                        severity="info",
                        message=(
                            f"phrase \"{m.group(0).strip()}\" conveys meaning "
                            "via color with no nearby icon/label/aria-* cue "
                            "for users who cannot perceive color."
                        ),
                        line=line,
                        snippet=segment.strip(),
                    )
                )
    return findings
