from __future__ import annotations

import json

import pytest

from server.agents.patient_persona import PatientPersonaAgent
from server.main import SimulationOrchestrator
from server.scenario_authoring import validate_scenario
from server.scenarios import all_scenarios, custom_scenarios, get_scenario, remove_custom_scenario
from server.schemas.validation import SimulationAction, SimulationRequest


def _scenario(scenario_id: str = "custom-chest", **overrides) -> dict:
    data: dict = {
        "scenario_id": scenario_id,
        "version": "1.0.0",
        "title": "Custom scenario",
        "opening": "Hello, I feel unwell.",
        "goal": "Assess the patient.",
        "difficulty": "basic",
        "safety_terms": ["collapse"],
        "pitfalls": ["go home"],
        "disclosures": [
            {"fact_id": "pain", "trigger_terms": ["pain"], "response": "It hurts here.", "emotional_state": "worried"},
        ],
        "metrics": [
            {
                "metric_id": "history",
                "name": "History",
                "trigger_terms": ["pain", "when"],
                "rationale": "Asks about the pain.",
                "max_score": 4,
                "coaching_hint": "Ask where and when.",
            }
        ],
    }
    data.update(overrides)
    return data


def _raw(**overrides) -> str:
    return json.dumps(_scenario(**overrides))


@pytest.fixture(autouse=True)
def _isolate_custom_registry():
    before = set(custom_scenarios())
    yield
    for scenario_id in set(custom_scenarios()) - before:
        remove_custom_scenario(scenario_id)


def test_validate_valid_scenario() -> None:
    result = validate_scenario(_raw())
    assert result.valid
    assert result.errors == []
    assert result.warnings == []
    assert result.scenario_id == "custom-chest"
    assert result.disclosure_count == 1
    assert result.metric_count == 1
    assert result.max_score == 4


def test_validate_invalid_json() -> None:
    result = validate_scenario("{not json")
    assert not result.valid
    assert any("Invalid JSON" in error for error in result.errors)


def test_validate_missing_required_field() -> None:
    data = _scenario()
    data.pop("metrics")
    result = validate_scenario(json.dumps(data))
    assert not result.valid
    assert any("metrics" in error for error in result.errors)


def test_validate_warns_unreachable_rapport() -> None:
    result = validate_scenario(
        _raw(
            disclosures=[
                {
                    "fact_id": "smoking",
                    "trigger_terms": ["smoke"],
                    "response": "I used to smoke.",
                    "emotional_state": "reflective",
                    "rapport_required": 5,
                }
            ]
        )
    )
    assert result.valid
    assert any("rapport ceiling" in warning for warning in result.warnings)


def test_validate_warns_duplicate_fact_id() -> None:
    result = validate_scenario(
        _raw(
            disclosures=[
                {"fact_id": "pain", "trigger_terms": ["pain"], "response": "A", "emotional_state": "worried"},
                {"fact_id": "pain", "trigger_terms": ["ache"], "response": "B", "emotional_state": "worried"},
            ]
        )
    )
    assert result.valid
    assert any("duplicate fact_id 'pain'" in warning for warning in result.warnings)


def test_validate_warns_empty_trigger_terms() -> None:
    result = validate_scenario(
        _raw(
            disclosures=[
                {"fact_id": "pain", "trigger_terms": [], "response": "It hurts.", "emotional_state": "worried"}
            ]
        )
    )
    assert result.valid
    assert any("no trigger_terms" in warning for warning in result.warnings)


def test_create_rejects_builtin_id(tmp_path) -> None:
    orch = SimulationOrchestrator(db_path=str(tmp_path / "db.sqlite"), patient_agent=PatientPersonaAgent())
    with pytest.raises(ValueError, match="reserved"):
        orch.create_scenario(_raw(scenario_id="chest-pain-basic"))


def test_create_and_run_custom_scenario(tmp_path) -> None:
    orch = SimulationOrchestrator(db_path=str(tmp_path / "db.sqlite"), patient_agent=PatientPersonaAgent())
    created = orch.create_scenario(_raw(scenario_id="custom-chest"))
    assert created.status == "created"
    assert "custom-chest" in all_scenarios()

    resp = orch.handle(
        SimulationRequest(session_id="custom-1", action=SimulationAction.start, scenario_id="custom-chest")
    )
    assert resp.patient is not None
    assert resp.patient.content == "Hello, I feel unwell."
    assert resp.scenario_id == "custom-chest"


def test_create_then_update_returns_updated(tmp_path) -> None:
    orch = SimulationOrchestrator(db_path=str(tmp_path / "db.sqlite"), patient_agent=PatientPersonaAgent())
    assert orch.create_scenario(_raw()).status == "created"
    assert orch.create_scenario(_raw(version="1.1.0")).status == "updated"
    assert get_scenario("custom-chest").version == "1.1.0"


def test_delete_custom_and_builtin(tmp_path) -> None:
    orch = SimulationOrchestrator(db_path=str(tmp_path / "db.sqlite"), patient_agent=PatientPersonaAgent())
    orch.create_scenario(_raw(scenario_id="custom-chest"))
    assert orch.delete_scenario("custom-chest").status == "deleted"
    assert orch.delete_scenario("custom-chest").status == "not_found"
    assert orch.delete_scenario("chest-pain-basic").status == "builtin"


def test_scenario_store_skips_corrupt_rows(tmp_path) -> None:
    from server.storage import ScenarioStore

    store = ScenarioStore(str(tmp_path / "db.sqlite"))
    store.upsert("good", {"scenario_id": "good", "version": "1.0.0"})
    with store._lock:
        store._conn.execute(
            "INSERT INTO custom_scenarios (scenario_id, definition) VALUES (?, ?)",
            ("bad", "{not json"),
        )
        store._conn.commit()

    listed = store.list()
    assert "good" in listed
    assert "bad" not in listed


def test_custom_scenario_persists_across_orchestrators(tmp_path) -> None:
    db = str(tmp_path / "db.sqlite")
    first = SimulationOrchestrator(db_path=db, patient_agent=PatientPersonaAgent())
    first.create_scenario(_raw(scenario_id="custom-chest"))
    # Simulate a fresh process: clear the in-memory registry so only the store
    # can bring the scenario back.
    remove_custom_scenario("custom-chest")

    second = SimulationOrchestrator(db_path=db, patient_agent=PatientPersonaAgent())
    assert "custom-chest" in second.scenario_store.list()
    assert get_scenario("custom-chest").title == "Custom scenario"
