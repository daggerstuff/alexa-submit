# Authoring scenarios

Scenarios and their versioned rubrics live as JSON in `server/scenarios_data/`.
They are loaded at startup, validated with pydantic, and listed in filename order —
the numeric prefix controls listing order, so **keep `01-chest-pain-basic.json`
first** (tests and the demo depend on it).

## File shape

```jsonc
{
  "scenario_id": "chest-pain-basic",   // unique, kebab-case, stable across versions
  "version": "1.1.0",                  // SemVer; change it when the rubric changes
  "title": "Adult with acute chest pressure",
  "opening": "Hello. I have been having pressure in my chest…",  // first patient line
  "safety_terms": ["collapse", "severe", "can't breathe"],       // trigger a safety note
  "disclosures": [ /* what the patient reveals, gated on trigger terms */ ],
  "metrics": [ /* the scored rubric dimensions */ ]
}
```

### Disclosure rule

A patient fact is disclosed only when one of its `trigger_terms` matches the
practitioner's utterance at a word boundary. Matching is case-insensitive and
allows a trailing suffix, so `"medication"` matches `"medications"` and
`"radiat"` matches `"radiating"`, but `"eat"` does **not** match inside
`"breath"` or `"treatment"`, and `"started"` does **not** match `"start"`.

```jsonc
{
  "fact_id": "dyspnea",
  "trigger_terms": ["breath", "shortness", "dyspnea"],
  "response": "I am a little short of breath, but I can still speak in full sentences.",
  "emotional_state": "concerned"
}
```

### Metric definition

```jsonc
{
  "metric_id": "symptoms",
  "name": "Symptom characterization",
  "trigger_terms": ["where", "when", "started", "pressure", "radiat", "severity", "scale"],
  "rationale": "Explores onset, location, character, or severity.",
  "max_score": 4,
  "coaching_hint": "Characterize the pain: 'Where exactly is the pressure, and when did it start?'"
}
```

- `trigger_terms` are the word-start signals the grader looks for across the
  practitioner's individual turns (multi-word terms must appear within a single
  turn).
- `max_score` defaults to 4.
- `coaching_hint` (optional) is the concrete next-step suggestion returned in the
  evaluation's `coaching` list when the metric is not fully demonstrated.

## Grading

Each metric is graded on a `1..max_score` band by counting **distinct** matched
trigger terms:

| distinct matches | score |
|---:|---:|
| 0 | 1 (not demonstrated) |
| 1 | 2 |
| 2 | 3 |
| 3+ | `max_score` |

The evaluator returns the matched practitioner turns as `evidence` and the matched
terms as `matched_terms`, so every score is self-explanatory.

## Adding a scenario

1. Copy an existing file to the next numeric prefix (e.g. `06-<id>.json`).
2. Choose a unique `scenario_id`, write the opening line, disclosures, and metrics.
3. Keep `safety_terms` aligned with the presentation's red flags so urgent language
   in the learner's turn surfaces a safety note.
4. Re-run `uv run pytest -q` — the loader validates every file at import time, and
   `test_mcp_protocol.py` asserts the full scenario set.

## Safety

Scenarios are educational simulation only. Write responses that model a patient
while withholding diagnosis and treatment; the server's disclaimer and the
`safety_terms` note carry the "real patient" boundary. Never author content that
instructs on dosing, diagnosis, or real care decisions.