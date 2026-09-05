"""
The HTTP surface.

Reproduced on the original code: ``POST /client/profile?client_id=k`` with no
credentials overwrote the profile (200); ``POST /run`` with
``task_type="nonsense"`` returned 200 and the untouched initial state.
"""

from __future__ import annotations

from typing import ClassVar

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.graphs.orchestrator import get_graph
from app.main import app
from tests.conftest import AUTH, PROFILE

RUN = {"client_id": "nexus", "task_type": "campaign"}

STATE_CHANGING = [
    ("post", "/client/profile/nexus", PROFILE),
    ("get", "/client/profiles", None),
    ("get", "/client/profile/nexus", None),
    ("post", "/run", RUN),
    ("get", "/approvals", None),
    ("post", "/approve/abc", None),
    ("post", "/reject/abc", None),
]


class TestAuthentication:
    @pytest.mark.parametrize("method,path,body", STATE_CHANGING)
    def test_every_protected_route_rejects_a_missing_key(self, client, method, path, body):
        response = client.request(method.upper(), path, json=body)
        assert response.status_code == 401, f"{method} {path}: {response.status_code}"
        assert response.headers.get("WWW-Authenticate") == "X-API-Key"

    @pytest.mark.parametrize("method,path,body", STATE_CHANGING)
    def test_every_protected_route_rejects_a_wrong_key(self, client, method, path, body):
        response = client.request(method.upper(), path, json=body, headers={"X-API-Key": "nope"})
        assert response.status_code == 401

    def test_the_configured_key_is_not_echoed(self, client):
        response = client.post("/run", json=RUN, headers={"X-API-Key": "nope"})
        assert AUTH["X-API-Key"] not in response.text

    @pytest.mark.parametrize("path", ["/health", "/ready", "/"])
    def test_ops_routes_need_no_key(self, client, path):
        assert client.get(path).status_code in (200, 503)

    def test_with_no_key_configured_routes_are_open_in_development(self, client, monkeypatch):
        """Preflight refuses this outside development; here it is allowed and logged."""
        monkeypatch.setattr(settings, "API_KEY", "")
        assert client.get("/client/profiles").status_code == 200


class TestProfiles:
    def test_a_profile_can_be_saved_and_read_back(self, registered):
        response = registered.get("/client/profile/nexus", headers=AUTH)
        assert response.status_code == 200
        assert response.json()["brand_name"] == PROFILE["brand_name"]

    def test_saved_profiles_are_listed(self, registered):
        assert registered.get("/client/profiles", headers=AUTH).json()["client_ids"] == ["nexus"]

    def test_an_unknown_profile_is_404(self, client):
        assert client.get("/client/profile/ghost", headers=AUTH).status_code == 404

    @pytest.mark.parametrize("client_id", ["has space", "a.b", "-leading", "x" * 65, "ü"])
    def test_a_malformed_client_id_is_rejected(self, client, client_id):
        response = client.post(f"/client/profile/{client_id}", headers=AUTH, json=PROFILE)
        assert response.status_code == 422, response.text

    def test_a_profile_without_a_brand_name_is_rejected(self, client):
        body = {k: v for k, v in PROFILE.items() if k != "brand_name"}
        assert client.post("/client/profile/nexus", headers=AUTH, json=body).status_code == 422

    def test_an_oversized_list_is_rejected(self, client):
        body = {**PROFILE, "banned_topics": [f"t{i}" for i in range(51)]}
        assert client.post("/client/profile/nexus", headers=AUTH, json=body).status_code == 422

    def test_blank_list_entries_are_dropped(self, client):
        body = {**PROFILE, "banned_topics": ["politics", "  ", ""]}
        client.post("/client/profile/nexus", headers=AUTH, json=body)
        saved = client.get("/client/profile/nexus", headers=AUTH).json()
        assert saved["banned_topics"] == ["politics"]


class TestRun:
    def test_an_unknown_client_is_404(self, client):
        assert client.post("/run", headers=AUTH, json=RUN).status_code == 404

    @pytest.mark.parametrize("task_type", ["nonsense", "", "CAMPAIGN", "scheduling"])
    def test_an_unknown_or_internal_task_type_is_422_not_a_silent_200(self, registered, task_type):
        """ "scheduling" re-enters after approval and bypasses guardrails; it is not public."""
        response = registered.post("/run", headers=AUTH, json={**RUN, "task_type": task_type})
        assert response.status_code == 422, response.text

    def test_a_campaign_runs_every_stage_in_mock_mode(self, registered):
        response = registered.post("/run", headers=AUTH, json=RUN)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "completed"
        assert body["mock_mode"] is True
        result = body["result"]
        assert result["trend_data"].startswith("[MOCK]")
        assert result["generated_content"].startswith("[MOCK]")
        assert result["scheduling_status"].startswith("[MOCK]")

    def test_the_mock_flag_is_on_every_response(self, registered):
        """A caller must be able to tell mock output from real output."""
        body = registered.post("/run", headers=AUTH, json=RUN).json()
        assert "mock_mode" in body

    def test_a_content_task_skips_trend_analysis(self, registered):
        body = registered.post("/run", headers=AUTH, json={**RUN, "task_type": "content"}).json()
        assert body["result"].get("trend_data") is None
        assert body["result"]["generated_content"]

    def test_engagement_and_analytics_finish(self, registered):
        for task_type, field in (("engagement", "messages"), ("analytics", "analytics_report")):
            body = registered.post(
                "/run", headers=AUTH, json={**RUN, "task_type": task_type}
            ).json()
            assert body["status"] == "completed"
            assert body["result"][field]

    def test_the_response_is_json_serialisable_including_the_profile(self, registered):
        body = registered.post("/run", headers=AUTH, json=RUN).json()
        assert body["result"]["brand_profile"]["brand_name"] == PROFILE["brand_name"]


