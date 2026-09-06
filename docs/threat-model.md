# Threat model

Scope: this repository as it runs — one FastAPI process serving an API and a
single-operator dashboard, holding state in memory. No multi-tenancy, no
persistence, no live platform integrations (see [ADR 0002](adr/0002-unimplemented-tools-say-so.md)).

## What it holds

| Asset | Where | Why it matters |
|---|---|---|
| `OPENAI_API_KEY` | `.env` / environment | Billable |
| Platform tokens (`TWITTER_*`, `META_*`, `BUFFER_*`) | `.env` | Unused by any live path today; would grant posting as the brand once one exists |
| `API_KEY` | `.env`, and the operator's browser tab (`sessionStorage`) | Gates every state change |
| Brand profiles | process memory | Audience, banned topics, competitor names — a client's marketing posture |
| Pending approvals | process memory | Generated content awaiting a human decision |

`.env` is gitignored; CI fails if it is ever tracked; history was scanned and
holds no credential.

## Threats

### T1 — Unauthenticated state changes *(was open)*

Reproduced on the original: `POST /client/profile?client_id=k` with no
credentials overwrote the profile; `POST /approve/{uuid}` released held
content with the UUID as the only secret.

**Controls.** `X-API-Key` on every route that reads or changes state,
constant-time comparison; refused in production if unset (preflight). Approval
ids are 128-bit `uuid4` hex and additionally require the key.

**Residual.** One shared key; no per-operator identity or audit trail beyond
application logs.

### T2 — Repository served over HTTP *(was open)*

`run_dashboard.py` served the repository root. Reproduced: `/app/main.py`,
`/requirements.txt`, `/.env.example` all 200. A real `.env` would have been
served identically.

**Controls.** The file is deleted; the API serves only `index.html`, from a
fixed path, at `/`. A test asserts the file is absent.

### T3 — Fake success *(was open)*

Tools reported `LIVE: Scheduled ...` and `Live data fetched, reach: 12000`
without making a request; the entry point defaulted to mock mode. An operator
could believe posts were published that never were.

**Controls.** Mock mode opt-in and labelled on every payload; unimplemented
tools return `not_implemented`; the dashboard shows no number it did not get
from the API. Tests with a socket guard; an AST test over string literals.

### T4 — Prompt injection

Today, no third-party text enters the prompts: the tools that would fetch
trends, comments or metrics are not implemented. The brand profile is
operator-supplied. When an integration lands, engagement text and trend
results become untrusted input to the content and engagement agents, and the
banned-topic guardrail is a keyword check, not a defence against instructions.

**Controls now.** Guardrails hold content naming a banned topic; a human
approves before scheduling; `MAX_CONTENT_CHARS` bounds generated text.

**Residual.** Nothing prevents an injected instruction from producing
plausible, on-topic content that passes the keyword check. The human approval
step is the control, and it only applies to content that was held.

### T5 — Error text reaching callers

`detail=str(e)` on every 500 returned provider and internal text. Errors now
return a correlation id; the detail is logged with `exc_info`.

### T6 — Wildcard CORS with credentials

`allow_origins=["*"]` with `allow_credentials=True`. CORS is now off by
default (same origin) and never a wildcard.

### T7 — Resource growth

`PENDING_APPROVALS` and `BRAND_DB` grew without bound. The approval store
expires entries (`APPROVAL_TTL_SECONDS`) and drops the oldest at
`APPROVAL_MAX_PENDING`. Profiles are bounded by validation (list lengths,
string lengths) but not counted; no rate limit exists.

### T8 — Supply chain

Eleven unpinned packages, two of them imported by nothing. Everything is
pinned; `pip-audit` and `bandit` run in CI; `crewai`'s `<3.14` constraint is
now a declared `requires-python` rather than a silent fallback.

## Not addressed

- No persistence: a restart loses profiles and pending approvals.
- No rate limiting on model spend.
- One shared API key; the dashboard keeps it in `sessionStorage`.
- The live crewai path is tested with fakes and by construction, not against
  the OpenAI API.
