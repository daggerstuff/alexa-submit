# Clinical Conversation Coach for Alexa+

## Three-Minute Amazon AppDev 2026 Pitch

**Primary track:** Alexa+  
**Format:** Three-minute demo video or live pitch  
**Core proof point:** A self-hosted MCP server over Streamable HTTP orchestrates a stateful clinical communication simulation and returns evidence-linked feedback.

---

## Pitch strategy

The pitch should present the project as a **voice-first learning workflow**, not as a healthcare chatbot. The central story is simple: clinical learners need a safe way to practice difficult conversations; Alexa+ provides a natural conversational interface; MCP gives the agent a structured set of tools; and the simulation engine turns every conversation into explainable feedback.

The pitch is designed around the official Alexa+ judging dimensions: **technical implementation, design, potential impact, and quality of idea** [1]. It also visibly addresses the Alexa+ requirement for a working Agent Skill or self-hosted MCP server implementing MCP over Streamable HTTP [1] [2].

---

## Timed slide outline

| Time | Slide | Purpose | Demo or visual proof |
|---|---:|---|---|
| 0:00–0:15 | Cover | Establish the product and customer | Product name and one-line promise |
| 0:15–0:35 | 1 | Frame the learner problem | Learner attempting a scenario without a live patient |
| 0:35–0:55 | 2 | Show the Alexa+ architecture | MCP endpoint and tool list |
| 0:55–1:30 | 3 | Demonstrate the live workflow | Scenario discovery, start, and two practitioner turns |
| 1:30–1:55 | 4 | Prove stateful, constrained patient behavior | Progressive disclosure and preserved patient state |
| 1:55–2:20 | 5 | Prove explainable evaluation | Metric scores with transcript evidence |
| 2:20–2:45 | 6 | Explain trust and reliability | Versioning, idempotency, session locking, disclaimer |
| 2:45–3:00 | 7 | Close on impact and next step | Target users, hackathon fit, and product feedback |

---

## Slide content and speaker script

## Cover

**Title:** Clinical Conversation Coach for Alexa+  
**Subtitle:** Practice the conversation. Understand the performance.  
**Presenter:** Amazon AppDev 2026 — Alexa+ Track

**Speaker script — 15 seconds:**

“Clinical Conversation Coach is a voice-first simulation for learners who need to practice patient interviews before they face a real one. Built as a self-hosted MCP server for Alexa+, it turns a natural conversation into a structured learning loop: practice, respond, and improve.”

---

## Slide 1 — Clinical communication is learned through practice

**Slide content:**

- Learners need repeated practice with difficult conversations.
- Real patients are not a safe or scalable training environment for every rehearsal.
- Existing chatbots often provide answers, but not a persistent scenario or measurable feedback.

**Speaker script — 20 seconds:**

“Clinical communication is not learned by reading a checklist once. Learners need repeated practice with uncertainty, emotion, and time pressure. But a live patient or standardized-patient session is not always available for every rehearsal. Most conversational bots answer questions; they do not maintain a scenario, respond like a person, and explain what the learner did well or missed. We built for that gap.”

**Judging connection:** Potential impact and quality of idea.

---

## Slide 2 — Alexa+ turns the lesson into an agentic workflow

**Slide content:**

```text
Alexa+ agent
    -> Streamable HTTP MCP endpoint
    -> Clinical Conversation Coach
    -> Scenario policy + session state
    -> Patient persona + evidence-linked evaluator
```

**MCP tools shown:**

- `list_simulation_scenarios`
- `start_simulation`
- `send_practitioner_turn`
- `evaluate_simulation`
- `end_simulation`

**Speaker script — 20 seconds:**

“The Alexa+ integration is not a mock API hidden behind a README. The project runs a self-hosted MCP server over Streamable HTTP. Alexa+ can discover five task-oriented tools: list scenarios, start a session, send a practitioner turn, evaluate the interaction, and end the session. The agent orchestrates those tools while the server owns the scenario, transcript, and rubric state.”

**Demo cue:** Display the MCP endpoint and tool list. Show the server running at `/mcp`.

**Judging connection:** Tech implementation and design.

---

## Slide 3 — One voice interaction becomes a complete learning loop

**Slide content:**

1. Choose a scenario.
2. Speak as the practitioner.
3. Hear the simulated patient respond.
4. Request feedback when finished.

**Speaker script — 35 seconds:**

“Here is the live workflow. The agent first discovers the available scenario and its rubric version. It starts a chest-pressure simulation. The learner says, ‘My name is Alex. Where is the pain, and are you short of breath?’ The server returns a patient response about substernal pressure and mild shortness of breath. The learner follows up about medications and allergies, and the patient discloses the next approved facts. At the end, the agent calls the evaluator and receives structured feedback instead of a vague statement like ‘good job.’”

**Demo cue:** Show the actual sequence of MCP calls and responses. Keep the spoken interaction audible and concise.

**Judging connection:** Design and technical implementation.

---

## Slide 4 — The patient is dynamic, but never unconstrained

**Slide content:**

- Scenario version: `chest-pain-basic / 1.1.0`
- Disclosure rules control what can be revealed.
- Patient state preserves disclosed facts and emotional continuity.
- Unknown questions receive a bounded fallback response.

**Speaker script — 25 seconds:**

“The patient feels dynamic because responses depend on what the learner asks and what has already been disclosed. But the behavior is constrained by the scenario policy. Each fact has a trigger, a permitted response, and an emotional state. The session remembers which facts were disclosed, so the patient remains coherent across turns. If the learner asks something outside the scenario, the system does not invent a diagnosis or a new symptom; it falls back to a bounded response.”

