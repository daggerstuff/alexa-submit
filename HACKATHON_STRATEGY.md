# Amazon AppDev 2026 Hackathon Alignment Strategy

## Recommended submission concept

The project should be submitted as **Clinical Conversation Coach for Alexa+**. The product is a self-hosted MCP server that lets an Alexa+ agent orchestrate an educational clinical communication simulation: discover scenarios, start a session, conduct a practitioner-patient conversation, and request evidence-linked feedback.

This is a stronger hackathon concept than “Alexa clinical simulation node” because it makes the Alexa+ integration the product surface while preserving the clinical education differentiator. The experience is not a generic symptom question-and-answer bot. It is a stateful, scenario-constrained workflow with a beginning, an interaction loop, and a measurable outcome.

The official rules require the Alexa+ primary track to use either a working Agent Skill or a self-hosted MCP server implementing MCP version 2025-11-25 or later over Streamable HTTP. The rules also provide an alternate simulated Alexa+ path, but the working MCP path is the stronger fit for this project because it demonstrates the required technology directly at runtime [1].

## Current alignment status

| Hackathon expectation                  | Current status                                                                                                                                                                                                              | Action                                                                         |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Alexa+ primary track                   | Strong conceptual fit                                                                                                                                                                                                       | Submit under Alexa+                                                            |
| Self-hosted MCP server                 | Implemented in `server/mcp_server.py`                                                                                                                                                                                       | Demonstrate `/mcp` over Streamable HTTP                                        |
| MCP version target                     | Pinned: `mcp==2.2.0`, protocol `2025-11-25` (Python 3.13)                                                                                                                                                                   | Documented in `server/requirements.txt` and `ALEXA_PLUS_MCP_PYTHON_RUNBOOK.md` |
| Public GitHub repository               | Repository code exists locally                                                                                                                                                                                              | Create a public GitHub repository with `LICENSE` and setup instructions        |
| Working demo video under three minutes | Recorded (`demo.mp4`, LLM persona, 8/20) + rendered re-angle (`demo-v2.mp4`, deterministic, 2:48, 11/20)                                                                  | Publish one on YouTube/Vimeo before submission                                                                  |
| Product feedback                       | Prepared in `PRODUCT_FEEDBACK.md`                                                                                                                                                                                           | Submit with friction log for up to 10% bonus                                   |
| AWS Builder mini-challenge             | **Deployed and verified.** MCP server live at `https://9jj4zdyhu2.us-east-2.awsapprunner.com/mcp` (App Runner + ECR, us-east-2). Full 8-step MCP demo flow passes against the live URL. Endpoint hardened with bearer/API-key auth + rate limiting; LLM patient persona runs on Featherless (`Qwen/Qwen2.5-14B-Instruct`). | Claim with the live URL and this row as evidence                               |
| Open Source mini-challenge             | Not yet claimed                                                                                                                                                                                                             | Claim only after a qualifying contribution during the hackathon window         |

## Architecture for the submission

```text
Alexa+ / MCP client
        |
        | Streamable HTTP, JSON-RPC, /mcp
        v
Clinical Conversation Coach MCP server
        |
        +--> list_simulation_scenarios
        +--> start_simulation
        +--> send_practitioner_turn
        +--> evaluate_simulation
        +--> end_simulation
        |
        v
Scenario registry + session orchestrator
        |
        +--> constrained patient persona
        +--> transcript and event state
        +--> versioned evidence-linked evaluator
```

The MCP tools are intentionally task-oriented. The client does not need to know internal FastAPI routes or manipulate transcript state directly. It asks the server to perform meaningful operations in the learner workflow.

## Recommended three-minute demo

Lead with the learner, not the protocol. The judges weight design and potential
impact as heavily as technical implementation, so the conversation and the
coaching must appear early; the MCP proof is a short, confirmable beat near the
end.

