from a11y_agent.rules import generic_alt


def test_flags_filename_like_alt():
    html = '<img src="a.png" alt="IMG_2384.png">'
    findings = generic_alt.check(html, "f.html")
    assert len(findings) == 1
    assert findings[0].rule_id == generic_alt.RULE_ID
    assert findings[0].line == 1


def test_flags_generic_word_alt():
    html = '<img src="a.png" alt="image">'
    findings = generic_alt.check(html, "f.html")
    assert len(findings) == 1
    assert findings[0].rule_id == generic_alt.RULE_ID


def test_flags_numeric_img_pattern():
    html = '<img src="a.png" alt="img_00123">'
    findings = generic_alt.check(html, "f.html")
    assert len(findings) == 1


def test_flags_empty_alt_without_decorative_signal():
    html = '<img src="a.png" alt="">'
    findings = generic_alt.check(html, "f.html")
    assert len(findings) == 1
    assert findings[0].rule_id == generic_alt.RULE_ID_EMPTY


def test_does_not_flag_descriptive_alt():
    html = '<img src="a.png" alt="Three engineers reviewing a whiteboard diagram">'
    findings = generic_alt.check(html, "f.html")
    assert findings == []


def test_does_not_flag_empty_alt_with_role_presentation():
    html = '<img src="a.png" alt="" role="presentation">'
    findings = generic_alt.check(html, "f.html")
    assert findings == []


def test_does_not_flag_empty_alt_with_aria_hidden():
    html = '<img src="a.png" alt="" aria-hidden="true">'
    findings = generic_alt.check(html, "f.html")
    assert findings == []


def test_does_not_flag_missing_alt_attribute_entirely():
    html = '<img src="a.png">'
    findings = generic_alt.check(html, "f.html")
    assert findings == []


def test_skips_dynamic_jsx_alt_expression():
    jsx = '<img src={photo.url} alt={photo.caption} />'
    findings = generic_alt.check(jsx, "f.jsx")
    assert findings == []
