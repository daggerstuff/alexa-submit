# Alexa+ Clinical Simulation Node

## Presentation Script: Redesigned Architecture, Security, and Evaluation Schema

> **Audience:** Engineering, clinical education, product, and security stakeholders  
> **Suggested length:** 12–15 minutes  
> **Positioning:** Educational clinical communication simulator, not a diagnostic or treatment system

---

## Slide 1 — From Alexa Prototype to Clinical Communication Simulator

**Speaker script:**

“Today I am presenting the redesigned Alexa+ Clinical Simulation Node. The central improvement is a clearer product definition. This is not an Alexa chatbot that happens to discuss symptoms. It is a scenario-based clinical communication simulator designed to help a learner practice history-taking, rapport, escalation language, and shared next-step communication.

The system is deliberately bounded. It does not diagnose patients, recommend treatment, perform triage, or make decisions about real clinical care. Its job is to create a repeatable educational interaction and return feedback that can be traced back to the learner’s observable behavior.

That change in product definition drives the rest of the architecture. We separate transport, session management, scenario policy, patient response policy, and evaluation policy so that each part can be tested and governed independently.”

**Key message:** The system’s value is **repeatable practice plus explainable feedback**, not automated clinical judgment.

---

## Slide 2 — Redesigned Architecture at a Glance

**Speaker script:**

“The redesigned system has five logical layers.

At the edge is the **transport layer**. Alexa hardware, an Alexa skill, or an MCP adapter sends requests into the backend. The starter exposes two development endpoints: `/alexa` and `/mcp/simulate`.

Next is the **session layer**. The `SimulationOrchestrator` creates or retrieves a session, enforces scenario consistency, records transcript turns, handles retries, and controls the session lifecycle.

The third layer is the **scenario policy**. In `server/scenarios.py`, a scenario defines its identifier, version, opening statement, disclosure rules, safety terms, and evaluation metrics. This is the source of truth for what the patient can reveal and how performance is scored.

The fourth layer is the **patient response policy**. The `PatientPersonaAgent` uses the active scenario and patient state to generate the next structured response.

The fifth layer is the **evaluation policy**. The `ClinicalEvaluatorAgent` examines practitioner turns, matches them against scenario metrics, and returns evidence-linked scores.”

| Layer | Main responsibility | Current implementation |
|---|---|---|
| Transport | Validate and receive Alexa/MCP requests | FastAPI endpoints |
| Session | Lifecycle, transcript, retries, scenario consistency | `SimulationOrchestrator` |
| Scenario | Facts, disclosure rules, safety policy, rubric | `ScenarioDefinition` |
| Patient policy | Stateful, constrained simulated responses | `PatientPersonaAgent` |
| Evaluation policy | Transparent scoring with evidence | `ClinicalEvaluatorAgent` |

---

## Slide 3 — Why Scenario Policy Is the Architectural Center

**Speaker script:**

“The most important redesign is moving scenario knowledge out of the HTTP handler and into an explicit scenario registry.

The current scenario is `chest-pain-basic`, version `1.1.0`. It defines the patient’s opening statement, disclosure rules such as chest pressure, radiation, dyspnea, medication history, and smoking history, as well as safety terms and five evaluation metrics.

Each disclosure rule contains four pieces of information: a stable fact identifier, trigger terms, the response text, and an emotional state. Each metric contains a stable metric identifier, a display name, trigger terms used as evidence signals, a rationale, and a maximum score.

This makes scenarios versionable and reviewable. A clinical educator can approve a scenario definition independently of the transport code. A later scenario can use different patient facts and a different rubric without requiring a rewrite of the orchestrator.”

**Transition:** “The scenario is therefore not just content. It is a policy boundary.”

---

## Slide 4 — Runtime Interaction Flow

**Speaker script:**

“Let us follow one live session.

First, the client sends a `start` action with a session ID and scenario ID. The orchestrator creates a session, selects the scenario, initializes `PatientState`, and records the opening interaction.

Second, the practitioner sends a `message` action. The orchestrator validates the request, records the practitioner’s turn, and passes the utterance, patient state, and scenario definition to the patient persona agent.

Third, the patient persona agent selects a scenario-approved disclosure rule, updates the patient state, and returns a structured `PatientResponse`. The response includes spoken content, emotional state, disclosed fact identifiers, an optional safety note, and the scenario version.

Fourth, the orchestrator records the patient response in the transcript and returns it to the transport adapter. The Alexa layer can speak the `content` field while retaining the structured metadata for the session.

Finally, the client requests `evaluate` or `end`. The evaluator analyzes the practitioner turns and returns the rubric result. The `end` action also locks the session so that additional messages are rejected.”

