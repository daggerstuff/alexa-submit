from fastapi.testclient import TestClient

from server.main import app, orchestrator

client = TestClient(app)


def setup_function() -> None:
    orchestrator.sessions.clear()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == "0.3.0"


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
        json={
            "session_id": session_id,
            "action": "message",
            "practitioner_message": "continue",
        },
    )
    assert blocked.status_code == 409


def test_multi_topic_matching_discloses_multiple_facts() -> None:
    session_id = "multi-topic"
    client.post("/mcp/simulate", json={"session_id": session_id, "action": "start"})

    response = client.post(
        "/mcp/simulate",
        json={
            "session_id": session_id,
            "action": "message",
            "practitioner_message": "Where is the pain and are you short of breath?",
        },
    )
    assert response.status_code == 200
    disclosed = set(response.json()["patient"]["disclosed_facts"])
    assert "chest-pressure" in disclosed
    assert "dyspnea" in disclosed


def test_abdominal_pain_scenario() -> None:
    session_id = "abdom-test"
    start = client.post(
        "/mcp/simulate",
        json={
            "session_id": session_id,
            "action": "start",
            "scenario_id": "abdominal-pain-basic",
        },
    )
    assert start.status_code == 200
    assert start.json()["scenario_version"] == "1.0.0"
    assert "stomach" in start.json()["patient"]["content"].lower()

    turn = client.post(
        "/mcp/simulate",
        json={
            "session_id": session_id,
            "action": "message",
            "practitioner_message": "Where does it hurt, is it sharp or dull, and have you had any fever or nausea?",
        },
    )
    assert turn.status_code == 200
    disclosed = set(turn.json()["patient"]["disclosed_facts"])
    assert "pain-location" in disclosed
    assert "pain-quality" in disclosed
    assert "fever" in disclosed
    assert "appetite" in disclosed

    evaluation = client.post(
        "/mcp/simulate",
        json={
            "session_id": session_id,
            "action": "evaluate",
        },
    )
    result = evaluation.json()["evaluation"]
    assert result["rubric_version"] == "1.0.0"
    assert result["max_score"] == 24  # 6 metrics x 4 max each
    metric_ids = {m["metric_id"] for m in result["metrics"]}
    assert "associated" in metric_ids
    assert "history" in metric_ids


def test_depression_screening_scenario() -> None:
    session_id = "dep-test"
    start = client.post(
        "/mcp/simulate",
        json={
            "session_id": session_id,
            "action": "start",
            "scenario_id": "depression-screening-basic",
        },
    )
    assert start.status_code == 200
    assert start.json()["scenario_version"] == "1.0.0"
    content = start.json()["patient"]["content"].lower()
    assert "tired" in content or "down" in content

    turn = client.post(
        "/mcp/simulate",
        json={
            "session_id": session_id,
            "action": "message",
            "practitioner_message": "My name is Sam. How long have you been feeling down, how is your sleep, and have you lost interest in things?",
        },
    )
    assert turn.status_code == 200
    disclosed = set(turn.json()["patient"]["disclosed_facts"])
    assert "mood-duration" in disclosed
    assert "sleep" in disclosed
    assert "interest" in disclosed

    evaluation = client.post(
        "/mcp/simulate",
        json={
            "session_id": session_id,
            "action": "evaluate",
        },
    )
    result = evaluation.json()["evaluation"]
    assert result["rubric_version"] == "1.0.0"
    assert result["max_score"] == 24  # 6 metrics x 4 max each
    metric_ids = {m["metric_id"] for m in result["metrics"]}
    assert "risk" in metric_ids
    assert "somatic" in metric_ids


def test_scenario_switch_rejected() -> None:
    session_id = "switch-test"
    client.post(
        "/mcp/simulate",
        json={
            "session_id": session_id,
            "action": "start",
            "scenario_id": "chest-pain-basic",
        },
    )
    response = client.post(
        "/mcp/simulate",
        json={
            "session_id": session_id,
            "action": "message",
            "scenario_id": "abdominal-pain-basic",
            "practitioner_message": "test",
        },
    )
    assert response.status_code == 409


def test_unknown_scenario_rejected() -> None:
    response = client.post(
        "/mcp/simulate",
        json={
            "session_id": "unknown-scenario",
            "action": "start",
            "scenario_id": "nonexistent",
        },
    )
    assert response.status_code == 404


def test_safety_note_on_severe_language() -> None:
    session_id = "safety-test"
    client.post("/mcp/simulate", json={"session_id": session_id, "action": "start"})
    response = client.post(
        "/mcp/simulate",
        json={
            "session_id": session_id,
            "action": "message",
            "practitioner_message": "Are you going to collapse? This seems severe.",
        },
    )
    assert response.status_code == 200
    assert response.json()["patient"]["safety_note"] is not None
