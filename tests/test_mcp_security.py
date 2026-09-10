from fastapi.testclient import TestClient

from server.mcp_server import create_app


def _secured_client(**kwargs) -> TestClient:
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


def _initialize(client: TestClient, **headers) -> TestClient:
    merged = {"accept": "application/json, text/event-stream", **headers}
    return client.post("/mcp", headers=merged, json=_INITIALIZE_BODY)


def test_no_auth_or_rate_limit_by_default() -> None:
    with _secured_client() as client:
        assert _initialize(client).status_code == 200


def test_unauthenticated_rejected_when_api_key_configured() -> None:
    with _secured_client(api_key="secret") as client:
        assert _initialize(client).status_code == 401


def test_bearer_token_accepted() -> None:
    with _secured_client(api_key="secret") as client:
        response = _initialize(client, authorization="Bearer secret")
        assert response.status_code == 200


def test_x_api_key_header_accepted() -> None:
    with _secured_client(api_key="secret") as client:
        response = _initialize(client, **{"x-api-key": "secret"})
        assert response.status_code == 200


def test_wrong_key_rejected() -> None:
    with _secured_client(api_key="secret") as client:
        assert _initialize(client, authorization="Bearer wrong").status_code == 401


def test_rate_limit_returns_429() -> None:
    with _secured_client(max_requests=2, window_seconds=60) as client:
        assert _initialize(client).status_code == 200
        assert _initialize(client).status_code == 200
        assert _initialize(client).status_code == 429


def test_rate_limit_disabled_by_default() -> None:
    # A zero/absent limit means no limiter is installed and requests are never throttled.
    with _secured_client(max_requests=0) as client:
        assert _initialize(client).status_code == 200
        assert _initialize(client).status_code == 200
        assert _initialize(client).status_code == 200
