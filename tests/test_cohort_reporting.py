from __future__ import annotations

from server.main import SimulationOrchestrator
from server.schemas.validation import SimulationAction, SimulationRequest


def _complete_session(orch: SimulationOrchestrator, session_id: str, learner_id: str) -> None:
    orch.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.start,
            scenario_id="chest-pain-basic",
            learner_id=learner_id,
        )
    )
    orch.handle(SimulationRequest(session_id=session_id, action=SimulationAction.end, learner_id=learner_id))


def test_empty_cohort() -> None:
    cohort = SimulationOrchestrator().cohort_progress()
    assert cohort.learner_count == 0
    assert cohort.total_sessions == 0
    assert cohort.learners == []
    assert cohort.cohort_weakest_metrics == []


def test_cohort_aggregates_learners_sorted_by_sessions() -> None:
    orch = SimulationOrchestrator()
    _complete_session(orch, "s1", "alice")
    _complete_session(orch, "s2", "bob")
    _complete_session(orch, "s3", "bob")

    cohort = orch.cohort_progress()
    assert cohort.learner_count == 2
    assert cohort.total_sessions == 3

    # Most sessions first.
    assert [item.learner_id for item in cohort.learners] == ["bob", "alice"]
    assert cohort.learners[0].sessions_completed == 2
    assert cohort.learners[1].sessions_completed == 1

    for summary in cohort.learners:
        assert 0.0 <= summary.mastery <= 1.0
        assert summary.metrics_attempted > 0
        assert summary.focus_next  # every completed session yields a weakest metric

    # Both learners share the same baseline weakest metric, so it tops the list.
    assert cohort.cohort_weakest_metrics
    assert cohort.cohort_weakest_metrics[0] == "Associated symptoms and risk"


def test_cohort_is_persisted_through_learner_store() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        db_path = f"{tmp}/sessions.db"
        orch = SimulationOrchestrator(db_path=db_path)
        _complete_session(orch, "s1", "carol")

        # A fresh orchestrator over the same DB sees the learner's progress.
        reloaded = SimulationOrchestrator(db_path=db_path)
        cohort = reloaded.cohort_progress()
        assert cohort.learner_count == 1
        assert cohort.learners[0].learner_id == "carol"
        assert cohort.learners[0].sessions_completed == 1