```text
start
  -> create session and patient state
message
  -> record practitioner turn
  -> apply scenario disclosure policy
  -> return structured patient response
  -> record patient turn
evaluate or end
  -> apply versioned rubric
  -> return evidence-linked feedback
```

---

## Slide 5 — Patient Persona: Constrained Dynamism

**Speaker script:**

“The patient agent is dynamic, but it is not unconstrained.

For each practitioner utterance, the agent lowercases the text and checks it against the disclosure rules of the active scenario. If the practitioner asks about the location or nature of the pain, the scenario allows the patient to disclose substernal chest pressure. If the practitioner asks about radiation, the patient may disclose left-arm discomfort. If the practitioner asks about shortness of breath, the patient may disclose mild dyspnea.

When a fact is disclosed, its stable identifier is added to `PatientState.disclosed_facts`. That prevents the interaction from losing continuity. The state also tracks turn count and the patient’s last emotional state.

If no disclosure rule matches, the patient gives a bounded fallback response instead of inventing a new symptom. If high-risk language appears, the response can include a safety note reminding the developer that a real patient would require local emergency protocols.

In a future model-backed implementation, the model should remain behind this same structured contract. It should receive scenario constraints and be required to return validated output. The scenario registry, not the model, should remain the authority over which facts may be disclosed.”

---

## Slide 6 — Security Improvement 1: Request and Session Boundaries

**Speaker script:**

“The redesign adds several security and reliability boundaries.

First, request schemas are explicit. Actions are limited to `start`, `message`, `evaluate`, and `end`. Session identifiers, scenario identifiers, practitioner messages, and client event identifiers have length constraints.

Second, sessions cannot silently change scenarios. Once a session is associated with a scenario, a later request that names another scenario receives a conflict response. This prevents a transcript from being evaluated against the wrong patient policy.

Third, ended sessions are immutable from the interaction perspective. A completed session can return its final evaluation, but additional practitioner messages are rejected.

Fourth, client event IDs provide idempotency. If a network retry repeats the same event ID, the orchestrator returns the prior response instead of generating an additional patient turn. This prevents duplicated turns caused by speech or network retries.”

**Important distinction:** These are application-level controls for the starter. They are not a replacement for production identity, authorization, encryption, or platform request verification.

---

## Slide 7 — Security Improvement 2: API, CORS, and Operational Controls

**Speaker script:**

“The starter also improves the edge boundary.

An optional `DEV_API_KEY` can protect the simulation and session-deletion endpoints. When configured, callers must provide the matching `X-API-Key` header. The health endpoint remains available for basic service checks.

CORS is no longer an unrestricted wildcard. The development configuration allows a local frontend origin and only the required HTTP methods and headers.

The service emits structured operational log lines containing session ID, action, and lifecycle status. This makes it easier to trace behavior during development without putting transcript content into the standard log message.

The implementation still requires additional production controls: verified Alexa request signatures or platform authentication, rate limiting, encrypted durable storage, privacy and retention policies, access control, redacted observability, secret management, and incident response. The local tunnel is strictly a development mechanism and must not carry real patient information.”

| Control | Starter behavior | Production requirement |
|---|---|---|
| API protection | Optional development API key | Strong identity and authorization |
| CORS | Local development origin | Explicit trusted origins |
| Retry handling | Client event idempotency | Durable idempotency store |
| Session state | In-memory | Encrypted durable storage |
| Logs | Correlation-oriented metadata | Redaction, retention, access controls |
| Alexa boundary | Mock passthrough | Verified platform requests |

---

## Slide 8 — Evaluation Schema: From Total Score to Explainable Feedback

**Speaker script:**

“The evaluator has also been redesigned. The old model was essentially a list of names and scores. The new model preserves the structure needed for explanation and auditability.

At the scenario level, each metric has a stable `metric_id`, a display name, evidence trigger terms, a rationale, and a maximum score.

At runtime, each `MetricScore` contains the metric ID, human-readable metric name, score, maximum score, evidence excerpts, and rationale. The evaluator also returns the rubric version, overall score, maximum score, strengths, improvements, and an educational disclaimer.

The evidence field is important. It identifies the practitioner utterances that triggered the metric. This lets a learner see not only that a metric was scored, but which part of the transcript supported that score.

The current scoring is intentionally simple: a demonstrated metric receives the maximum score of four, while a missing metric receives a low partial score of one. That is suitable for a transparent starter, but educator review is required before treating the rubric as a validated assessment instrument.”

---

## Slide 9 — Current Evaluation Metrics

