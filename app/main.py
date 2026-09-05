"""
HTTP surface.

What changed, and the defect behind each change:

* Every state-changing route requires ``X-API-Key``. Before, anyone who could
  reach the port could overwrite any client's brand profile
  (``POST /client/profile?client_id=...``) or approve held content for
  publication with nothing but the approval's UUID.
* The dashboard is served from ``/`` by this process. It used to be served by
  a separate ``http.server`` on port 3000 whose document root was the
  repository -- ``.env`` included -- and the cross-origin gap between the two
  was closed with ``allow_origins=["*"]`` plus ``allow_credentials=True``.
* ``task_type`` is validated. An unknown value used to produce a 200 with the
  untouched initial state.
* The graph is compiled once at startup, not per request.
* ``GET /approvals`` exists, so a dashboard reload no longer orphans held items.
* Errors return a request id, not ``str(exc)``.
* Startup runs preflight and refuses an invalid configuration -- production
  with mock mode on, or with no API key.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi import Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from app import preflight
from app.approvals import ApprovalStore
from app.config import settings
from app.graphs.orchestrator import get_graph
from app.schemas.state import BrandProfile, PublicTaskType

logger = logging.getLogger("socialpilot.api")

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "index.html"

CLIENT_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"
ClientId = Annotated[str, PathParam(pattern=CLIENT_ID_PATTERN)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=settings.LOG_LEVEL, format="%(levelname)-8s %(name)s %(message)s")
    problems = preflight.run()
    if problems:
        # Raising here makes uvicorn exit non-zero. The previous code would
        # have served mock data from a production environment.
        raise RuntimeError("refusing to start: " + "; ".join(problems))

    app.state.graph = get_graph()
    app.state.profiles: dict[str, BrandProfile] = {}
    app.state.approvals = ApprovalStore(
        ttl_seconds=settings.APPROVAL_TTL_SECONDS,
        max_pending=settings.APPROVAL_MAX_PENDING,
    )
    logger.info("ready: mock_mode=%s environment=%s", settings.MOCK_MODE, settings.ENVIRONMENT)
    yield


app = FastAPI(
    title="SocialPilot API",
    version="0.2.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    openapi_url=None if settings.is_production else "/openapi.json",
)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["X-API-Key", "Content-Type"],
    )


# -- auth -------------------------------------------------------------------

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: Annotated[str | None, Depends(_api_key_header)]) -> None:
    """
    Constant-time key check.

    With no key configured the check is skipped. Preflight refuses that
    outside development, so "skipped" only ever happens on a developer's
    machine, and it is logged at startup.
    """
    if not settings.has_api_key:
        return
    if not api_key or not secrets.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "X-API-Key"},
        )


Protected = Depends(require_api_key)


# -- models -----------------------------------------------------------------


class RunRequest(BaseModel):
    client_id: str = Field(pattern=CLIENT_ID_PATTERN)
    task_type: PublicTaskType = "campaign"


class RejectRequest(BaseModel):
    feedback: str = Field(default="Rejected by operator", max_length=2000)


def _internal_error(request_id: str) -> HTTPException:
    return HTTPException(
        status_code=500,
        detail={
            "code": "processing_failed",
            "message": "The request could not be processed. Quote the request id to support.",
            "request_id": request_id,
        },
    )


def _serialisable(state: dict[str, Any]) -> dict[str, Any]:
    out = dict(state)
    brand = out.get("brand_profile")
    if isinstance(brand, BrandProfile):
        out["brand_profile"] = brand.model_dump()
    out.pop("next_step", None)
    return out


# -- ops --------------------------------------------------------------------


@app.get("/health", tags=["ops"])
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "mock_mode": settings.MOCK_MODE,
        "version": app.version,
    }


@app.get("/ready", tags=["ops"])
async def ready(request: Request) -> JSONResponse:
    problems = settings.problems()
    checks: dict[str, dict[str, Any]] = {
        "configuration": {"ok": not problems, "detail": "; ".join(problems) or "valid"},
        "graph": {
            "ok": getattr(request.app.state, "graph", None) is not None,
            "detail": "compiled",
        },
        "auth": {
            "ok": settings.has_api_key or not settings.is_production,
            "detail": "API_KEY set" if settings.has_api_key else "open (development only)",
        },
    }
    if settings.MOCK_MODE:
        checks["model"] = {"ok": True, "detail": "mock mode; no model is used"}
    else:
        try:
            import crewai  # noqa: F401

            crew_ok = True
        except ImportError:
            crew_ok = False
        checks["model"] = {
            "ok": crew_ok and bool(settings.OPENAI_API_KEY.strip()),
            "detail": f"crewai={'installed' if crew_ok else 'MISSING'}; "
            f"OPENAI_API_KEY={'set' if settings.OPENAI_API_KEY.strip() else 'UNSET'}",
        }
    is_ready = all(check["ok"] for check in checks.values())
    return JSONResponse(
        status_code=200 if is_ready else 503, content={"ready": is_ready, "checks": checks}
    )


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    if not DASHBOARD.is_file():
        raise HTTPException(status_code=404, detail="dashboard not found")
    return FileResponse(DASHBOARD, media_type="text/html")


# -- profiles ---------------------------------------------------------------


@app.post("/client/profile/{client_id}", dependencies=[Protected], tags=["profiles"])
async def upsert_profile(
    client_id: ClientId, profile: BrandProfile, request: Request
) -> dict[str, str]:
    request.app.state.profiles[client_id] = profile
    return {"message": "Profile saved", "client_id": client_id}


@app.get("/client/profiles", dependencies=[Protected], tags=["profiles"])
async def list_profiles(request: Request) -> dict[str, list[str]]:
    return {"client_ids": sorted(request.app.state.profiles)}


@app.get("/client/profile/{client_id}", dependencies=[Protected], tags=["profiles"])
async def get_profile(client_id: ClientId, request: Request) -> BrandProfile:
    profile = request.app.state.profiles.get(client_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Client profile not found")
    return profile


# -- runs and approvals -----------------------------------------------------


@app.post("/run", dependencies=[Protected], tags=["runs"])
async def run_task(body: RunRequest, request: Request) -> dict[str, Any]:
    profile = request.app.state.profiles.get(body.client_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Client profile not found")

    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    initial = {
        "client_id": body.client_id,
        "brand_profile": profile,
        "task_type": body.task_type,
        "messages": [],
        "requires_human_approval": False,
    }
    try:
        result = request.app.state.graph.invoke(initial)
    except Exception:
        logger.exception(
            "run failed [%s] client=%s task=%s", request_id, body.client_id, body.task_type
        )
        raise _internal_error(request_id) from None

    if result.get("requires_human_approval"):
        item = request.app.state.approvals.add(
            client_id=body.client_id,
            reason=result.get("escalation_reason") or "held by guardrails",
            content=result.get("generated_content") or "",
            state=result,
        )
        return {
            "status": "awaiting_approval",
            "approval_id": item.approval_id,
            "reason": item.reason,
            "content": item.content,
            "mock_mode": settings.MOCK_MODE,
        }

    return {
        "status": "completed",
        "task_type": body.task_type,
        "mock_mode": settings.MOCK_MODE,
        "result": _serialisable(result),
    }


@app.get("/approvals", dependencies=[Protected], tags=["approvals"])
async def list_approvals(request: Request) -> dict[str, Any]:
    items = request.app.state.approvals.list()
    return {"approvals": [item.summary() for item in items], "count": len(items)}


@app.post("/approve/{approval_id}", dependencies=[Protected], tags=["approvals"])
async def approve(approval_id: str, request: Request) -> dict[str, Any]:
    item = request.app.state.approvals.pop(approval_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Approval request not found")

    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    state = dict(item.state)
    state["requires_human_approval"] = False
    state["escalation_reason"] = None
    state["task_type"] = "scheduling"
    try:
        result = request.app.state.graph.invoke(state)
    except Exception:
        logger.exception("approve failed [%s] approval=%s", request_id, approval_id)
        raise _internal_error(request_id) from None

    return {
        "message": "Content approved and sent to scheduling",
        "mock_mode": settings.MOCK_MODE,
        "result": {"scheduling_status": result.get("scheduling_status")},
    }


@app.post("/reject/{approval_id}", dependencies=[Protected], tags=["approvals"])
async def reject(
    approval_id: str, request: Request, body: RejectRequest | None = None
) -> dict[str, str]:
    item = request.app.state.approvals.pop(approval_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    feedback = (body or RejectRequest()).feedback
    logger.info("rejected approval %s for %s: %s", approval_id, item.client_id, feedback)
    return {"message": "Content rejected", "feedback": feedback}