class TestApprovalFlow:
    # "post" appears as a whole word in the mock content.
    HELD: ClassVar[dict] = {**PROFILE, "banned_topics": ["post"]}

    def _hold(self, client):
        client.post("/client/profile/held", headers=AUTH, json=self.HELD)
        response = client.post(
            "/run", headers=AUTH, json={"client_id": "held", "task_type": "content"}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "awaiting_approval", body
        return body

    def test_a_banned_topic_holds_the_content(self, client):
        body = self._hold(client)
        assert "post" in body["reason"]
        assert body["approval_id"]
        assert body["content"].startswith("[MOCK]")

    def test_a_banned_topic_inside_another_word_does_not_hold(self, client):
        client.post(
            "/client/profile/free", headers=AUTH, json={**PROFILE, "banned_topics": ["ost"]}
        )
        body = client.post(
            "/run", headers=AUTH, json={"client_id": "free", "task_type": "content"}
        ).json()
        assert body["status"] == "completed"

    def test_held_items_are_listed(self, client):
        body = self._hold(client)
        listed = client.get("/approvals", headers=AUTH).json()
        assert listed["count"] == 1
        assert listed["approvals"][0]["approval_id"] == body["approval_id"]
        assert listed["approvals"][0]["client_id"] == "held"

    def test_the_listing_does_not_expose_the_full_graph_state(self, client):
        self._hold(client)
        item = client.get("/approvals", headers=AUTH).json()["approvals"][0]
        assert set(item) == {"approval_id", "client_id", "reason", "content", "created_at"}

    def test_approving_sends_it_to_scheduling_and_removes_it(self, client):
        approval_id = self._hold(client)["approval_id"]
        response = client.post(f"/approve/{approval_id}", headers=AUTH)
        assert response.status_code == 200, response.text
        assert response.json()["result"]["scheduling_status"].startswith("[MOCK]")
        assert client.get("/approvals", headers=AUTH).json()["count"] == 0

    def test_an_approval_can_only_be_used_once(self, client):
        approval_id = self._hold(client)["approval_id"]
        client.post(f"/approve/{approval_id}", headers=AUTH)
        assert client.post(f"/approve/{approval_id}", headers=AUTH).status_code == 404

    def test_rejecting_records_the_feedback_from_the_body(self, client):
        """Feedback used to be a query parameter on a POST."""
        approval_id = self._hold(client)["approval_id"]
        response = client.post(
            f"/reject/{approval_id}", headers=AUTH, json={"feedback": "too salesy"}
        )
        assert response.status_code == 200
        assert response.json()["feedback"] == "too salesy"
        assert client.get("/approvals", headers=AUTH).json()["count"] == 0

    def test_rejecting_without_a_body_uses_a_default(self, client):
        approval_id = self._hold(client)["approval_id"]
        assert client.post(f"/reject/{approval_id}", headers=AUTH).status_code == 200

    @pytest.mark.parametrize("path", ["/approve/ghost", "/reject/ghost"])
    def test_an_unknown_approval_is_404(self, client, path):
        assert client.post(path, headers=AUTH).status_code == 404


class TestErrorContract:
    def test_a_failure_does_not_leak_internal_detail(self, registered, monkeypatch):
        """The handlers returned detail=str(e)."""

        class Boom:
            def invoke(self, state):
                raise RuntimeError("sk-live-SECRET while calling https://internal.example/v1")

        monkeypatch.setattr(app.state, "graph", Boom())
        response = registered.post("/run", headers=AUTH, json=RUN)
        assert response.status_code == 500
        assert "SECRET" not in response.text
        assert "internal.example" not in response.text
        assert response.json()["detail"]["request_id"]

    def test_a_caller_supplied_request_id_is_echoed(self, registered, monkeypatch):
        class Boom:
            def invoke(self, state):
                raise RuntimeError("boom")

        monkeypatch.setattr(app.state, "graph", Boom())
        response = registered.post("/run", headers={**AUTH, "X-Request-ID": "req-42"}, json=RUN)
        assert response.json()["detail"]["request_id"] == "req-42"


class TestOps:
    def test_health_reports_mock_mode(self, client):
        body = client.get("/health").json()
        assert body["mock_mode"] is True
        assert body["environment"] == "testing"

    def test_ready_reports_each_check(self, client):
        body = client.get("/ready").json()
        assert body["ready"] is True
        assert set(body["checks"]) == {"configuration", "graph", "auth", "model"}

    def test_ready_is_503_on_an_invalid_configuration(self, client, monkeypatch):
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")  # with MOCK_MODE on
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["checks"]["configuration"]["ok"] is False

    def test_the_dashboard_is_served_by_the_api(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert "<title>" in response.text

    def test_the_graph_is_compiled_once(self, client):
        assert get_graph() is get_graph()
        assert app.state.graph is get_graph()


class TestStartup:
    def test_startup_refuses_production_with_mock_mode(self, monkeypatch):
        """
        The previous server would have started and served mock data. Raising
        in lifespan makes uvicorn exit non-zero, which is what the container
        job asserts.
        """
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        with pytest.raises(RuntimeError, match="MOCK_MODE"), TestClient(app):
            pass

    def test_startup_refuses_production_without_an_api_key(self, monkeypatch):
        monkeypatch.setattr(settings, "ENVIRONMENT", "production")
        monkeypatch.setattr(settings, "MOCK_MODE", False)
        monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
        monkeypatch.setattr(settings, "API_KEY", "")
        with pytest.raises(RuntimeError, match="API_KEY"), TestClient(app):
            pass
