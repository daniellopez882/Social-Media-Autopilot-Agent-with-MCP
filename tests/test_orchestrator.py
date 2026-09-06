"""Routing and graph shape."""

from __future__ import annotations

import pytest

from app.graphs.orchestrator import ENTRY_NODE, build_graph, get_graph, orchestrator_node
from app.schemas.state import PUBLIC_TASK_TYPES, TASK_TYPES, BrandProfile

BRAND = BrandProfile(brand_name="B", target_audience="T", active_platforms=["x"])


class TestRouting:
    def test_every_task_type_has_an_entry_node(self):
        assert set(ENTRY_NODE) == set(TASK_TYPES)

    def test_public_task_types_are_a_subset(self):
        assert set(PUBLIC_TASK_TYPES) < set(TASK_TYPES)
        assert "scheduling" not in PUBLIC_TASK_TYPES

    @pytest.mark.parametrize("task_type", TASK_TYPES)
    def test_known_types_route(self, task_type):
        assert orchestrator_node({"task_type": task_type})["next_step"] == ENTRY_NODE[task_type]

    @pytest.mark.parametrize("task_type", ["nonsense", None, "", "Campaign"])
    def test_unknown_types_raise_instead_of_ending_quietly(self, task_type):
        """The old node returned END, and the API turned that into a 200."""
        with pytest.raises(ValueError, match="task_type"):
            orchestrator_node({"task_type": task_type})


class TestGraph:
    def test_the_graph_is_built_once(self):
        assert get_graph() is get_graph()

    def test_build_graph_makes_a_fresh_instance(self):
        assert build_graph() is not build_graph()

    def _run(self, task_type, mock_mode, **extra):
        mock_mode(True)
        return get_graph().invoke(
            {
                "client_id": "c",
                "brand_profile": BRAND,
                "task_type": task_type,
                "messages": [],
                **extra,
            }
        )

    def test_campaign_visits_trends_content_guardrails_and_scheduling(self, mock_mode):
        out = self._run("campaign", mock_mode)
        assert out["trend_data"] and out["generated_content"] and out["scheduling_status"]
        assert out["requires_human_approval"] is False

    def test_content_skips_trends(self, mock_mode):
        out = self._run("content", mock_mode)
        assert out.get("trend_data") is None
        assert out["generated_content"]

    def test_a_hold_stops_before_scheduling(self, mock_mode):
        held = BrandProfile(brand_name="B", target_audience="T", banned_topics=["post"])
        out = self._run("content", mock_mode, brand_profile=held)
        assert out["requires_human_approval"] is True
        assert out.get("scheduling_status") is None

    def test_scheduling_entry_goes_straight_to_the_scheduler(self, mock_mode):
        out = self._run("scheduling", mock_mode, generated_content="approved text")
        assert out["scheduling_status"]
        assert out.get("trend_data") is None

    @pytest.mark.parametrize(
        "task_type,field", [("engagement", "messages"), ("analytics", "analytics_report")]
    )
    def test_single_node_tasks_end_after_their_node(self, mock_mode, task_type, field):
        out = self._run(task_type, mock_mode)
        assert out[field]
        assert out.get("scheduling_status") is None
