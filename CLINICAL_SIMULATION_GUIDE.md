# Alexa+ Clinical Simulation Node

## Presentation Script, Live-Agent Walkthrough, and Metric Extension Guide

> **Note:** This guide originally documented the four-layer concept. The current implementation separates five concerns and makes the scenario registry the policy center. See [`REDESIGN.md`](REDESIGN.md) and [`REDESIGNED_ARCHITECTURE_PRESENTATION.md`](REDESIGNED_ARCHITECTURE_PRESENTATION.md) for the current architecture. The metric-extension instructions in Part III have been updated to match the current data-driven model in `server/scenarios.py`.

> **Educational safety boundary:** This starter is a simulation scaffold. It is not a medical device, diagnostic service, triage system, or substitute for supervised clinical education. Do not use it with real patient data or for real-time clinical decision-making.

---

## Part I — Presentation Script

### Slide 1 — Title: Alexa+ Clinical Simulation Node

**Speaker script:**

“Today I will walk through the architecture and deployment sequence of an Alexa-enabled clinical interview simulation. The system allows a practitioner or learner to speak with a simulated patient through an Alexa-compatible interface. Behind that interface, a Python orchestration service maintains session state, routes each turn to a patient persona agent, and evaluates the practitioner’s performance against a transparent clinical rubric.

This is an educational simulation. The starter implementation deliberately uses deterministic logic, mock endpoints, and in-memory state so that the complete request path can be understood and tested locally before adding external model providers, durable storage, authentication, or a live Alexa integration.”

### Slide 2 — End-to-End Architecture

**Speaker script:**

“The architecture has four logical layers.

First is the **edge interface**: Alexa-enabled hardware such as an Echo device or Fire TV. In the starter repository, this layer is represented by a JSON passthrough contract rather than a live device connection.

Second is the **integration layer**. The intended role of this layer is to translate Alexa or Alexa+ MCP requests into the simulation request schema and to translate the backend response back into an Alexa-compatible response. The starter exposes both `/alexa` and `/mcp/simulate` for this purpose.

Third is the **backend orchestrator**. It is implemented with FastAPI in `server/main.py`. The orchestrator creates or retrieves a session, records transcript turns, invokes the patient persona agent, and invokes the clinical evaluator when requested.

Fourth is the **agent layer**. The patient persona agent generates the simulated patient’s next response. The evaluator agent reviews practitioner turns and produces metric-level scores, rationales, strengths, and improvements.”

### Slide 3 — Core Data Flow

**Speaker script:**

“A live interaction follows a simple stateful loop. A client sends a `start` request with a session identifier. The orchestrator creates a `Session` object and initializes a `PatientState` object for the selected scenario.

The practitioner then sends a `message` request. The orchestrator appends that utterance to the transcript, passes the utterance and patient state to the patient persona agent, appends the patient response to the transcript, and returns the response to the integration layer.

When the interaction is complete, the client sends either `evaluate` or `end`. The evaluator reads the practitioner turns from the transcript, applies its rubric, and returns an `EvaluationResult`. The session can then be deleted explicitly through the session deletion endpoint.”

### Slide 4 — Session State and Transcript

**Speaker script:**

“The starter keeps state in memory for clarity. Each session contains a session identifier, a scenario identifier, a patient state, and a transcript.

The patient state currently tracks the scenario, the turn count, and the facts already disclosed by the simulated patient. This means the persona can expose a fact during one turn and preserve that fact in later response metadata.

Each transcript turn has a role, content, and timestamp. Roles are constrained to practitioner, patient, and system. In a production implementation, this state should move to an appropriately protected and durable store, with a defined retention policy and strict controls against storing real protected health information.”

### Slide 5 — Patient Persona Agent

**Speaker script:**

“The patient persona agent is deterministic in the starter version. It lowercases the practitioner’s utterance, checks it against intent-like keyword groups, updates the set of disclosed facts, and returns a structured `PatientResponse`.

For example, a question containing terms such as ‘where’ or ‘pain’ produces a response about substernal chest pressure. A question containing ‘breath’ or ‘dyspnea’ produces a response about mild shortness of breath. Questions about medications or history disclose hypertension and medication-allergy information.

The agent also returns an emotional state and may return a safety note when the utterance contains severe-risk language such as collapse, unresponsiveness, or inability to breathe. This structured response gives the Alexa adapter enough information to speak the patient content while preserving metadata for logging or evaluation.”

### Slide 6 — Clinical Evaluator Agent

**Speaker script:**

“The evaluator agent is also intentionally transparent. It extracts practitioner turns from the transcript and, for each metric registered in the active scenario, collects the turns whose text matches that metric's trigger terms as evidence.

