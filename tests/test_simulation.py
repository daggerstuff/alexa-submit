import pytest
from fastapi import HTTPException

from server.main import orchestrator
from server.schemas.validation import SimulationAction, SimulationRequest


def setup_function() -> None:
    orchestrator.sessions.clear()


def test_session_flow_and_versioned_rubric() -> None:
    session_id = "test-session"
    start = orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.start))
    assert start.status == "active"
    assert start.scenario_version == "1.2.0"

    message = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.message,
            client_event_id="event-1",
            practitioner_message="My name is Alex. Where is the pain, are you short of breath, and what medications do you take?",
        )
    )
    assert "chest" in message.patient.content.lower()
    assert "chest-pressure" in message.patient.disclosed_facts

    duplicate = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.message,
            client_event_id="event-1",
            practitioner_message="This should not be processed twice.",
        )
    )
    assert len(duplicate.transcript) == len(message.transcript)

    evaluation = orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.evaluate))
    result = evaluation.evaluation
    assert result.rubric_version == "1.2.0"
    assert result.max_score == 20
    assert any(item.metric_id == "closed_loop" for item in result.metrics)


def test_end_locks_session() -> None:
    session_id = "ended-session"
    orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.start))
    ended = orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.end))
    assert ended.status == "ended"
    with pytest.raises(HTTPException) as exc:
        orchestrator.handle(
            SimulationRequest(session_id=session_id, action=SimulationAction.message, practitioner_message="continue")
        )
    assert exc.value.status_code == 409


def test_multi_topic_matching_discloses_multiple_facts() -> None:
    session_id = "multi-topic"
    orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.start))
    response = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.message,
            practitioner_message="Where is the pain and are you short of breath?",
        )
    )
    disclosed = set(response.patient.disclosed_facts)
    assert "chest-pressure" in disclosed
    assert "dyspnea" in disclosed


def test_abdominal_pain_scenario() -> None:
    session_id = "abdom-test"
    start = orchestrator.handle(
        SimulationRequest(session_id=session_id, action=SimulationAction.start, scenario_id="abdominal-pain-basic")
    )
    assert start.scenario_version == "1.0.0"
    assert "stomach" in start.patient.content.lower()

    turn = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.message,
            practitioner_message="Where does it hurt, is it sharp or dull, and have you had any fever or nausea?",
        )
    )
    disclosed = set(turn.patient.disclosed_facts)
    assert "pain-location" in disclosed
    assert "pain-quality" in disclosed
    assert "fever" in disclosed
    assert "appetite" in disclosed

    evaluation = orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.evaluate))
    result = evaluation.evaluation
    assert result.rubric_version == "1.0.0"
    assert result.max_score == 24
    metric_ids = {m.metric_id for m in result.metrics}
    assert "associated" in metric_ids
    assert "history" in metric_ids


def test_depression_screening_scenario() -> None:
    session_id = "dep-test"
    start = orchestrator.handle(
        SimulationRequest(session_id=session_id, action=SimulationAction.start, scenario_id="depression-screening-basic")
    )
    assert start.scenario_version == "1.0.0"
    content = start.patient.content.lower()
    assert "tired" in content or "down" in content

    turn = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.message,
            practitioner_message="My name is Sam. How long have you been feeling down, how is your sleep, and have you lost interest in things?",
        )
    )
    disclosed = set(turn.patient.disclosed_facts)
    assert "mood-duration" in disclosed
    assert "sleep" in disclosed
    assert "interest" in disclosed

    evaluation = orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.evaluate))
    result = evaluation.evaluation
    assert result.rubric_version == "1.0.0"
    assert result.max_score == 24
    metric_ids = {m.metric_id for m in result.metrics}
    assert "risk" in metric_ids
    assert "somatic" in metric_ids


def test_scenario_switch_rejected() -> None:
    session_id = "switch-test"
    orchestrator.handle(
        SimulationRequest(session_id=session_id, action=SimulationAction.start, scenario_id="chest-pain-basic")
    )
    with pytest.raises(HTTPException) as exc:
        orchestrator.handle(
            SimulationRequest(
                session_id=session_id,
                action=SimulationAction.message,
                scenario_id="abdominal-pain-basic",
                practitioner_message="test",
            )
        )
    assert exc.value.status_code == 409


def test_unknown_scenario_rejected() -> None:
    with pytest.raises(HTTPException) as exc:
        orchestrator.handle(
            SimulationRequest(session_id="unknown-scenario", action=SimulationAction.start, scenario_id="nonexistent")
        )
    assert exc.value.status_code == 404


def test_safety_note_on_severe_language() -> None:
    session_id = "safety-test"
    orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.start))
    response = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.message,
            practitioner_message="Are you going to collapse? This seems severe.",
        )
    )
    assert response.patient.safety_note is not None
