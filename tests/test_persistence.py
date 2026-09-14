import time

from server.main import SimulationOrchestrator
from server.schemas.validation import SimulationAction, SimulationRequest


def test_session_survives_process_restart(tmp_path) -> None:
    db = str(tmp_path / "sessions.db")

    first = SimulationOrchestrator(db_path=db)
    first.handle(SimulationRequest(session_id="s1", action=SimulationAction.start, scenario_id="chest-pain-basic"))
    message = first.handle(
        SimulationRequest(
            session_id="s1",
            action=SimulationAction.message,
            practitioner_message="Where is the pain, and when did it start?",
            client_event_id="turn-1",
        )
    )
    assert message.patient is not None

    # A fresh orchestrator over the same file reloads the session.
    second = SimulationOrchestrator(db_path=db)
    resumed = second.get_or_create(SimulationRequest(session_id="s1", action=SimulationAction.evaluate))
    assert resumed.scenario.scenario_id == "chest-pain-basic"
    assert resumed.patient_state.turn_count == 1
    assert "chest-pressure" in resumed.patient_state.disclosed_facts
    assert len(resumed.transcript) == 3  # opening + practitioner + patient reply

    # Idempotency survives the reload: replay returns the cached response.
    replay = second.handle(
        SimulationRequest(
            session_id="s1",
            action=SimulationAction.message,
            practitioner_message="Where is the pain, and when did it start?",
            client_event_id="turn-1",
        )
    )
    assert replay == message

    first.store.close()
    second.store.close()


def test_remove_session_persists_deletion(tmp_path) -> None:
    db = str(tmp_path / "sessions.db")
    orch = SimulationOrchestrator(db_path=db)
    orch.handle(SimulationRequest(session_id="s1", action=SimulationAction.start))

    assert orch.remove_session("s1") is True
    assert orch.remove_session("s1") is False

    reloaded = SimulationOrchestrator(db_path=db)
    fresh = reloaded.get_or_create(SimulationRequest(session_id="s1", action=SimulationAction.start))
    assert fresh.transcript == []  # recreated from scratch, not a stale row

    orch.store.close()
    reloaded.store.close()


def test_store_only_expired_rows_are_swept(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SESSION_TTL_SECONDS", "60")
    db = str(tmp_path / "sessions.db")

    first = SimulationOrchestrator(db_path=db)
    first.handle(SimulationRequest(session_id="old", action=SimulationAction.start))
    first.sessions["old"].last_accessed = time.time() - 120
    first._persist(first.sessions["old"])
    first.store.close()

    second = SimulationOrchestrator(db_path=db)
    second.get_or_create(SimulationRequest(session_id="new", action=SimulationAction.start))
    assert second.store.get("old") is None  # swept even though never loaded into memory
    second.store.close()
