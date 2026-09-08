from __future__ import annotations

from unittest.mock import MagicMock, patch

from server.agents.llm_persona import LLMPersonaAgent
from server.agents.patient_persona import PatientState
from server.scenarios import CHEST_PAIN_BASIC


def test_llm_falls_back_when_not_configured() -> None:
    import os

    os.environ.pop("INFERENCE_BASE_URL", None)
    os.environ.pop("INFERENCE_API_KEY", None)

    agent = LLMPersonaAgent()
    assert not agent.available

    state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
    response = agent.respond(state, CHEST_PAIN_BASIC, "Where is the pain?")
    assert "chest" in response.content.lower()
    assert "chest-pressure" in response.disclosed_facts


def test_llm_falls_back_on_api_error() -> None:
    agent = LLMPersonaAgent()
    agent.base_url = "http://fake"
    agent.api_key = "fake"

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("Connection refused")

    with patch("server.agents.llm_persona.httpx.post", return_value=mock_response):
        state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
        response = agent.respond(state, CHEST_PAIN_BASIC, "Where is the pain?")
        assert "chest" in response.content.lower()
        assert "chest-pressure" in response.disclosed_facts


def test_llm_parses_response_and_enforces_constraints() -> None:
    agent = LLMPersonaAgent()
    agent.base_url = "http://fake"
    agent.api_key = "fake"

    llm_output = '{"content": "It hurts right here in my chest.", "emotional_state": "anxious", "disclosed_facts": ["chest-pressure", "fake-fact"]}'
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": llm_output}}]}

    with patch("server.agents.llm_persona.httpx.post", return_value=mock_response):
        state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
        response = agent.respond(state, CHEST_PAIN_BASIC, "Where is the pain?")

    assert "chest" in response.content.lower()
    assert "chest-pressure" in response.disclosed_facts
    assert "fake-fact" not in response.disclosed_facts
    assert response.emotional_state == "anxious"


def test_llm_preserves_previously_disclosed_facts() -> None:
    agent = LLMPersonaAgent()
    agent.base_url = "http://fake"
    agent.api_key = "fake"

    llm_output = '{"content": "I still feel the pressure.", "emotional_state": "worried", "disclosed_facts": []}'
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": llm_output}}]}

    state = PatientState(
        scenario_id="chest-pain-basic",
        scenario_version="1.1.0",
        disclosed_facts={"chest-pressure"},
    )

    with patch("server.agents.llm_persona.httpx.post", return_value=mock_response):
        response = agent.respond(state, CHEST_PAIN_BASIC, "Tell me more about it.")

    assert "chest-pressure" in response.disclosed_facts


def test_llm_safety_note_on_severe_language() -> None:
    agent = LLMPersonaAgent()
    agent.base_url = "http://fake"
    agent.api_key = "fake"

    llm_output = '{"content": "I feel like I might collapse.", "emotional_state": "distressed", "disclosed_facts": []}'
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": llm_output}}]}

    with patch("server.agents.llm_persona.httpx.post", return_value=mock_response):
        state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
        response = agent.respond(state, CHEST_PAIN_BASIC, "Are you going to collapse?")

    assert response.safety_note is not None
