"""
Shared fixtures.

Environment is set before ``app`` is imported: ``app.config.settings`` is
built at import time, and the previous code's own test scripts set
``MOCK_MODE`` inside ``if __name__ == "__main__"`` -- after import -- which
did nothing under pytest.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("API_KEY", "test-key-not-real")
os.environ.setdefault("OPENAI_API_KEY", "")

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

API_KEY = os.environ["API_KEY"]
AUTH = {"X-API-Key": API_KEY}

PROFILE = {
    "brand_name": "Nexus AI",
    "brand_voice": "bold",
    "target_audience": "CTOs",
    "content_pillars": ["Generative AI", "Agentic Workflows"],
    "active_platforms": ["linkedin", "twitter"],
}


@pytest.fixture
def client():
    """A client whose app has been through startup (lifespan), with clean stores."""
    with TestClient(app) as test_client:
        app.state.profiles.clear()
        app.state.approvals.clear()
        yield test_client


@pytest.fixture
def registered(client):
    """A client with one profile registered under ``nexus``."""
    response = client.post("/client/profile/nexus", headers=AUTH, json=PROFILE)
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def mock_mode(monkeypatch):
    """Flip mock mode without re-importing anything."""

    def apply(value: bool):
        monkeypatch.setattr(settings, "MOCK_MODE", value)

    return apply


@pytest.fixture
def no_network(monkeypatch):
    """Any attempt to open a socket fails the test."""
    import socket

    def refuse(*args, **kwargs):
        raise AssertionError("a network connection was attempted")

    monkeypatch.setattr(socket.socket, "connect", refuse)
