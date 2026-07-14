from a11y_agent.rules import link_text


def test_flags_click_here():
    html = '<a href="/pricing">click here</a>'
    findings = link_text.check(html, "f.html")
    assert len(findings) == 1
    assert findings[0].rule_id == link_text.RULE_ID


def test_flags_read_more():
    html = '<a href="/blog/post-1">Read more</a>'
    findings = link_text.check(html, "f.html")
    assert len(findings) == 1


def test_flags_bare_here_case_insensitive():
    html = '<a href="/docs">HERE</a>'
    findings = link_text.check(html, "f.html")
    assert len(findings) == 1


def test_does_not_flag_click_here_with_aria_label():
    html = '<a href="/pricing" aria-label="View pricing plans">click here</a>'
    findings = link_text.check(html, "f.html")
    assert findings == []


def test_does_not_flag_click_here_with_title():
    html = '<a href="/pricing" title="View pricing plans">click here</a>'
    findings = link_text.check(html, "f.html")
    assert findings == []


def test_does_not_flag_descriptive_link_text():
    html = '<a href="/pricing">View our pricing plans</a>'
    findings = link_text.check(html, "f.html")
    assert findings == []


def test_href_slug_hint_included_in_message():
    html = '<a href="/docs/getting-started">click here</a>'
    findings = link_text.check(html, "f.html")
    assert len(findings) == 1
    assert "getting started" in findings[0].message
