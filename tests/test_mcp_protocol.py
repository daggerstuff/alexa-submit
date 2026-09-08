from fastapi.testclient import TestClient
from mcp.server.transport_security import TransportSecuritySettings

from server.main import orchestrator
from server.mcp_server import mcp


def _make_client() -> TestClient:
    app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=False,
        host="127.0.0.1",
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=["testserver"],
            allowed_origins=["http://testserver"],
        ),
    )
    return TestClient(app)


def _init_session(client: TestClient) -> str:
    response = client.post(
        "/mcp",
        headers={"accept": "application/json, text/event-stream"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "pytest-client", "version": "0.1.0"},
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["result"]["protocolVersion"] == "2025-11-25"
    session_id = response.headers["mcp-session-id"]

    initialized = client.post(
        "/mcp",
        headers={
            "accept": "application/json, text/event-stream",
            "mcp-session-id": session_id,
        },
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert initialized.status_code == 202
    return session_id


def _call_tool(client: TestClient, session_id: str, req_id: int, name: str, arguments: dict) -> dict:
    response = client.post(
        "/mcp",
        headers={
            "accept": "application/json, text/event-stream",
            "mcp-session-id": session_id,
        },
        json={
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    assert response.status_code == 200
    return response.json()["result"]["structuredContent"]


def test_mcp_initialize_discover_and_call() -> None:
    with _make_client() as client:
        session_id = _init_session(client)

        tools = client.post(
            "/mcp",
            headers={
                "accept": "application/json, text/event-stream",
                "mcp-session-id": session_id,
            },
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        assert tools.status_code == 200
        names = {tool["name"] for tool in tools.json()["result"]["tools"]}
        assert {
            "list_simulation_scenarios",
            "start_simulation",
            "send_practitioner_turn",
            "evaluate_simulation",
            "end_simulation",
        }.issubset(names)

        call = _call_tool(client, session_id, 3, "list_simulation_scenarios", {})
        assert call["scenarios"][0]["scenario_id"] == "chest-pain-basic"


def test_mcp_full_simulation_workflow() -> None:
    orchestrator.sessions.clear()
    with _make_client() as client:
        session_id = _init_session(client)

        # List scenarios — all three should be present
        scenarios = _call_tool(client, session_id, 10, "list_simulation_scenarios", {})
        scenario_ids = {s["scenario_id"] for s in scenarios["scenarios"]}
        assert {
            "chest-pain-basic",
            "abdominal-pain-basic",
            "depression-screening-basic",
        } <= scenario_ids

        # Start simulation
        started = _call_tool(
            client,
            session_id,
            11,
            "start_simulation",
            {
                "session_id": "mcp-flow-1",
                "scenario_id": "chest-pain-basic",
            },
        )
        assert started["status"] == "active"
        assert started["patient"] is not None
        assert "chest" in started["patient"]["content"].lower()

        # Send practitioner turn — multi-topic question
        turn1 = _call_tool(
            client,
            session_id,
            12,
            "send_practitioner_turn",
            {
                "session_id": "mcp-flow-1",
                "practitioner_message": "My name is Alex. Where is the pain, are you short of breath, and what medications do you take?",
                "client_event_id": "mcp-event-1",
            },
        )
        assert turn1["patient"] is not None
        disclosed = set(turn1["patient"]["disclosed_facts"])
        # Multi-topic matching should disclose multiple facts in one turn
        assert "chest-pressure" in disclosed
        assert "dyspnea" in disclosed
        assert "history-medications" in disclosed

        # Retry with same client_event_id — should be idempotent
        retry = _call_tool(
            client,
            session_id,
            13,
            "send_practitioner_turn",
            {
                "session_id": "mcp-flow-1",
                "practitioner_message": "This should not be processed.",
                "client_event_id": "mcp-event-1",
            },
        )
        assert len(retry["transcript"]) == len(turn1["transcript"])

        # Evaluate (without ending)
        evaluation = _call_tool(
            client,
            session_id,
            14,
            "evaluate_simulation",
            {
                "session_id": "mcp-flow-1",
            },
        )
        assert evaluation["evaluation"] is not None
        assert evaluation["evaluation"]["rubric_version"] == "1.1.0"
        assert evaluation["status"] == "evaluated"

        # End simulation — should lock session
        ended = _call_tool(
            client,
            session_id,
            15,
            "end_simulation",
            {
                "session_id": "mcp-flow-1",
            },
        )
        assert ended["status"] == "ended"
        assert ended["evaluation"] is not None


def test_mcp_abdominal_pain_scenario() -> None:
    orchestrator.sessions.clear()
    with _make_client() as client:
        session_id = _init_session(client)

        started = _call_tool(
            client,
            session_id,
            20,
            "start_simulation",
            {
                "session_id": "abdom-1",
                "scenario_id": "abdominal-pain-basic",
            },
        )
        assert started["status"] == "active"
        assert "stomach" in started["patient"]["content"].lower()

        turn1 = _call_tool(
            client,
            session_id,
            21,
            "send_practitioner_turn",
            {
                "session_id": "abdom-1",
                "practitioner_message": "Where does it hurt and have you had any nausea or fever?",
            },
        )
        disclosed = set(turn1["patient"]["disclosed_facts"])
        assert "pain-location" in disclosed
        assert "appetite" in disclosed
        assert "fever" in disclosed

        evaluation = _call_tool(
            client,
            session_id,
            22,
            "evaluate_simulation",
            {
                "session_id": "abdom-1",
            },
        )
        assert evaluation["evaluation"]["rubric_version"] == "1.0.0"


def test_mcp_depression_screening_scenario() -> None:
    orchestrator.sessions.clear()
    with _make_client() as client:
        session_id = _init_session(client)

        started = _call_tool(
            client,
            session_id,
            30,
            "start_simulation",
            {
                "session_id": "dep-1",
                "scenario_id": "depression-screening-basic",
            },
        )
        assert started["status"] == "active"
        assert "tired" in started["patient"]["content"].lower() or "down" in started["patient"]["content"].lower()

        turn1 = _call_tool(
            client,
            session_id,
            31,
            "send_practitioner_turn",
            {
                "session_id": "dep-1",
                "practitioner_message": "Hello, my name is Sam. How long have you been feeling down, and how has your sleep been?",
            },
        )
        disclosed = set(turn1["patient"]["disclosed_facts"])
        assert "mood-duration" in disclosed
        assert "sleep" in disclosed

        evaluation = _call_tool(
            client,
            session_id,
            32,
            "evaluate_simulation",
            {
                "session_id": "dep-1",
            },
        )
        assert evaluation["evaluation"]["rubric_version"] == "1.0.0"
        metric_ids = {m["metric_id"] for m in evaluation["evaluation"]["metrics"]}
        assert "risk" in metric_ids
