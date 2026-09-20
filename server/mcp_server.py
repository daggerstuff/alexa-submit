from __future__ import annotations

import logging
import os
import threading
import time
from secrets import compare_digest
from typing import Annotated, Any
from uuid import uuid4

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from server._version import __version__
from server.main import orchestrator
from server.observability import registry, render_prometheus, request_id_var
from server.scenario_authoring import validate_scenario as validate_scenario_definition
from server.scenarios import SCENARIOS, all_scenarios
from server.schemas.validation import (
    CohortProgress,
    CreateScenarioResult,
    DeleteScenarioResult,
    LearnerProgress,
    ScenarioValidation,
    SimulationAction,
    SimulationRequest,
    SimulationResponse,
)

logger = logging.getLogger("alexa_clinical_sim")

mcp = MCPServer(
    name="clinical-conversation-coach",
    title="Clinical Conversation Coach",
    version=__version__,
    description=(
        "A scenario-based clinical communication simulator for educational practice. "
        "It returns simulated patient turns and evidence-linked rubric feedback."
    ),
    instructions=(
        "Use only for educational simulation. Never use this server for real patient care, "
        "diagnosis, triage, or treatment decisions."
    ),
)


def _handle(request: SimulationRequest) -> SimulationResponse:
    """Run an orchestrator request, surfacing anticipated domain errors to the client."""
    try:
        return orchestrator.handle(request)
    except HTTPException as exc:
        raise ToolError(str(exc.detail)) from exc


class ScenarioListItem(BaseModel):
    scenario_id: str
    version: str
    title: str
    difficulty: str
    metric_ids: list[str]
    source: str = "builtin"


class ScenarioListResult(BaseModel):
    scenarios: list[ScenarioListItem]
    disclaimer: str


class SessionListItem(BaseModel):
    session_id: str
    scenario_id: str
    status: str
    turn_count: int


class SessionListResult(BaseModel):
    sessions: list[SessionListItem]


class DeleteSessionResult(BaseModel):
    status: str
    session_id: str


@mcp.tool(
    description="List the available educational simulation scenarios and their rubric versions.",
    structured_output=True,
)
def list_simulation_scenarios() -> ScenarioListResult:
    return ScenarioListResult(
        scenarios=[
            ScenarioListItem(
                scenario_id=scenario.scenario_id,
                version=scenario.version,
                title=scenario.title,
                difficulty=scenario.difficulty,
                metric_ids=[metric.metric_id for metric in scenario.metrics],
                source="builtin" if scenario.scenario_id in SCENARIOS else "custom",
            )
            for scenario in all_scenarios().values()
        ],
        disclaimer="Educational simulation only; do not use for real patient care.",
    )


@mcp.tool(
    description=(
        "Validate an educator-authored scenario definition (JSON) without creating it. "
        "Returns schema errors (which block creation) and authoring warnings such as "
        "unreachable rapport gates or duplicate fact/metric ids."
    ),
    structured_output=True,
)
def validate_scenario(
    scenario_json: Annotated[str, Field(description="A scenario definition as a JSON string.")],
) -> ScenarioValidation:
    return validate_scenario_definition(scenario_json)


@mcp.tool(
    description=(
        "Validate and register an educator-authored scenario so it can be started in a new "
        "session. Persists across restarts and rejects scenario ids that collide with built-ins."
    ),
    structured_output=True,
)
def create_scenario(
    scenario_json: Annotated[str, Field(description="A scenario definition as a JSON string.")],
) -> CreateScenarioResult:
    try:
        return orchestrator.create_scenario(scenario_json)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool(
    description="Remove a previously created custom scenario. Built-in scenarios cannot be deleted.",
    structured_output=True,
)
def delete_scenario(
    scenario_id: Annotated[str, Field(description="The custom scenario id to delete.", max_length=128)],
) -> DeleteScenarioResult:
    return orchestrator.delete_scenario(scenario_id)


@mcp.tool(
    description="Start an educational patient communication simulation session.",
    structured_output=True,
)
def start_simulation(
    session_id: Annotated[str, Field(description="Stable application session identifier.", max_length=128)],
    scenario_id: Annotated[str, Field(description="Scenario id to start; defaults to chest-pain-basic.", max_length=128)] = "chest-pain-basic",
    learner_id: Annotated[str | None, Field(description="Optional stable learner identifier for cross-session progress tracking.", max_length=128)] = None,
) -> SimulationResponse:
    return _handle(
        SimulationRequest(
            session_id=session_id,
            scenario_id=scenario_id,
            action=SimulationAction.start,
            learner_id=learner_id,
        )
    )


