"""
Brand-safety check on generated content.

The previous check lived inline in ``guardrails_node``::

    for topic in banned:
        if topic.lower() in content.lower():
            triggered.append(topic)

Substring containment. A brand that bans "art" had every post mentioning
"start", "smart" or "party" held for human review; banning "AI" caught "said",
"rain" and "email"; banning the platform "X" caught everything. The check that
was meant to stop a rare bad post instead stopped almost all of them, and a
reviewer who sees a false alarm on every run stops reading the reason.

Two further things were wrong with the surrounding code:

* A hardcoded ``"politics" in content or "competitor" in content`` labelled
  ``(simulation)`` fired regardless of the brand's own list.
* The content node, in mock mode, **appended the brand's first banned topic
  to the generated content** "for testing purposes" -- so any brand with a
  banned list was escalated on every run, and the repository's approval test
  passed only because of that.

This module matches whole words, escapes the topic, and does nothing else.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class GuardrailResult:
    triggered: list[str] = field(default_factory=list)

    @property
    def requires_human_approval(self) -> bool:
        return bool(self.triggered)

    @property
    def reason(self) -> str | None:
        if not self.triggered:
            return None
        return "Guardrail alert: banned topic(s) present: " + ", ".join(self.triggered)


def _pattern(topic: str) -> re.Pattern[str] | None:
    """
    A whole-word, case-insensitive pattern for one banned topic.

    ``\\b`` is not enough on its own: a topic like "#politics" or "C++" starts
    or ends with a non-word character, and ``\\b`` would then require a word
    character *outside* it. Lookarounds for "not preceded/followed by a word
    character" behave correctly for both.
    """
    cleaned = topic.strip()
    if not cleaned:
        return None
    return re.compile(r"(?<!\w)" + re.escape(cleaned) + r"(?!\w)", re.IGNORECASE)


def evaluate(content: str, banned_topics: list[str]) -> GuardrailResult:
    """Which of ``banned_topics`` appear in ``content`` as whole words."""
    text = content or ""
    triggered: list[str] = []
    seen: set[str] = set()
    for topic in banned_topics or []:
        pattern = _pattern(str(topic))
        if pattern is None:
            continue
        key = topic.strip().lower()
        if key in seen:
            continue
        if pattern.search(text):
            triggered.append(topic.strip())
            seen.add(key)
    return GuardrailResult(triggered=triggered)
