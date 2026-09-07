from fastapi.testclient import TestClient

from mcp.server.transport_security import TransportSecuritySettings

from server.mcp_server import mcp


def test_mcp_initialize_discover_and_call() -> None:
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
    with TestClient(app) as client:
        initialize = client.post(
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
        assert initialize.status_code == 200
        session_id = initialize.headers["mcp-session-id"]
        assert initialize.json()["result"]["protocolVersion"] == "2025-11-25"

        initialized = client.post(
            "/mcp",
            headers={"accept": "application/json, text/event-stream", "mcp-session-id": session_id},
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        assert initialized.status_code == 202

        tools = client.post(
            "/mcp",
            headers={"accept": "application/json, text/event-stream", "mcp-session-id": session_id},
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

        call = client.post(
            "/mcp",
            headers={"accept": "application/json, text/event-stream", "mcp-session-id": session_id},
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "list_simulation_scenarios", "arguments": {}},
            },
        )
        assert call.status_code == 200
        assert call.json()["result"]["structuredContent"]["scenarios"][0]["scenario_id"] == "chest-pain-basic"
