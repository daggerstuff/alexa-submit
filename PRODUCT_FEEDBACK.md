# Product Feedback and Friction Log

## Amazon AppDev 2026 — Alexa+ Track

This document satisfies the product-feedback and friction-log submission requirements. The rules state that friction-log entries can contribute a bonus of up to 10% during Stage One downselection [1].

---

## Tools used

| Tool                   | Version    | Purpose                                       |
| ---------------------- | ---------- | --------------------------------------------- |
| Python MCP SDK (`mcp`) | 2.2.0      | Self-hosted MCP server over Streamable HTTP   |
| MCP protocol           | 2025-11-25 | Transport specification version               |
| FastAPI                | 0.141.1    | HTTP exception types and Starlette `TestClient` |
| Pydantic               | 2.13.5     | Request/response validation and serialization |
| Uvicorn                | 0.52.4     | ASGI server for the MCP endpoint              |
| pytest                 | 9.1.1      | Test suite                                    |
| Ruff                   | 0.16.6     | Linting and formatting                        |
| Docker                 | —          | Containerized deployment for judges           |
| Python                 | 3.13.15    | Runtime                                       |
| AWS App Runner         | —          | Managed hosting for the public `/mcp` endpoint |
| AWS ECR                | —          | Container image registry                      |
| Amazon Bedrock         | —          | Optional LLM persona via Converse API (AWS Builder mini-challenge) |
| NVIDIA NIM             | —          | Optional OpenAI-compatible LLM persona fallback |
| Cloudflare Workers AI  | —          | Optional OpenAI-compatible LLM persona fallback |
| GitHub Actions         | —          | CI (lint + test) and deploy pipeline          |
| Remotion               | 4.0.484    | Demo video (synthetic terminal recording)     |
| ElevenLabs             | `eleven_v3`| Demo narration voice-over                     |

---

## What worked well

### MCP Python SDK

- The `MCPServer` class and `@mcp.tool()` decorator make tool registration concise and readable. Defining five tools with typed parameters and structured output took under 100 lines of code.
- The `streamable_http_app()` factory is testable with Starlette's `TestClient`, which let us write integration tests that exercise the full MCP protocol (initialize → initialized → tools/list → tools/call) without starting a separate process.
- `TransportSecuritySettings` with DNS rebinding protection, allowed hosts, and allowed origins is a sensible default for local development.
- The SDK correctly handles session negotiation via `MCP-Session-Id` headers. The test confirms that the server returns a session ID on `initialize` and accepts it on subsequent requests.

### Pydantic + FastAPI

- Pydantic v2 models made the simulation request/response contracts self-documenting. The `Field` constraints (min_length, max_length) catch malformed input before it reaches the orchestrator.
- FastAPI's `TestClient` (built on Starlette) gave us a full MCP-protocol test surface — initialize, tools/list, and tools/call — without starting a separate process.

### Docker

- The slim Python 3.13 image produces a ~150 MB container that starts in under 2 seconds. The MCP server responds to `initialize` immediately after startup.

### AWS (Bedrock + App Runner + ECR + GitHub Actions)

- Amazon Bedrock's Converse API gives the LLM persona one provider-agnostic request/response shape; a single `bedrock-runtime` client call covers text completion with explicit `maxTokens` and adaptive retry.
- The persona's provider chain (`bedrock`, `nim`, `cloudflare`) abstracts three backends behind one completion seam — Bedrock Converse plus two OpenAI-compatible `/chat/completions` hosts — so a provider outage degrades to the next configured provider instead of dropping to the deterministic script.
- App Runner took the container and gave us a TLS endpoint with no load-balancer or ingress configuration; the `/mcp` Streamable HTTP endpoint passed the full MCP flow on the first successful push.
- ECR with a unique tag per deploy made builds deterministic and rollback simple; a `latest`-style tag would have let stale images deploy silently.
- GitHub Actions runs lint and the test suite on push, and the deploy job builds the image, pushes to ECR, and updates App Runner in one pipeline.

### Remotion + ElevenLabs (demo)

- Remotion rendered a deterministic, pixel-perfect 1080p terminal recording with per-character typing and no live desktop capture. ElevenLabs `eleven_v3` produced natural narration from speech-normalized text (acronyms spelled out, punctuation-driven pacing).

---

## What needs improvement

### MCP Python SDK

