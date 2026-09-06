"""
Banned-topic matching.

The previous check was ``topic.lower() in content.lower()``. Reproduced on the
original code: banning "art" held "Let's start the week with a smart plan";
banning "X" held "Next week we expand".
"""

from __future__ import annotations

import pytest

from app.guardrails import evaluate


class TestNoFalsePositives:
    def test_a_topic_inside_another_word_does_not_match(self):
        assert evaluate("Let's start the week with a smart plan.", ["art"]).triggered == []

    def test_a_one_letter_topic_does_not_match_every_word_containing_it(self):
        assert evaluate("Next week we expand.", ["X"]).triggered == []

    def test_ai_does_not_match_said_rain_or_email(self):
        assert evaluate("She said the rain delayed the email.", ["AI"]).triggered == []


class TestTruePositives:
    def test_a_whole_word_matches(self):
        assert evaluate("We love modern art.", ["art"]).triggered == ["art"]

    def test_matching_is_case_insensitive(self):
        assert evaluate("POLITICS again.", ["politics"]).triggered == ["politics"]

    def test_a_topic_at_the_start_of_the_text(self):
        assert evaluate("Politics is off-limits.", ["politics"]).triggered == ["politics"]

    def test_a_topic_followed_by_punctuation(self):
        assert evaluate("Say nothing about politics!", ["politics"]).triggered == ["politics"]

    def test_a_multi_word_topic(self):
        assert evaluate("Our competitor Acme Corp launched.", ["Acme Corp"]).triggered == [
            "Acme Corp"
        ]

    def test_a_topic_with_regex_metacharacters(self):
        """re.escape: "C++" must match "C++" and not be parsed as a quantifier."""
        assert evaluate("Written in C++ for speed.", ["C++"]).triggered == ["C++"]

    def test_a_topic_starting_with_a_non_word_character(self):
        """A leading '#' is not a word character, so a plain \\b would fail here."""
        assert evaluate("Trending: #politics today", ["#politics"]).triggered == ["#politics"]

    def test_the_letter_x_matches_as_a_word(self):
        assert evaluate("Post it on X tomorrow.", ["X"]).triggered == ["X"]


class TestResult:
    def test_no_triggers_means_no_approval_needed(self):
        result = evaluate("Nothing to see.", ["politics"])
        assert result.requires_human_approval is False
        assert result.reason is None

    def test_the_reason_names_every_trigger(self):
        result = evaluate("politics and religion", ["politics", "religion"])
        assert result.requires_human_approval is True
        assert "politics" in result.reason
        assert "religion" in result.reason

    def test_duplicate_topics_are_reported_once(self):
        assert evaluate("politics", ["politics", "Politics", " politics "]).triggered == [
            "politics"
        ]

    @pytest.mark.parametrize("topics", [[], [""], ["   "], None])
    def test_no_topics_never_triggers(self, topics):
        assert evaluate("anything at all", topics).triggered == []

    @pytest.mark.parametrize("content", ["", None])
    def test_empty_content_never_triggers(self, content):
        assert evaluate(content, ["politics"]).triggered == []
