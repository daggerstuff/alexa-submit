from __future__ import annotations

import json
import logging
import threading
from contextvars import ContextVar
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class Registry:
    """Thread-safe, process-local counters backing the /metrics endpoint."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.requests_total = 0
        self.rate_limited_total = 0
        self.llm_fallbacks_total = 0
        self.sessions_created_total = 0

    def incr(self, name: str, amount: int = 1) -> None:
        with self._lock:
            setattr(self, name, getattr(self, name) + amount)

    def reset(self) -> None:
        with self._lock:
            self.requests_total = 0
            self.rate_limited_total = 0
            self.llm_fallbacks_total = 0
            self.sessions_created_total = 0

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "requests_total": self.requests_total,
                "rate_limited_total": self.rate_limited_total,
                "llm_fallbacks_total": self.llm_fallbacks_total,
                "sessions_created_total": self.sessions_created_total,
            }


registry = Registry()


class JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record, annotated with the request id."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def render_prometheus(active_sessions: int) -> str:
    """Render the registry counters plus the live session gauge as Prometheus text."""
    snap = registry.snapshot()
    return "\n".join(
        [
            "# HELP clinical_sim_requests_total Total HTTP requests handled by the MCP server.",
            "# TYPE clinical_sim_requests_total counter",
            f"clinical_sim_requests_total {snap['requests_total']}",
            "# HELP clinical_sim_rate_limited_total Requests rejected by rate limiting.",
            "# TYPE clinical_sim_rate_limited_total counter",
            f"clinical_sim_rate_limited_total {snap['rate_limited_total']}",
            "# HELP clinical_sim_llm_fallbacks_total LLM persona fallbacks to the deterministic persona.",
            "# TYPE clinical_sim_llm_fallbacks_total counter",
            f"clinical_sim_llm_fallbacks_total {snap['llm_fallbacks_total']}",
            "# HELP clinical_sim_sessions_created_total Simulation sessions created since start.",
            "# TYPE clinical_sim_sessions_created_total counter",
            f"clinical_sim_sessions_created_total {snap['sessions_created_total']}",
            "# HELP clinical_sim_sessions_active Current in-memory active sessions.",
            "# TYPE clinical_sim_sessions_active gauge",
            f"clinical_sim_sessions_active {active_sessions}",
            "",
        ]
    )
