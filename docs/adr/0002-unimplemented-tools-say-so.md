# ADR 0002 — A tool that is not implemented says so

**Status:** accepted

## Context

None of the four social tools was connected to a live API. That was also true
of the previous version, but the previous version reported otherwise as soon
as a credential variable was set:

```python
token = os.getenv("BUFFER_ACCESS_TOKEN")
if not token:
    return f"MOCK: Successfully scheduled to {platform} via Buffer at {scheduled_time}"
return f"LIVE: Scheduled content to {platform} via Buffer API"
```

Reproduced with a socket guard: the "LIVE" branch made no request. The
Instagram tool returned `{"status": "Live data fetched", "reach": 12000}` — a
fabricated metric — the same way. The system was *more* misleading with
credentials configured than without.

## Decision

Every tool returns one of two shapes:

- `{"status": "mock", ...}` in mock mode, with values that are obviously
  synthetic (`reach: 0`, `#MockTrendOne`), never plausible-looking numbers.
- `{"status": "not_implemented", "provider": ..., "credential_present": ...,
  "message": "... no request was made."}` otherwise.

`IMPLEMENTED_PROVIDERS` is a module constant, and it is empty. It stays empty
until an integration exists and is tested against a recorded response.

A test invokes every tool with credentials present and a socket guard, and
asserts the status. A second test walks the module's AST and fails if any
non-docstring string literal contains "live".

## Consequences

The scheduler node, in live mode, now tells the model to report which
scheduling calls returned `not_implemented`, so the output says "nothing was
scheduled" instead of implying otherwise.

The README's feature list shrank accordingly. What remains is what the code
does.
