from __future__ import annotations

from server.rapport import clamp_rapport, rapport_delta
from server.scenarios import ScenarioDefinition, matches_term
from server.schemas.validation import CoachingSuggestion, EvaluationResult, MetricScore, Role, TranscriptTurn


class ClinicalEvaluatorAgent:
    """Transparent educational rubric evaluator, not a diagnostic or treatment engine.

    Each metric is graded on a 1..max_score band by counting the distinct trigger
    terms the practitioner covered: 0 matches -> 1 (not demonstrated), 1 -> 2,
    2 -> 3, 3+ -> max_score. Matched practitioner turns are returned as evidence.

    In addition to the rubric, the evaluator replays the session's rapport: each
    practitioner turn shifts the patient's trust by at most one step, and the
    result reports the final trust level, the lowest point reached, and the
    trust-gated facts the patient never disclosed.
    """

    def evaluate(
        self,
        transcript: list[TranscriptTurn],
        scenario: ScenarioDefinition,
        disclosed_facts: set[str] | None = None,
    ) -> EvaluationResult:
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
        safety_flags = [
            term
            for term in scenario.pitfalls
            if any(matches_term(term, turn.content.lower()) for turn in practitioner_turns)
        ]
        rapport_score, rapport_low = self._replay_rapport(scenario, practitioner_turns)
        disclosed = disclosed_facts or set()
        withheld_facts = sorted(
            rule.fact_id for rule in scenario.disclosures if rule.rapport_required > 0 and rule.fact_id not in disclosed
        )
        return EvaluationResult(
            rubric_version=scenario.version,
            overall_score=total,
            max_score=maximum,
            metrics=metrics,
            strengths=strengths,
            improvements=improvements,
            coaching=coaching,
            safety_flags=safety_flags,
            rapport_score=rapport_score,
            rapport_low=rapport_low,
            withheld_facts=withheld_facts,
            summary=self._summary(metrics, coaching, safety_flags, rapport_low, withheld_facts),
        )

    @staticmethod
    def _replay_rapport(scenario: ScenarioDefinition, practitioner_turns: list[TranscriptTurn]) -> tuple[int, int]:
        """Replay the session's rapport, returning (final, lowest) trust levels."""
        rapport = 0
        lowest = 0
        for turn in practitioner_turns:
            rapport = clamp_rapport(rapport + rapport_delta(turn.content, scenario))
            lowest = min(lowest, rapport)
        return rapport, lowest

    @staticmethod
    def _grade(distinct_matches: int, max_score: int) -> int:
        if distinct_matches == 0:
            return 1
        return min(max_score, distinct_matches + 1)

    @staticmethod
    def _summary(
        metrics: list[MetricScore],
        coaching: list[CoachingSuggestion],
        safety_flags: list[str],
        rapport_low: int,
        withheld_facts: list[str],
    ) -> str:
        """A spoken-friendly coaching takeaway for the learner."""
        strong = [item.metric for item in metrics if item.score == item.max_score]
        pieces: list[str] = []
        if safety_flags:
            pieces.append(f'Safety: avoid dismissing this presentation (e.g. "{safety_flags[0]}").')
        if strong:
            pieces.append(f"Strong: {', '.join(strong)}.")
        else:
            pieces.append("No dimension is fully demonstrated yet.")
        if coaching:
            pieces.append(f"Next: {coaching[0].suggestion}")
        if withheld_facts:
            pieces.append(
                f"Trust: {len(withheld_facts)} sensitive detail{'s' if len(withheld_facts) != 1 else ''} "
                "stayed hidden because rapport was too low; a warmer opener (name, permission, empathy) usually helps."
            )
        elif rapport_low < 0:
            pieces.append("Trust: your wording read as dismissive at points; warmer phrasing keeps the patient open.")
        return " ".join(pieces)

    @staticmethod
    def _rationale(base: str, distinct_matches: int, score: int, max_score: int) -> str:
        if distinct_matches == 0:
            return f"Not clearly demonstrated. {base}"
        if score < max_score:
            return f"Partially demonstrated ({distinct_matches} signal(s)). {base}"
        return base
