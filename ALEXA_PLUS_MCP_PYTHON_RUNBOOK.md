# Alexa+ MCP Integration in Python

## Technical implementation runbook for Clinical Conversation Coach

This runbook describes how to expose the clinical simulation node as a self-hosted MCP server for Alexa+. The intended integration is **MCP over Streamable HTTP**, with the Python MCP SDK handling JSON-RPC, session negotiation, tool discovery, and tool invocation. The current repository already contains the first working implementation in `server/mcp_server.py`; the steps below explain how to reproduce, harden, and validate it.

> **Safety boundary:** The server is an educational simulation. It must not be used for diagnosis, treatment, triage, or real-patient care. Use synthetic scenarios only.

## 1. Confirm the target integration

The Alexa+ hackathon path requires a working Agent Skill or a self-hosted MCP server using MCP version 2025-11-25 or later over Streamable HTTP [1]. Streamable HTTP uses a single MCP endpoint that supports HTTP POST and may support HTTP GET for server-sent events. Clients send JSON-RPC messages through POST and advertise support for both `application/json` and `text/event-stream` [2].

The Python MCP documentation recommends Python 3.10 or newer and MCP SDK 2.0.0 or newer. It also recommends using the standard logging module and avoiding accidental protocol output, especially for stdio servers [3]. The current project uses Python 3.13, `mcp==2.2.0` (protocol version 2025-11-25), and the HTTP transport path.

## 2. Install the dependencies

The validated dependency set is in `server/requirements.txt`:

```text
fastapi==0.141.1
uvicorn[standard]==0.34.0
pydantic==2.13.5
pydantic-settings==2.15.0
httpx==0.28.1
pytest==8.3.4
pytest-asyncio==0.25.2
mcp==2.2.0
ruff==0.14.0
```

Initialize the repository with:

```bash
./scripts/initialize.sh
source .venv/bin/activate
```

The FastAPI version is pinned to the version validated with the installed MCP SDK’s Starlette dependency. Whenever the MCP SDK is upgraded, rerun the full test suite and the MCP startup smoke test.

## 3. Create the MCP server instance

Import `MCPServer` from the Python SDK and create one server instance with a stable name, version, description, and safety instructions:

```python
from mcp.server.mcpserver import MCPServer

mcp = MCPServer(
    name="clinical-conversation-coach",
    title="Clinical Conversation Coach",
    version="0.3.0",
    description=(
        "A scenario-based clinical communication simulator for educational practice."
    ),
    instructions=(
        "Use only for educational simulation. Never use this server for real patient care, "
        "diagnosis, triage, or treatment decisions."
    ),
)
```

The server metadata matters because an MCP client uses it to understand what the server does before selecting tools. The description should describe the workflow, while the instructions should establish the system’s educational boundary.

## 4. Reuse the existing domain orchestrator

Do not place simulation logic directly inside MCP tool functions. Import the existing orchestrator and scenario registry instead:

```python
from server.main import orchestrator
from server.scenarios import SCENARIOS
from server.schemas.validation import SimulationAction, SimulationRequest
```

This gives the MCP surface the same behavior as the development REST API. The orchestrator remains responsible for scenario lookup, session lifecycle, transcript management, patient-agent calls, evaluation, idempotency, and status transitions.

The integration boundary should convert MCP arguments into the validated domain request:

```python
request = SimulationRequest(
    session_id=session_id,
    scenario_id=scenario_id,
    action=SimulationAction.message,
    practitioner_message=practitioner_message,
    client_event_id=client_event_id,
)
response = orchestrator.handle(request)
```

This separation prevents transport-specific behavior from leaking into the clinical simulation model.

## 5. Design the MCP tool surface around user tasks

Expose a small set of meaningful tools rather than internal CRUD operations. The current tool surface is:

| Tool                        | Inputs                                                                          | Result                                         |
| --------------------------- | ------------------------------------------------------------------------------- | ---------------------------------------------- |
| `list_simulation_scenarios` | None                                                                            | Scenario IDs, versions, titles, and metric IDs |
| `start_simulation`          | `session_id`, `scenario_id`                                                     | Patient opening response and session state     |
| `send_practitioner_turn`    | `session_id`, `practitioner_message`, optional `client_event_id`, `scenario_id` | Next patient response and transcript           |
| `evaluate_simulation`       | `session_id`, `scenario_id`                                                     | Current evidence-linked evaluation             |
| `end_simulation`            | `session_id`, `scenario_id`                                                     | Final evaluation and locked session            |

A discovery tool makes the integration self-describing. A start tool makes the session boundary explicit. A turn tool represents the core interaction. Separate evaluate and end tools support both intermediate review and finalization.

## 6. Register typed tools with the SDK