1. **Pydantic version constraint is strict.** MCP 2.2.0 requires `pydantic>=2.12.0`. The original project pinned `pydantic==2.10.5`, which caused a silent resolution failure. The SDK should either loosen its floor or document the constraint more prominently in the installation guide.

2. **`streamable_http_app()` is not in the public API docs.** We found it by reading the SDK source. The official "Build an MCP Server" guide [2] shows `mcp.run()` but does not mention the test-app factory. A testing section in the docs would save significant time.

3. **Tool error handling had to be mapped by hand.** The MCP SDK wraps an uncaught tool exception in a generic `UnexpectedToolError`, which drops the domain status and message. We worked around it by catching `HTTPException` and re-raising a `ToolError` that preserves the message; a documented pattern (or a structured `ToolError` result type) would make this unnecessary.

4. **No built-in health endpoint in the SDK.** The MCP SDK ships no health or metadata route, so we hand-rolled unauthenticated GET `/health`, `/ready`, and `/metrics` around the Streamable HTTP app. A first-class health preset would remove that boilerplate.

### Alexa+ integration

5. **No Alexa+ MCP client documentation.** The hackathon rules describe the MCP server requirement, but there is no public documentation for how an Alexa+ agent discovers and calls MCP tools. We inferred the workflow (list scenarios → start → send turns → evaluate → end) from the MCP protocol spec, not from Alexa+ documentation.

6. **No Alexa+ local testing tool.** We could not find a mock Alexa+ MCP client for local development. The closest option was a raw MCP client using the Python SDK, which does not simulate the Alexa+ conversation UX (voice prompts, session management, spoken response formatting).

### AWS

7. **App Runner deploy has no dry-run or preview.** The only way to know whether a build/tag/region combination works is to push and watch the service update. A preview or validate step (or a clearer error when the tag already exists) would have saved two failed deploys.

8. **Region must match the `aws login` session exactly.** A mismatched region caused silent credential-refresh failures until the deploy region was aligned with the login profile. This should be surfaced as an explicit error rather than a generic refresh failure.

9. **Bedrock Converse has no native JSON-mode toggle.** The Converse API has no `response_format: json_object` equivalent; JSON output is prompt-driven. We rely on the persona's system prompt ("Return JSON only") plus a tolerant parser. A first-class structured-output option would remove the need.

---

## Would we build with this again?

**Yes.** The MCP Python SDK is the strongest part of the stack. The tool registration pattern is clean, the Streamable HTTP transport works, and the test infrastructure is solid. The main gaps are documentation (test app factory, error handling patterns, FastAPI mounting) rather than fundamental design problems.

We would also build with Pydantic again. Its models made the simulation contracts self-documenting, and the `Field` constraints catch malformed input before it reaches the orchestrator.

We would build with **Alexa+** again: voice-first clinical practice is a strong fit for the MCP tool surface, and the missing piece is local testing tooling rather than the platform itself. We would build with **AWS** again — App Runner + ECR gave a zero-config TLS deploy, and **Bedrock** is a clean swap-in for the persona when AWS is the deployment target; NIM and Cloudflare Workers AI cover the same role off-AWS.

---

## Onboarding experience

- **MCP Python SDK (zero → hello world):** a working `@mcp.tool()` server over Streamable HTTP came up in under an hour from the "Build an MCP Server" guide. Getting from "hello world" to "hello world with tests" was the real climb — the test factory (`streamable_http_app()`) is not documented, so we read SDK source to write protocol-level integration tests.
- **Alexa+:** there is no local Alexa+ MCP client simulator, so we onboarded against a raw MCP client plus the hosted endpoint. The protocol flow itself (initialize → tools/list → tools/call) was unambiguous.
- **AWS:** ECR push + App Runner deploy reached a working TLS `/mcp` endpoint in a single session; the friction was region/credential alignment and the unique-tag requirement, not the service model. Bedrock onboarding is a single `bedrock-runtime` Converse call once model access is enabled.

---

## Feature requests

| Priority     | Request                                           | Rationale                                                                    |
| ------------ | ------------------------------------------------- | ---------------------------------------------------------------------------- |
| Critical     | Document `streamable_http_app()` in the SDK guide | The test factory is essential for integration testing but undocumented       |
| Important    | Add tool-level error result pattern               | Allow tools to return structured errors without raising exceptions           |
| Important    | Support mounting MCP inside an existing ASGI app  | Simplify single-process deployment                                           |
| Nice-to-have | Add built-in `/health` endpoint option            | Container orchestration support                                              |
| Important    | Provide an Alexa+ MCP client simulator            | Reduce the gap between MCP server development and Alexa+ integration testing |

