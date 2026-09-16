from __future__ import annotations

from unittest.mock import MagicMock, patch

from server.agents.llm_persona import LLMPersonaAgent
from server.agents.patient_persona import PatientState
from server.scenarios import CHEST_PAIN_BASIC


def test_not_spoken_accepts_clean_spoken_prose() -> None:
    assert not LLMPersonaAgent._not_spoken("It feels like pressure right in the middle of my chest.")


def test_not_spoken_rejects_bullet_lists() -> None:
    assert LLMPersonaAgent._not_spoken("- It hurts here.\n- I feel short of breath.")


def test_not_spoken_rejects_role_break() -> None:
    assert LLMPersonaAgent._not_spoken("As a simulated patient, I would say it hurts.")


def test_not_spoken_rejects_verbosity() -> None:
    content = " ".join(["It hurts here."] * 30)  # 90 words
    assert LLMPersonaAgent._not_spoken(content)


def test_system_prompt_includes_voice_rules() -> None:
    state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
    prompt = LLMPersonaAgent()._build_system_prompt(state, CHEST_PAIN_BASIC)
    assert "VOICE RULES" in prompt
    assert "read aloud" in prompt
    assert "under about 35 words" in prompt
    assert "Never break character" in prompt


def test_respond_falls_back_on_non_spoken_output() -> None:
    agent = LLMPersonaAgent()
    agent.bedrock_model = "qwen/qwen3-30b-a3b-instruct"
    agent.providers = [{"name": "bedrock", "kind": "bedrock"}]

    llm_output = (
        '{"content": "- It hurts here.\\n- I feel short of breath.", '
        '"emotional_state": "anxious", "disclosed_facts": []}'
    )
    client = MagicMock()
    client.converse.return_value = {"output": {"message": {"content": [{"text": llm_output}]}}}

    with patch.object(LLMPersonaAgent, "_bedrock_client", return_value=client):
        state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
        response = agent.respond(state, CHEST_PAIN_BASIC, "Where is the pain?")

    # Deterministic fallback, not the bullet-list content.
    assert "chest" in response.content.lower()
    assert "- " not in response.content
