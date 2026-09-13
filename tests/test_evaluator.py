from server.agents.clinical_evaluator import ClinicalEvaluatorAgent
from server.scenarios import CHEST_PAIN_BASIC
from server.schemas.validation import Role, TranscriptTurn


def _turn(content: str) -> TranscriptTurn:
    return TranscriptTurn(role=Role.practitioner, content=content, timestamp="2026-01-01T00:00:00+00:00")


def test_partial_credit_for_single_matched_term() -> None:
    evaluator = ClinicalEvaluatorAgent()
    result = evaluator.evaluate([_turn("Where is the pain?")], CHEST_PAIN_BASIC)
    symptoms = next(m for m in result.metrics if m.metric_id == "symptoms")
    assert symptoms.score == 2  # 1 distinct term -> 2/4, not the old binary 4/4
    assert symptoms.matched_terms == ["where"]


def test_no_match_scores_floor_of_one() -> None:
    evaluator = ClinicalEvaluatorAgent()
    result = evaluator.evaluate([_turn("Hello.")], CHEST_PAIN_BASIC)
    rapport = next(m for m in result.metrics if m.metric_id == "rapport")
    assert rapport.score == 1
    assert rapport.matched_terms == []


def test_full_coverage_scores_max() -> None:
    evaluator = ClinicalEvaluatorAgent()
    msg = "Where is the pain, when did it start, and how severe is it on a scale?"
    result = evaluator.evaluate([_turn(msg)], CHEST_PAIN_BASIC)
    symptoms = next(m for m in result.metrics if m.metric_id == "symptoms")
    # "where", "when", "scale" -> 3 distinct -> capped at max.
    assert symptoms.score == 4
    assert symptoms.matched_terms == ["where", "when", "scale"]
