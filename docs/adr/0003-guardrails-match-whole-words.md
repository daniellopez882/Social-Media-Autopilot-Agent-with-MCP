# ADR 0003 — Guardrails match whole words, and production code carries no test hooks

**Status:** accepted

## Context

```python
for topic in banned:
    if topic.lower() in content.lower():
        triggered.append(topic)
```

Reproduced: banning `art` held "Let's start the week with a smart plan";
banning `X` held "Next week we expand". A check that fires on almost every
post trains the reviewer to click Approve without reading the reason, which
defeats the one control the system has.

Alongside it, in the content node:

```python
if banned_topics:
    content += f" (Note: We mention {banned_topics[0]} for testing purposes)"
```

Every brand with a banned list was escalated on every run. The repository's
approval test passed *because* of this line.

## Decision

`app/guardrails.py` matches each topic as a whole word: `re.escape` (so `C++`
and `#politics` work), case-insensitive, with lookarounds rather than `\b`
so a topic that starts or ends with a non-word character still anchors
correctly. The hardcoded `"politics"`/`"competitor"` check labelled
"(simulation)" is removed; the brand's list is the list.

No node contains behaviour that exists for a test. The approval flow is
tested by giving a brand a banned topic that the mock content genuinely
contains as a word.

## Consequences

A topic inside another word no longer holds content. A one-letter topic such
as `X` matches only the standalone word. Both are covered by tests that were
first run against the old code to confirm they failed.
