import os
from contextlib import contextmanager

from a11y_agent.findings import Finding
from a11y_agent.suggest import suggest_fix_with_llm


@contextmanager
def _without_api_key():
    """Temporarily ensure ANTHROPIC_API_KEY is unset, restoring it after."""
    old = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        yield
    finally:
        if old is not None:
            os.environ["ANTHROPIC_API_KEY"] = old


def test_falls_back_to_template_without_api_key_or_client():
    finding = Finding(
        file="f.html",
        rule_id="generic-alt-text",
        severity="warning",
        message="alt looks like a filename",
        line=3,
        snippet='<img src="a.png" alt="a.png">',
    )
    with _without_api_key():
        result = suggest_fix_with_llm(finding, "A chart showing quarterly revenue growth")
    assert "template, no LLM" in result
    assert "quarterly revenue growth" in result.lower() or "chart" in result.lower()


def test_falls_back_to_todo_when_no_context_available():
    finding = Finding(
        file="f.html",
        rule_id="generic-alt-text",
        severity="warning",
        message="alt looks like a filename",
        line=3,
        snippet='<img src="a.png" alt="a.png">',
    )
    with _without_api_key():
        result = suggest_fix_with_llm(finding, "")
    assert "TODO" in result


def test_link_text_fallback_uses_href_slug():
    finding = Finding(
        file="f.html",
        rule_id="non-descriptive-link-text",
        severity="warning",
        message="vague link text",
        line=1,
        snippet='<a href="/pricing-plans">click here</a>',
    )
    with _without_api_key():
        result = suggest_fix_with_llm(finding, "")
    assert "pricing plans" in result


def test_uses_injected_llm_client_when_provided():
    class FakeResponse:
        content = [type("Block", (), {"text": "A laptop showing the setup wizard"})()]

    class FakeClient:
        def __init__(self):
            self.messages = self

        def create(self, **kwargs):
            return FakeResponse()

    finding = Finding(
        file="f.html",
        rule_id="generic-alt-text",
        severity="warning",
        message="alt looks like a filename",
        line=3,
        snippet='<img src="a.png" alt="a.png">',
    )
    with _without_api_key():
        result = suggest_fix_with_llm(finding, "some context", llm_client=FakeClient())
    assert result == "A laptop showing the setup wizard"
