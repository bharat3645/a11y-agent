from a11y_agent.rules import color_only


def test_flags_shown_in_color_with_no_cue():
    html = "<p>Fields shown in red are required.</p>"
    findings = color_only.check(html, "f.html")
    assert len(findings) == 1
    assert findings[0].rule_id == color_only.RULE_ID


def test_flags_the_color_noun_pattern():
    html = "<p>The red button cancels your order.</p>"
    findings = color_only.check(html, "f.html")
    assert len(findings) == 1


def test_does_not_flag_when_icon_cue_present_same_line():
    html = '<p>The red button <span class="icon-warning"></span> cancels your order.</p>'
    findings = color_only.check(html, "f.html")
    assert findings == []


def test_does_not_flag_when_aria_label_cue_present_same_line():
    html = '<p>Shown in red <span aria-label="warning">(!)</span> means the field failed validation.</p>'
    findings = color_only.check(html, "f.html")
    assert findings == []


def test_does_not_flag_unrelated_text():
    html = "<p>Please review the quarterly report before Friday.</p>"
    findings = color_only.check(html, "f.html")
    assert findings == []
