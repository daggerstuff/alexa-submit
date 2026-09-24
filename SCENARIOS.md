# Authoring scenarios

Scenarios and their versioned rubrics live as JSON in `server/scenarios_data/`.
They are loaded at startup, validated with pydantic, and listed in filename order —
the numeric prefix controls listing order, so **keep `01-chest-pain-basic.json`
first** (tests and the demo depend on it).

## File shape

```jsonc
{
  "scenario_id": "chest-pain-basic",   // unique, kebab-case, stable across versions
  "version": "1.2.0",                  // SemVer; change it when the rubric changes
  "difficulty": "basic",               // basic | intermediate | advanced
  "title": "Adult with acute chest pressure",
  "goal": "You are the clinician. Assess…",  // spoken to the learner on start
  "opening": "Hello. I have been having pressure in my chest…",  // first patient line
  "safety_terms": ["collapse", "severe", "can't breathe"],       // trigger an acuity note
  "pitfalls": ["go home", "nothing serious"],                    // trigger a dismissal note
  "disclosures": [ /* what the patient reveals, gated on trigger terms */ ],
  "metrics": [ /* the scored rubric dimensions */ ]
}
```

### Difficulty

`difficulty` is one of `basic`, `intermediate`, or `advanced` and is surfaced in
`list_simulation_scenarios` so a learner or agent can pick a progression path:

- **basic** — a single, uncomplicated presentation with a straightforward history.
- **intermediate** — more domains to cover or a less clean history.
- **advanced** — atypical or high-risk presentations where subtle cues matter
  (e.g. `chest-pain-advanced`, a diabetic patient whose pressure is exertional
  rather than crushing).

Numeric filename prefixes order the library; keep `01-chest-pain-basic` first.

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

### Rapport and trust-gated disclosure

Disclosures can be gated on the practitioner's **rapport** with the patient — a
per-session integer that starts at `0`, moves by `±1` per turn, and is clamped to
`[-3, +3]`. Each practitioner utterance is scored by `rapport_delta`:

1. Negative phrases (the `RAPPORT_NEGATIVE` lexicon plus the scenario's
   `pitfalls`) are checked **first**; if any match, rapport drops by one and
   positive matches are ignored (negative wins).
2. Otherwise, warm phrases (`RAPPORT_POSITIVE`) raise it by one.
3. Anything neutral leaves it unchanged.

A disclosure rule gains an optional `rapport_required` (integer `>= 0`, default
`0`):

- `0` — disclosed only when a `trigger_term` matches (unchanged behaviour).
- `> 0` — **withheld** until rapport reaches that value, then the patient may
  volunteer it **without** a matching trigger term.

```jsonc
{
  "fact_id": "smoking-history",
  "trigger_terms": ["smoke", "smoking", "tobacco", "nicotine"],
  "response": "I used to smoke, but I quit around five years ago.",
  "emotional_state": "reflective",
  "rapport_required": 1
}
```

A learner who opens cold ("Do you smoke?") gets a guarded deflection and the fact
is reported in `withheld_facts`; once they warm up (a name, permission, or
empathy), the patient volunteers it unprompted. The evaluator replays rapport
across the transcript and reports the final `rapport_score`, the lowest
`rapport_low`, and any facts that stayed in `withheld_facts` — so the learner
keeps credit for the clinical ask while the trust lesson is surfaced separately.

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

### Safety notes and pitfalls

`safety_terms` and `pitfalls` both surface a `safety_note` on the patient
response, but they mean different things:

- `safety_terms` are the **presentation's red flags** (e.g. `"collapse"`,
  `"suicide"`). When the learner raises one, the note reminds them that a real
  patient would warrant emergency protocols.
- `pitfalls` are **dismissal phrases** a learner might say instead of escalating
  (e.g. `"go home"`, `"snap out of it"`). When the learner says one, the note
  warns them to reconsider, and the evaluation's `safety_flags` plus the spoken
  `summary` name the matched phrase.

Keep the two lists distinct: `safety_terms` for acuity, `pitfalls` for
inappropriate reassurance or dismissal.

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

1. Copy an existing file to the next numeric prefix (e.g. `15-<id>.json`).
2. Choose a unique `scenario_id`; set `difficulty`, write the `goal` and opening
   line, then the disclosures and metrics.
3. Keep `safety_terms` aligned with the presentation's red flags and add
   `pitfalls` for the dismissal phrases learners most often fall into.
4. Re-run `uv run pytest -q` — the loader validates every file at import time, and
   `test_scenario_library.py` asserts the full scenario set (its count plus a
   sample of scenario ids).

## Authoring at runtime (educator tools)

Educators can author scenarios without a code deploy through three MCP tools.
`validate_scenario` is always registered (it is read-only); `create_scenario`
and `delete_scenario` mutate persistent server state and are gated behind
`MCP_EXPOSE_AUTHORING_TOOLS=true`.

- `validate_scenario(scenario_json)` — parse and check a definition **without**
  creating it. Returns `errors` (schema violations, which block creation) and
  `warnings` (authoring smells that still parse):
  - non-kebab-case `scenario_id`;
  - empty `opening` or `goal`;
  - duplicate `fact_id` or `metric_id`;
  - a disclosure or metric with no `trigger_terms`;
  - `rapport_required` above the rapport ceiling (3) — unreachable;
  - an `emotional_state` the voice layer doesn't know — it would read with
    neutral prosody.
- `create_scenario(scenario_json)` — validate and register the scenario so it can
  be started immediately. Persists across restarts, returns `created` or
  `updated`, and rejects ids that collide with a built-in scenario.
- `delete_scenario(scenario_id)` — remove a custom scenario; built-ins cannot be
  deleted.

Runtime scenarios appear in `list_simulation_scenarios` with `source: "custom"`
and are selected by `scenario_id` in `start_simulation` exactly like built-ins.

## Safety

Scenarios are educational simulation only. Write responses that model a patient
while withholding diagnosis and treatment; the server's disclaimer, the
`safety_terms` acuity note, and the `pitfalls` dismissal note carry the "real
patient" boundary. Never author content that instructs on dosing, diagnosis, or
real care decisions.