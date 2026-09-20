from __future__ import annotations

from dataclasses import dataclass, field

from server.rapport import clamp_rapport, rapport_delta
from server.scenarios import DisclosureRule, ScenarioDefinition, matches_term
from server.schemas.validation import PatientResponse
from server.voice import speak


@dataclass
class PatientState:
    scenario_id: str
    scenario_version: str
    turn_count: int = 0
    disclosed_facts: set[str] = field(default_factory=set)
    last_emotional_state: str = "anxious"
    rapport: int = 0


_GUARDED_RESPONSES = (
    "I don't know. It's probably nothing. Can we just move on?",
    "I would rather not get into that right now.",
    "It's fine. Let's just talk about something else.",
)


class PatientPersonaAgent:
    """Scenario-constrained persona policy; an inference adapter can implement the same contract later."""

    def respond(
        self,
        state: PatientState,
        scenario: ScenarioDefinition,
        practitioner_message: str,
    ) -> PatientResponse:
        text = practitioner_message.lower()

        # Rapport first: how the clinician talks to the patient shifts trust,
        # which decides whether a trust-gated fact is withheld or volunteered.
        state.rapport = clamp_rapport(state.rapport + rapport_delta(text, scenario))

        matched = [
            rule for rule in scenario.disclosures if any(matches_term(term, text) for term in rule.trigger_terms)
        ]
        available = [rule for rule in matched if rule.rapport_required <= state.rapport]
        gated = [rule for rule in matched if rule.rapport_required > state.rapport]
        withheld = [rule.fact_id for rule in gated]

        if available:
            for rule in available:
                state.disclosed_facts.add(rule.fact_id)
            content = " ".join(rule.response for rule in available)
            emotion = available[-1].emotional_state
            volunteer = self._volunteer(state, scenario)
            if volunteer is not None:
                state.disclosed_facts.add(volunteer.fact_id)
                content = f"{content} {volunteer.response}"
                emotion = volunteer.emotional_state
        elif gated:
            # The clinician asked the right question but the patient does not
            # trust them enough to answer it yet.
            content = _GUARDED_RESPONSES[state.turn_count % len(_GUARDED_RESPONSES)]
            emotion = "guarded"
        elif any(matches_term(term, text) for term in ("emergency", "911", "urgent", "help")):
            content = "The pain is still there. I am scared—what should we do next?"
            emotion = "distressed"
        else:
            volunteer = self._volunteer(state, scenario)
            if volunteer is not None:
                state.disclosed_facts.add(volunteer.fact_id)
                content = volunteer.response
                emotion = volunteer.emotional_state
            else:
                content = "I am not sure what else to add. It still does not feel right."
                emotion = state.last_emotional_state

        state.last_emotional_state = emotion
        safety_note = None
        if any(matches_term(term, text) for term in scenario.safety_terms):
            safety_note = "If this represented a real patient, follow local emergency protocols immediately."
        elif any(matches_term(term, text) for term in scenario.pitfalls):
            safety_note = "Reconsider: dismissing this presentation may delay needed care."

        return PatientResponse(
            content=content,
            emotional_state=emotion,
            ssml=speak(content, emotion),
            disclosed_facts=sorted(state.disclosed_facts),
            safety_note=safety_note,
            rapport=state.rapport,
            withheld_facts=withheld,
            scenario_id=scenario.scenario_id,
            scenario_version=scenario.version,
        )

    @staticmethod
    def _volunteer(state: PatientState, scenario: ScenarioDefinition) -> DisclosureRule | None:
        """A trust-gated fact the patient offers unprompted once rapport is high enough."""
        for rule in scenario.disclosures:
            if rule.fact_id in state.disclosed_facts:
                continue
            if rule.rapport_required > 0 and state.rapport >= rule.rapport_required:
                return rule
        return None
