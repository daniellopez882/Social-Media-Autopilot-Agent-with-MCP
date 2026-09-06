"""
The social tools.

Reproduced on the original code, with a socket guard proving no request was
made: ``buffer_post_scheduler`` returned "LIVE: Scheduled content to linkedin
via Buffer API" and ``instagram_analytics_fetcher`` returned
``{"status": "Live data fetched", "reach": 12000}`` whenever the credential
variable was set. Neither talked to anything.
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.tools import social_tools
from app.tools.social_tools import IMPLEMENTED_PROVIDERS, crewai_tools, get_all_tools

CALLS = {
    "twitter_trend_search": {"query": "ai"},
    "google_trends_analyzer": {"keyword": "ai"},
    "instagram_analytics_fetcher": {"client_id": "acct"},
    "buffer_post_scheduler": {"content": "c", "platform": "linkedin", "scheduled_time": "09:00"},
}

SUCCESS_WORDS = ("live", "scheduled to", "fetched", "success")


def _invoke(name):
    tool = next(t for t in get_all_tools() if t.name == name)
    return tool.invoke(CALLS[name])


@pytest.fixture
def credentials_present(monkeypatch):
    monkeypatch.setattr(settings, "TWITTER_API_KEY", "present")
    monkeypatch.setattr(settings, "META_ACCESS_TOKEN", "present")
    monkeypatch.setattr(settings, "BUFFER_ACCESS_TOKEN", "present")


class TestOutsideMockMode:
    @pytest.mark.parametrize("name", sorted(CALLS))
    def test_a_tool_never_claims_success_it_did_not_have(
        self, name, mock_mode, credentials_present, no_network
    ):
        mock_mode(False)
        result = _invoke(name)
        assert result["status"] == "not_implemented"
        rendered = str(result).lower()
        assert not any(word in rendered for word in SUCCESS_WORDS), rendered

    @pytest.mark.parametrize("name", sorted(CALLS))
    def test_the_result_says_whether_a_credential_was_present(
        self, name, mock_mode, credentials_present
    ):
        mock_mode(False)
        result = _invoke(name)
        assert "credential_present" in result
        assert result["message"]

    def test_a_credential_does_not_change_the_answer(self, mock_mode, monkeypatch):
        """With or without a token, an unimplemented integration is unimplemented."""
        mock_mode(False)
        monkeypatch.setattr(settings, "BUFFER_ACCESS_TOKEN", "")
        without = _invoke("buffer_post_scheduler")
        monkeypatch.setattr(settings, "BUFFER_ACCESS_TOKEN", "present")
        with_token = _invoke("buffer_post_scheduler")
        assert without["status"] == with_token["status"] == "not_implemented"
        assert without["credential_present"] is False
        assert with_token["credential_present"] is True

    def test_no_provider_is_claimed_as_implemented(self):
        """Empty is the honest value until an integration exists and is tested."""
        assert frozenset() == IMPLEMENTED_PROVIDERS

    def test_no_fabricated_metric_is_returned(self, mock_mode, credentials_present):
        mock_mode(False)
        result = _invoke("instagram_analytics_fetcher")
        assert "reach" not in result


class TestMockMode:
    @pytest.mark.parametrize("name", sorted(CALLS))
    def test_mock_results_are_labelled(self, name, mock_mode, no_network):
        mock_mode(True)
        assert _invoke(name)["status"] == "mock"

    def test_mock_analytics_do_not_invent_reach(self, mock_mode):
        mock_mode(True)
        assert _invoke("instagram_analytics_fetcher")["reach"] == 0

    def test_mock_mode_is_read_at_call_time(self, mock_mode):
        """The previous module read MOCK_MODE once at import."""
        mock_mode(True)
        assert _invoke("twitter_trend_search")["status"] == "mock"
        mock_mode(False)
        assert _invoke("twitter_trend_search")["status"] == "not_implemented"


class TestWiring:
    def test_every_tool_has_a_name_and_description(self):
        for tool in get_all_tools():
            assert tool.name
            assert tool.description

    def test_crewai_tools_returns_one_per_tool(self):
        assert len(crewai_tools()) == len(get_all_tools())

    def test_no_success_word_in_any_code_literal(self):
        """
        Asserted on string literals in the AST, excluding docstrings by node
        identity -- the module docstring quotes the old messages in order to
        explain them.
        """
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(social_tools))
        docstrings = set()
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if (
                isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef))
                and body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
            ):
                docstrings.add(id(body[0].value))
        literals = [
            node.value.lower()
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ]
        offenders = [text for text in literals if "live" in text and "nothing" not in text]
        assert not offenders, offenders


class TestCrewAIAdapters:
    """Only meaningful where crewai is importable, which the pinned environment guarantees."""

    def test_each_adapter_carries_its_tool_name_and_description(self):
        pytest.importorskip("crewai")
        names = [adapter.name for adapter in crewai_tools()]
        assert names == [tool.name for tool in get_all_tools()]
        assert all(adapter.description for adapter in crewai_tools())

    def test_each_adapter_dispatches_to_its_own_tool(self, mock_mode):
        """A class defined inside a loop would have bound every adapter to the last tool."""
        pytest.importorskip("crewai")
        mock_mode(True)
        by_name = {adapter.name: adapter for adapter in crewai_tools()}
        assert (
            by_name["buffer_post_scheduler"]._run(
                content="c", platform="linkedin", scheduled_time="09:00"
            )["platform"]
            == "linkedin"
        )
        assert by_name["twitter_trend_search"]._run(query="ai")["query"] == "ai"

    def test_adapters_are_accepted_by_a_crewai_agent(self, monkeypatch):
        """The original assignment of LangChain tools would have failed crewai's validation."""
        crewai = pytest.importorskip("crewai")
        agent = crewai.Agent(
            role="r",
            goal="g",
            backstory="b",
            tools=crewai_tools(),
            llm=crewai.LLM(model="gpt-4o", api_key="sk-test-not-real"),
            allow_delegation=False,
        )
        assert len(agent.tools) == len(get_all_tools())
