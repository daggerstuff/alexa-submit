import time

from server.main import SimulationOrchestrator
from server.schemas.validation import SimulationRequest


def test_expired_session_is_recreated() -> None:
    orch = SimulationOrchestrator()
    orch.session_ttl = 1.0
    orch.max_sessions = 0

    req = SimulationRequest(session_id="s1", action="start")
    first = orch.get_or_create(req)
    first.last_accessed = time.monotonic() - 10

    second = orch.get_or_create(req)
    assert second is not first
    assert second.session_id == "s1"
    assert len(orch.sessions) == 1


def test_ttl_zero_disables_expiry() -> None:
    orch = SimulationOrchestrator()
    orch.session_ttl = 0
    req = SimulationRequest(session_id="s1", action="start")
    first = orch.get_or_create(req)
    first.last_accessed = time.monotonic() - 1000
    assert orch.get_or_create(req) is first


def test_lru_eviction_enforces_cap() -> None:
    orch = SimulationOrchestrator()
    orch.session_ttl = 0
    orch.max_sessions = 2

    a = orch.get_or_create(SimulationRequest(session_id="a", action="start"))
    orch.get_or_create(SimulationRequest(session_id="b", action="start"))
    a.last_accessed = time.monotonic()  # touch a so b becomes least-recently-used

    orch.get_or_create(SimulationRequest(session_id="c", action="start"))
    assert "a" in orch.sessions
    assert "b" not in orch.sessions
    assert "c" in orch.sessions
    assert len(orch.sessions) == 2