| Time      | Demo beat               | What judges should see |
| --------- | ---------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| 0:00–0:20 | Learner problem         | "Clinical learners need safe, repeatable practice of difficult conversations." One line, then cut to the product.        |
| 0:20–0:45 | Onboarding + goal       | The agent starts `chest-pain-basic` and speaks the scenario's learner-facing `goal` before the patient's opening line.  |
| 0:45–1:30 | Live conversation       | Two or three practitioner turns; the patient discloses progressively and preserves state across turns.                  |
| 1:30–2:00 | Evidence-linked coaching| `evaluate_simulation` returns the score plus the spoken `summary` ("you covered where and when; next, confirm escalation"), with matched terms as evidence. |
| 2:00–2:25 | Safety boundary         | The learner says "go home and rest"; the response carries the dismissal `safety_note`, and the evaluation names it in `safety_flags`. |
| 2:25–2:45 | MCP proof (compressed)  | One glance at the `/mcp` endpoint, the five-tool list, and the typed `structuredContent` — enough to satisfy the MCP requirement without dwelling. |
| 2:45–3:00 | Impact + feedback       | Target users, the difficulty progression (`basic` → `advanced`), and one concrete product-feedback point for the Alexa+/MCP experience. |

The code repository carries the implementation details; the video must prove the
product works on Alexa+ and that the required MCP technology is actually used [1].
Keep the voice interaction audible and the patient turns short enough to hear.

## Judging strategy

The official judging criteria are equally weighted across tech implementation, design, potential impact, and quality of idea [1]. The project should therefore aim for more than protocol compliance.

**Tech implementation** is addressed by exposing a real MCP server over Streamable HTTP, using the official Python MCP SDK, and providing typed, scenario-aware tools. The repository should include a reproducible setup command and a smoke test.

**Design** is addressed by keeping the tool surface small and meaningful. The learner should not need to understand internal session mechanics. The agent should guide the conversation, keep spoken responses concise, and reserve detailed evaluation for the end of the simulation.

**Potential impact** is addressed by focusing on clinical learners, simulation programs, faculty coaches, and communication-skills educators. The product already ships a seven-scenario library across `basic`/`advanced` difficulty and can grow to educator-authored rubrics, cohort reporting, and accessibility-oriented voice practice without changing the core MCP contract.

**Quality of idea** is addressed by combining a stateful cross-turn interaction, scenario-constrained patient behavior, evidence-linked evaluation, and safe educational boundaries. This goes beyond a single-turn health-information bot or a basic MCP wrapper.

## Security and trust positioning

The product must clearly state that it is an educational simulator and must not be used for diagnosis, treatment, or real-patient triage. The demo should use synthetic scenarios only.

The MCP transport should be bound to localhost during development, validate origins, and use authentication before any hosted demonstration. The official Streamable HTTP specification warns about DNS rebinding, recommends validating `Origin`, recommends binding local servers to `127.0.0.1`, and recommends authentication [2].

The current implementation includes scenario locking, session-ending controls, idempotent client event IDs, optional `MCP_API_KEY` authentication on the MCP endpoint, per-client rate limiting, restricted local CORS, request logging, and explicit disclaimers. A public hosted demo should still add HTTPS, an authenticated reverse proxy, and secret management; the AWS App Runner deployment enables rate limiting by default and injects `MCP_API_KEY` when set.

## Product feedback to prepare

The submission should include specific feedback rather than generic praise. The most useful feedback topics are:

| Area                 | Example feedback to document                                               |
| -------------------- | -------------------------------------------------------------------------- |
| MCP setup            | Whether the Streamable HTTP setup was easy to understand and test          |
| Alexa+ workflow      | Whether tool descriptions led the agent to choose the correct sequence     |
| Session state        | Whether preserving context across tool calls felt reliable                 |
| Developer experience | Errors, missing examples, or debugging friction encountered while building |
| Voice UX             | Whether the patient responses were concise enough for spoken interaction   |
| Evaluation output    | Whether structured evidence and rubric versions were easy to consume       |

The rules explicitly request what tools were used, what worked, what needs improvement, whether the entrant would build with them again, and optionally feature requests and friction logs. Friction log entries can provide a judging bonus of up to 10% during Stage One downselection [1].

## Submission checklist

Before submitting, complete the following items:

