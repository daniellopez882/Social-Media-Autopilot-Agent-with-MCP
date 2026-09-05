# ADR 0001 — Mock mode is opt-in, read at call time, and refused in production

**Status:** accepted

## Context

```python
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
try:
    from crewai import Task, Crew
except ImportError:
    MOCK_MODE = True
```

Three properties of those five lines, each verified on the original code:

1. The default was *on*. An operator who never set the variable ran a system
   whose scheduler returned `"MOCK SCHEDULED: All posts queued for 9 AM."` and
   whose API reported that as a completed run.
2. It was read once, at import. Setting `MOCK_MODE=false` after any import
   changed nothing. The repository's own test scripts set it inside
   `if __name__ == "__main__"` — after import — and it had no effect.
3. If `crewai` was not importable, the system *silently became a mock
   system*. `crewai` declares `<3.14`; on a machine whose default Python is
   3.14 the install fails and the app runs, returning mock data, with no
   indication anywhere that it did.

## Decision

`Settings.MOCK_MODE` defaults to `False`. Every node and tool reads
`settings.MOCK_MODE` when it runs. Every mock result carries a `[MOCK]` prefix
or `status: "mock"`. Every API response that ran the graph includes
`mock_mode: true|false`.

Preflight refuses to start with `ENVIRONMENT=production` and mock mode on.
CI asserts both halves: that the value is `False` with the variable unset,
and that a production configuration with it on exits non-zero.

A missing `crewai` outside mock mode raises `CrewAINotInstalled` with a
message naming the package and the alternative. It does not fall back.

## Consequences

Running without a model key now requires saying so (`MOCK_MODE=true`). That
is one more line in `.env.example` and the first thing the README shows.

A caller can always tell mock output from real output, from the payload alone.
