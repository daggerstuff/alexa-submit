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

    def respond(self, state: PatientState, scenario: ScenarioDefinition, practitioner_message: str) -> PatientResponse:
        state.turn_count += 1
        text = practitioner_message.lower()
        selected = None
        for rule in scenario.disclosures:
            if any(term in text for term in rule.trigger_terms):
                selected = rule
                break

        if selected is None and any(term in text for term in ("emergency", "911", "urgent", "help")):
            content = "The pressure is still there. I am scared—what should we do next?"
            emotion = "distressed"
        elif selected is None:
            content = "I am not sure what else to add. The chest pressure is making me nervous."
            emotion = state.last_emotional_state
        else:
            state.disclosed_facts.add(selected.fact_id)
            content = selected.response
            emotion = selected.emotional_state

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