1. Register for the hackathon and confirm entrant eligibility.
2. ~~Create a public GitHub repository containing the source, assets, setup instructions, and `LICENSE`.~~ — Done: `https://github.com/daggerstuff/alexa-submit` (public, MIT).
3. ~~Pin and document the tested MCP SDK and protocol version.~~ — Done: `mcp==2.2.0`, protocol `2025-11-25`, Python 3.13.
4. Demonstrate the MCP endpoint and tool calls in the video.
5. Keep the demo video under three minutes and publish it publicly on YouTube or Vimeo.
6. ~~Explain the meaningful update made during the hackathon period if the project existed beforehand.~~ — Done: see the "Meaningful update statement" section below.
7. ~~Provide product feedback for MCP, Alexa+, and any AWS or other tools actually used.~~ — Done: see `PRODUCT_FEEDBACK.md`.
8. ~~Add a friction log with concrete reproduction steps and recommended improvements.~~ — Done: see `PRODUCT_FEEDBACK.md`.
9. Claim the AWS Builder mini-challenge only if the submission documents a qualifying AWS integration or qualifying development-tool usage.
10. ~~Claim the Open Source mini-challenge only if a qualifying public contribution is made during the hackathon window.~~ — Done: claimed via this submission as a new open-source project; see the "Open Source mini-challenge" section below.

## Meaningful update statement

This repository existed before the hackathon window as a local FastAPI clinical-simulation prototype: a mock `/alexa` passthrough and a deterministic patient Q&A, with no MCP surface and no deployment. The meaningful update made during the hackathon window is the Alexa+ integration itself, built from that prototype:

- A self-hosted MCP server (`server/mcp_server.py`) implementing MCP `2025-11-25` over Streamable HTTP, exposing five tools.
- A stateful, scenario-constrained simulation engine with versioned, evidence-linked rubric evaluation — graded with partial credit and per-metric matched-term evidence.
- A coaching loop: every evaluation returns concrete next-step questions for metrics not yet demonstrated.
- An optional LLM patient persona (Featherless `Qwen/Qwen2.5-14B-Instruct`) with JSON-mode responses, tolerant parsing, automatic retry, and a deterministic fallback.
- Bearer/API-key auth (constant-time comparison) and proxy-safe per-IP rate limiting on the public endpoint.
- Session lifecycle controls: idle TTL, a bounded session cache with LRU eviction, and optional SQLite persistence (WAL) so state survives process restarts.
- Seven authorable scenarios across `basic`/`advanced` difficulty (chest pain basic + advanced, abdominal pain, depression screening, migraine, back pain, syncope) defined as validated JSON data, with an authoring guide (`SCENARIOS.md`).
- Observability: structured JSON request logs, per-request IDs, and unauthenticated `/health`, `/ready`, and `/metrics` (Prometheus) endpoints.
- A public AWS deployment (ECR + App Runner, us-east-2).
- CI (lint + test) and an automated deploy pipeline (GitHub Actions → ECR → App Runner), a full test suite, and the submission documents (`README.md`, `TOOLS.md`, `PRODUCT_FEEDBACK.md`, demo materials).

The pre-existing mock `/alexa` passthrough and its placeholder skill config were removed during the hackathon window; the MCP server, evaluation rubric, security layer, LLM persona, deployment, and documentation were added.

## Open Source mini-challenge

This submission also claims the Open Source mini-challenge through the "create a new open-source project" path: the project repository is a new public, MIT-licensed project built during the hackathon window.

- **Contribution URL:** https://github.com/daggerstuff/alexa-submit
- **Project repository URL:** https://github.com/daggerstuff/alexa-submit
- **GitHub username:** daggerstuff
- **What was done:** Built a self-hosted MCP server (MCP `2025-11-25`, Streamable HTTP) that exposes a clinical-communication simulation as five agent-callable tools, with a versioned evidence-linked evaluator that returns coaching suggestions and a spoken takeaway, seven authorable scenarios across difficulty levels, an optional LLM patient persona (Featherless `Qwen/Qwen2.5-14B-Instruct`) with deterministic fallback, bearer/API-key auth plus per-IP rate limiting, and optional SQLite session persistence.
- **How it works:** `list_simulation_scenarios`, `start_simulation`, `send_practitioner_turn`, `evaluate_simulation`, and `end_simulation` run over `/mcp`; each session holds scenario state and a transcript; patient turns are scenario-constrained; evaluation returns rubric scores with transcript evidence.
- **Why it matters:** It gives clinical learners a repeatable, safe, evidence-linked surface for practicing patient interviews, and it demonstrates a stateful multi-tool Alexa+ workflow rather than a single-turn Q&A bot.

## References

[1]: https://amazonappdev2026.devpost.com/rules "Build, Ship, Shape: Amazon Developer Hackathon Official Rules"
[2]: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports "Model Context Protocol: Transports — Streamable HTTP"
[3]: https://amazonappdev2026.devpost.com/resources "Build, Ship, Shape: Amazon Developer Hackathon Resources"
