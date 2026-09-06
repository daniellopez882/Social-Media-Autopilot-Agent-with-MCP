"""
Graph nodes.

Reproduced on the original code: the mock content node appended the brand's
first banned topic to its output; ``MOCK_MODE`` was frozen at import.
"""

from __future__ import annotations

import json
import sys

import pytest

from app.agents import factory
from app.agents.factory import CrewAINotInstalled, LLMNotConfigured
from app.config import settings
from app.graphs import nodes
from app.graphs.nodes import MOCK_PREFIX
from app.schemas.state import BrandProfile

BRAND = BrandProfile(
    brand_name="Nexus AI",
    target_audience="CTOs",
    content_pillars=["AI"],
    active_platforms=["linkedin"],
    banned_topics=["CompetitorX"],
)


def state(**extra):
    return {"client_id": "c", "brand_profile": BRAND, "messages": [], **extra}


class TestMockOutputsAreLabelled:
    @pytest.mark.parametrize(
        "node,field",
        [
            (nodes.trend_analyzer_node, "trend_data"),
            (nodes.content_generator_node, "generated_content"),
            (nodes.campaign_scheduler_node, "scheduling_status"),
            (nodes.analytics_reporter_node, "analytics_report"),
        ],
    )
    def test_every_mock_result_carries_the_prefix(self, node, field, mock_mode):
        mock_mode(True)
        assert node(state())[field].startswith(MOCK_PREFIX)

    def test_mock_engagement_appends_a_labelled_message(self, mock_mode):
        mock_mode(True)
        out = nodes.engagement_responder_node(state(messages=["earlier"]))
        assert out["messages"][0] == "earlier"
        assert out["messages"][-1].startswith(MOCK_PREFIX)

    def test_mock_scheduling_says_nothing_was_scheduled(self, mock_mode):
        mock_mode(True)
        assert (
            "nothing was scheduled" in nodes.campaign_scheduler_node(state())["scheduling_status"]
        )


class TestNoInjection:
    def test_mock_content_never_contains_the_banned_topic(self, mock_mode):
        """The old node did this on purpose, "for testing purposes"."""
        mock_mode(True)
        content = nodes.content_generator_node(state())["generated_content"]
        assert "CompetitorX" not in content

    def test_a_brand_with_banned_topics_is_not_held_by_default(self, mock_mode):
        mock_mode(True)
        content = nodes.content_generator_node(state())["generated_content"]
        out = nodes.guardrails_node(state(generated_content=content))
        assert out["requires_human_approval"] is False
        assert out["escalation_reason"] is None


class TestGuardrailsNode:
    def test_a_whole_word_hit_holds_the_content(self):
        out = nodes.guardrails_node(state(generated_content="Beats CompetitorX easily."))
        assert out["requires_human_approval"] is True
        assert "CompetitorX" in out["escalation_reason"]

    def test_a_dict_profile_is_accepted(self):
        out = nodes.guardrails_node(
            {"brand_profile": {"banned_topics": ["politics"]}, "generated_content": "politics"}
        )
        assert out["requires_human_approval"] is True

    def test_no_profile_means_nothing_to_check(self):
        assert (
            nodes.guardrails_node({"generated_content": "anything"})["requires_human_approval"]
            is False
        )


class TestMockModeIsReadAtCallTime:
    def test_flipping_the_setting_changes_the_next_call(self, mock_mode, monkeypatch):
        mock_mode(True)
        assert nodes.trend_analyzer_node(state())["trend_data"].startswith(MOCK_PREFIX)
        mock_mode(False)
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
        with pytest.raises(LLMNotConfigured, match="OPENAI_API_KEY"):
            nodes.trend_analyzer_node(state())


class TestLiveModeFailsLoudly:
    def test_a_missing_model_key_names_the_setting(self, mock_mode, monkeypatch):
        mock_mode(False)
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "")
        with pytest.raises(LLMNotConfigured, match="OPENAI_API_KEY"):
            nodes.content_generator_node(state())

    def test_a_missing_crewai_names_the_package_and_the_alternative(self, mock_mode, monkeypatch):
        """The old factory substituted a do-nothing Agent class on ImportError."""
        mock_mode(False)
        monkeypatch.setattr(factory, "build_llm", lambda: object())
        monkeypatch.setitem(sys.modules, "crewai", None)  # makes `import crewai` raise ImportError
        with pytest.raises(CrewAINotInstalled, match="MOCK_MODE=true"):
            nodes.content_generator_node(state())


class FakeCrewAI:
    """Just enough of crewai's surface for the nodes to run."""

    class Agent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Task:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Crew:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def kickoff(self):
            class Output:
                raw = "generated text"

                def __str__(self):
                    return "CrewOutput(...)"

            return Output()


class TestLiveModeReturnsText:
    def test_a_crew_output_is_reduced_to_its_text(self, mock_mode, monkeypatch):
        """CrewOutput objects used to land in Optional[str] fields and break JSON serialisation."""
        mock_mode(False)
        monkeypatch.setattr(factory, "build_llm", lambda: object())
        monkeypatch.setattr(factory, "crewai_module", lambda: FakeCrewAI)
        monkeypatch.setattr(nodes, "crewai_module", lambda: FakeCrewAI)
        out = nodes.content_generator_node(state())
        assert out["generated_content"] == "generated text"
        json.dumps(out)

    def test_text_helper_handles_each_shape(self):
        class WithRaw:
            raw = "from raw"

        assert nodes._text(WithRaw()) == "from raw"
        assert nodes._text("plain") == "plain"
        assert nodes._text(42) == "42"

    def test_generated_content_is_bounded(self, mock_mode, monkeypatch):
        mock_mode(False)
        monkeypatch.setattr(factory, "build_llm", lambda: object())

        class Huge(FakeCrewAI):
            class Crew(FakeCrewAI.Crew):
                def kickoff(self):
                    class Output:
                        raw = "x" * (settings.MAX_CONTENT_CHARS + 500)

                    return Output()

        monkeypatch.setattr(factory, "crewai_module", lambda: Huge)
        monkeypatch.setattr(nodes, "crewai_module", lambda: Huge)
        out = nodes.content_generator_node(state())
        assert len(out["generated_content"]) == settings.MAX_CONTENT_CHARS


class TestFactory:
    def test_agents_receive_the_brand_prompt_and_no_delegation(self, monkeypatch):
        monkeypatch.setattr(factory, "crewai_module", lambda: FakeCrewAI)
        agent = factory.AgentFactory(BRAND.model_dump(), llm=object()).create_content_generator()
        assert "Nexus AI" in agent.kwargs["backstory"]
        assert agent.kwargs["allow_delegation"] is False

    def test_the_model_name_is_configuration(self, monkeypatch):
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
        captured = {}

        class FakeCrewAI:
            class LLM:
                def __init__(self, **kwargs):
                    captured.update(kwargs)

        monkeypatch.setattr(factory, "crewai_module", lambda: FakeCrewAI)
        factory.build_llm()
        assert captured["model"] == "gpt-4o-mini"
        assert captured["api_key"] == "sk-test", (
            "the key must be passed explicitly, not via os.environ"
        )

    def test_the_key_is_passed_explicitly_to_the_real_crewai_llm(self, monkeypatch):
        """A key configured only in .env must reach crewai without touching os.environ."""
        crewai = pytest.importorskip("crewai")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test-not-real")
        llm = factory.build_llm()
        # crewai.LLM(...) hands back a provider-specific object, so assert on
        # behaviour rather than on the class.
        assert getattr(llm, "model", None) == settings.OPENAI_MODEL
        assert callable(getattr(llm, "call", None))
        assert crewai is not None
