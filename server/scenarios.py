from __future__ import annotations

import re
from functools import cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

# Scenarios and their versioned rubrics live as JSON in this directory so
# non-engineers can author and version them independently of code. Files are
# loaded in filename order; the numeric prefix controls listing order.
SCENARIOS_DIR = Path(__file__).resolve().parent / "scenarios_data"


@cache
def _term_pattern(term: str) -> re.Pattern[str]:
    """Compile a trigger term into a word-start prefix regex.

    Each whitespace-separated word must begin at a word boundary and the final
    word may be a prefix, so 'medication' matches 'medications' while 'eat' does
    not match inside 'breath'. Multi-word terms must be adjacent words.
    """
    words = term.split()
    return re.compile(r"\s+".join(rf"\b{re.escape(word)}" for word in words), re.IGNORECASE)


def matches_term(term: str, text: str) -> bool:
    """Return True if `term` matches `text` as a word-start prefix sequence."""
    return _term_pattern(term).search(text) is not None


class DisclosureRule(BaseModel):
    """A patient fact disclosed only when a trigger term matches the utterance."""

    model_config = ConfigDict(frozen=True)

    fact_id: str
    trigger_terms: tuple[str, ...]
    response: str
    emotional_state: str


class MetricDefinition(BaseModel):
    """One scored rubric dimension."""

    model_config = ConfigDict(frozen=True)

    metric_id: str
    name: str
    trigger_terms: tuple[str, ...]
    rationale: str
    max_score: int = Field(default=4, ge=1)
    coaching_hint: str | None = None


class ScenarioDefinition(BaseModel):
    """A complete scenario with its versioned disclosure rules and rubric."""

    model_config = ConfigDict(frozen=True)

    scenario_id: str
    version: str
    title: str
    opening: str
    goal: str = ""
    pitfalls: tuple[str, ...] = ()
    disclosures: tuple[DisclosureRule, ...]
    metrics: tuple[MetricDefinition, ...]
    safety_terms: tuple[str, ...]


def _load_scenarios() -> dict[str, ScenarioDefinition]:
    scenarios: dict[str, ScenarioDefinition] = {}
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        scenario = ScenarioDefinition.model_validate_json(path.read_text(encoding="utf-8"))
        if scenario.scenario_id in scenarios:
            raise ValueError(f"Duplicate scenario_id across files: {scenario.scenario_id}")
        scenarios[scenario.scenario_id] = scenario
    if not scenarios:
        raise ValueError(f"No scenario JSON files found in {SCENARIOS_DIR}")
    return scenarios


SCENARIOS: dict[str, ScenarioDefinition] = _load_scenarios()

# Named aliases kept for direct imports in tests and scripts.
CHEST_PAIN_BASIC = SCENARIOS["chest-pain-basic"]
ABDOMINAL_PAIN_BASIC = SCENARIOS["abdominal-pain-basic"]
DEPRESSION_SCREENING_BASIC = SCENARIOS["depression-screening-basic"]
MIGRAINE_BASIC = SCENARIOS["migraine-basic"]
BACK_PAIN_BASIC = SCENARIOS["back-pain-basic"]


def get_scenario(scenario_id: str) -> ScenarioDefinition:
    try:
        return SCENARIOS[scenario_id]
    except KeyError as exc:
        raise ValueError(f"Unknown scenario: {scenario_id}") from exc