Each criterion produces a `MetricScore` with a stable `metric_id`, a human-readable metric name, score, maximum score, evidence excerpts, and a rationale. The overall score is the sum of metric scores, and the maximum score is calculated from the metrics registered in the scenario's rubric. For `chest-pain-basic` that is five metrics: introduction and consent, symptom characterization, associated symptoms and risk, safety escalation, and shared next-step confirmation.

This design is useful because a reviewer can explain exactly why a score was produced and see which practitioner turns supported it. A future model-assisted evaluator can be introduced behind the same schema, but its output should remain validated and its rubric version should be recorded.”

### Slide 7 — Deployment Sequence

**Speaker script:**

“The deployment sequence begins with local initialization. The `scripts/initialize.sh` script creates a Python virtual environment, installs the dependencies from `server/requirements.txt`, and copies `.env.example` to `.env` when needed.

Next, the developer starts the FastAPI service with Uvicorn. The service exposes `/health`, `/mcp/simulate`, and `/alexa`.

For local Alexa-console testing, the developer starts an HTTPS tunnel to port 8000. The public HTTPS URL is then placed in `alexa_config/skill.json` and configured as the skill endpoint. The interaction model in `alexa_config/interactionModels/en-US.json` provides a minimal invocation name and a free-form query slot for experimentation.

Finally, the developer runs the automated tests before connecting a device or console. In a production sequence, authentication, request verification, rate limiting, observability, durable state, and privacy review must be added before deployment.”

### Slide 8 — Demonstration and Closing

**Speaker script:**

“The demonstration uses three requests. First, a `start` request begins a session. Second, one or more `message` requests represent practitioner questions. Third, an `evaluate` request returns the rubric result.

The important architectural property is the separation of concerns: the edge adapter handles Alexa-specific transport, the orchestrator manages the session, the patient agent manages persona behavior, and the evaluator manages scoring. That separation makes it possible to replace the deterministic patient logic with a constrained inference provider without rewriting the Alexa integration or the evaluator contract.

The next engineering priorities are durable and protected session storage, authenticated edge requests, a versioned scenario and rubric registry, and clinical review of every scenario and scoring rule.”

---

## Part II — Live Patient Persona Walkthrough

### 1. The Alexa turn enters the backend

The intended production adapter receives an Alexa request and extracts a session identifier, scenario identifier, and recognized practitioner utterance. It sends those values to the backend contract:

```json
{
  "session_id": "demo-1",
  "action": "message",
  "scenario_id": "chest-pain-basic",
  "practitioner_message": "Where is the pain and are you short of breath?"
}
```

In the starter, either `POST /alexa` or `POST /mcp/simulate` accepts this request. Both routes call the same `SimulationOrchestrator.handle()` method.

### 2. The orchestrator retrieves session state

The orchestrator calls `get_or_create()`. If `demo-1` does not exist, it creates a `Session` containing a `PatientState` and an empty transcript. If it already exists, the existing patient state is reused. Reusing the same state is what allows the simulated patient to behave as one continuing person rather than as a new patient on every turn.

### 3. The practitioner utterance is recorded

Before generating a response, the orchestrator appends a practitioner transcript turn:

```python
session.transcript.append(
    self._turn(Role.practitioner, request.practitioner_message)
)
```

This is important because the evaluator later scores the practitioner’s behavior from the transcript rather than from a separate data path.

### 4. The patient agent updates its state

`PatientPersonaAgent.respond()` increments `state.turn_count`, lowercases the utterance, and evaluates the keyword groups in order. For the example above, the first matching branch is the location/pain branch because the utterance contains “Where” and “pain.” The agent adds `substernal chest pressure` to `state.disclosed_facts` and returns a structured response.

The current starter response is:

```json
{
  "content": "It feels like pressure right in the middle of my chest. It started about 30 minutes ago.",
  "emotional_state": "anxious",
  "disclosed_facts": ["chest-pressure"],
  "safety_note": null,
  "scenario_id": "chest-pain-basic",
  "scenario_version": "1.1.0"
}
```

The `disclosed_facts` list holds stable fact identifiers (such as `chest-pressure`) and is rebuilt from the state set and sorted before returning. Therefore, later turns can expose additional facts while retaining the facts already disclosed.

### 5. The patient response is added to the transcript

The orchestrator appends only the patient’s spoken content as a patient transcript turn:

```python
session.transcript.append(
    self._turn(Role.patient, patient.content)
)
```

The complete structured `PatientResponse` is still returned to the caller, so an adapter can speak `content` while using `emotional_state`, `disclosed_facts`, and `safety_note` for non-spoken metadata or safety handling.

### 6. Alexa speaks the response

