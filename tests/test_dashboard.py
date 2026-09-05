"""
The dashboard page and how it is served.

Two things were wrong. ``run_dashboard.py`` served the *repository root* over
HTTP -- reproduced: ``/app/main.py``, ``/requirements.txt`` and
``/.env.example`` all came back 200, and a real ``.env`` would have too. And
the page itself displayed hardcoded figures ("Weekly Growth +12.4%", "14.2K
Total Accounts Reached", "#AIAutomation 8.4k") styled as live metrics.
"""

from __future__ import annotations

import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = (ROOT / "index.html").read_text(encoding="utf-8")


class TestServing:
    def test_the_root_serving_server_is_gone(self):
        assert not (ROOT / "run_dashboard.py").exists()

    def test_the_page_calls_the_api_on_its_own_origin(self):
        assert "127.0.0.1" not in PAGE
        assert "localhost" not in PAGE
        assert re.search(r'const API_BASE\s*=\s*"";', PAGE)


class TestNoFabricatedMetrics:
    @pytest.mark.parametrize(
        "fragment",
        ["14.2K", "12.4%", "8.4k", "#AIAutomation", "#FutureOfWork", "Total Accounts Reached"],
    )
    def test_the_old_figures_are_absent(self, fragment):
        assert fragment not in PAGE

    def test_no_percentage_or_count_is_hardcoded_in_markup(self):
        """Any number shown must arrive from the API. Markup may not carry one."""
        markup = PAGE.split("<script>")[0]
        body = markup[markup.index("<body>") :]
        assert not re.search(r">\s*[+-]?\d[\d.,]*\s*[%Kk]\s*<", body), (
            "a metric is hardcoded in the page"
        )


class TestContract:
    def test_it_lists_pending_approvals_from_the_api(self):
        assert '"/approvals"' in PAGE

    def test_it_sends_the_api_key_header(self):
        assert '"X-API-Key"' in PAGE

    def test_it_registers_profiles_through_the_api(self):
        assert '"/client/profile/"' in PAGE

    def test_reject_sends_feedback_in_the_body(self):
        assert re.search(r'"/reject/"[^;]*\{\s*feedback\s*\}', PAGE, re.DOTALL)

    def test_the_key_is_kept_in_session_storage_not_local_storage(self):
        assert "sessionStorage" in PAGE
        assert "localStorage" not in PAGE

    def test_every_fetch_result_is_checked(self):
        """The old reject() ignored the response entirely."""
        assert "resp.ok" in PAGE
