from fastapi.testclient import TestClient

from server.main import app, orchestrator

client = TestClient(app)


def setup_function() -> None:
    orchestrator.sessions.clear()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == "0.2.0"


def test_session_flow_and_versioned_rubric() -> None:
    session_id = "test-session"
    start = client.post("/mcp/simulate", json={"session_id": session_id, "action": "start"})
    assert start.status_code == 200
    assert start.json()["status"] == "active"
    assert start.json()["scenario_version"] == "1.1.0"

    message = client.post(
        "/mcp/simulate",
        json={
            "session_id": session_id,
            "action": "message",
            "client_event_id": "event-1",
            "practitioner_message": "My name is Alex. Where is the pain, are you short of breath, and what medications do you take?",
        },
    )
    assert message.status_code == 200
    assert "chest" in message.json()["patient"]["content"].lower()
    assert "chest-pressure" in message.json()["patient"]["disclosed_facts"]

    duplicate = client.post(
        "/mcp/simulate",
        json={
            "session_id": session_id,
            "action": "message",
            "client_event_id": "event-1",
            "practitioner_message": "This should not be processed twice.",
        },
    )
    assert duplicate.status_code == 200
    assert len(duplicate.json()["transcript"]) == len(message.json()["transcript"])

    evaluation = client.post("/mcp/simulate", json={"session_id": session_id, "action": "evaluate"})
    assert evaluation.status_code == 200
    result = evaluation.json()["evaluation"]
    assert result["rubric_version"] == "1.1.0"
    assert result["max_score"] == 20
    assert any(item["metric_id"] == "closed_loop" for item in result["metrics"])


def test_end_locks_session() -> None:
    session_id = "ended-session"
    client.post("/mcp/simulate", json={"session_id": session_id, "action": "start"})
    ended = client.post("/mcp/simulate", json={"session_id": session_id, "action": "end"})
    assert ended.status_code == 200
    blocked = client.post(
        "/mcp/simulate",
        json={"session_id": session_id, "action": "message", "practitioner_message": "continue"},
    )
    assert blocked.status_code == 409
