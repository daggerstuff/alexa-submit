from __future__ import annotations

from unittest.mock import MagicMock, patch

from server.agents.llm_persona import LLMPersonaAgent
from server.agents.patient_persona import PatientState
from server.scenarios import CHEST_PAIN_BASIC


def _agent() -> LLMPersonaAgent:
    agent = LLMPersonaAgent()
    agent.bedrock_model = "qwen/qwen3-30b-a3b-instruct"
    return agent


def _converse(raw_text: str) -> MagicMock:
    """Return a fake bedrock-runtime client whose `converse` returns `raw_text`."""
    client = MagicMock()
    client.converse.return_value = {"output": {"message": {"content": [{"text": raw_text}]}}}
    return client


def test_falls_back_when_bedrock_not_configured() -> None:
    import os

    os.environ.pop("BEDROCK_MODEL_ID", None)
    agent = LLMPersonaAgent()
    assert not agent.available

    state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
    response = agent.respond(state, CHEST_PAIN_BASIC, "Where is the pain?")
    assert "chest" in response.content.lower()
    assert "chest-pressure" in response.disclosed_facts


def test_falls_back_on_bedrock_error() -> None:
    agent = _agent()
    client = MagicMock()
    client.converse.side_effect = Exception("ThrottlingException")

    with patch.object(LLMPersonaAgent, "_bedrock_client", return_value=client):
        state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
        response = agent.respond(state, CHEST_PAIN_BASIC, "Where is the pain?")
        assert "chest" in response.content.lower()
        assert "chest-pressure" in response.disclosed_facts


def test_parses_response_and_enforces_constraints() -> None:
    agent = _agent()
    llm_output = (
        '{"content": "It hurts right here in my chest.", "emotional_state": "anxious", '
        '"disclosed_facts": ["chest-pressure", "fake-fact"]}'
    )
    client = _converse(llm_output)

    with patch.object(LLMPersonaAgent, "_bedrock_client", return_value=client):
        state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
        response = agent.respond(state, CHEST_PAIN_BASIC, "Where is the pain?")

    assert "chest" in response.content.lower()
    assert "chest-pressure" in response.disclosed_facts
    assert "fake-fact" not in response.disclosed_facts
    assert response.emotional_state == "anxious"


def test_preserves_previously_disclosed_facts() -> None:
    agent = _agent()
    llm_output = '{"content": "I still feel the pressure.", "emotional_state": "worried", "disclosed_facts": []}'
    client = _converse(llm_output)

    state = PatientState(
        scenario_id="chest-pain-basic",
        scenario_version="1.1.0",
        disclosed_facts={"chest-pressure"},
    )

    with patch.object(LLMPersonaAgent, "_bedrock_client", return_value=client):
        response = agent.respond(state, CHEST_PAIN_BASIC, "Tell me more about it.")

    assert "chest-pressure" in response.disclosed_facts


def test_safety_note_on_severe_language() -> None:
    agent = _agent()
    llm_output = '{"content": "I feel like I might collapse.", "emotional_state": "distressed", "disclosed_facts": []}'
    client = _converse(llm_output)

    with patch.object(LLMPersonaAgent, "_bedrock_client", return_value=client):
        state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
        response = agent.respond(state, CHEST_PAIN_BASIC, "Are you going to collapse?")

    assert response.safety_note is not None


def test_parse_extracts_json_object_from_prose() -> None:
    raw = 'Sure, here you go:\n{"content": "It hurts.", "emotional_state": "anxious", "disclosed_facts": []}\nHope that helps.'
    parsed = LLMPersonaAgent._parse_response(raw)
    assert parsed["content"] == "It hurts."
    assert parsed["disclosed_facts"] == []


def test_rejects_claimed_disallowed_fact() -> None:
    agent = _agent()
    # Practitioner asks about pain only; the model claims a fact it may not disclose.
    llm_output = (
        '{"content": "It hurts in my chest.", "emotional_state": "anxious", '
        '"disclosed_facts": ["chest-pressure", "history-medications"]}'
    )
    client = _converse(llm_output)

    with patch.object(LLMPersonaAgent, "_bedrock_client", return_value=client):
        state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
        response = agent.respond(state, CHEST_PAIN_BASIC, "Where is the pain?")

    assert "chest-pressure" in response.disclosed_facts
    assert "history-medications" not in response.disclosed_facts


def test_rejects_disallowed_content_leak() -> None:
    agent = _agent()
    # Metadata is honest, but the prose repeats a disallowed disclosure verbatim.
    llm_output = (
        '{"content": "It hurts, and I take a blood-pressure medicine. I have high blood pressure, '
        'but no known medication allergies.", "emotional_state": "anxious", '
        '"disclosed_facts": ["chest-pressure"]}'
    )
    client = _converse(llm_output)

    with patch.object(LLMPersonaAgent, "_bedrock_client", return_value=client):
        state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
        response = agent.respond(state, CHEST_PAIN_BASIC, "Where is the pain?")

    assert "chest-pressure" in response.disclosed_facts
    assert "blood-pressure" not in response.content.lower()
