"""Rule: generic / filename-like / unexplained-empty alt text on <img>.

What it catches that plain linters don't:
    eslint-plugin-jsx-a11y's `alt-text` rule and axe-core's `image-alt` check
    only verify that an `alt` *attribute is present*. Neither judges whether
    the value is actually useful. `alt="IMG_2384.png"` or `alt="image"`
    passes both of those checks today while being useless to a screen
    reader user.

Heuristic and known risks (documented per project requirements):
    * False positives: an image whose *真实* filename genuinely is
      meaningful text (rare) would still be flagged; a photographer's site
      that legitimately uses "photo" as a caption word could be flagged.
    * False negatives: alt text that is present, non-generic-looking, and
      still wrong ("a picture of some text" -> passes) is not caught -
      that requires real image understanding, out of scope for a static
      text scanner.
    * Dynamic alt values (`alt={someVar}`) cannot be evaluated statically
      and are skipped rather than guessed at.
"""

import re

from ..findings import Finding
from ..parser import find_self_closing, get_line_snippet

RULE_ID = "generic-alt-text"
RULE_ID_EMPTY = "empty-alt-no-decorative-signal"

_FILENAME_ALT_RE = re.compile(r"^(img|image|dsc|photo|pic)[_-]?\d+$", re.IGNORECASE)
_FILE_EXT_RE = re.compile(r"\.(png|jpe?g|gif|svg|webp|bmp|tiff?)$", re.IGNORECASE)
_GENERIC_WORDS = {"image", "photo", "picture", "img", "graphic", "pic"}

_DECORATIVE_SIGNALS = (
    ("role", "presentation"),
    ("role", "none"),
    ("aria-hidden", "true"),
)


def _is_dynamic(value: str) -> bool:
    return value.startswith("{") and value.endswith("}")


def _is_decorative(attrs: dict) -> bool:
    for attr_name, expected in _DECORATIVE_SIGNALS:
        value = attrs.get(attr_name, "")
        if value.lower() == expected:
            return True
    return False


def _looks_filename_like(alt: str) -> bool:
    stripped = alt.strip()
    if _FILENAME_ALT_RE.match(stripped):
        return True
    if _FILE_EXT_RE.search(stripped):
        return True
    if stripped.lower() in _GENERIC_WORDS:
        return True
    return False


def check(text: str, filepath: str):
    findings = []
    for img in find_self_closing(text, "img"):
        if "alt" not in img.attrs:
            # Missing alt entirely is exactly what axe-core / jsx-a11y
            # already flag well; out of scope here.
            continue

        alt = img.attrs["alt"]
        if _is_dynamic(alt):
            continue

        snippet = get_line_snippet(text, img.line) or img.raw.strip()

        if alt.strip() == "":
            if not _is_decorative(img.attrs):
                findings.append(
                    Finding(
                        file=filepath,
                        rule_id=RULE_ID_EMPTY,
                        severity="warning",
                        message=(
                            "img has alt=\"\" with no role=\"presentation\"/"
                            "\"none\" or aria-hidden=\"true\" to signal it is "
                            "intentionally decorative; confirm this image "
                            "truly conveys no information."
                        ),
                        line=img.line,
                        snippet=snippet,
                    )
                )
            continue

        if _looks_filename_like(alt):
            findings.append(
                Finding(
                    file=filepath,
                    rule_id=RULE_ID,
                    severity="warning",
                    message=(
                        f"alt=\"{alt}\" looks like a filename or generic "
                        "placeholder rather than a description of the image "
                        "content."
                    ),
                    line=img.line,
                    snippet=snippet,
                )
            )
    return findings