---

## Friction log

Each entry includes: specific task attempted, steps taken, expected vs. actual result, severity, workaround, and actionable suggestion.

### Friction 1: Pydantic version conflict blocks installation

| Field                    | Value                                                                                                                                                                                                          |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Attempted task**       | Install dependencies from `server/requirements.txt` in a fresh virtualenv                                                                                                                                      |
| **Steps taken**          | 1. Create a fresh virtualenv. 2. Run `pip install -r server/requirements.txt`. |
| **Expected result**      | `pip install -r server/requirements.txt` completes successfully                                                                                                                                                |
| **Actual result**        | `ResolutionImpossible` — `mcp>=2.0.0` requires `pydantic>=2.12.0` but `requirements.txt` pinned `pydantic==2.10.5`                                                                                             |
| **Severity**             | High — blocks initial setup                                                                                                                                                                                    |
| **Workaround**           | Updated pins to `pydantic==2.13.5` and `pydantic-settings==2.15.0`                                                                                                                                             |
| **Proposed improvement** | The MCP SDK should print a clearer conflict message that names the conflicting package and the required version floor. Alternatively, document the pydantic version requirement in the SDK installation guide. |

### Friction 2: MCP server crashes on lowercase LOG_LEVEL

| Field                    | Value                                                                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| **Attempted task**       | Start the MCP server with `python -m server.mcp_server`                                                                        |
| **Steps taken**          | 1. Export `LOG_LEVEL=info`. 2. Run `python -m server.mcp_server`. |
| **Expected result**      | Server starts and listens on `127.0.0.1:8001/mcp`                                                                              |
| **Actual result**        | `ValueError: Unknown level: 'info'` — Python's `logging.basicConfig()` rejects lowercase level names                           |
| **Severity**             | Medium — crashes on startup if the environment sets `LOG_LEVEL=info` (common in shell configs)                                 |
| **Workaround**           | Added `.upper()` to the `os.getenv("LOG_LEVEL", "INFO")` call                                                                  |
| **Proposed improvement** | Document that `LOG_LEVEL` must be uppercase, or use `logging.getLevelNamesMapping()` which accepts both cases in Python 3.11+. |

### Friction 3: `streamable_http_app()` is undocumented

| Field                    | Value                                                                                                                                            |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Attempted task**       | Write an integration test that calls the MCP server through the protocol (initialize, tools/list, tools/call)                                    |
| **Steps taken**          | 1. Search the SDK guide for a test client. 2. Read the `mcp/server/mcpserver.py` source. 3. Write a `TestClient` integration test. |
| **Expected result**      | Find a documented test factory or test client in the MCP Python SDK                                                                              |
| **Actual result**        | No testing documentation in the official guide. Found `streamable_http_app()` by reading `mcp/server/mcpserver.py` source code                   |
| **Severity**             | Medium — costs 30+ minutes of source-code reading                                                                                                |
| **Workaround**           | Used `mcp.streamable_http_app()` with Starlette `TestClient`                                                                                     |
| **Proposed improvement** | Add a "Testing your MCP server" section to the SDK guide that shows how to create a test app, initialize a session, list tools, and call a tool. |

### Friction 4: Tool errors lose domain context

| Field                    | Value                                                                                                                                                                               |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Attempted task**       | Call `send_practitioner_turn` via MCP with a `scenario_id` that conflicts with the session's scenario                                                                               |
| **Steps taken**          | 1. Start a session with `start_simulation`. 2. Call `send_practitioner_turn` with a conflicting `scenario_id`. 3. Inspect the MCP error payload. |
| **Expected result**      | Client receives a structured error with status 409 and message "Session cannot switch scenarios"                                                                                    |
| **Actual result**        | Client receives a generic `UnexpectedToolError: Error executing tool send_practitioner_turn` — the 409 status and detail message are lost                                           |
| **Severity**             | Medium — makes debugging harder for the MCP client                                                                                                                                  |
| **Workaround**           | Made `scenario_id` optional (None) for non-start actions so the default value no longer triggers a false conflict                                                                   |
| **Proposed improvement** | Document a pattern for returning tool-level errors that preserve the domain error code and message, or add a `ToolError` result type that the SDK serializes into the MCP response. |

