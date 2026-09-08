from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from server.agents.patient_persona import PatientPersonaAgent, PatientState
from server.scenarios import ScenarioDefinition
from server.schemas.validation import PatientResponse

logger = logging.getLogger("alexa_clinical_sim")


class LLMPersonaAgent:
    """LLM-backed patient persona that respects scenario disclosure rules.

    Falls back to the deterministic PatientPersonaAgent when the LLM is
    unavailable, returns invalid output, or INFERENCE_PROVIDER is not 'llm'.
    The scenario registry — not the model — remains the authority over which
    facts may be disclosed.
    """

    def __init__(self) -> None:
        self.base_url = os.getenv("INFERENCE_BASE_URL", "")
        self.api_key = os.getenv("INFERENCE_API_KEY", "")
        self.model = os.getenv("INFERENCE_MODEL", "gpt-4o-mini")
        self.fallback = PatientPersonaAgent()
        self.timeout = float(os.getenv("INFERENCE_TIMEOUT", "15"))

    @property
    def available(self) -> bool:
        return bool(self.base_url and self.api_key)

    def respond(
        self,
        state: PatientState,
        scenario: ScenarioDefinition,
        practitioner_message: str,
    ) -> PatientResponse:
        if not self.available:
            return self.fallback.respond(state, scenario, practitioner_message)

        try:
            return self._llm_respond(state, scenario, practitioner_message)
        except Exception as exc:
            logger.warning("LLM persona failed, falling back to deterministic: %s", exc)
            return self.fallback.respond(state, scenario, practitioner_message)

    def _llm_respond(
        self,
        state: PatientState,
        scenario: ScenarioDefinition,
        practitioner_message: str,
    ) -> PatientResponse:
        state.turn_count += 1
        system_prompt = self._build_system_prompt(state, scenario)
        user_prompt = f"Practitioner says: {practitioner_message}"

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 300,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]

        parsed = self._parse_response(raw)

        # Enforce scenario constraints: only allow disclosure of facts whose
        # trigger terms appear in the practitioner message.
        text = practitioner_message.lower()
        allowed_facts: set[str] = set()
        for rule in scenario.disclosures:
            if any(term in text for term in rule.trigger_terms):
                allowed_facts.add(rule.fact_id)

        disclosed = set(parsed.get("disclosed_facts", []))
        # Drop any facts the model claims to have disclosed but the scenario
        # doesn't permit for this utterance. Keep previously disclosed facts.
        disclosed = (disclosed & allowed_facts) | state.disclosed_facts
        state.disclosed_facts = disclosed

        emotion = parsed.get("emotional_state", state.last_emotional_state)
        state.last_emotional_state = emotion

        safety_note = None
        if any(term in text for term in scenario.safety_terms):
            safety_note = "If this represented a real patient, follow local emergency protocols immediately."

        return PatientResponse(
            content=parsed.get("content", "I am not sure what to say."),
            emotional_state=emotion,
            disclosed_facts=sorted(disclosed),
            safety_note=safety_note,
            scenario_id=scenario.scenario_id,
            scenario_version=scenario.version,
        )

    def _build_system_prompt(self, state: PatientState, scenario: ScenarioDefinition) -> str:
        disclosure_lines = []
        for rule in scenario.disclosures:
            already = " (already disclosed)" if rule.fact_id in state.disclosed_facts else ""
            disclosure_lines.append(
                f"  - {rule.fact_id}: triggered by [{', '.join(rule.trigger_terms)}]{already}\n"
                f'    say: "{rule.response}" (emotion: {rule.emotional_state})'
            )

        return (
            f"You are a simulated patient in a clinical communication exercise.\n"
            f"Scenario: {scenario.title}\n"
            f"Opening: {scenario.opening}\n\n"
            f"Disclosure rules (only disclose a fact if the practitioner's question "
            f"contains a trigger term for it):\n"
            f"{chr(10).join(disclosure_lines)}\n\n"
            f"Facts already disclosed: {', '.join(sorted(state.disclosed_facts)) or 'none'}\n"
            f"Turn count: {state.turn_count}\n"
            f"Last emotional state: {state.last_emotional_state}\n\n"
            f"Respond as the patient in first person. Be brief (1-3 sentences).\n"
            f"Only disclose facts whose trigger terms appear in the practitioner's question.\n"
            f"If no rule matches, give a brief non-committal response.\n\n"
            f"Return JSON only:\n"
            f'{{"content": "...", "emotional_state": "...", "disclosed_facts": ["fact-id", ...]}}'
        )

    @staticmethod
    def _parse_response(raw: str) -> dict[str, Any]:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw
            raw = raw.rsplit("```", 1)[0]
        return json.loads(raw)
