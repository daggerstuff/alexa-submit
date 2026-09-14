import pytest
from mcp.server.mcpserver.exceptions import ToolError

from server.main import SimulationOrchestrator, orchestrator
from server.mcp_server import send_practitioner_turn
from server.schemas.validation import SimulationAction, SimulationRequest


class _RaisingAgent:
    def respond(self, state, scenario, message):
        raise RuntimeError("boom")


def test_failed_turn_rolls_back_state() -> None:
    orch = SimulationOrchestrator(patient_agent=_RaisingAgent())
    sid = "fail-session"
    orch.handle(SimulationRequest(session_id=sid, action=SimulationAction.start))
    with pytest.raises(RuntimeError):
        orch.handle(SimulationRequest(session_id=sid, action=SimulationAction.message, practitioner_message="hello"))
    session = orch.sessions[sid]
    assert session.patient_state.turn_count == 0
    assert len(session.transcript) == 1  # only the opening patient turn remains


def test_domain_error_surfaces_as_tool_error() -> None:
    orchestrator.sessions.clear()
    sid = "err-session"
    try:
        orchestrator.handle(SimulationRequest(session_id=sid, action=SimulationAction.start))
        orchestrator.handle(SimulationRequest(session_id=sid, action=SimulationAction.end))
        with pytest.raises(ToolError) as exc:
            send_practitioner_turn(sid, "hello")
        assert "Session has ended" in str(exc.value)
    finally:
        orchestrator.sessions.clear()