@mcp.tool(
    description="Send the learner's next practitioner utterance and receive the simulated patient's response.",
    structured_output=True,
)
def send_practitioner_turn(
    session_id: Annotated[str, Field(description="Stable application session identifier.", max_length=128)],
    practitioner_message: Annotated[str, Field(description="The learner's next utterance.", max_length=4000)],
    client_event_id: Annotated[str | None, Field(description="Idempotency key; a retried key is not reprocessed.", max_length=128)] = None,
    scenario_id: Annotated[str | None, Field(description="Must match the session's scenario when provided.", max_length=128)] = None,
    learner_id: Annotated[str | None, Field(description="Optional stable learner identifier for cross-session progress tracking.", max_length=128)] = None,
) -> SimulationResponse:
    return _handle(
        SimulationRequest(
            session_id=session_id,
            scenario_id=scenario_id,
            action=SimulationAction.message,
            practitioner_message=practitioner_message,
            client_event_id=client_event_id,
            learner_id=learner_id,
        )
    )


@mcp.tool(
    description="Evaluate the current session using the active scenario's versioned rubric.",
    structured_output=True,
)
def evaluate_simulation(
    session_id: Annotated[str, Field(description="Stable application session identifier.", max_length=128)],
    scenario_id: Annotated[str | None, Field(description="Must match the session's scenario when provided.", max_length=128)] = None,
    learner_id: Annotated[str | None, Field(description="Optional stable learner identifier for cross-session progress tracking.", max_length=128)] = None,
) -> SimulationResponse:
    return _handle(
        SimulationRequest(
            session_id=session_id,
            scenario_id=scenario_id,
            action=SimulationAction.evaluate,
            learner_id=learner_id,
        )
    )


@mcp.tool(
    description="End a simulation and return its final evidence-linked evaluation.",
    structured_output=True,
)
def end_simulation(
    session_id: Annotated[str, Field(description="Stable application session identifier.", max_length=128)],
    scenario_id: Annotated[str | None, Field(description="Must match the session's scenario when provided.", max_length=128)] = None,
    learner_id: Annotated[str | None, Field(description="Optional stable learner identifier for cross-session progress tracking.", max_length=128)] = None,
) -> SimulationResponse:
    return _handle(
        SimulationRequest(
            session_id=session_id,
            scenario_id=scenario_id,
            action=SimulationAction.end,
            learner_id=learner_id,
        )
    )


if os.getenv("MCP_EXPOSE_SESSION_TOOLS", "").lower() in ("1", "true", "yes"):

    @mcp.tool(
        description=(
            "List active simulation sessions. Registered only when MCP_EXPOSE_SESSION_TOOLS "
            "is enabled, because session IDs are sensitive."
        ),
        structured_output=True,
    )
    def list_sessions() -> SessionListResult:
        return SessionListResult(sessions=[SessionListItem(**item) for item in orchestrator.list_sessions()])

    @mcp.tool(
        description="Delete a simulation session. Registered only when MCP_EXPOSE_SESSION_TOOLS is enabled.",
        structured_output=True,
    )
    def delete_session(
        session_id: Annotated[str, Field(description="Session identifier to delete.", max_length=128)],
    ) -> DeleteSessionResult:
        removed = orchestrator.remove_session(session_id)
        return DeleteSessionResult(status="deleted" if removed else "not_found", session_id=session_id)


if os.getenv("MCP_EXPOSE_LEARNER_TOOLS", "").lower() in ("1", "true", "yes"):

    @mcp.tool(
        description=(
            "Return a learner's accumulated progress across simulation sessions — per-metric "
            "mastery, sessions completed, and a recommended next focus. Registered only when "
            "MCP_EXPOSE_LEARNER_TOOLS is enabled, because learner identifiers may be personal."
        ),
        structured_output=True,
    )
    def get_learner_progress(
        learner_id: Annotated[str, Field(description="Stable learner identifier.", max_length=128)],
    ) -> LearnerProgress:
        return orchestrator.get_learner_progress(learner_id)


if os.getenv("MCP_EXPOSE_COHORT_TOOLS", "").lower() in ("1", "true", "yes"):

    @mcp.tool(
        description=(
            "Return aggregate progress across all learners for a faculty/coach view: per-learner "
            "session counts and mastery, plus the metrics the cohort most often needs to work on. "
            "Registered only when MCP_EXPOSE_COHORT_TOOLS is enabled, because it reveals every "
            "learner identifier."
        ),
        structured_output=True,
    )
    def list_cohort_progress() -> CohortProgress:
        return orchestrator.cohort_progress()


