"""
Settings and preflight.

Reproduced on the original code: with ``MOCK_MODE`` unset, ``nodes.MOCK_MODE``
was ``True``; setting the variable to ``false`` after import left it ``True``.
"""

from __future__ import annotations

import pytest

from app import preflight
from app.config import Settings


def build(**overrides) -> Settings:
    base = {"_env_file": None, "API_KEY": "k", "OPENAI_API_KEY": "sk-test", "MOCK_MODE": False}
    base.update(overrides)
    return Settings(**base)


class TestMockModeIsOptIn:
    def test_the_default_is_off(self, monkeypatch):
        monkeypatch.delenv("MOCK_MODE", raising=False)
        assert Settings(_env_file=None, OPENAI_API_KEY="x").MOCK_MODE is False

    @pytest.mark.parametrize("value", ["true", "True", "1", "yes"])
    def test_it_can_be_switched_on(self, value, monkeypatch):
        monkeypatch.setenv("MOCK_MODE", value)
        assert Settings(_env_file=None).MOCK_MODE is True


class TestBlankMockMode:
    @pytest.mark.parametrize("value", ["", "   "])
    def test_a_blank_value_means_off_not_a_crash(self, value, monkeypatch):
        """`MOCK_MODE=` with nothing after it is a plausible .env line."""
        monkeypatch.setenv("MOCK_MODE", value)
        assert Settings(_env_file=None, OPENAI_API_KEY="x").MOCK_MODE is False

    def test_garbage_is_still_refused(self, monkeypatch):
        monkeypatch.setenv("MOCK_MODE", "maybe")
        with pytest.raises(ValueError):
            Settings(_env_file=None)


class TestProblems:
    def test_a_valid_configuration_has_none(self):
        assert build().problems() == []

    def test_production_with_mock_mode_is_refused(self):
        problems = build(ENVIRONMENT="production", MOCK_MODE=True).problems()
        assert any("MOCK_MODE" in p for p in problems)

    def test_production_without_an_api_key_is_refused(self):
        problems = build(ENVIRONMENT="production", API_KEY="").problems()
        assert any("API_KEY" in p for p in problems)

    def test_both_problems_are_reported_together(self):
        problems = build(ENVIRONMENT="production", API_KEY="", MOCK_MODE=True).problems()
        assert len(problems) == 2

    def test_live_mode_without_a_model_key_is_refused(self):
        problems = build(MOCK_MODE=False, OPENAI_API_KEY="").problems()
        assert any("OPENAI_API_KEY" in p for p in problems)

    def test_mock_mode_needs_no_model_key(self):
        assert build(MOCK_MODE=True, OPENAI_API_KEY="").problems() == []

    def test_development_without_an_api_key_is_allowed(self):
        assert build(ENVIRONMENT="development", API_KEY="").problems() == []

    def test_validate_or_raise_lists_everything(self):
        with pytest.raises(ValueError) as excinfo:
            build(ENVIRONMENT="production", API_KEY="", MOCK_MODE=True).validate_or_raise()
        assert "MOCK_MODE" in str(excinfo.value)
        assert "API_KEY" in str(excinfo.value)


class TestNormalisation:
    @pytest.mark.parametrize("value", ["production", "PRODUCTION", " Production "])
    def test_production_is_recognised(self, value):
        assert build(ENVIRONMENT=value).is_production is True

    def test_an_invalid_log_level_is_refused_at_load(self):
        with pytest.raises(ValueError, match="LOG_LEVEL"):
            build(LOG_LEVEL="VERBOSE")

    def test_cors_origins_are_parsed(self):
        assert build(CORS_ALLOW_ORIGINS="http://a, http://b,,").cors_origins == [
            "http://a",
            "http://b",
        ]

    def test_cors_is_empty_by_default(self):
        """The API serves the dashboard itself; no cross-origin access is needed."""
        assert build().cors_origins == []

    def test_whitespace_is_not_an_api_key(self):
        assert build(API_KEY="   ").has_api_key is False


class TestPreflightCommand:
    def test_exit_code_is_nonzero_on_problems(self, monkeypatch):
        monkeypatch.setattr(preflight, "settings", build(ENVIRONMENT="production", API_KEY=""))
        assert preflight.main() == preflight.EXIT_CONFIG

    def test_exit_code_is_zero_when_fit(self, monkeypatch):
        monkeypatch.setattr(preflight, "settings", build())
        assert preflight.main() == preflight.EXIT_OK

    def test_run_returns_the_problems(self, monkeypatch):
        monkeypatch.setattr(preflight, "settings", build(ENVIRONMENT="production", MOCK_MODE=True))
        assert preflight.run(log=False)