### Friction 5: Docker DNS rebinding protection blocks host requests

| Field                    | Value                                                                                                                                                                   |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Attempted task**       | Run the MCP server in Docker and call it from the host                                                                                                                  |
| **Steps taken**          | 1. `docker build` the image. 2. `docker run -p 8001:8001`. 3. `curl http://127.0.0.1:8001/mcp`. |
| **Expected result**      | `curl http://127.0.0.1:8001/mcp` returns the `initialize` response                                                                                                      |
| **Actual result**        | `Invalid Host header` — `TransportSecuritySettings` rejects the request because the container's allowed hosts don't include the host's `127.0.0.1`                      |
| **Severity**             | Low — easily worked around                                                                                                                                              |
| **Workaround**           | Set `MCP_HOST=0.0.0.0` and `MCP_ALLOWED_HOSTS=0.0.0.0:*,127.0.0.1:*,localhost:*` in the Dockerfile                                                                      |
| **Proposed improvement** | Document the Docker deployment pattern including the required `MCP_ALLOWED_HOSTS` override, or provide a `--docker` preset that configures sensible container defaults. |

### Friction 6: AWS region mismatch breaks credential refresh

| Field                    | Value                                                                                                                                                     |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Attempted task**       | Run the deploy pipeline to build, push to ECR, and update App Runner in `us-east-2`                                                                        |
| **Steps taken**          | 1. Run `aws login`. 2. Run `scripts/deploy_aws.sh`. 3. Observe the `aws ecr` credential-refresh failure. |
| **Expected result**      | `aws ecr` and `aws apprunner` commands succeed with the logged-in profile                                                                                  |
| **Actual result**        | Credential-refresh failures because the deploy region did not match the `aws login` session region                                                          |
| **Severity**             | High — blocks every deploy until aligned                                                                                                                   |
| **Workaround**           | Aligned the deploy region with the `aws login` profile region in the deploy script                                                                         |
| **Proposed improvement** | Read the region from the AWS profile instead of a hardcoded value, and fail with an explicit "region mismatch" message rather than a generic refresh error. |

### Friction 7: Reusing a single ECR tag caused stale deploys

| Field                    | Value                                                                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| **Attempted task**       | Push a rebuilt image and update App Runner                                                                                      |
| **Steps taken**          | 1. Rebuild the image with the same tag. 2. Push to ECR. 3. Update App Runner and confirm the old image is still serving. |
| **Expected result**      | The new image is pushed and served                                                                                              |
| **Actual result**        | Pushing over a reused tag let the previous image persist, so the new build did not actually ship                                |
| **Severity**             | Medium — silently serves stale code                                                                                             |
| **Workaround**           | Generate a unique ECR tag per deploy and build the image with that tag                                                          |
| **Proposed improvement** | Fail or warn when pushing an image over an existing tag, or make unique-per-deploy tags the documented default.                |

### Friction 8: LLM persona returns malformed JSON

| Field                    | Value                                                                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| **Attempted task**       | Get a patient response from the Bedrock persona via the Converse API                                                           |
| **Steps taken**          | 1. Set `INFERENCE_PROVIDER=bedrock` with `BEDROCK_MODEL_ID`. 2. Call `send_practitioner_turn`. 3. Parse the persona's JSON response. |
| **Expected result**      | A single valid JSON object per turn                                                                                            |
| **Actual result**        | Occasional trailing prose or unescaped characters after the JSON object, which broke strict parsing                            |
| **Severity**             | Medium — intermittent persona failures                                                                                         |
| **Workaround**           | Added a tolerant parser that extracts the first JSON object, plus Bedrock's adaptive retry                                     |
| **Proposed improvement** | Bedrock should offer a first-class structured-output option for the Converse API so the parser never sees trailing text.      |

---

## References

[1]: https://amazonappdev2026.devpost.com/rules "Build, Ship, Shape: Amazon Developer Hackathon Official Rules"
[2]: https://modelcontextprotocol.io/docs/2026-07-28/develop/build-server "Model Context Protocol: Build an MCP Server"
[3]: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports "Model Context Protocol: Transports — Streamable HTTP"
