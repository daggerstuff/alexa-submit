from __future__ import annotations

from server.main import orchestrator
from server.scenarios import SCENARIOS
from server.schemas.validation import SimulationAction, SimulationRequest


def setup_function() -> None:
    orchestrator.sessions.clear()


def test_library_covers_all_difficulties() -> None:
    assert len(SCENARIOS) == 12
    difficulties = {scenario.difficulty for scenario in SCENARIOS.values()}
    assert difficulties == {"basic", "intermediate", "advanced"}
    for scenario_id in (
        "suicide-risk-screening-advanced",
        "pediatric-fever-basic",
        "stroke-fast-intermediate",
        "medication-reconciliation-intermediate",
        "alcohol-screening-basic",
    ):
        assert scenario_id in SCENARIOS


def test_suicide_risk_screening_scenario() -> None:
    session_id = "suicide-test"
    start = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.start,
            scenario_id="suicide-risk-screening-advanced",
        )
    )
    assert start.scenario_version == "1.0.0"
    assert "better off" in start.patient.content.lower()

    turn = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.message,
            practitioner_message=(
                "My name is Sam. Have you been having thoughts of ending your life? "
                "Do you have a plan or access to a gun? Do you intend to act soon, "
                "and what gives you hope?"
            ),
        )
    )
    disclosed = set(turn.patient.disclosed_facts)
    assert "ideation-frequency" in disclosed
    assert "plan" in disclosed
    assert "means-access" in disclosed
    assert "intent-imminence" in disclosed
    assert "protective-factors" in disclosed
    # Raising suicide/plan/means red flags surfaces an acuity note.
    assert turn.patient.safety_note is not None

    evaluation = orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.evaluate))
    metric_ids = {m.metric_id for m in evaluation.evaluation.metrics}
    assert {"direct_inquiry", "plan_means", "intent_timing", "protective", "safety_plan"} <= metric_ids


def test_suicide_risk_dismissal_is_flagged() -> None:
    session_id = "suicide-pitfall"
    orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.start,
            scenario_id="suicide-risk-screening-advanced",
        )
    )
    turn = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.message,
            practitioner_message="Don't worry, you'll be fine. Just cheer up.",
        )
    )
    assert turn.patient.safety_note is not None
    evaluation = orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.end))
    assert "you'll be fine" in evaluation.evaluation.safety_flags


def test_pediatric_fever_scenario() -> None:
    session_id = "peds-test"
    start = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.start,
            scenario_id="pediatric-fever-basic",
        )
    )
    assert start.scenario_version == "1.0.0"
    assert "fever" in start.patient.content.lower()

    turn = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.message,
            practitioner_message=(
                "My name is Sam. What was her temperature and when did it start? "
                "How much is she drinking and how many wet diapers? Any cough, rash, "
                "or vomiting? Is she alert and playing normally?"
            ),
        )
    )
    disclosed = set(turn.patient.disclosed_facts)
    assert "fever-measurement" in disclosed
    assert "onset-duration" in disclosed
    assert "feeding-hydration" in disclosed
    assert "associated-symptoms" in disclosed
    assert "behavior-energy" in disclosed

    evaluation = orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.evaluate))
    metric_ids = {m.metric_id for m in evaluation.evaluation.metrics}
    assert {"fever_timing", "hydration", "associated", "red_flags", "closed_loop"} <= metric_ids


def test_stroke_fast_scenario() -> None:
    session_id = "stroke-test"
    start = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.start,
            scenario_id="stroke-fast-intermediate",
        )
    )
    assert start.scenario_version == "1.0.0"
    assert "arm" in start.patient.content.lower()

    turn = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.message,
            practitioner_message=(
                "My name is Sam. When were you last completely normal? Can you smile "
                "for me — any drooping? Raise both arms — is one weak? Repeat a phrase "
                "— any slurring? This is an emergency — call 911 right now."
            ),
        )
    )
    disclosed = set(turn.patient.disclosed_facts)
    assert "onset-time" in disclosed
    assert "last-known-well" in disclosed
    assert "face-droop" in disclosed
    assert "arm-weakness" in disclosed
    assert "speech-slurring" in disclosed

    evaluation = orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.evaluate))
    metric_ids = {m.metric_id for m in evaluation.evaluation.metrics}
    assert {"onset_time", "fast_face", "fast_arm", "fast_speech", "escalation"} <= metric_ids
    # The escalation metric should be fully demonstrated by the explicit 911 call.
    escalation = next(m for m in evaluation.evaluation.metrics if m.metric_id == "escalation")
    assert escalation.score == escalation.max_score


def test_medication_reconciliation_scenario() -> None:
    session_id = "medrec-test"
    start = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.start,
            scenario_id="medication-reconciliation-intermediate",
        )
    )
    assert start.scenario_version == "1.0.0"
    assert "pills" in start.patient.content.lower()

    turn = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.message,
            practitioner_message=(
                "My name is Sam. Can you list every pill you take and how often? "
                "Do you ever miss a dose? Any stomach upset, bruising, or dizziness? "
                "What about over-the-counter pain relievers or supplements?"
            ),
        )
    )
    disclosed = set(turn.patient.disclosed_facts)
    assert "medication-list" in disclosed
    assert "dosing-frequency" in disclosed
    assert "adherence" in disclosed
    assert "side-effects" in disclosed
    assert "otc-supplements" in disclosed

    evaluation = orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.evaluate))
    metric_ids = {m.metric_id for m in evaluation.evaluation.metrics}
    assert {"inventory", "dosing", "adherence", "side_effects", "otc"} <= metric_ids


def test_alcohol_screening_scenario() -> None:
    session_id = "alcohol-test"
    start = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.start,
            scenario_id="alcohol-screening-basic",
        )
    )
    assert start.scenario_version == "1.0.0"
    assert "drinks" in start.patient.content.lower()

    turn = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.message,
            practitioner_message=(
                "My name is Sam. How many drinks on a typical day, and how many days a week? "
                "How has it affected your work or relationships? Any shaking or nausea when "
                "you stop? Would you want to cut down?"
            ),
        )
    )
    disclosed = set(turn.patient.disclosed_facts)
    assert "quantity" in disclosed
    assert "frequency" in disclosed
    assert "impact" in disclosed
    assert "withdrawal" in disclosed
    assert "readiness" in disclosed

    evaluation = orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.evaluate))
    metric_ids = {m.metric_id for m in evaluation.evaluation.metrics}
    assert {"quantity_frequency", "impact", "withdrawal", "readiness"} <= metric_ids
