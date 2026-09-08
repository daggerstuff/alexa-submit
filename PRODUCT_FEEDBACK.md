# Product Feedback and Friction Log

## Amazon AppDev 2026 — Alexa+ Track

This document satisfies the product-feedback and friction-log submission requirements. The rules state that friction-log entries can contribute a bonus of up to 10% during Stage One downselection [1].

---

## Tools used

| Tool                   | Version    | Purpose                                       |
| ---------------------- | ---------- | --------------------------------------------- |
| Python MCP SDK (`mcp`) | 2.2.0      | Self-hosted MCP server over Streamable HTTP   |
| MCP protocol           | 2025-11-25 | Transport specification version               |
| FastAPI                | 0.141.1    | Development REST API and test surface         |
| Pydantic               | 2.13.5     | Request/response validation and serialization |
| Uvicorn                | 0.34.0     | ASGI server for MCP and REST                  |
| pytest                 | 8.3.4      | Test suite                                    |
| Ruff                   | 0.14.0     | Linting and formatting                        |
| Docker                 | —          | Containerized deployment for judges           |
| Python                 | 3.13.14    | Runtime                                       |

---

## What worked well

### MCP Python SDK

- The `MCPServer` class and `@mcp.tool()` decorator make tool registration concise and readable. Defining five tools with typed parameters and structured output took under 100 lines of code.
- The `streamable_http_app()` factory is testable with Starlette's `TestClient`, which let us write integration tests that exercise the full MCP protocol (initialize → initialized → tools/list → tools/call) without starting a separate process.
- `TransportSecuritySettings` with DNS rebinding protection, allowed hosts, and allowed origins is a sensible default for local development.
- The SDK correctly handles session negotiation via `MCP-Session-Id` headers. The test confirms that the server returns a session ID on `initialize` and accepts it on subsequent requests.

### Pydantic + FastAPI

- Pydantic v2 models made the simulation request/response contracts self-documenting. The `Field` constraints (min_length, max_length) catch malformed input before it reaches the orchestrator.
- FastAPI's `TestClient` integration with dependency injection (for the optional `DEV_API_KEY`) worked without any custom fixtures.

### Docker

- The slim Python 3.13 image produces a ~150 MB container that starts in under 2 seconds. The MCP server responds to `initialize` immediately after startup.

---

## What needs improvement

### MCP Python SDK

1. **Pydantic version constraint is strict.** MCP 2.2.0 requires `pydantic>=2.12.0`. The original project pinned `pydantic==2.10.5`, which caused a silent resolution failure. The SDK should either loosen its floor or document the constraint more prominently in the installation guide.

2. **`streamable_http_app()` is not in the public API docs.** We found it by reading the SDK source. The official "Build an MCP Server" guide [2] shows `mcp.run()` but does not mention the test-app factory. A testing section in the docs would save significant time.

3. **Tool error handling surfaces as `UnexpectedToolError`.** When the orchestrator raises an `HTTPException` (e.g., 409 for scenario switching), the MCP SDK wraps it in `UnexpectedToolError` and the client receives a generic error instead of the structured HTTP status. There is no documented pattern for returning a tool-level error result that preserves the domain error code and message.

4. **No built-in health or metadata endpoint.** The MCP server exposes only `/mcp`. A companion `/health` endpoint would be useful for container orchestration and load balancer checks. We worked around this by running the REST API separately, but a single-process deployment would benefit from a built-in health check.

### FastAPI + MCP coexistence

5. **Two ports for one project.** The REST API runs on port 8000 and the MCP server on port 8001. There is no documented pattern for mounting the MCP Streamable HTTP app as a sub-application inside the FastAPI app. This would simplify deployment and reduce the number of processes judges need to start.

### Alexa+ integration

6. **No Alexa+ MCP client documentation.** The hackathon rules describe the MCP server requirement, but there is no public documentation for how an Alexa+ agent discovers and calls MCP tools. We inferred the workflow (list scenarios → start → send turns → evaluate → end) from the MCP protocol spec, not from Alexa+ documentation.

7. **No Alexa+ local testing tool.** We could not find a mock Alexa+ MCP client for local development. The closest option was a raw MCP client using the Python SDK, which does not simulate the Alexa+ conversation UX (voice prompts, session management, spoken response formatting).

---

## Would we build with this again?

**Yes.** The MCP Python SDK is the strongest part of the stack. The tool registration pattern is clean, the Streamable HTTP transport works, and the test infrastructure is solid. The main gaps are documentation (test app factory, error handling patterns, FastAPI mounting) rather than fundamental design problems.

We would also build with FastAPI and Pydantic again. The combination of Pydantic validation and FastAPI dependency injection made the REST API easy to test and secure.

---

## Feature requests

| Priority | Request                                           | Rationale                                                                    |
| -------- | ------------------------------------------------- | ---------------------------------------------------------------------------- |
| High     | Document `streamable_http_app()` in the SDK guide | The test factory is essential for integration testing but undocumented       |
| High     | Add tool-level error result pattern               | Allow tools to return structured errors without raising exceptions           |
| Medium   | Support mounting MCP inside an existing ASGI app  | Simplify single-process deployment                                           |
| Medium   | Add built-in `/health` endpoint option            | Container orchestration support                                              |
| Low      | Provide an Alexa+ MCP client simulator            | Reduce the gap between MCP server development and Alexa+ integration testing |

