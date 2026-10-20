from __future__ import annotations

from unittest.mock import MagicMock, patch

from server.agents.llm_persona import LLMPersonaAgent
from server.agents.patient_persona import PatientState
from server.scenarios import CHEST_PAIN_BASIC


def test_bedrock_unavailable_without_model_id() -> None:
    agent = LLMPersonaAgent()

    agent.bedrock_model = ""

    assert not agent.available

    state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
    response = agent.respond(state, CHEST_PAIN_BASIC, "Where is the pain?")
    assert "chest" in response.content.lower()
    assert "chest-pressure" in response.disclosed_facts


def test_bedrock_request_builds_converse_shape() -> None:
    agent = LLMPersonaAgent()

    agent.bedrock_model = "qwen/qwen3-30b-a3b-instruct"

    messages = [
        {"role": "system", "content": "You are a simulated patient."},
        {"role": "user", "content": "Practitioner says: Where is the pain?"},
    ]
    req = agent._build_bedrock_request(messages)

    assert req["modelId"] == "qwen/qwen3-30b-a3b-instruct"
    assert req["system"] == [{"text": "You are a simulated patient."}]
    assert req["messages"] == [{"role": "user", "content": [{"text": "Practitioner says: Where is the pain?"}]}]
    # maxTokens must be explicit (unset values reserve the model's full quota).
    assert req["inferenceConfig"]["maxTokens"] == 300
    assert req["inferenceConfig"]["temperature"] == 0.7


def test_bedrock_complete_calls_converse() -> None:
    agent = LLMPersonaAgent()

    agent.bedrock_model = "qwen/qwen3-30b-a3b-instruct"

    fake_client = MagicMock()
    fake_client.converse.return_value = {
        "output": {
            "message": {
                "content": [
                    {
                        "text": '{"content": "It hurts in my chest.", '
                        '"emotional_state": "anxious", "disclosed_facts": ["chest-pressure"]}'
                    }
                ]
            }
        }
    }

    messages = [
        {"role": "system", "content": "You are a simulated patient."},
        {"role": "user", "content": "Practitioner says: Where is the pain?"},
    ]
    with patch.object(LLMPersonaAgent, "_bedrock_client", return_value=fake_client):
        raw = agent._complete_bedrock(messages)

    assert "chest" in raw
    fake_client.converse.assert_called_once()
    kwargs = fake_client.converse.call_args.kwargs
    assert kwargs["modelId"] == "qwen/qwen3-30b-a3b-instruct"
    assert kwargs["inferenceConfig"]["maxTokens"] == 300


def test_bedrock_respond_enforces_constraints() -> None:
    agent = LLMPersonaAgent()
    agent.bedrock_model = "qwen/qwen3-30b-a3b-instruct"
    agent.providers = [{"name": "bedrock", "kind": "bedrock"}]

    fake_client = MagicMock()
    fake_client.converse.return_value = {
        "output": {
            "message": {
                "content": [
                    {
                        "text": '{"content": "It hurts right here in my chest.", '
                        '"emotional_state": "anxious", '
                        '"disclosed_facts": ["chest-pressure", "fake-fact"]}'
                    }
                ]
            }
        },
        "stopReason": "end_turn",
    }

    state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
    with patch.object(LLMPersonaAgent, "_bedrock_client", return_value=fake_client):
        response = agent.respond(state, CHEST_PAIN_BASIC, "Where is the pain?")

    assert "chest" in response.content.lower()
    assert "chest-pressure" in response.disclosed_facts
    assert "fake-fact" not in response.disclosed_facts


def test_bedrock_guardrail_config_sent_when_configured() -> None:
    agent = LLMPersonaAgent()
    agent.bedrock_model = "qwen/qwen3-30b-a3b-instruct"
    agent.bedrock_guardrail_id = "gr-1234567890"
    agent.bedrock_guardrail_version = "3"

    messages = [
        {"role": "system", "content": "You are a simulated patient."},
        {"role": "user", "content": "Practitioner says: Where is the pain?"},
    ]
    req = agent._build_bedrock_request(messages)

    # Blanket guardrailConfig: identifier + pinned numbered version + trace off.
    assert req["guardrailConfig"] == {
        "guardrailIdentifier": "gr-1234567890",
        "guardrailVersion": "3",
        "trace": "disabled",
    }


def test_bedrock_guardrail_config_omitted_when_unset() -> None:
    agent = LLMPersonaAgent()
    agent.bedrock_model = "qwen/qwen3-30b-a3b-instruct"
    agent.bedrock_guardrail_id = ""

    req = agent._build_bedrock_request([{"role": "user", "content": "Practitioner says: Where is the pain?"}])

    assert "guardrailConfig" not in req


def test_bedrock_guardrail_trace_flag_propagates() -> None:
    agent = LLMPersonaAgent()
    agent.bedrock_model = "qwen/qwen3-30b-a3b-instruct"
    agent.bedrock_guardrail_id = "gr-1234567890"
    agent.bedrock_guardrail_trace = True

    req = agent._build_bedrock_request([{"role": "user", "content": "Practitioner says: Where is the pain?"}])

    assert req["guardrailConfig"]["trace"] == "enabled"


def test_bedrock_guardrail_intervention_degrades_to_deterministic() -> None:
    agent = LLMPersonaAgent()
    agent.bedrock_model = "qwen/qwen3-30b-a3b-instruct"
    agent.providers = [{"name": "bedrock", "kind": "bedrock"}]

    # A blocked turn returns stopReason=guardrail_intervened and no content.
    fake_client = MagicMock()
    fake_client.converse.return_value = {"stopReason": "guardrail_intervened"}

    state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
    with patch.object(LLMPersonaAgent, "_bedrock_client", return_value=fake_client):
        response = agent.respond(state, CHEST_PAIN_BASIC, "Where is the pain?")

    # The deterministic persona still answers, inside the scenario constraints.
    assert "chest" in response.content.lower()
    assert "chest-pressure" in response.disclosed_facts
    fake_client.converse.assert_called_once()


def test_bedrock_empty_content_degrades_to_deterministic() -> None:
    agent = LLMPersonaAgent()
    agent.bedrock_model = "qwen/qwen3-30b-a3b-instruct"
    agent.providers = [{"name": "bedrock", "kind": "bedrock"}]

    fake_client = MagicMock()
    fake_client.converse.return_value = {
        "output": {"message": {"content": []}},
        "stopReason": "end_turn",
    }

    state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
    with patch.object(LLMPersonaAgent, "_bedrock_client", return_value=fake_client):
        response = agent.respond(state, CHEST_PAIN_BASIC, "Where is the pain?")

    assert "chest" in response.content.lower()