**Demo cue:** Repeat a client event ID once and show that the server does not duplicate the patient turn.

**Judging connection:** Quality of idea, trust, and technical implementation.

---

## Slide 5 — Feedback is explainable, not just a score

**Slide content:**

| Metric | Score | Evidence |
|---|---:|---|
| Symptom characterization | 4 / 4 | “Where is the pain, and when did it start?” |
| Associated symptoms and risk | 4 / 4 | “Are you short of breath, and what medications do you take?” |
| Safety escalation | 1 / 4 | No urgent escalation language detected |
| Shared next-step confirmation | 1 / 4 | No plan or understanding check detected |

**Speaker script — 25 seconds:**

“The evaluator is designed for explanation. Every metric has a stable ID, a score, a maximum, a rationale, and evidence from the practitioner transcript. In this example, the learner receives full credit for characterizing symptoms and checking associated risks, but sees that escalation and shared next-step confirmation were not demonstrated. The result is actionable: it tells the learner what to practice next and shows why the system reached that conclusion.”

**Demo cue:** Show the `evaluate_simulation` response with `rubric_version`, metric IDs, evidence excerpts, strengths, and improvements.

**Judging connection:** Design, impact, and technical implementation.

---

## Slide 6 — Trust is designed into the runtime

**Slide content:**

- Synthetic educational scenarios only.
- Explicit disclaimer on responses and evaluations.
- Scenario locking prevents rubric mismatch.
- Idempotent event IDs prevent duplicate turns.
- Ended sessions reject further messages.
- Local MCP binding by default; production requires HTTPS, origin validation, and authentication.

**Speaker script — 25 seconds:**

“This is an educational simulator, not a clinical decision-maker, and the runtime makes that boundary visible. Responses carry an educational disclaimer. A session cannot silently switch scenarios or be evaluated against the wrong rubric version. Retry-safe event IDs prevent duplicate turns, and an ended session is locked. The local MCP server binds to localhost by default. Before public hosting, we add HTTPS, origin validation, authentication, rate limiting, and protected durable storage, following the Streamable HTTP security guidance.”

**Judging connection:** Tech implementation and product maturity.

---

## Slide 7 — A focused Alexa+ use case with room to grow

**Slide content:**

**For:** Clinical learners, simulation programs, and communication-skills educators  
**Now:** One working scenario, one MCP workflow, evidence-linked feedback  
**Next:** Educator-authored scenarios, rubric libraries, cohort reporting, and optional constrained model augmentation

**Speaker script — 15 seconds:**

“Clinical Conversation Coach gives Alexa+ a focused, useful workflow: help someone practice a difficult conversation and make the feedback understandable. The current demo proves the core loop with a working MCP server, stateful simulation, and evidence-linked evaluation. The next step is an educator-authored scenario library and a governed feedback platform. We are also submitting concrete product feedback on MCP setup, voice interaction, session state, and developer tooling so this experience can become easier to build and safer to use.”

**Closing line:**

“Alexa+ provides the conversation. MCP provides the orchestration. Clinical Conversation Coach provides the learning outcome.”

---

## Demo operator checklist

Before recording, verify that the video visibly demonstrates the project functioning through the intended Alexa+ integration path. The official rules require the demo video to be shorter than three minutes, publicly hosted on YouTube or Vimeo, and to show the project functioning on its intended platform [1].

| Check | Expected result |
|---|---|
| MCP server | Starts on `127.0.0.1:8001/mcp` or a secured HTTPS deployment |
| Tool discovery | All five simulation tools are visible to the MCP client |
| Scenario selection | The client calls `list_simulation_scenarios` |
| Session start | The patient opening response is returned |
| Practitioner turn | A spoken or typed learner turn produces a patient response |
| State continuity | A follow-up question reveals another scenario-approved fact |
| Evaluation | The result includes metric IDs, evidence, rationale, and rubric version |
| Retry behavior | Reusing a client event ID does not create a duplicate turn |
| Safety boundary | The disclaimer is visible or spoken |
| Ending | `end_simulation` returns the evaluation and locks the session |

## Submission compliance notes

The public GitHub repository should contain the complete source code, assets, setup instructions, and an open-source license. The repository must demonstrate actual runtime use of the Alexa+ technology rather than only naming it in documentation [1].

The submission description should identify the Alexa+ primary track. Claim the AWS Builder mini-challenge only if the project includes and documents a qualifying AWS service or qualifying development-tool usage. Claim the Open Source mini-challenge only if a qualifying contribution is made during the hackathon window.

The product-feedback section should cover which developer tools were used, what worked, what needs improvement, whether the team would build with them again, and concrete feature requests. A friction log should record the attempted task, expected result, actual result, severity, workaround, and proposed improvement. The rules state that friction logs can contribute a bonus of up to 10% during Stage One downselection [1].

## Delivery guidance

The speaker should sound like a product builder showing a working system, not like someone reading a technical specification. Keep the voice interaction audible, use one scenario, avoid unnecessary code, and make the evidence-linked evaluation the final proof of value.

Do not claim that the system diagnoses patients, provides medical advice, or is ready for clinical deployment. The strongest claim is narrower and more credible: it provides a repeatable, scenario-constrained practice environment for clinical communication.

## References

[1]: https://amazonappdev2026.devpost.com/rules "Build, Ship, Shape: Amazon Developer Hackathon Official Rules"

[2]: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports "Model Context Protocol: Transports — Streamable HTTP"

[3]: https://amazonappdev2026.devpost.com/resources "Build, Ship, Shape: Amazon Developer Hackathon Resources"
