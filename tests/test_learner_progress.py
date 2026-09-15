from __future__ import annotations

from server.main import SimulationOrchestrator
from server.schemas.validation import SimulationAction, SimulationRequest


def _orch() -> SimulationOrchestrator:
    return SimulationOrchestrator()


def test_end_records_progress_for_learner() -> None:
    orch = _orch()
    orch.handle(
        SimulationRequest(session_id="s1", action=SimulationAction.start, scenario_id="chest-pain-basic", learner_id="alice")
    )
    resp = orch.handle(SimulationRequest(session_id="s1", action=SimulationAction.end, learner_id="alice"))

    assert resp.learner_progress is not None
    assert resp.learner_progress.learner_id == "alice"
    assert resp.learner_progress.sessions_completed == 1
    assert len(resp.learner_progress.metrics) == len(resp.evaluation.metrics)
    assert "Session 1 complete" in resp.learner_progress.adaptive_note
    assert resp.learner_progress.focus_next


def test_no_progress_without_learner_id() -> None:
    orch = _orch()
    orch.handle(SimulationRequest(session_id="s1", action=SimulationAction.start, scenario_id="chest-pain-basic"))
    resp = orch.handle(SimulationRequest(session_id="s1", action=SimulationAction.end))
    assert resp.learner_progress is None


def test_progress_uses_session_learner_id_at_end() -> None:
    orch = _orch()
    orch.handle(
        SimulationRequest(session_id="s1", action=SimulationAction.start, scenario_id="chest-pain-basic", learner_id="bob")
    )
    # End without repeating learner_id: the session remembers it from start.
    resp = orch.handle(SimulationRequest(session_id="s1", action=SimulationAction.end))
    assert resp.learner_progress is not None
    assert resp.learner_progress.learner_id == "bob"


def test_second_session_detects_improvement_and_focus() -> None:
    orch = _orch()

    # Session 1: only introduces self — every other metric stays at baseline 1.
    orch.handle(
        SimulationRequest(session_id="s1", action=SimulationAction.start, scenario_id="chest-pain-basic", learner_id="carol")
    )
    orch.handle(
        SimulationRequest(
            session_id="s1",
            action=SimulationAction.message,
            practitioner_message="Hi, my name is Dr. Chen.",
            learner_id="carol",
        )
    )
    first = orch.handle(SimulationRequest(session_id="s1", action=SimulationAction.end, learner_id="carol"))
    assert first.learner_progress.sessions_completed == 1

    # Session 2: covers symptoms, risk, escalation, and next-step confirmation.
    orch.handle(
        SimulationRequest(session_id="s2", action=SimulationAction.start, scenario_id="chest-pain-basic", learner_id="carol")
    )
    orch.handle(
        SimulationRequest(
            session_id="s2",
            action=SimulationAction.message,
            practitioner_message=(
                "Hi, my name is Dr. Chen. Where is the pain and when did it start? "
                "Are you short of breath? Do you take any medications? "
                "Should we call 911 or arrange an ECG? Do you have any questions about the plan?"
            ),
            learner_id="carol",
        )
    )
    second = orch.handle(SimulationRequest(session_id="s2", action=SimulationAction.end, learner_id="carol"))

    assert second.learner_progress.sessions_completed == 2
    # At least one metric improved relative to its prior best.
    assert second.learner_progress.improved_this_session
    # The weakest metric remains "Introduction and consent" (name matched only once).
    assert second.learner_progress.focus_next == "Introduction and consent"

    # The recorded mastery reflects the better score across sessions.
    by_id = {m.metric_id: m for m in second.learner_progress.metrics}
    assert by_id["symptoms"].best_score >= 3  # improved from the session-1 baseline of 1
    assert by_id["symptoms"].attempts == 2


def test_get_learner_progress_empty_for_unknown() -> None:
    orch = _orch()
    progress = orch.get_learner_progress("nobody")
    assert progress.learner_id == "nobody"
    assert progress.sessions_completed == 0
    assert progress.metrics == []