Use the SDK’s `@mcp.tool()` decorator. Provide a clear description and request structured output where the return value is a JSON object:

```python
@mcp.tool(
    description="Send the learner's next practitioner utterance and receive the simulated patient's response.",
    structured_output=True,
)
def send_practitioner_turn(
    session_id: str,
    practitioner_message: str,
    client_event_id: str | None = None,
    scenario_id: str = "chest-pain-basic",
) -> dict[str, Any]:
    response = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            scenario_id=scenario_id,
            action=SimulationAction.message,
            practitioner_message=practitioner_message,
            client_event_id=client_event_id,
        )
    )
    return response.model_dump(mode="json")
```

The function signature becomes part of the tool schema. Keep parameters explicit, bounded, and easy for an agent to fill. Avoid accepting arbitrary JSON for the primary workflow because it makes tool selection and validation less reliable.

## 7. Serialize Pydantic responses at the boundary

The domain layer returns Pydantic models. Serialize them at the MCP edge:

```python
def serialize(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json")
    return response
```

The serialized result should preserve the fields that matter to the Alexa+ experience:

```json
{
  "request_id": "generated-correlation-id",
  "session_id": "demo-1",
  "scenario_id": "chest-pain-basic",
  "scenario_version": "1.1.0",
  "action": "message",
  "patient": {
    "content": "I am a little short of breath, but I can still speak in full sentences.",
    "emotional_state": "concerned",
    "disclosed_facts": ["chest-pressure", "dyspnea"],
    "safety_note": null,
    "scenario_id": "chest-pain-basic",
    "scenario_version": "1.1.0"
  },
  "status": "active",
  "disclaimer": "Educational simulation only; do not use for real patient care."
}
```

The spoken adapter should use `patient.content`. The remaining fields are useful for agent reasoning, UI display, evaluation, logging, and safety handling.

## 8. Run Streamable HTTP on a single MCP endpoint

Use the SDK’s built-in Streamable HTTP runner:

```python
if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=os.getenv("MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("MCP_PORT", "8001")),
        streamable_http_path=os.getenv("MCP_PATH", "/mcp"),
        json_response=True,
        stateless_http=False,
    )
```

Run it locally with:

```bash
source .venv/bin/activate
MCP_HOST=127.0.0.1 MCP_PORT=8001 python -m server.mcp_server
```

The expected endpoint is:

```text
http://127.0.0.1:8001/mcp
```

The MCP transport owns the JSON-RPC and Streamable HTTP details. Do not manually implement a second JSON-RPC endpoint unless there is a specific interoperability requirement.

## 9. Respect Streamable HTTP security requirements

The official transport specification calls out three important controls: validate the `Origin` header to prevent DNS rebinding, bind local servers to `127.0.0.1` rather than `0.0.0.0`, and implement authentication for connections [2].

The current implementation already defaults to `127.0.0.1`. Before exposing the MCP server through a tunnel or hosted URL, add the following controls:

| Control         | Development behavior            | Hosted behavior                                     |
| --------------- | ------------------------------- | --------------------------------------------------- |
| Binding         | `127.0.0.1`                     | Private service behind a reverse proxy              |
| Origin          | Allow local development origin  | Explicit allowlist; reject invalid origins with 403 |
| Authentication  | Optional REST `DEV_API_KEY`     | MCP-layer authentication or authenticated proxy     |
| TLS             | Not required on localhost       | HTTPS required                                      |
| Rate limiting   | Not yet required for local demo | Per-client and per-session limits                   |
| Secrets         | `.env`, never committed         | Secret manager or deployment secret store           |
| Transcript data | Synthetic only                  | Encrypted storage and retention policy              |

Do not send real protected health information through a local tunnel or hackathon demo endpoint.

## 10. Preserve MCP session state and simulation session state separately

There are two different session concepts:

**MCP transport session** is the protocol-level session negotiated through `MCP-Session-Id`. The client must preserve and send that header on subsequent requests when the server assigns one [2].

**Simulation session** is the application-level clinical practice session identified by `session_id`. It contains the scenario, patient state, transcript, processed client event IDs, and lifecycle status.

Keep these concepts separate. The MCP session controls protocol continuity. The simulation session controls the learner’s scenario. If a client reconnects and the MCP session changes, it should still provide the application `session_id` when continuing the simulation, subject to the server’s authorization policy.

## 11. Start the local REST API separately

The REST API remains useful for deterministic development and regression testing:

```bash
uvicorn server.main:app --host 127.0.0.1 --port 8000 --reload
```

Use it to test the domain layer independently from MCP transport. This gives the project two validation levels:

