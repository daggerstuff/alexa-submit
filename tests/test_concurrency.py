import threading
import time

from server.main import SimulationOrchestrator
from server.schemas.validation import PatientResponse, Role, SimulationAction, SimulationRequest


class _SlowAgent:
    """Deterministic persona that sleeps to widen interleaving windows."""

    def respond(self, state, scenario, message):
        time.sleep(0.02)
        return PatientResponse(
            content="ok",
            emotional_state="anxious",
            disclosed_facts=[],
            scenario_id=scenario.scenario_id,
            scenario_version=scenario.version,
        )


def _message_worker(orch: SimulationOrchestrator, session_id: str, count: int):
    def worker() -> None:
        for _ in range(count):
            orch.handle(
                SimulationRequest(session_id=session_id, action=SimulationAction.message, practitioner_message="hello")
            )

    return worker


def test_concurrent_same_session_is_serialized() -> None:
    orch = SimulationOrchestrator(patient_agent=_SlowAgent())
    sid = "same-session"
    threads = [threading.Thread(target=_message_worker(orch, sid, 5)) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    session = orch.sessions[sid]
    assert session.patient_state.turn_count == 20
    assert len(session.transcript) == 40
    roles = [turn.role for turn in session.transcript]
    assert all(role is Role.practitioner for role in roles[0::2])
    assert all(role is Role.patient for role in roles[1::2])


def test_concurrent_distinct_sessions_are_independent() -> None:
    orch = SimulationOrchestrator(patient_agent=_SlowAgent())
    sids = ["a", "b", "c", "d"]
    threads = [threading.Thread(target=_message_worker(orch, sid, 3)) for sid in sids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    for sid in sids:
        session = orch.sessions[sid]
        assert session.patient_state.turn_count == 3
        assert len(session.transcript) == 6
