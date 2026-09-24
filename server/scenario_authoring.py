"""Validation and authoring feedback for educator-authored scenarios.

Scenarios ship as JSON files, but educators can also author them through the MCP
tools. This module turns a scenario definition into a structured verdict:
``errors`` block creation (schema violations), while ``warnings`` flag
authoring smells that still parse but would produce a weak or broken simulation.
"""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from server.rapport import RAPPORT_CEILING
from server.scenarios import ScenarioDefinition
from server.schemas.validation import ScenarioValidation
from server.voice import EMOTION_PROSODY

_KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_scenario(raw: str) -> ScenarioValidation:
    """Parse and validate an educator-authored scenario definition."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return ScenarioValidation(
            valid=False,
            errors=[f"Invalid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}"],
        )
    if not isinstance(data, dict):
        return ScenarioValidation(valid=False, errors=["Scenario must be a JSON object."])

    try:
        scenario = ScenarioDefinition.model_validate(data)
    except ValidationError as exc:
        return ScenarioValidation(valid=False, errors=_flatten_errors(exc))

    return ScenarioValidation(
        valid=True,
        warnings=_warnings(scenario),
        scenario_id=scenario.scenario_id,
        version=scenario.version,
        title=scenario.title,
        disclosure_count=len(scenario.disclosures),
        metric_count=len(scenario.metrics),
        max_score=sum(item.max_score for item in scenario.metrics),
    )


def _flatten_errors(exc: ValidationError) -> list[str]:
    errors: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"]) or "scenario"
        errors.append(f"{location}: {error['msg']}")
    return errors


def _warnings(scenario: ScenarioDefinition) -> list[str]:
    warnings: list[str] = []
    if not _KEBAB_RE.match(scenario.scenario_id):
        warnings.append(f"scenario_id '{scenario.scenario_id}' is not kebab-case (lowercase letters, digits, hyphens).")
    if not scenario.opening.strip():
        warnings.append("opening is empty; the patient will not greet the learner.")
    if not scenario.goal.strip():
        warnings.append("goal is empty; the learner will not be told their objective.")
    if scenario.opening_emotional_state.strip().lower() not in EMOTION_PROSODY:
        warnings.append(
            f"opening_emotional_state '{scenario.opening_emotional_state}' is unknown to the voice "
            f"layer; it will read with neutral prosody."
        )

    for duplicate in _duplicates([rule.fact_id for rule in scenario.disclosures]):
        warnings.append(f"duplicate fact_id '{duplicate}' across disclosures; only one will ever fire.")
    for duplicate in _duplicates([metric.metric_id for metric in scenario.metrics]):
        warnings.append(f"duplicate metric_id '{duplicate}' across metrics; grading will double-count it.")

    for rule in scenario.disclosures:
        if not rule.trigger_terms:
            warnings.append(f"disclosure '{rule.fact_id}' has no trigger_terms and can never be disclosed.")
        if rule.rapport_required > RAPPORT_CEILING:
            warnings.append(
                f"disclosure '{rule.fact_id}' rapport_required={rule.rapport_required} exceeds the "
                f"rapport ceiling ({RAPPORT_CEILING}); it can never be reached."
            )
        if rule.emotional_state.strip().lower() not in EMOTION_PROSODY:
            warnings.append(
                f"disclosure '{rule.fact_id}' emotional_state '{rule.emotional_state}' is unknown to the "
                f"voice layer; it will read with neutral prosody."
            )
    for metric in scenario.metrics:
        if not metric.trigger_terms:
            warnings.append(f"metric '{metric.metric_id}' has no trigger_terms and will always score minimum.")
    return warnings


def _duplicates(items: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for item in items:
        if item in seen and item not in duplicates:
            duplicates.append(item)
        seen.add(item)
    return duplicates
