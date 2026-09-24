from __future__ import annotations

from server.agents.clinical_evaluator import ClinicalEvaluatorAgent
from server.agents.patient_persona import PatientPersonaAgent, PatientState
from server.main import SimulationOrchestrator
from server.rapport import clamp_rapport, rapport_delta
from server.scenarios import CHEST_PAIN_BASIC, get_scenario
from server.schemas.validation import Role, SimulationAction, SimulationRequest, TranscriptTurn


def _state() -> PatientState:
    return PatientState(scenario_id="chest-pain-basic", scenario_version=CHEST_PAIN_BASIC.version)


def _turn(content: str) -> TranscriptTurn:
    return TranscriptTurn(role=Role.practitioner, content=content, timestamp="2026-01-01T00:00:00+00:00")


def test_rapport_delta_warm_cold_and_neutral() -> None:
    assert rapport_delta("I'm sorry this must be scary", CHEST_PAIN_BASIC) == 1
    assert rapport_delta("Calm down, you're fine", CHEST_PAIN_BASIC) == -1
    assert rapport_delta("Where is the pain?", CHEST_PAIN_BASIC) == 0
    # Dismissive language outweighs warmth within a single utterance.
    assert rapport_delta("I'm sorry, but hurry up", CHEST_PAIN_BASIC) == -1


def test_clamp_rapport_bounds() -> None:
    assert clamp_rapport(5) == 3
    assert clamp_rapport(-5) == -3


def test_withholds_trust_gated_fact_when_rapport_low() -> None:
    agent = PatientPersonaAgent()
    state = _state()
    resp = agent.respond(state, CHEST_PAIN_BASIC, "Do you smoke?")
    assert resp.withheld_facts == ["smoking-history"]
    assert "smoking-history" not in resp.disclosed_facts
    assert resp.emotional_state == "guarded"


def test_volunteers_gated_fact_unprompted_when_rapport_high() -> None:
    agent = PatientPersonaAgent()
    state = _state()
    resp = agent.respond(state, CHEST_PAIN_BASIC, "I'm sorry this must be scary. Take your time.")
    assert state.rapport == 1
    assert "smoking-history" in resp.disclosed_facts
    assert "smoke" in resp.content.lower()


def test_cold_then_warm_recovers_withheld_fact() -> None:
    agent = PatientPersonaAgent()
    state = _state()
    cold = agent.respond(state, CHEST_PAIN_BASIC, "Do you smoke?")
    assert "smoking-history" not in cold.disclosed_facts
    warm = agent.respond(state, CHEST_PAIN_BASIC, "I'm sorry, this must be scary.")
    assert state.rapport == 1
    assert "smoking-history" in warm.disclosed_facts


def test_evaluator_replays_rapport_and_reports_withheld() -> None:
    evaluator = ClinicalEvaluatorAgent()
    result = evaluator.evaluate(
        [_turn("Do you smoke?"), _turn("Hurry up and answer.")],
        CHEST_PAIN_BASIC,
    )
    assert result.rapport_score == -1
    assert result.rapport_low == -1
    assert "smoking-history" in result.withheld_facts


def test_evaluator_respects_disclosed_facts() -> None:
    evaluator = ClinicalEvaluatorAgent()
    result = evaluator.evaluate(
        [_turn("I'm sorry this must be scary. Take your time.")],
        CHEST_PAIN_BASIC,
        disclosed_facts={"smoking-history"},
    )
    assert result.rapport_score == 1
    assert result.rapport_low == 0
    assert result.withheld_facts == []


def test_rapport_survives_a_full_session() -> None:
    orchestrator = SimulationOrchestrator(patient_agent=PatientPersonaAgent())
    session_id = "rapport-session"
    orchestrator.handle(SimulationRequest(session_id=session_id, action=SimulationAction.start))
    cold = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.message,
            client_event_id="r1",
            practitioner_message="Do you smoke?",
        )
    )
    assert "smoking-history" in cold.patient.withheld_facts
    warm = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            action=SimulationAction.message,
            client_event_id="r2",
            practitioner_message="I'm sorry, this must be scary.",
        )
    )
    assert "smoking-history" in warm.patient.disclosed_facts


def test_evaluator_reports_withheld_only_when_probed() -> None:
    evaluator = ClinicalEvaluatorAgent()
    # Never asked about smoking -> not "withheld", just not covered.
    unprobed = evaluator.evaluate([_turn("Where is the pain?")], CHEST_PAIN_BASIC)
    assert unprobed.withheld_facts == []
    # Asked coldly -> rapport kept it hidden, so it is withheld.
    probed = evaluator.evaluate([_turn("Do you smoke?")], CHEST_PAIN_BASIC)
    assert "smoking-history" in probed.withheld_facts


def test_panic_attack_scenario_rapport_gate() -> None:
    scenario = get_scenario("panic-attack-basic")
    agent = PatientPersonaAgent()
    state = PatientState(scenario_id=scenario.scenario_id, scenario_version=scenario.version)
    cold = agent.respond(state, scenario, "Have you had any energy drinks?")
    assert "energy-drinks" in cold.withheld_facts
    assert cold.emotional_state == "guarded"
    warm = agent.respond(state, scenario, "I'm sorry, that sounds terrifying. Take your time.")
    assert "energy-drinks" in warm.disclosed_facts


def test_teen_vaping_scenario_rapport_gate() -> None:
    scenario = get_scenario("teen-vaping-basic")
    agent = PatientPersonaAgent()
    state = PatientState(scenario_id=scenario.scenario_id, scenario_version=scenario.version)
    cold = agent.respond(state, scenario, "Have you been vaping?")
    assert "vaping" in cold.withheld_facts
    assert cold.emotional_state == "guarded"
    warm = agent.respond(
        state,
        scenario,
        "I'm sorry this is awkward. This stays between us, and I'm not here to judge. Take your time.",
    )
    assert "vaping" in warm.disclosed_facts
