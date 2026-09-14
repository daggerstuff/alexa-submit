from __future__ import annotations

from server.scenarios import ScenarioDefinition, matches_term
from server.schemas.validation import CoachingSuggestion, EvaluationResult, MetricScore, Role, TranscriptTurn


class ClinicalEvaluatorAgent:
    """Transparent educational rubric evaluator, not a diagnostic or treatment engine.

    Each metric is graded on a 1..max_score band by counting the distinct trigger
    terms the practitioner covered: 0 matches -> 1 (not demonstrated), 1 -> 2,
    2 -> 3, 3+ -> max_score. Matched practitioner turns are returned as evidence.
    """

    def evaluate(self, transcript: list[TranscriptTurn], scenario: ScenarioDefinition) -> EvaluationResult:
        practitioner_turns = [t for t in transcript if t.role == Role.practitioner]
        metrics: list[MetricScore] = []
        coaching: list[CoachingSuggestion] = []
        for definition in scenario.metrics:
            matched_terms = [
                term
                for term in definition.trigger_terms
                if any(matches_term(term, turn.content.lower()) for turn in practitioner_turns)
            ]
            evidence = [
                turn.content
                for turn in practitioner_turns
                if any(matches_term(term, turn.content.lower()) for term in definition.trigger_terms)
            ]
            score = self._grade(len(matched_terms), definition.max_score)
            metrics.append(
                MetricScore(
                    metric_id=definition.metric_id,
                    metric=definition.name,
                    score=score,
                    max_score=definition.max_score,
                    evidence=evidence[:3],
                    matched_terms=matched_terms,
                    rationale=self._rationale(definition.rationale, len(matched_terms), score, definition.max_score),
                )
            )
            if score < definition.max_score and definition.coaching_hint:
                coaching.append(
                    CoachingSuggestion(
                        metric_id=definition.metric_id,
                        metric=definition.name,
                        suggestion=definition.coaching_hint,
                    )
                )

        total = sum(item.score for item in metrics)
        maximum = sum(item.max_score for item in metrics)
        strengths = [item.metric for item in metrics if item.score == item.max_score]
        improvements = [item.metric for item in metrics if item.score < item.max_score]
        return EvaluationResult(
            rubric_version=scenario.version,
            overall_score=total,
            max_score=maximum,
            metrics=metrics,
            strengths=strengths,
            improvements=improvements,
            coaching=coaching,
            summary=self._summary(metrics, coaching),
        )

    @staticmethod
    def _grade(distinct_matches: int, max_score: int) -> int:
        if distinct_matches == 0:
            return 1
        return min(max_score, distinct_matches + 1)

    @staticmethod
    def _summary(metrics: list[MetricScore], coaching: list[CoachingSuggestion]) -> str:
        """A spoken-friendly coaching takeaway for the learner."""
        strong = [item.metric for item in metrics if item.score == item.max_score]
        pieces: list[str] = []
        if strong:
            pieces.append(f"Strong: {', '.join(strong)}.")
        else:
            pieces.append("No dimension is fully demonstrated yet.")
        if coaching:
            pieces.append(f"Next: {coaching[0].suggestion}")
        return " ".join(pieces)

    @staticmethod
    def _rationale(base: str, distinct_matches: int, score: int, max_score: int) -> str:
        if distinct_matches == 0:
            return f"Not clearly demonstrated. {base}"
        if score < max_score:
            return f"Partially demonstrated ({distinct_matches} signal(s)). {base}"
        return base
