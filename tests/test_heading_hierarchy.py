from a11y_agent.rules import heading_hierarchy


def test_flags_h1_to_h3_skip():
    html = "<h1>Title</h1><h3>Subsection</h3>"
    findings = heading_hierarchy.check(html, "f.html")
    assert len(findings) == 1
    assert findings[0].rule_id == heading_hierarchy.RULE_ID
    assert "h1" in findings[0].message and "h3" in findings[0].message


def test_flags_h2_to_h5_skip():
    html = "<h1>Title</h1><h2>Section</h2><h5>Deep</h5>"
    findings = heading_hierarchy.check(html, "f.html")
    assert len(findings) == 1


def test_does_not_flag_valid_sequential_hierarchy():
    html = "<h1>Title</h1><h2>Section</h2><h3>Subsection</h3><h2>Another section</h2>"
    findings = heading_hierarchy.check(html, "f.html")
    assert findings == []


def test_does_not_flag_going_back_up_levels():
    # h3 -> h2 is a legitimate "close a subsection, start a new one" move,
    # not a skip (skips are only about jumps deeper by more than one level).
    html = "<h1>Title</h1><h2>Section</h2><h3>Sub</h3><h2>Next section</h2><h3>Sub</h3>"
    findings = heading_hierarchy.check(html, "f.html")
    assert findings == []


def test_single_heading_never_flagged():
    html = "<h3>Only heading</h3>"
    findings = heading_hierarchy.check(html, "f.html")
    assert findings == []
