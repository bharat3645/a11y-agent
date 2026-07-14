import os
import tempfile

from a11y_agent.rules import run_all_rules
from a11y_agent.report import generate_report, to_json
from a11y_agent.suggest import suggest_fix
from a11y_agent.walker import find_source_files

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return fh.read()


def test_bad_fixture_trips_all_four_rules():
    text = _read("sample_bad.html")
    findings = run_all_rules(text, "sample_bad.html")
    rule_ids = {f.rule_id for f in findings}
    assert "generic-alt-text" in rule_ids
    assert "non-descriptive-link-text" in rule_ids
    assert "heading-hierarchy-skip" in rule_ids
    assert "color-only-meaning" in rule_ids


def test_good_fixture_is_clean():
    text = _read("sample_good.html")
    findings = run_all_rules(text, "sample_good.html")
    assert findings == []


def test_report_formats_render():
    text = _read("sample_bad.html")
    findings = run_all_rules(text, "sample_bad.html")
    assert "sample_bad.html" in generate_report(findings, "text")
    assert "## a11y-agent report" in generate_report(findings, "markdown")
    json_report = to_json(findings)
    assert '"rule_id"' in json_report


def test_suggest_fix_produces_diff_style_preview_without_writing_files():
    text = _read("sample_bad.html")
    findings = run_all_rules(text, "sample_bad.html")
    alt_finding = next(f for f in findings if f.rule_id == "generic-alt-text")
    suggestion = suggest_fix(alt_finding, text)
    assert suggestion.startswith("- ")
    assert "\n+ " in suggestion
    # must not touch the actual fixture file on disk
    assert _read("sample_bad.html") == text


def test_walker_finds_fixture_files_and_skips_excluded_dirs():
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "node_modules"))
        with open(os.path.join(tmp, "node_modules", "ignored.html"), "w") as fh:
            fh.write("<h1>x</h1>")
        with open(os.path.join(tmp, "app.jsx"), "w") as fh:
            fh.write("<div />")
        with open(os.path.join(tmp, "index.html"), "w") as fh:
            fh.write("<h1>x</h1>")

        found = sorted(os.path.basename(p) for p in find_source_files(tmp))
        assert found == ["app.jsx", "index.html"]
