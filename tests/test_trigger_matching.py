from server.agents.clinical_evaluator import ClinicalEvaluatorAgent
from server.agents.patient_persona import PatientPersonaAgent, PatientState
from server.scenarios import get_scenario, matches_term
from server.schemas.validation import Role, TranscriptTurn


def test_matches_term_stemming() -> None:
    assert matches_term("medication", "what medications do you take")
    assert matches_term("radiat", "does it radiate to your arm")
    assert matches_term("breath", "breathing is hard")
    assert matches_term("eat", "I have not eaten since yesterday")


def test_matches_term_no_mid_word_substring() -> None:
    assert not matches_term("eat", "I am short of breath")
    assert not matches_term("eat", "this is a treatment plan")
    assert not matches_term("arm", "is there a pharmacy nearby")
    assert not matches_term("name", "could you rename that")
    assert not matches_term("hot", "I got a flu shot")


def test_matches_term_multi_word() -> None:
    assert matches_term("next step", "what is the next step")
    assert not matches_term("next step", "what happens next? step one is")


def test_persona_mid_word_substring_does_not_disclose() -> None:
    agent = PatientPersonaAgent()
    chest = get_scenario("chest-pain-basic")
    state = PatientState(scenario_id=chest.scenario_id, scenario_version=chest.version)
    # "arm" appears inside "warm"; radiation must not trigger.
    resp = agent.respond(state, chest, "I feel warm, like my body is overheating")
    assert "radiation" not in resp.disclosed_facts

    abdomen = get_scenario("abdominal-pain-basic")
    state2 = PatientState(scenario_id=abdomen.scenario_id, scenario_version=abdomen.version)
    # "eat" appears inside "breath" and "treatment"; appetite must not trigger.
    resp2 = agent.respond(state2, abdomen, "I am short of breath and worried about treatment")
    assert "appetite" not in resp2.disclosed_facts


def test_persona_prefix_stem_still_discloses() -> None:
    agent = PatientPersonaAgent()
    abdomen = get_scenario("abdominal-pain-basic")
    state = PatientState(scenario_id=abdomen.scenario_id, scenario_version=abdomen.version)
    resp = agent.respond(state, abdomen, "have you eaten anything today?")
    assert "appetite" in resp.disclosed_facts


def test_evaluator_word_start_matching() -> None:
    evaluator = ClinicalEvaluatorAgent()
    abdomen = get_scenario("abdominal-pain-basic")
    turns = [TranscriptTurn(role=Role.practitioner, content="are you short of breath?", timestamp="t1")]
    result = evaluator.evaluate(turns, abdomen)
    associated = next(m for m in result.metrics if m.metric_id == "associated")
    assert "eat" not in associated.matched_terms


def test_evaluator_stem_still_matches() -> None:
    evaluator = ClinicalEvaluatorAgent()
    chest = get_scenario("chest-pain-basic")
    turns = [TranscriptTurn(role=Role.practitioner, content="what medications do you take?", timestamp="t1")]
    result = evaluator.evaluate(turns, chest)
    risk = next(m for m in result.metrics if m.metric_id == "risk")
    assert "medication" in risk.matched_terms


def test_persona_dismissal_triggers_pitfall_note() -> None:
    agent = PatientPersonaAgent()
    chest = get_scenario("chest-pain-basic")
    state = PatientState(scenario_id=chest.scenario_id, scenario_version=chest.version)
    resp = agent.respond(state, chest, "I would tell you to go home and sleep it off")
    assert resp.safety_note == "Reconsider: dismissing this presentation may delay needed care."


def test_persona_normal_question_has_no_pitfall_note() -> None:
    agent = PatientPersonaAgent()
    chest = get_scenario("chest-pain-basic")
    state = PatientState(scenario_id=chest.scenario_id, scenario_version=chest.version)
    resp = agent.respond(state, chest, "Where is the pain, and are you short of breath?")
    assert resp.safety_note is None
