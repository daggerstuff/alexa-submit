from __future__ import annotations

from unittest.mock import MagicMock, patch

from server.agents.llm_persona import LLMPersonaAgent
from server.agents.patient_persona import PatientState
from server.scenarios import CHEST_PAIN_BASIC


def test_openai_completion_posts_chat_completions() -> None:
    agent = LLMPersonaAgent()
    agent.timeout = 15.0
    provider = {
        "name": "nim",
        "kind": "openai",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key": "nv-key",
        "model": "qwen/qwen2.5-72b-instruct",
    }

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "hello"}}]}

    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    with patch("server.agents.llm_persona.httpx.post", return_value=mock_response) as post:
        raw = agent._complete_openai(provider, messages)

    assert raw == "hello"
    post.assert_called_once()
    assert post.call_args.args[0] == "https://integrate.api.nvidia.com/v1/chat/completions"
    kwargs = post.call_args.kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer nv-key"
    assert kwargs["json"]["model"] == "qwen/qwen2.5-72b-instruct"
    assert kwargs["json"]["messages"] == messages


def test_fallback_chain_skips_failed_provider() -> None:
    agent = LLMPersonaAgent()
    agent.bedrock_model = "qwen/qwen3-30b-a3b-instruct"
    agent.providers = [
        {"name": "bedrock", "kind": "bedrock"},
        {
            "name": "nim",
            "kind": "openai",
            "base_url": "https://integrate.api.nvidia.com/v1",
            "api_key": "k",
            "model": "m",
        },
    ]

    bedrock_client = MagicMock()
    bedrock_client.converse.side_effect = Exception("throttled")
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '{"content": "ok", "emotional_state": "calm", "disclosed_facts": []}'}}]
    }

    with (
        patch.object(LLMPersonaAgent, "_bedrock_client", return_value=bedrock_client),
        patch("server.agents.llm_persona.httpx.post", return_value=mock_response) as post,
    ):
        raw = agent._complete([{"role": "user", "content": "u"}])

    assert "ok" in raw
    post.assert_called_once()  # NIM was tried after Bedrock failed


def test_complete_raises_when_every_provider_fails() -> None:
    agent = LLMPersonaAgent()
    agent.bedrock_model = "qwen/qwen3-30b-a3b-instruct"
    agent.providers = [{"name": "bedrock", "kind": "bedrock"}]

    client = MagicMock()
    client.converse.side_effect = Exception("down")

    with patch.object(LLMPersonaAgent, "_bedrock_client", return_value=client):
        state = PatientState(scenario_id="chest-pain-basic", scenario_version="1.1.0")
        response = agent.respond(state, CHEST_PAIN_BASIC, "Where is the pain?")

    # `_complete` raised, so `respond` fell back to the deterministic persona.
    assert "chest" in response.content.lower()
    assert "chest-pressure" in response.disclosed_facts


def test_provider_chain_from_env(monkeypatch) -> None:
    monkeypatch.setenv("INFERENCE_PROVIDER", "bedrock,nim,cloudflare")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "qwen/qwen3-30b-a3b-instruct")
    monkeypatch.setenv("NIM_API_KEY", "nv-key")
    monkeypatch.setenv("NIM_MODEL", "qwen/qwen2.5-72b-instruct")
    # CLOUDFLARE_BASE_URL is unset → cloudflare has no base URL and is skipped.
    monkeypatch.delenv("CLOUDFLARE_BASE_URL", raising=False)

    agent = LLMPersonaAgent()
    assert agent.available
    assert [p["name"] for p in agent.providers] == ["bedrock", "nim"]


def test_nim_uses_default_base_url(monkeypatch) -> None:
    monkeypatch.setenv("INFERENCE_PROVIDER", "nim")
    monkeypatch.setenv("NIM_API_KEY", "nv-key")
    monkeypatch.setenv("NIM_MODEL", "qwen/qwen2.5-72b-instruct")
    monkeypatch.delenv("NIM_BASE_URL", raising=False)

    agent = LLMPersonaAgent()
    assert agent.available
    assert agent.providers[0]["base_url"] == "https://integrate.api.nvidia.com/v1"


def test_cloudflare_provider_from_env(monkeypatch) -> None:
    monkeypatch.setenv("INFERENCE_PROVIDER", "cloudflare")
    monkeypatch.setenv("CLOUDFLARE_BASE_URL", "https://api.cloudflare.com/client/v4/accounts/abc/ai/v1")
    monkeypatch.setenv("CLOUDFLARE_API_KEY", "cf-key")
    monkeypatch.setenv("CLOUDFLARE_MODEL", "@cf/qwen/qwen1.5-14b-chat")

    agent = LLMPersonaAgent()
    assert agent.available
    assert agent.providers[0]["name"] == "cloudflare"
    assert agent.providers[0]["kind"] == "openai"


def test_orchestrator_selects_llm_agent_for_openai_provider(monkeypatch) -> None:
    monkeypatch.setenv("INFERENCE_PROVIDER", "nim")
    monkeypatch.setenv("NIM_API_KEY", "k")
    monkeypatch.setenv("NIM_MODEL", "m")

    from server.agents.llm_persona import LLMPersonaAgent
    from server.main import SimulationOrchestrator

    orch = SimulationOrchestrator()
    assert isinstance(orch.patient_agent, LLMPersonaAgent)
