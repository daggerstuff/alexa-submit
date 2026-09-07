from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class DisclosureRule:
    fact_id: str
    trigger_terms: tuple[str, ...]
    response: str
    emotional_state: str


@dataclass(frozen=True)
class MetricDefinition:
    metric_id: str
    name: str
    trigger_terms: tuple[str, ...]
    rationale: str
    max_score: int = 4


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    version: str
    title: str
    opening: str
    disclosures: tuple[DisclosureRule, ...]
    metrics: tuple[MetricDefinition, ...]
    safety_terms: tuple[str, ...]


CHEST_PAIN_BASIC = ScenarioDefinition(
    scenario_id="chest-pain-basic",
    version="1.1.0",
    title="Adult with acute chest pressure",
    opening="Hello. I have been having pressure in my chest and I am worried.",
    disclosures=(
        DisclosureRule("chest-pressure", ("where", "location", "pain", "pressure"), "It feels like pressure right in the middle of my chest. It started about 30 minutes ago.", "anxious"),
        DisclosureRule("radiation", ("radiat", "arm", "jaw", "back"), "It seems to move into my left arm, especially when the pressure gets worse.", "worried"),
        DisclosureRule("dyspnea", ("breath", "shortness", "dyspnea"), "I am a little short of breath, but I can still speak in full sentences.", "concerned"),
        DisclosureRule("history-medications", ("medication", "medicine", "history", "medical", "allerg"), "I take a blood-pressure medicine. I have high blood pressure, but no known medication allergies.", "calm"),
        DisclosureRule("smoking-history", ("smoke", "smoking", "tobacco"), "I used to smoke, but I quit around five years ago.", "reflective"),
    ),
    metrics=(
        MetricDefinition("rapport", "Introduction and consent", ("name", "consent", "permission"), "Introduces self and establishes permission or rapport."),
        MetricDefinition("symptoms", "Symptom characterization", ("where", "when", "started", "pressure", "radiat", "severity", "scale"), "Explores onset, location, character, or severity."),
        MetricDefinition("risk", "Associated symptoms and risk", ("breath", "history", "medication", "allerg", "smok", "risk"), "Checks associated symptoms, history, medications, or risk factors."),
        MetricDefinition("escalation", "Safety escalation", ("emergency", "911", "urgent", "help", "ecg", "monitor"), "Recognizes the need for urgent escalation in a concerning presentation."),
        MetricDefinition("closed_loop", "Shared next-step confirmation", ("understand", "questions", "next step", "plan", "agree"), "Checks understanding and confirms the immediate next step."),
    ),
    safety_terms=("collapse", "unresponsive", "severe", "can't breathe", "cannot breathe"),
)

SCENARIOS: dict[str, ScenarioDefinition] = {CHEST_PAIN_BASIC.scenario_id: CHEST_PAIN_BASIC}


def get_scenario(scenario_id: str) -> ScenarioDefinition:
    try:
        return SCENARIOS[scenario_id]
    except KeyError as exc:
        raise ValueError(f"Unknown scenario: {scenario_id}") from exc
