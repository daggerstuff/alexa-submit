from __future__ import annotations

from server.agents.clinical_evaluator import ClinicalEvaluatorAgent
from server.agents.patient_persona import PatientPersonaAgent, PatientState
from server.main import SimulationOrchestrator
from server.scenarios import CHEST_PAIN_BASIC
from server.schemas.validation import Role, SimulationAction, SimulationRequest, TranscriptTurn
from server.voice import NEUTRAL_PROSODY, prosody_for, speak, spoken_evaluation, ssml_escape


def _state() -> PatientState:
    return PatientState(scenario_id="chest-pain-basic", scenario_version=CHEST_PAIN_BASIC.version)


def _turn(content: str) -> TranscriptTurn:
    return TranscriptTurn(role=Role.practitioner, content=content, timestamp="2026-01-01T00:00:00+00:00")


def test_ssml_escape_all_special_characters() -> None:
    assert ssml_escape("a & b < c > d \"e\" 'f'") == "a &amp; b &lt; c &gt; d &quot;e&quot; &apos;f&apos;"


def test_prosody_for_known_unknown_and_none() -> None:
    assert prosody_for("guarded") == 'rate="slow" pitch="low" volume="soft"'
    assert prosody_for("Guarded") == 'rate="slow" pitch="low" volume="soft"'
    assert prosody_for("anxious") == 'rate="fast" pitch="high"'
    assert prosody_for("made-up-mood") == NEUTRAL_PROSODY
    assert prosody_for(None) == NEUTRAL_PROSODY


def test_speak_wraps_and_escapes_content() -> None:
    out = speak("I am a little short of breath.", "anxious")
    assert out.startswith('<speak><prosody rate="fast" pitch="high">')
    assert out.endswith("</prosody></speak>")
    assert "I am a little short of breath." in out


def test_speak_escapes_ampersand_and_quote() -> None:
    out = speak('He said "hello" & goodbye', "calm")
    assert "&quot;hello&quot;" in out
    assert "&amp;" in out
    assert "&lt;" not in out  # no literal angle brackets from the content


def test_patient_response_carries_ssml_with_emotion_prosody() -> None:
    agent = PatientPersonaAgent()
    state = _state()
    resp = agent.respond(state, CHEST_PAIN_BASIC, "Do you smoke?")
    assert resp.emotional_state == "guarded"
    assert resp.ssml.startswith('<speak><prosody rate="slow" pitch="low" volume="soft">')
    assert ssml_escape(resp.content) in resp.ssml


def test_opening_patient_line_has_ssml() -> None:
    orchestrator = SimulationOrchestrator(patient_agent=PatientPersonaAgent())
    resp = orchestrator.handle(SimulationRequest(session_id="voice-open", action=SimulationAction.start))
    assert resp.patient is not None
    assert resp.patient.ssml.startswith('<speak><prosody rate="fast" pitch="high">')


def test_evaluator_spoken_summary_prefixed_with_score() -> None:
    evaluator = ClinicalEvaluatorAgent()
    result = evaluator.evaluate([_turn("I'm sorry this must be scary. Take your time.")], CHEST_PAIN_BASIC)
    assert result.spoken_summary.startswith('<speak><prosody rate="medium" pitch="medium">You scored ')
    assert f"You scored {result.overall_score} out of {result.max_score}." in result.spoken_summary


def test_spoken_evaluation_helper() -> None:
    out = spoken_evaluation(8, 20, "Strong: Symptom characterization.")
    assert out.startswith('<speak><prosody rate="medium" pitch="medium">You scored 8 out of 20. ')
    assert "Strong: Symptom characterization." in out