The Alexa adapter should take the returned `patient.content`, convert it into the appropriate speech response, and preserve the same `session_id` for the next turn. The next practitioner utterance will therefore be evaluated against the same `PatientState` and transcript.

### 7. Current behavior versus a future inference-backed behavior

The starter is deterministic: keyword groups select predefined response branches. A future inference-backed patient agent should preserve the same outer contract while changing the internal response policy. It should receive the scenario definition, patient state, transcript context, and current practitioner utterance; generate structured output that validates against `PatientResponse`; and enforce scenario-specific disclosure rules so that the model cannot invent arbitrary clinical facts or reveal information prematurely.

---

## Part III — Adding a New Clinical Evaluation Metric

Metrics are now data, not code: each scenario in `server/scenarios.py` carries a tuple of `MetricDefinition` objects, and `ClinicalEvaluatorAgent` scores every registered metric uniformly. To add a metric, extend the scenario's `metrics` tuple — no evaluator or schema change is required.

For example, suppose the new metric is **Medication and allergy confirmation**. It should receive full credit when the practitioner asks about medication use or allergies.

### Minimal code change

Open `server/scenarios.py` and append a `MetricDefinition` to the `chest-pain-basic` scenario's `metrics` tuple:

```python
metrics=(
    MetricDefinition(
        "rapport",
        "Introduction and consent",
        ("name", "consent", "permission"),
        "Introduces self and establishes permission or rapport.",
    ),
    # ... existing metrics ...
    MetricDefinition(
        "medications",
        "Medication and allergy confirmation",
        ("medication", "medicine", "allerg"),
        "Explicitly checks current medications and medication allergies.",
    ),
),
```

`ClinicalEvaluatorAgent.evaluate()` already iterates `scenario.metrics`, gathers evidence turns, and scores each metric, so the new metric is picked up automatically. Because `max_score` is computed with `sum(item.max_score for item in metrics)`, the maximum score for `chest-pain-basic` increases from 20 to 24. The `list_simulation_scenarios` tool also reports the new `metric_id`, since it reads the same registry.

> **Note:** `medication` and `allerg` already appear in the existing `risk` metric's trigger terms, so this illustrative metric would overlap with it. In practice, choose trigger terms that target behavior not already covered, or split an existing metric rather than duplicating it.

### Better maintainability: the data-driven model

The current code already represents metrics as data. `MetricDefinition` lives in `server/scenarios.py` and carries `metric_id`, `name`, `trigger_terms`, `rationale`, and `max_score`:

```python
@dataclass(frozen=True)
class MetricDefinition:
    metric_id: str
    name: str
    trigger_terms: tuple[str, ...]
    rationale: str
    max_score: int = 4
```

The evaluator then matches trigger terms against practitioner turns and records evidence:

```python
for definition in scenario.metrics:
    evidence = [
        turn.content
        for turn in practitioner_turns
        if any(term in turn.content.lower() for term in definition.trigger_terms)
    ]
    metrics.append(
        MetricScore(
            metric_id=definition.metric_id,
            metric=definition.name,
            score=definition.max_score if evidence else 1,
            max_score=definition.max_score,
            evidence=evidence[:3],
            rationale=definition.rationale if evidence else f"Not clearly demonstrated. {definition.rationale}",
        )
    )
```

This keeps the rubric versionable and reviewable, and makes it possible to load scenario and rubric definitions from a configuration file later.

### Add a regression test

Extend `tests/test_simulation.py` with a test that proves the metric is present and can receive full credit:

```python
def test_medication_allergy_metric() -> None:
    session_id = "metric-session"
    client.post(
        "/mcp/simulate",
        json={"session_id": session_id, "action": "start"},
    )
    client.post(
        "/mcp/simulate",
        json={
            "session_id": session_id,
            "action": "message",
            "practitioner_message": "What medications do you take, and do you have any medication allergies?",
        },
    )

    response = client.post(
        "/mcp/simulate",
        json={"session_id": session_id, "action": "evaluate"},
    )

    assert response.status_code == 200
    evaluation = response.json()["evaluation"]
    assert evaluation["max_score"] == 24

    metric = next(
        item
        for item in evaluation["metrics"]
        if item["metric_id"] == "medications"
    )
    assert metric["score"] == 4
```

Run the tests with:

```bash
source .venv/bin/activate
pytest -q
```

### Metric design cautions

A keyword metric is appropriate for a deterministic starter, but it is not equivalent to clinical-quality assessment. Before using a metric in a serious educational program, define what counts as sufficient evidence, test paraphrases and false positives, separate “mentioned” from “adequately explored,” and have qualified clinical educators review the rubric. If a model is later used to score responses, retain the structured metric schema, rubric version, evidence span, and evaluator provenance so that scores can be audited.
