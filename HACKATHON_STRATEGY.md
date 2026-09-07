# Amazon AppDev 2026 Hackathon Alignment Strategy

## Recommended submission concept

The project should be submitted as **Clinical Conversation Coach for Alexa+**. The product is a self-hosted MCP server that lets an Alexa+ agent orchestrate an educational clinical communication simulation: discover scenarios, start a session, conduct a practitioner-patient conversation, and request evidence-linked feedback.

This is a stronger hackathon concept than “Alexa clinical simulation node” because it makes the Alexa+ integration the product surface while preserving the clinical education differentiator. The experience is not a generic symptom question-and-answer bot. It is a stateful, scenario-constrained workflow with a beginning, an interaction loop, and a measurable outcome.

The official rules require the Alexa+ primary track to use either a working Agent Skill or a self-hosted MCP server implementing MCP version 2025-11-25 or later over Streamable HTTP. The rules also provide an alternate simulated Alexa+ path, but the working MCP path is the stronger fit for this project because it demonstrates the required technology directly at runtime [1].

## Current alignment status

| Hackathon expectation | Current status | Action |
|---|---|---|
| Alexa+ primary track | Strong conceptual fit | Submit under Alexa+ |
| Self-hosted MCP server | Implemented in `server/mcp_server.py` | Demonstrate `/mcp` over Streamable HTTP |
| MCP version target | SDK dependency is `mcp>=2.0.0`; protocol behavior is delegated to SDK | Pin and document the tested SDK/protocol version before submission |
| Public GitHub repository | Repository code exists locally | Create a public GitHub repository with `LICENSE` and setup instructions |
| Working demo video under three minutes | Not yet produced | Record one concise end-to-end demo |
| Product feedback | Not yet prepared | Submit a tool-by-tool feedback section and friction log |
| AWS Builder mini-challenge | Not yet claimed | Claim only after adding a real AWS runtime integration or qualifying development-tool usage |
| Open Source mini-challenge | Not yet claimed | Claim only after a qualifying contribution during the hackathon window |

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

The demo should open with the problem and immediately show the Amazon-compatible integration.

| Time | Demo beat | What judges should see |
|---|---|---|
| 0:00–0:20 | Product framing | “Clinical Conversation Coach helps learners practice structured patient interviews through Alexa+.” |
| 0:20–0:40 | MCP connection | MCP client connects to the self-hosted `/mcp` Streamable HTTP endpoint and lists the available tools. |
| 0:40–1:05 | Scenario discovery | The agent calls `list_simulation_scenarios` and selects the chest-pain scenario and rubric version. |
| 1:05–1:55 | Live conversation | The agent calls `start_simulation`, then `send_practitioner_turn` several times. The patient discloses information progressively and preserves state. |
| 1:55–2:25 | Evaluation | The agent calls `evaluate_simulation`; the result shows metric IDs, scores, evidence excerpts, and improvements. |
| 2:25–2:45 | Safety and reliability | Show the educational disclaimer, stable scenario version, and a repeated `client_event_id` returning the same result rather than duplicating a turn. |
| 2:45–3:00 | Impact and feedback | Explain the target users and one concrete friction point or feature request for the Alexa+/MCP developer experience. |

The video should avoid spending most of its time on code. The code repository can carry the implementation details; the video must prove that the product works on the intended platform and that the required MCP technology is actually used [1].

## Judging strategy

The official judging criteria are equally weighted across tech implementation, design, potential impact, and quality of idea [1]. The project should therefore optimize for more than protocol compliance.

**Tech implementation** is addressed by exposing a real MCP server over Streamable HTTP, using the official Python MCP SDK, and providing typed, scenario-aware tools. The repository should include a reproducible setup command and a smoke test.

**Design** is addressed by keeping the tool surface small and meaningful. The learner should not need to understand internal session mechanics. The agent should guide the conversation, keep spoken responses concise, and reserve detailed evaluation for the end of the simulation.

**Potential impact** is addressed by focusing on clinical learners, simulation programs, faculty coaches, and communication-skills educators. The product can eventually support scenario libraries, educator-authored rubrics, cohort reporting, and accessibility-oriented voice practice without changing the core MCP contract.

**Quality of idea** is addressed by combining a stateful cross-turn interaction, scenario-constrained patient behavior, evidence-linked evaluation, and safe educational boundaries. This is materially stronger than a single-turn health-information bot or a basic MCP wrapper.

## Security and trust positioning

The product must clearly state that it is an educational simulator and must not be used for diagnosis, treatment, or real-patient triage. The demo should use synthetic scenarios only.

The MCP transport should be bound to localhost during development, validate origins, and use authentication before any hosted demonstration. The official Streamable HTTP specification warns about DNS rebinding, recommends validating `Origin`, recommends binding local servers to `127.0.0.1`, and recommends authentication [2].

The current implementation includes scenario locking, session-ending controls, idempotent client event IDs, optional development API-key protection on the REST surface, restricted local CORS, request logging, and explicit disclaimers. Before a public hosted demo, add MCP-layer authentication, origin allowlisting, HTTPS, rate limiting, and secret management.

## Product feedback to prepare

The submission should include specific feedback rather than generic praise. The most useful feedback topics are:

| Area | Example feedback to document |
|---|---|
| MCP setup | Whether the Streamable HTTP setup was easy to understand and test |
| Alexa+ workflow | Whether tool descriptions led the agent to choose the correct sequence |
| Session state | Whether preserving context across tool calls felt reliable |
| Developer experience | Errors, missing examples, or debugging friction encountered while building |
| Voice UX | Whether the patient responses were concise enough for spoken interaction |
| Evaluation output | Whether structured evidence and rubric versions were easy to consume |

The rules explicitly request what tools were used, what worked, what needs improvement, whether the entrant would build with them again, and optionally feature requests and friction logs. Friction log entries can provide a judging bonus of up to 10% during Stage One downselection [1].

## Submission checklist

Before submitting, complete the following items:

1. Register for the hackathon and confirm entrant eligibility.
2. Create a public GitHub repository containing the source, assets, setup instructions, and `LICENSE`.
3. Pin and document the tested MCP SDK and protocol version.
4. Demonstrate the MCP endpoint and tool calls in the video.
5. Keep the demo video under three minutes and publish it publicly on YouTube or Vimeo.
6. Explain the meaningful update made during the hackathon period if the project existed beforehand.
7. Provide product feedback for MCP, Alexa+, and any AWS or other tools actually used.
8. Add a friction log with concrete reproduction steps and recommended improvements.
9. Claim the AWS Builder mini-challenge only if the submission documents a qualifying AWS integration or qualifying development-tool usage.
10. Claim the Open Source mini-challenge only if a qualifying public contribution is made during the hackathon window.

## References

[1]: https://amazonappdev2026.devpost.com/rules "Build, Ship, Shape: Amazon Developer Hackathon Official Rules"

[2]: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports "Model Context Protocol: Transports — Streamable HTTP"

[3]: https://amazonappdev2026.devpost.com/resources "Build, Ship, Shape: Amazon Developer Hackathon Resources"
