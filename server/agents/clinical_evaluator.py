from __future__ import annotations

from server.scenarios import ScenarioDefinition
from server.schemas.validation import EvaluationResult, MetricScore, Role, TranscriptTurn


class ClinicalEvaluatorAgent:
    """Transparent educational rubric evaluator, not a diagnostic or treatment engine."""

    def evaluate(self, transcript: list[TranscriptTurn], scenario: ScenarioDefinition) -> EvaluationResult:
        practitioner_turns = [t for t in transcript if t.role == Role.practitioner]
        metrics: list[MetricScore] = []
        for definition in scenario.metrics:
            evidence = [
                turn.content
                for turn in practitioner_turns
                if any(term in turn.content.lower() for term in definition.trigger_terms)
            ]
            met = bool(evidence)
            metrics.append(
                MetricScore(
                    metric_id=definition.metric_id,
                    metric=definition.name,
                    score=definition.max_score if met else 1,
                    max_score=definition.max_score,
                    evidence=evidence[:3],
                    rationale=definition.rationale if met else f"Not clearly demonstrated. {definition.rationale}",
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
        )
