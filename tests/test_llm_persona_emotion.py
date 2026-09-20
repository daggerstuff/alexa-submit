from __future__ import annotations

from server.agents.llm_persona import LLMPersonaAgent
from server.agents.patient_persona import PatientState
from server.scenarios import DisclosureRule


def _state(last_emotional_state: str = "anxious") -> PatientState:
    return PatientState(
        scenario_id="chest-pain-basic", scenario_version="1.2.0", last_emotional_state=last_emotional_state
    )


def test_resolve_emotion_forces_guarded_on_pure_withholding() -> None:
    emotion = LLMPersonaAgent._resolve_emotion({}, _state(), None, ["smoking-history"], set())
    assert emotion == "guarded"


def test_resolve_emotion_keeps_known_llm_state() -> None:
    emotion = LLMPersonaAgent._resolve_emotion({"emotional_state": "Concerned"}, _state(), None, [], {"pain"})
    assert emotion == "concerned"


def test_resolve_emotion_bounds_unknown_state_to_last() -> None:
    emotion = LLMPersonaAgent._resolve_emotion({"emotional_state": "reluctant"}, _state("worried"), None, [], {"pain"})
    assert emotion == "worried"


def test_resolve_emotion_prefers_volunteer() -> None:
    volunteer = DisclosureRule(
        fact_id="smoking-history", trigger_terms=("smoke",), response="x", emotional_state="reflective"
    )
    emotion = LLMPersonaAgent._resolve_emotion({"emotional_state": "anxious"}, _state(), volunteer, [], {"pain"})
    assert emotion == "reflective"


def test_resolve_emotion_defaults_to_last_when_llm_omits() -> None:
    emotion = LLMPersonaAgent._resolve_emotion({}, _state("calm"), None, [], {"pain"})
    assert emotion == "calm"