| Level      | Endpoint/process        | Purpose                                            |
| ---------- | ----------------------- | -------------------------------------------------- |
| Domain/API | FastAPI on port 8000    | Test validation, state transitions, and evaluation |
| Protocol   | MCP server on port 8001 | Test tool discovery, JSON-RPC, and Streamable HTTP |

This separation makes failures easier to diagnose. A failed REST test usually indicates domain logic. A failed MCP client test usually indicates tool registration, transport, serialization, or session negotiation.

## 12. Add tests in three layers

### Domain tests

Test scenario lookup, patient disclosures, rubric output, duplicate event IDs, scenario switching rejection, and ended-session locking. The current suite covers these behaviors in `tests/test_simulation.py`.

### Tool registration tests

Import the MCP server module and verify that the process starts without import errors. For stronger coverage, use an MCP client or protocol fixture to initialize the server and call `tools/list`, then assert that the five expected tool names are present.

### End-to-end protocol tests

Start the server on a test port and run an MCP client through this sequence:

```text
initialize
initialized notification
list tools
call list_simulation_scenarios
call start_simulation
call send_practitioner_turn
call evaluate_simulation
call end_simulation
```

Assert that the client sees a valid MCP session, receives structured tool results, and can reuse the application `session_id` across calls.

## 13. Validate with a real MCP client

The minimum manual validation should confirm:

1. The client can connect to `http://127.0.0.1:8001/mcp`.
2. Initialization succeeds and the server advertises its name and version.
3. Tool discovery returns all five simulation tools.
4. The client can start a scenario.
5. A practitioner turn returns a patient response.
6. A repeated `client_event_id` does not create another transcript turn.
7. Evaluation returns `rubric_version`, metric IDs, evidence, and rationales.
8. Ending a session prevents later messages.
9. The client can handle JSON responses and does not assume that every request must use SSE.

The Streamable HTTP specification allows a server to return either `application/json` or `text/event-stream` for a request, and a conforming client must support both [2]. The current server uses JSON responses for the initial demo path to keep the interaction easy to inspect.

## 14. Prepare the Alexa+ adapter behavior

The Alexa+ or agent-facing layer should follow this sequence:

```text
User asks to practice a clinical conversation
    -> call list_simulation_scenarios
    -> choose or ask the user to choose a scenario
    -> create a stable application session_id
    -> call start_simulation
    -> speak the patient content
    -> for each learner turn:
         call send_practitioner_turn
         speak patient.content
    -> when the learner asks for feedback:
         call evaluate_simulation or end_simulation
         summarize strengths and improvements
```

The agent should not narrate raw internal fields unless useful. It should speak the patient’s content during the interaction and present structured feedback at the end. The disclaimer should be shown or spoken at the beginning and included in final feedback.

## 15. Deploy behind HTTPS for a public demo

For a public or judge-accessible demo, place the server behind an HTTPS reverse proxy or secure hosting layer. The deployment must preserve the single MCP path, for example:

```text
https://demo.example.com/mcp
```

The proxy should:

- Terminate TLS.
- Allow only the MCP methods and headers required by the SDK.
- Validate or forward authentication.
- Enforce request size and timeout limits.
- Preserve `MCP-Session-Id` and `Last-Event-ID` when resumability is used.
- Emit redacted access logs.
- Prevent direct exposure of internal admin endpoints.

Do not treat the local tunnel helper as a production deployment. It is only a development bridge.

## 16. Final Alexa+ readiness checklist

| Area         | Ready when                                                                                 |
| ------------ | ------------------------------------------------------------------------------------------ |
| Protocol     | MCP SDK and protocol version are documented and tested                                     |
| Runtime hook | `mcp_server.py` imports the SDK and calls the server at runtime                            |
| Tools        | Tool names, descriptions, inputs, and outputs are stable                                   |
| State        | MCP session and application simulation session are clearly separated                       |
| Safety       | Synthetic-only demo, disclaimer, and no clinical decision claims                           |
| Security     | Origin validation, HTTPS, authentication, and rate limiting are in place for hosted access |
| Tests        | Domain, tool discovery, and end-to-end MCP paths pass                                      |
| Demo         | Three-minute video visibly shows MCP tool use and the working simulation                   |
| Repository   | Public repository contains setup instructions and an open-source license                   |
| Feedback     | Product feedback and a concrete friction log are ready for submission                      |

## References

[1]: https://amazonappdev2026.devpost.com/rules "Build, Ship, Shape: Amazon Developer Hackathon Official Rules"
[2]: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports "Model Context Protocol: Transports — Streamable HTTP"
[3]: https://modelcontextprotocol.io/docs/2026-07-28/develop/build-server "Model Context Protocol: Build an MCP Server"
[4]: https://amazonappdev2026.devpost.com/resources "Build, Ship, Shape: Amazon Developer Hackathon Resources"
