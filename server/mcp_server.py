from __future__ import annotations

import os
import threading
import time
from secrets import compare_digest
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from server._version import __version__
from server.main import orchestrator
from server.scenarios import SCENARIOS
from server.schemas.validation import SimulationAction, SimulationRequest

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
        if self.api_key:
            auth = request.headers.get("authorization", "")
            bearer = auth[7:] if auth.lower().startswith("bearer ") else ""
            header_key = request.headers.get("x-api-key", "")
            key = self.api_key.encode()
            if not compare_digest(bearer.encode(), key) and not compare_digest(header_key.encode(), key):
                return JSONResponse({"detail": "unauthorized"}, status_code=401)

        if self.limiter is not None and not self.limiter.allow(_client_ip(request)):
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)

        return await call_next(request)


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
    if key or limiter is not None:
        app.add_middleware(SecurityMiddleware, api_key=key, limiter=limiter)
    return app


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8001"))
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    uvicorn.run(create_app(), host=host, port=port, log_level=log_level.lower())
