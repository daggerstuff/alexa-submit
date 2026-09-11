# Amazon AppDev 2026 Hackathon — Initial Official Findings

Source page: https://amazonappdev2026.devpost.com/
Rules page: https://amazonappdev2026.devpost.com/rules

## Official facts observed

- The event is titled “Build, Ship, Shape: Amazon Developer Hackathon.”
- Primary tracks include Fire TV, Alexa+, Bee, and Ring.
- The Alexa+ track requires a working Agent Skill or a self-hosted MCP server implementing MCP specification version 2025-11-25 or later. The rules also say developers may optionally simulate the Alexa+ experience in a web app using their own agentic tools.
- The project must be a working application using Amazon developer tools and must be submitted with a working demo, code repository, and product feedback by the deadline.
- The rules page lists the submission period as Aug. 31, 2026 at 10:15 a.m. Pacific Time through Oct. 23, 2026 at 12:00 p.m. Pacific Time.
- The judging period is listed as Nov. 9, 2026 at 12:00 p.m. Pacific Time through Nov. 20, 2026 at 12:00 p.m. Pacific Time.
- Winners are listed as announced around Dec. 3, 2026 at 12:00 p.m. Pacific Time.
- The rules mention optional AWS promotional credits of $150, subject to availability, with a request deadline of Oct. 21, 2026 at 12:00 p.m. Pacific Time.
- The page promotes Fire TV, Alexa+, Ring, and Bee as the device/service ecosystem and references SDKs, simulators, sample code, and developer resources.

## Immediate implication for this project

The current project is conceptually aligned with Alexa+ but is not yet hackathon-compliant because its `/alexa` endpoint is only a mock passthrough and the repository does not yet expose a self-hosted MCP server implementing the required MCP version. The best move is to retain the clinical communication simulation but add a real MCP server/tool surface, a clear Alexa+ agent workflow, and a demo path that visibly uses Amazon’s target integration rather than only a generic FastAPI API.

## Additional official findings from the full rules

The Alexa+ track requires either a working Agent Skill or a self-hosted MCP server implementing MCP version 2025-11-25 or later over Streamable HTTP. The rules also allow an alternate simulated Alexa+ experience built with any agentic tool, but the repository must still contain the simulation source and the demo video must clearly show it.

The GitHub repository must be public, include all source code/assets/instructions, and include a detectable open-source license. For Alexa+, the runtime technology must actually be imported and called in the code when using the working MCP path. The demo video must be under three minutes, publicly visible on YouTube or Vimeo, and show the project functioning on its intended platform.

The submission must include product feedback for each tool/API/SDK: what was used, what worked, what needs improvement, whether the entrant would build with it again, and any feature requests or friction logs. Friction-log entries can provide up to a 10% judging bonus during Stage One downselection.

Stage One is a pass/fail viability check: the project must fit the theme and reasonably apply the required APIs/SDKs. Stage Two uses equally weighted criteria:

| Criterion | Implication for this project |
|---|---|
| Tech Implementation | A real MCP/Streamable HTTP path must be visible and working; the clinical simulation must be reliable enough to demo. |
| Design | The voice interaction must be concise and coherent for Alexa+; the learner should know what to say and what feedback means. |
| Potential Impact | The project needs a specific customer: clinical learners, educators, or simulation programs, with a credible workflow beyond the hackathon. |
| Quality of Idea | A generic symptom chatbot is weak. The differentiated idea should be a stateful, scenario-constrained communication simulator with explainable feedback and safe boundaries. |

The Alexa+ creative examples in the rules favor agentic workflows that orchestrate across services, maintain state across sessions, and use richer MCP capabilities rather than single-turn Q&A or a basic wrapper. Therefore, the project should emphasize persistent scenario state, evaluator feedback, and a true MCP tool surface.

## Alignment decision

The project should pivot from “Alexa clinical simulation node” to **Clinical Conversation Coach for Alexa+**: an Alexa+ MCP server that exposes scenario discovery, simulation session control, practitioner turn processing, and evidence-linked evaluation as tools. The clinical domain remains the differentiator, but the hackathon artifact must make the Amazon/MCP integration the visible product surface.

Recommended submission tracks are the Alexa+ primary track and the AWS Builder mini-challenge only if an AWS runtime service is actually integrated and documented. The Open Source mini-challenge is possible if a qualifying public contribution is made during the hackathon window.
