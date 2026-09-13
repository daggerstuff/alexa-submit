from __future__ import annotations

from dataclasses import dataclass, field

from server.scenarios import ScenarioDefinition
from server.schemas.validation import PatientResponse


@dataclass
class PatientState:
    scenario_id: str
    scenario_version: str
    turn_count: int = 0
    disclosed_facts: set[str] = field(default_factory=set)
    last_emotional_state: str = "anxious"


class PatientPersonaAgent:
    """Scenario-constrained persona policy; an inference adapter can implement the same contract later."""

    def respond(
        self,
        state: PatientState,
        scenario: ScenarioDefinition,
        practitioner_message: str,
    ) -> PatientResponse:
        text = practitioner_message.lower()

        matched = [rule for rule in scenario.disclosures if any(term in text for term in rule.trigger_terms)]

        if not matched and any(term in text for term in ("emergency", "911", "urgent", "help")):
            content = "The pain is still there. I am scared—what should we do next?"
            emotion = "distressed"
        elif not matched:
            content = "I am not sure what else to add. It still does not feel right."
            emotion = state.last_emotional_state
        else:
            for rule in matched:
                state.disclosed_facts.add(rule.fact_id)
            content = " ".join(rule.response for rule in matched)
            emotion = matched[-1].emotional_state

        state.last_emotional_state = emotion
        safety_note = None
        if any(term in text for term in scenario.safety_terms):
            safety_note = "If this represented a real patient, follow local emergency protocols immediately."

        return PatientResponse(
            content=content,
            emotional_state=emotion,
            disclosed_facts=sorted(state.disclosed_facts),
            safety_note=safety_note,
            scenario_id=scenario.scenario_id,
            scenario_version=scenario.version,
        )