**Speaker script:**

“The current chest-pain scenario uses five metrics.

The first is **Introduction and consent**, which looks for evidence that the practitioner establishes rapport and permission.

The second is **Symptom characterization**, which looks for questions about onset, location, character, radiation, or severity.

The third is **Associated symptoms and risk**, which covers breathing symptoms, history, medication, allergies, smoking, and other risk signals.

The fourth is **Safety escalation**, which looks for language indicating urgent escalation or monitoring.

The fifth is **Shared next-step confirmation**, which checks whether the practitioner confirms understanding and the immediate plan.

The rubric is versioned with the scenario. The current version is `1.1.0`, and the maximum score is calculated from the active metric definitions rather than hard-coded. This means a new metric can be added without changing the response schema.”

| Metric ID | Metric | Purpose |
|---|---|---|
| `rapport` | Introduction and consent | Establish rapport and permission |
| `symptoms` | Symptom characterization | Explore the presenting concern |
| `risk` | Associated symptoms and risk | Identify relevant context |
| `escalation` | Safety escalation | Recognize urgency in the scenario |
| `closed_loop` | Shared next-step confirmation | Confirm understanding and plan |

---

## Slide 10 — Evaluation Response Example

**Speaker script:**

“Here is the shape of the evaluation response. The response identifies the session, scenario, and scenario version. It includes the full transcript and a structured evaluation.

The evaluation identifies the rubric version, overall score, maximum score, and an array of metric-level results. Each metric has a stable ID, score, evidence, and rationale. Strengths and improvements are derived from the metric results.

This structure supports several user experiences: spoken feedback at the end of a session, a learner dashboard, educator review, or later analytics. It also makes it possible to compare results across rubric versions without pretending that a score from one rubric is directly equivalent to a score from another.”

Example metric result:

```json
{
  "metric_id": "symptoms",
  "metric": "Symptom characterization",
  "score": 4,
  "max_score": 4,
  "evidence": [
    "Where is the pain, when did it start, and does it radiate?"
  ],
  "rationale": "Explores onset, location, character, or severity."
}
```

---

## Slide 11 — What the Redesign Enables

**Speaker script:**

“This architecture creates a clear path for responsible growth.

New scenarios can be added through the scenario registry. New metrics can be introduced without changing the transport contract. The deterministic persona can later be replaced or augmented by a constrained inference provider. The evaluator can evolve from keyword evidence to a hybrid system that combines deterministic checks, structured extraction, and educator-reviewed model assistance.

Because scenario versions and rubric versions are preserved, the system can remain reproducible. Because transcript evidence is returned with scores, feedback can remain explainable. Because sessions have explicit lifecycle and retry controls, the runtime is more predictable.

The main principle is that the model, if added, should be a policy component—not the system of record. The source of truth should remain the validated scenario, event history, transcript, and versioned rubric.”

---

## Slide 12 — Closing and Responsible Deployment Sequence

**Speaker script:**

“To close, the improved deployment sequence is deliberately staged.

First, run the deterministic local implementation and validate the request, session, patient, and evaluator contracts. Second, have qualified clinical educators review the scenarios, disclosure behavior, feedback language, and rubric definitions. Third, add an authenticated Alexa or MCP adapter with verified requests, stable event IDs, and rate limiting. Fourth, replace in-memory state with protected durable storage and establish retention and access policies. Fifth, only then consider optional model augmentation, with strict structured-output validation and deterministic fallback behavior.

The system is successful when it helps learners practice communication in a controlled and explainable way. It is not successful if it creates the appearance of clinical authority without governance.

The redesigned node therefore combines a conversational interface with explicit scenario policy, operational safeguards, and evidence-linked evaluation. That is the foundation required for a useful and responsible clinical simulation product.”

---

## Presenter Reference: Core Files

| File | Presentation relevance |
|---|---|
| `server/main.py` | Session lifecycle, API endpoints, idempotency, API key boundary, logging |
| `server/scenarios.py` | Scenario version, disclosure rules, safety terms, evaluation metrics |
| `server/agents/patient_persona.py` | Stateful constrained patient responses |
| `server/agents/clinical_evaluator.py` | Evidence-linked rubric scoring |
| `server/schemas/validation.py` | Validated request, response, transcript, and evaluation contracts |
| `tests/test_simulation.py` | Regression coverage for versioning, idempotency, metrics, and session locking |

## Closing Safety Statement

> This system is an educational simulation scaffold. It must not be used with real patient information or for diagnosis, treatment, triage, or clinical decision-making without a separate program of security, privacy, clinical governance, validation, and regulatory review.