class RateLimiter:
    """Thread-safe sliding-window rate limiter keyed by client address.

    In-memory and per-process: run a single worker, or move to a shared store
    if the limit must be global across instances.
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, client: str) -> bool:
        if self.max_requests <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            window_start = now - self.window_seconds
            if len(self._hits) > 4096:
                self._prune(window_start)
            recent = [t for t in self._hits.get(client, []) if t > window_start]
            if len(recent) >= self.max_requests:
                self._hits[client] = recent
                registry.incr("rate_limited_total")
                return False
            recent.append(now)
            self._hits[client] = recent
            return True

    def _prune(self, window_start: float) -> None:
        stale = [client for client, hits in self._hits.items() if not hits or hits[-1] <= window_start]
        for client in stale:
            del self._hits[client]


class SecurityMiddleware(BaseHTTPMiddleware):
    """Gate the MCP endpoint with an optional API key and an optional rate limit."""

    def __init__(self, app: Any, api_key: str, limiter: RateLimiter | None, trust_proxy: bool = False) -> None:
        super().__init__(app)
        self.api_key = api_key
        self.limiter = limiter
        self.trust_proxy = trust_proxy

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        request_id = request.headers.get("x-request-id") or uuid4().hex
        token = request_id_var.set(request_id)
        registry.incr("requests_total")
        try:
            if self.api_key:
                auth = request.headers.get("authorization", "")
                bearer = auth[7:] if auth.lower().startswith("bearer ") else ""
                header_key = request.headers.get("x-api-key", "")
                key = self.api_key.encode()
                if not compare_digest(bearer.encode(), key) and not compare_digest(header_key.encode(), key):
                    return self._reject(401, "unauthorized", request_id)

            if self.limiter is not None and not self.limiter.allow(_client_ip(request, self.trust_proxy)):
                return self._reject(429, "rate limit exceeded", request_id)

            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            logger.info(
                "request method=%s path=%s status=%s client=%s",
                request.method,
                request.url.path,
                response.status_code,
                _client_ip(request, self.trust_proxy),
            )
            return response
        finally:
            request_id_var.reset(token)

    @staticmethod
    def _reject(status: int, detail: str, request_id: str) -> JSONResponse:
        response = JSONResponse({"detail": detail}, status_code=status)
        response.headers["x-request-id"] = request_id
        return response


def _client_ip(request: Request, trust_proxy: bool) -> str:
    """Return the client address for rate limiting.

    Only consult X-Forwarded-For when MCP_TRUST_PROXY is enabled (the server is
    behind a trusted proxy such as App Runner that appends the real client IP as
    the rightmost hop). Otherwise use the direct peer so a client cannot spoof
    X-Forwarded-For to rotate past the rate limit.
    """
    if trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        if hops:
            return hops[-1]
    return request.client.host if request.client is not None else "unknown"


def _transport_security(allowed_hosts: str, allowed_origins: str) -> TransportSecuritySettings:
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[item.strip() for item in allowed_hosts.split(",") if item.strip()],
        allowed_origins=[item.strip() for item in allowed_origins.split(",") if item.strip()],
    )


def _observability_response(path: str) -> JSONResponse | PlainTextResponse | None:
    if path == "/health":
        return JSONResponse(
            {
                "status": "ok",
                "service": "clinical-conversation-coach",
                "active_sessions": len(orchestrator.sessions),
                "version": __version__,
            }
        )
    if path == "/ready":
        if not SCENARIOS:
            return JSONResponse({"detail": "no scenarios loaded"}, status_code=503)
        return JSONResponse({"status": "ready", "version": __version__})
    if path == "/metrics":
        return PlainTextResponse(
            render_prometheus(len(orchestrator.sessions)),
            media_type="text/plain; version=0.0.4",
        )
    return None


def _with_observability(app: Any) -> Any:
    """Serve unauthenticated GET /health, /ready, /metrics around the MCP app."""

    async def wrapper(scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "http" and scope["method"].upper() == "GET":
            response = _observability_response(scope.get("path", ""))
            if response is not None:
                await response(scope, receive, send)
                return
        await app(scope, receive, send)

    return wrapper


def create_app(
    *,
    api_key: str | None = None,
    max_requests: int | None = None,
    window_seconds: float | None = None,
    allowed_hosts: str | None = None,
    allowed_origins: str | None = None,
    trust_proxy: bool | None = None,
) -> Any:
    """Build the Streamable HTTP app wrapped with auth and rate-limiting middleware."""
    host = os.getenv("MCP_HOST", "127.0.0.1")
    path = os.getenv("MCP_PATH", "/mcp")
    hosts = os.getenv("MCP_ALLOWED_HOSTS", f"{host}:*") if allowed_hosts is None else allowed_hosts
    origins = (
        os.getenv("MCP_ALLOWED_ORIGINS", "http://127.0.0.1:*,http://localhost:*")
        if allowed_origins is None
        else allowed_origins
    )

    key = os.getenv("MCP_API_KEY", "") if api_key is None else api_key
    limit = int(os.getenv("MCP_RATE_LIMIT_REQUESTS", "0")) if max_requests is None else max_requests
    window = float(os.getenv("MCP_RATE_LIMIT_WINDOW_SECONDS", "60")) if window_seconds is None else window_seconds

    app = mcp.streamable_http_app(
        streamable_http_path=path,
        json_response=True,
        stateless_http=False,
        host=host,
        transport_security=_transport_security(hosts, origins),
    )

    trust_proxy = (
        os.getenv("MCP_TRUST_PROXY", "").lower() in ("1", "true", "yes") if trust_proxy is None else trust_proxy
    )
    limiter = RateLimiter(limit, window) if limit > 0 else None
    app.add_middleware(SecurityMiddleware, api_key=key, limiter=limiter, trust_proxy=trust_proxy)
    return _with_observability(app)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8001"))
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    uvicorn.run(create_app(), host=host, port=port, log_level=log_level.lower())