---

## Friction log

Each entry includes: attempted task, expected result, actual result, severity, workaround, and proposed improvement.

### Friction 1: Pydantic version conflict blocks installation

| Field                    | Value                                                                                                                                                                                                          |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Attempted task**       | Install dependencies from `server/requirements.txt` in a fresh virtualenv                                                                                                                                      |
| **Expected result**      | `pip install -r server/requirements.txt` completes successfully                                                                                                                                                |
| **Actual result**        | `ResolutionImpossible` — `mcp>=2.0.0` requires `pydantic>=2.12.0` but `requirements.txt` pinned `pydantic==2.10.5`                                                                                             |
| **Severity**             | High — blocks initial setup                                                                                                                                                                                    |
| **Workaround**           | Updated pins to `pydantic==2.13.5` and `pydantic-settings==2.15.0`                                                                                                                                             |
| **Proposed improvement** | The MCP SDK should print a clearer conflict message that names the conflicting package and the required version floor. Alternatively, document the pydantic version requirement in the SDK installation guide. |

### Friction 2: MCP server crashes on lowercase LOG_LEVEL

| Field                    | Value                                                                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| **Attempted task**       | Start the MCP server with `python -m server.mcp_server`                                                                        |
| **Expected result**      | Server starts and listens on `127.0.0.1:8001/mcp`                                                                              |
| **Actual result**        | `ValueError: Unknown level: 'info'` — Python's `logging.basicConfig()` rejects lowercase level names                           |
| **Severity**             | Medium — crashes on startup if the environment sets `LOG_LEVEL=info` (common in shell configs)                                 |
| **Workaround**           | Added `.upper()` to the `os.getenv("LOG_LEVEL", "INFO")` call                                                                  |
| **Proposed improvement** | Document that `LOG_LEVEL` must be uppercase, or use `logging.getLevelNamesMapping()` which accepts both cases in Python 3.11+. |

### Friction 3: `streamable_http_app()` is undocumented

| Field                    | Value                                                                                                                                            |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Attempted task**       | Write an integration test that calls the MCP server through the protocol (initialize, tools/list, tools/call)                                    |
| **Expected result**      | Find a documented test factory or test client in the MCP Python SDK                                                                              |
| **Actual result**        | No testing documentation in the official guide. Found `streamable_http_app()` by reading `mcp/server/mcpserver.py` source code                   |
| **Severity**             | Medium — costs 30+ minutes of source-code reading                                                                                                |
| **Workaround**           | Used `mcp.streamable_http_app()` with Starlette `TestClient`                                                                                     |
| **Proposed improvement** | Add a "Testing your MCP server" section to the SDK guide that shows how to create a test app, initialize a session, list tools, and call a tool. |

### Friction 4: Tool errors lose domain context

| Field                    | Value                                                                                                                                                                               |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Attempted task**       | Call `send_practitioner_turn` via MCP with a `scenario_id` that conflicts with the session's scenario                                                                               |
| **Expected result**      | Client receives a structured error with status 409 and message "Session cannot switch scenarios"                                                                                    |
| **Actual result**        | Client receives a generic `UnexpectedToolError: Error executing tool send_practitioner_turn` — the 409 status and detail message are lost                                           |
| **Severity**             | Medium — makes debugging harder for the MCP client                                                                                                                                  |
| **Workaround**           | Made `scenario_id` optional (None) for non-start actions so the default value no longer triggers a false conflict                                                                   |
| **Proposed improvement** | Document a pattern for returning tool-level errors that preserve the domain error code and message, or add a `ToolError` result type that the SDK serializes into the MCP response. |

### Friction 5: Docker DNS rebinding protection blocks host requests

| Field                    | Value                                                                                                                                                                   |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Attempted task**       | Run the MCP server in Docker and call it from the host                                                                                                                  |
| **Expected result**      | `curl http://127.0.0.1:8001/mcp` returns the `initialize` response                                                                                                      |
| **Actual result**        | `Invalid Host header` — `TransportSecuritySettings` rejects the request because the container's allowed hosts don't include the host's `127.0.0.1`                      |
| **Severity**             | Low — easily worked around                                                                                                                                              |
| **Workaround**           | Set `MCP_HOST=0.0.0.0` and `MCP_ALLOWED_HOSTS=0.0.0.0:*,127.0.0.1:*,localhost:*` in the Dockerfile                                                                      |
| **Proposed improvement** | Document the Docker deployment pattern including the required `MCP_ALLOWED_HOSTS` override, or provide a `--docker` preset that configures sensible container defaults. |

---

## References

[1]: https://amazonappdev2026.devpost.com/rules "Build, Ship, Shape: Amazon Developer Hackathon Official Rules"
[2]: https://modelcontextprotocol.io/docs/2026-07-28/develop/build-server "Model Context Protocol: Build an MCP Server"
[3]: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports "Model Context Protocol: Transports — Streamable HTTP"
