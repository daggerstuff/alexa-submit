from __future__ import annotations

import re
from functools import cache
from pathlib import Path
from typing import Literal

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
    """A patient fact disclosed only when a trigger term matches the utterance.

    `rapport_required` gates a stigma- or trust-sensitive fact behind the
    session rapport score: the patient withholds it until rapport reaches that
    level, then may volunteer it unprompted. 0 (the default) behaves as before —
    triggered purely by terms, never withheld.
    """

    model_config = ConfigDict(frozen=True)

    fact_id: str
    trigger_terms: tuple[str, ...]
    response: str
    emotional_state: str
    rapport_required: int = Field(default=0, ge=0)


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
    opening_emotional_state: str = "anxious"
    goal: str = ""
    difficulty: Literal["basic", "intermediate", "advanced"] = "basic"
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


# Educator-authored scenarios registered at runtime (persisted via ScenarioStore
# and re-registered on startup). They overlay the built-in library without
# mutating it: built-in ids stay reserved, and custom ids are checked against
# them so a runtime scenario can never shadow a shipped one.
_custom: dict[str, ScenarioDefinition] = {}


def register_custom_scenario(scenario: ScenarioDefinition) -> bool:
    """Register a runtime scenario; returns True if it overwrote an existing custom id."""
    if scenario.scenario_id in SCENARIOS:
        raise ValueError(f"scenario_id '{scenario.scenario_id}' is reserved by a built-in scenario")
    existed = scenario.scenario_id in _custom
    _custom[scenario.scenario_id] = scenario
    return existed


def remove_custom_scenario(scenario_id: str) -> bool:
    """Remove a runtime scenario; returns False when the id was not a custom scenario."""
    return _custom.pop(scenario_id, None) is not None


def is_builtin_scenario(scenario_id: str) -> bool:
    return scenario_id in SCENARIOS


def custom_scenarios() -> dict[str, ScenarioDefinition]:
    return dict(_custom)


def all_scenarios() -> dict[str, ScenarioDefinition]:
    """Built-in scenarios first, then runtime (educator-authored) scenarios."""
    merged = dict(SCENARIOS)
    merged.update(_custom)
    return merged


def get_scenario(scenario_id: str) -> ScenarioDefinition:
    if scenario_id in _custom:
        return _custom[scenario_id]
    try:
        return SCENARIOS[scenario_id]
    except KeyError as exc:
        raise ValueError(f"Unknown scenario: {scenario_id}") from exc
