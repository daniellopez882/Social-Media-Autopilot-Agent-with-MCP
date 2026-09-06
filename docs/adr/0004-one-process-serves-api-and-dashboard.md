# ADR 0004 — One process serves the API and the dashboard; every state change needs a key

**Status:** accepted

## Context

The dashboard was a static page served by `run_dashboard.py` on port 3000 —
an `http.server` whose document root was the repository. Reproduced with the
repo's own handler: `/app/main.py`, `/requirements.txt` and `/.env.example`
came back 200. A real `.env` would have too.

Because the page and the API were on different origins, the API carried
`allow_origins=["*"]` with `allow_credentials=True`.

No route required any credential. `POST /client/profile?client_id=X`
overwrote any client's profile; `POST /approve/{uuid}` released held content
with the UUID as the only secret.

There was no `GET` for pending approvals, so the page only knew about items
it had created in the same browser session; a reload orphaned them on the
server, where they lived until the process died.

## Decision

- The API serves `index.html` at `/`. `run_dashboard.py` is deleted. CORS is
  off unless `CORS_ALLOW_ORIGINS` is set, and never a wildcard.
- Every route that reads or changes state requires `X-API-Key`, compared in
  constant time. With no key configured the routes are open — allowed only in
  development, refused by preflight elsewhere, logged at startup.
- `GET /approvals` lists pending items. The store expires them and is bounded.
- `client_id` is a path parameter validated against `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`.
- `task_type` is a `Literal`; `scheduling` is not in the public set because it
  is the post-approval re-entry and bypasses guardrails.

## Consequences

The page holds the key in `sessionStorage` (this tab only). For a
single-operator tool that is acceptable and documented; it is not a
multi-user design.

State is still process memory: a restart drops profiles and pending approvals,
and replicas would not share them. The README says so. `sqlalchemy` was in
`requirements.txt` and imported by nothing; it is gone rather than left to
suggest persistence that does not exist.
