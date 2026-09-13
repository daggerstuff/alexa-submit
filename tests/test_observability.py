from fastapi.testclient import TestClient

from server.mcp_server import create_app
from server.observability import registry


def _client(**kwargs) -> TestClient:
    kwargs.setdefault("allowed_hosts", "testserver")
    kwargs.setdefault("allowed_origins", "http://testserver")
    return TestClient(create_app(**kwargs))


_INITIALIZE_BODY = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "pytest-client", "version": "0.1.0"},
    },
}


def test_health_ready_metrics_exposed() -> None:
    with _client() as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["service"] == "clinical-conversation-coach"

        ready = client.get("/ready")
        assert ready.status_code == 200
        assert ready.json()["status"] == "ready"

        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert "clinical_sim_sessions_active" in metrics.text
        assert "clinical_sim_requests_total" in metrics.text
        assert "clinical_sim_llm_fallbacks_total" in metrics.text


def test_health_endpoints_unauthenticated_with_api_key() -> None:
    with _client(api_key="secret") as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200
        assert client.get("/metrics").status_code == 200


def test_request_id_echoed_on_mcp_requests() -> None:
    with _client(api_key="secret") as client:
        response = client.post(
            "/mcp",
            headers={
                "accept": "application/json, text/event-stream",
                "authorization": "Bearer secret",
                "x-request-id": "req-123",
            },
            json=_INITIALIZE_BODY,
        )
        assert response.status_code == 200
        assert response.headers["x-request-id"] == "req-123"


def test_rate_limited_requests_are_counted() -> None:
    registry.reset()
    with _client(max_requests=1, window_seconds=60) as client:
        headers = {"accept": "application/json, text/event-stream"}
        assert client.post("/mcp", headers=headers, json=_INITIALIZE_BODY).status_code == 200
        assert client.post("/mcp", headers=headers, json=_INITIALIZE_BODY).status_code == 429
        assert "clinical_sim_rate_limited_total 1" in client.get("/metrics").text
    registry.reset()
