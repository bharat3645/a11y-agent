# a11y-agent

**A context-aware accessibility smell scanner for HTML, JSX and TSX.**

Structural accessibility linters like [axe-core](https://github.com/dequelabs/axe-core)
and [eslint-plugin-jsx-a11y](https://github.com/jsx-eslint/eslint-plugin-jsx-a11y)
are excellent at catching *presence/absence* problems: is there an `alt`
attribute, is there an accessible name, is contrast high enough. What they
cannot do is judge the *content* of markup that is technically well-formed
but semantically useless - because that requires reading the text like a
human would, not just walking the DOM.

`a11y-agent` statically scans a repository for exactly that class of
issue: alt text that's just a filename, link text that means nothing out
of context, meaning conveyed only through color, and heading levels that
skip a rung on the ladder.

## The gap this fills (vs. axe-core / eslint-plugin-jsx-a11y)

| Already covered well by axe-core / jsx-a11y | Covered by a11y-agent instead |
|---|---|
| `<img>` missing an `alt` attribute entirely (`image-alt`, `alt-text`) | `alt="IMG_2384.png"`, `alt="image"` - present but meaningless |
| `<a>`/`<button>` with no accessible name at all (`link-name`, `anchor-has-content`) | `<a>click here</a>` - has text, but the text is vague |
| Color **contrast** ratio (`color-contrast`) | Meaning conveyed **only** via color word in prose ("shown in red") with no other cue |
| Heading exists / is not empty | Heading **order** - jumping from `<h1>` straight to `<h4>` |

These tools are complementary, not competitors - run both. axe-core/jsx-a11y
should stay in your CI as the structural safety net; a11y-agent is meant to
run alongside them (or in a periodic content-quality pass) to catch the
issues that need judgement rather than a DOM query.

## Install

```bash
git clone https://github.com/bharat3645/a11y-agent.git
cd a11y-agent
pip install -r requirements.txt   # only pytest, for running the test suite
```

No dependencies are required to actually run the scanner - it's pure
standard-library Python (`re`, `argparse`, `dataclasses`). `requirements.txt`
only pulls in `pytest` for the test suite, and optionally `anthropic` if you
want the real LLM-backed suggestion path (see below).

## Usage

```bash
python -m a11y_agent scan <path> [--format text|markdown|json] [--suggest-fix]
```

- `<path>` - a file or directory. Directories are walked recursively,
  skipping `node_modules`, `dist`, `build`, `.git`, and similar.
- `--format` - `text` (default, terminal-friendly), `markdown` (for PR
  comments/reports), or `json` (machine-readable, for CI tooling).
- `--suggest-fix` - attach a heuristic, diff-style fix *preview* to each
  finding. **This never modifies files on disk** - it only prints a
  `- old` / `+ new` suggestion for a human to apply.

### Example

Given:

```html
<h1>Welcome</h1>
<h3>Skipped section</h3>
<img src="foo.png" alt="IMG_2384.png">
<img src="bar.png" alt="">
<a href="/pricing-plans">click here</a>
<p>Fields shown in red are required.</p>
<img src="chart.png" alt="picture">
```

Running `python -m a11y_agent scan sample --format text` produces:

```
sample/page.html
  [WARNING] heading-hierarchy-skip (line 2)
      heading level jumps from h1 ("Welcome") straight to h3 ("Skipped section") - skips 1 level(s).
      > <h3>Skipped section</h3>
  [WARNING] generic-alt-text (line 3)
      alt="IMG_2384.png" looks like a filename or generic placeholder rather than a description of the image content.
      > <img src="foo.png" alt="IMG_2384.png">
  [WARNING] empty-alt-no-decorative-signal (line 4)
      img has alt="" with no role="presentation"/"none" or aria-hidden="true" to signal it is intentionally decorative; confirm this image truly conveys no information.
      > <img src="bar.png" alt="">
  [WARNING] non-descriptive-link-text (line 5)
      link text "click here" is not descriptive out of context, and has no aria-label/title to compensate (href suggests: "pricing plans").
      > <a href="/pricing-plans">click here</a>
  [INFO   ] color-only-meaning (line 6)
      phrase "shown in red" conveys meaning via color with no nearby icon/label/aria-* cue for users who cannot perceive color.
      > Fields shown in red are required.
  [WARNING] generic-alt-text (line 7)
      alt="picture" looks like a filename or generic placeholder rather than a description of the image content.
      > <img src="chart.png" alt="picture">

6 finding(s) across 1 file(s) (1 info, 5 warning)
```

With `--suggest-fix`, each finding additionally gets a diff-style preview, e.g.:

```
      suggestion: - <img src="foo.png" alt="IMG_2384.png">
+ <img src="foo.png" alt="Skipped section (image)">
```

`--format json` emits the same findings as a JSON array of objects with
`file`, `rule_id`, `severity`, `message`, `line`, `snippet`, `suggestion`.

## The rules, and their heuristic limitations

`a11y-agent` uses a lightweight regex-based tag/attribute extractor
(`a11y_agent/parser.py`), **not** a full HTML5 or JSX/Babel AST parser. This
is a deliberate scope decision: a real parser adds a heavy dependency and
still can't resolve JSX conditionals/expressions statically, so it wouldn't
eliminate the fundamental heuristic limitations below - it would just move
where they show up. Every rule is a **hint for human review**, not an
authoritative verdict.

### 1. Generic / filename-like alt text (`generic-alt-text`, `empty-alt-no-decorative-signal`)

Flags `alt` values that are filename patterns (`img_1234`, anything ending
in `.png/.jpg/.jpeg/.gif/.svg/.webp`), or literally "image"/"photo"/
"picture". Also flags `alt=""` when there's no `role="presentation"`/
`role="none"`/`aria-hidden="true"` alongside it to confirm the emptiness is
intentional (a correctly-decorative `alt=""` with one of those signals is
*not* flagged - that's the right pattern).

- **False positives:** an image whose genuinely-correct alt text happens to
  contain the word "photo" (e.g. "Photo ID card") is fine; only an *exact*
  match against the generic-word list is flagged, but names like `img_42`
  used as legitimate shorthand would still trip the rule.
- **False negatives:** alt text that's present, doesn't look like a
  filename, and is *still* wrong (e.g. `alt="a picture of some text"`) is
  not caught - judging whether alt text actually matches image content
  requires real image understanding, out of scope for a static text scanner.
- Alt values that are JSX expressions (`alt={photo.caption}`) are skipped
  entirely rather than guessed at, since their runtime value is unknown.

### 2. Non-descriptive link text (`non-descriptive-link-text`)

Flags `<a>` text matching a blocklist (`click here`, `read more`, `here`,
`link`, `more`, `learn more`, `this link`, `click`) case-insensitively,
*unless* the link has a non-empty `aria-label` or `title`.

- **False positives:** a "More" pagination link with a screen-reader-only
  sibling span for context (not an `aria-label` on the anchor itself) will
  still be flagged, because the rule only inspects the anchor's own
  attributes and text, not sibling markup.
- **False negatives:** longer-but-still-vague phrases ("check this out",
  "go here now") aren't on the blocklist.

### 3. Color-only meaning (`color-only-meaning`)

Flags prose matching `"<verb> in <color>"` (e.g. "shown in red", "marked in
green") or `"the <color> <noun>"` (e.g. "the red button") *unless* the same
source line also contains a non-color cue word (`icon`, `label`, `aria-`,
`title=`, `alt=`, `role=`, `asterisk`, `* required`, etc).

- This is the bluntest heuristic in the project, by necessity - it's a
  regex over prose, not language understanding.
- **False positives:** "the red carpet" would match the color+noun pattern
  even though it has nothing to do with UI state.
- **False negatives:** any phrasing outside the two trigger patterns (e.g.
  "green means success") isn't caught at all; a cue word one line above or
  below (rather than on the same line) won't suppress a real finding, but
  also won't be picked up as satisfying one.
- Cue-word matching is textual, so a component name like `<IconWarning />`
  counts as a cue even if it isn't actually adjacent at render time.

### 4. Heading hierarchy skips (`heading-hierarchy-skip`)

Tracks `<h1>`-`<h6>` levels **in document order within a single file** and
flags any jump of more than one level between consecutive headings (h1 -> h3,
h2 -> h5, etc). Going back *up* the tree (h3 -> h2) is never flagged - only
forward skips are a problem.

- **False positives:** JSX conditionally-rendered branches that never
  actually appear together in one render are still compared as if they
  share a document flow.
- **False negatives:** modern component-based frontends routinely split a
  document's headings across multiple files (e.g. a layout renders `<h1>`,
  a page component assumes it and starts at `<h3>`) - this is invisible to
  a per-file scan by design. A document that never starts at h1 at all
  (e.g. a card component meant to be embedded under an existing h2) is also
  not flagged, since only the *jumps between consecutive headings* are
  checked, not the absolute starting level.

## `--suggest-fix`: what it does and doesn't do

For **generic/empty alt text**, the suggestion looks for a `<figcaption>`
within a few lines of the image, then the nearest preceding heading, and
proposes that as alt text; if neither exists, it proposes a `TODO:` marker.

For **non-descriptive link text**, the suggestion appends a plain-words
version of the link's `href` slug (e.g. `/docs/getting-started` ->
"getting started") to the existing text as a starting point.

Every suggestion is rendered as a `- before` / `+ after` diff-style string
in the report. **`a11y-agent` never writes to your source files** - the
`--suggest-fix` flag only changes what gets printed.

## Optional LLM-backed suggestions

`a11y_agent.suggest.suggest_fix_with_llm(finding, surrounding_context,
llm_client=None)` is a second, more powerful suggestion path:

- With no `ANTHROPIC_API_KEY` environment variable set and no `llm_client`
  passed in, it falls back to the same deterministic template logic
  described above - **this is the path exercised by the test suite**, so
  the project works fully offline/without any API key.
- If `ANTHROPIC_API_KEY` is set (or an `llm_client` is injected directly,
  useful for testing), it calls the real Anthropic Messages API to draft a
  suggestion grounded in the offending snippet and surrounding context.
  This path is implemented but intentionally **not exercised by CI/tests**
  in this repository, since it costs real API calls and needs a live key.

This function is not (yet) wired into the CLI; it's available as a library
call for callers who want LLM-quality suggestions instead of the
templates `--suggest-fix` uses today.

## Running the tests

```bash
pip install -r requirements.txt
pytest
```

The suite (`tests/`) covers all four rules with true-positive and
true-negative cases each, an end-to-end pass over "bad" and "good" fixture
HTML files, report generation in all three formats, the file walker's
exclusion rules, and both branches (template fallback + injected client) of
the LLM suggestion path.

## Known non-goals

- Not a replacement for axe-core / eslint-plugin-jsx-a11y - run both.
- Not a JSX/TSX AST parser - see the heuristic notes above and in
  `a11y_agent/parser.py`'s module docstring.
- Not a runtime/browser-based tool - purely static text analysis, so
  anything determined at render time (conditional rendering, computed
  props) is out of reach.

## License

MIT (c) 2026 Bharat Singh Parihar. See [LICENSE](LICENSE).
