# Alexa+ Clinical Simulation Node — Improved Concept and Execution

## Executive direction

The project should be positioned as a **scenario-based clinical communication simulator**, not as an Alexa chatbot or an automated clinical decision-maker. Its purpose is to let a learner practice structured history-taking and communication while receiving transparent, rubric-linked feedback.

The improved design separates five concerns:

| Concern | Responsibility | Current implementation |
|---|---|---|
| Transport | Convert Alexa/MCP requests into a validated simulation request | `/alexa` and `/mcp/simulate` |
| Session | Maintain lifecycle, transcript, idempotency, and scenario version | `SimulationOrchestrator` |
| Persona | Respond within scenario-defined disclosure and safety rules | `PatientPersonaAgent` |
| Evaluation | Score observable practitioner behaviors with evidence | `ClinicalEvaluatorAgent` |
| Scenario | Define patient facts, response triggers, safety terms, and rubric | `server/scenarios.py` |

This is a stronger boundary than placing all behavior in `main.py`, because a scenario can now be changed or versioned without rewriting the transport layer.

## Main improvements made

### Product concept

The original concept centered on “dynamic symptomatic responses.” The improved concept is more precise: the patient agent exposes information according to **disclosure rules**, maintains emotional continuity, and reports structured metadata. This prevents the simulated patient from becoming an unconstrained generator of clinical claims.

The evaluator no longer produces only a total score. Every metric has an identifier, a versioned rubric context, evidence excerpts from the practitioner transcript, a rationale, and a score. This makes feedback explainable and makes later educator review possible.

### Execution model

The improved lifecycle is:

1. **Start:** Create a session against a specific scenario and scenario version.
2. **Interact:** Append the practitioner turn, generate one patient response, and append the patient turn.
3. **Evaluate:** Apply the scenario’s rubric to the practitioner turns and return evidence-linked scores.
4. **End:** Return the final evaluation and lock the session against further messages.

Client event identifiers make message processing idempotent. If a network retry repeats the same event, the backend returns the original result rather than generating a second patient turn.

### Safety and operational boundaries

The system now returns an educational disclaimer on every simulation response, rejects unknown scenarios, prevents a session from switching scenarios midstream, and supports an optional `DEV_API_KEY` for local gateway protection. CORS is restricted to a local development origin rather than allowing every origin.

These are starter controls, not a production security program. A production deployment still needs authenticated Alexa request verification, encrypted durable storage, retention controls, redacted logs, rate limiting, access control, privacy review, and clinician governance.

## Recommended production architecture

For a serious implementation, replace the in-memory store with a protected session service. Keep the scenario registry immutable and versioned. Treat every interaction as an append-only event with a correlation ID. Run the patient and evaluator policies behind explicit interfaces so the deterministic implementation can be replaced by a constrained model adapter.

A production request path should look like this:

```text
Alexa device
    -> verified Alexa/MCP adapter
    -> request schema + authorization
    -> session/event store
    -> scenario policy
    -> patient response policy
    -> speech response adapter
    -> transcript/event store

end session
    -> evaluator policy
    -> evidence-linked rubric result
    -> learner feedback view
```

The key design principle is that **the model, if introduced, is a policy component rather than the system of record**. The system of record should remain the validated scenario, event log, transcript, and rubric version.

## Recommended roadmap

| Stage | Objective | Exit criteria |
|---|---|---|
| Local foundation | Validate interaction flow and contracts | Tests pass; no real patient data; deterministic scenario works |
| Educator pilot | Validate scenario realism and rubric usefulness | Clinician educators approve scenarios and feedback language |
| Controlled integration | Connect a verified Alexa/MCP adapter | Requests are authenticated, correlated, rate-limited, and observable |
| Model augmentation | Add optional constrained inference | Structured outputs validate; fallback policy works; outputs are auditable |
| Institutional deployment | Support learners and reporting | Privacy, retention, access, governance, and incident processes are approved |

## What should not be added casually

Do not add diagnostic recommendations, medication dosing, triage decisions, or claims that the system can assess a real patient. Do not allow a general-purpose model to invent undisclosed symptoms, alter the scenario without authorization, or silently change the evaluator rubric. Do not mix real patient data into the development tunnel or local transcript store.

## Files changed in this improvement pass

The core changes are in `server/scenarios.py`, `server/schemas/validation.py`, `server/agents/patient_persona.py`, `server/agents/clinical_evaluator.py`, `server/main.py`, and `tests/test_simulation.py`. The test suite now covers versioned scenarios, the new shared-next-step metric, event idempotency, and session locking after termination.
