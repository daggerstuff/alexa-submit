from __future__ import annotations

import logging
import os
import threading
import time
from secrets import compare_digest
from typing import Any
from uuid import uuid4

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from server._version import __version__
from server.main import orchestrator
from server.observability import registry, render_prometheus, request_id_var
from server.scenarios import SCENARIOS
from server.schemas.validation import SimulationAction, SimulationRequest

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


def _serialize(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json")
    return response


@mcp.tool(
    description="List the available educational simulation scenarios and their rubric versions.",
    structured_output=True,
)
def list_simulation_scenarios() -> dict[str, Any]:
    return {
        "scenarios": [
            {
                "scenario_id": scenario.scenario_id,
                "version": scenario.version,
                "title": scenario.title,
                "metric_ids": [metric.metric_id for metric in scenario.metrics],
            }
            for scenario in SCENARIOS.values()
        ],
        "disclaimer": "Educational simulation only; do not use for real patient care.",
    }


@mcp.tool(
    description="Start an educational patient communication simulation session.",
    structured_output=True,
)
def start_simulation(session_id: str, scenario_id: str = "chest-pain-basic") -> dict[str, Any]:
    response = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            scenario_id=scenario_id,
            action=SimulationAction.start,
        )
    )
    return _serialize(response)


@mcp.tool(
    description="Send the learner's next practitioner utterance and receive the simulated patient's response.",
    structured_output=True,
)
def send_practitioner_turn(
    session_id: str,
    practitioner_message: str,
    client_event_id: str | None = None,
    scenario_id: str | None = None,
) -> dict[str, Any]:
    response = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            scenario_id=scenario_id,
            action=SimulationAction.message,
            practitioner_message=practitioner_message,
            client_event_id=client_event_id,
        )
    )
    return _serialize(response)


@mcp.tool(
    description="Evaluate the current session using the active scenario's versioned rubric.",
    structured_output=True,
)
def evaluate_simulation(session_id: str, scenario_id: str | None = None) -> dict[str, Any]:
    response = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            scenario_id=scenario_id,
            action=SimulationAction.evaluate,
        )
    )
    return _serialize(response)


@mcp.tool(
    description="End a simulation and return its final evidence-linked evaluation.",
    structured_output=True,
)
def end_simulation(session_id: str, scenario_id: str | None = None) -> dict[str, Any]:
    response = orchestrator.handle(
        SimulationRequest(session_id=session_id, scenario_id=scenario_id, action=SimulationAction.end)
    )
    return _serialize(response)


if os.getenv("MCP_EXPOSE_SESSION_TOOLS", "").lower() in ("1", "true", "yes"):

    @mcp.tool(
        description=(
            "List active simulation sessions. Registered only when MCP_EXPOSE_SESSION_TOOLS "
            "is enabled, because session IDs are sensitive."
        ),
        structured_output=True,
    )
    def list_sessions() -> dict[str, Any]:
        return {
            "sessions": [
                {
                    "session_id": sid,
                    "scenario_id": sess.scenario.scenario_id,
                    "status": sess.status,
                    "turn_count": sess.patient_state.turn_count,
                }
                for sid, sess in orchestrator.sessions.items()
            ]
        }

    @mcp.tool(
        description="Delete a simulation session. Registered only when MCP_EXPOSE_SESSION_TOOLS is enabled.",
        structured_output=True,
    )
    def delete_session(session_id: str) -> dict[str, Any]:
        removed = orchestrator.remove_session(session_id)
        return {"status": "deleted" if removed else "not_found", "session_id": session_id}


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

    def __init__(self, app: Any, api_key: str, limiter: RateLimiter | None) -> None:
        super().__init__(app)
        self.api_key = api_key
        self.limiter = limiter

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

            if self.limiter is not None and not self.limiter.allow(_client_ip(request)):
                return self._reject(429, "rate limit exceeded", request_id)

            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            logger.info(
                "request method=%s path=%s status=%s client=%s",
                request.method,
                request.url.path,
                response.status_code,
                _client_ip(request),
            )
            return response
        finally:
            request_id_var.reset(token)

    @staticmethod
    def _reject(status: int, detail: str, request_id: str) -> JSONResponse:
        response = JSONResponse({"detail": detail}, status_code=status)
        response.headers["x-request-id"] = request_id
        return response


def _client_ip(request: Request) -> str:
    """Return the client address, trusting only the rightmost X-Forwarded-For hop.

    Behind App Runner's load balancer, the last XFF entry is the address the
    proxy recorded for the client; earlier entries may be client-supplied and
    spoofable, so they are ignored.
    """
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

    limiter = RateLimiter(limit, window) if limit > 0 else None
    app.add_middleware(SecurityMiddleware, api_key=key, limiter=limiter)
    return _with_observability(app)


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8001"))
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    uvicorn.run(create_app(), host=host, port=port, log_level=log_level.lower())
