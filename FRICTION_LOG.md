# Friction Log — Clinical Conversation Coach (Amazon AppDev 2026)

This is the canonical friction log for the submission. Every entry follows the
six required fields: **(1) specific task attempted, (2) exact steps taken,
(3) expected vs. actual result, (4) severity, (5) workaround used — referencing
the shipped code, (6) actionable suggestion** for the Amazon/MCP engineering
teams. Per the official rules, structured friction logs can contribute a
bonus of up to 10% during Stage One downselection [1].

The entries are ordered by surface: MCP Streamable HTTP (2), Alexa+/tool
schemas (1), Amazon Bedrock (2), AWS App Runner (1), AWS IAM/OIDC (1). Earlier
deployment-infrastructure entries (the `aws login` session expiry, the
App Runner `Port`-as-string quirk, the silent-rollback trap, ECR tag reuse,
region/credential alignment, and others) remain in the rubric-formatted
archive in
[`PRODUCT_FEEDBACK.md`](PRODUCT_FEEDBACK.md#friction-log-deployment-archive).

---

## 1. Streamable HTTP rejects our own served browser client until its Origin is allow-listed

| Field | Value |
| --- | --- |
| **Task attempted** | Serve a browser-based simulator page (`GET /simulator`) from the same Starlette app that serves `/mcp`, and let it drive the full MCP flow with `fetch()` — the "clearly show it working" requirement for the simulated-experience path. |
| **Steps taken** | 1. Serve the page from the MCP app's public-route wrapper (`server/mcp_server.py`, `_with_public_pages`). 2. From the page, POST `initialize` to `/mcp` on the same origin (`server/simulator.py`, `initializeRaw`). 3. Deploy to App Runner with `MCP_ALLOWED_ORIGINS=http://127.0.0.1:*,http://localhost:*`. |
| **Expected result** | A same-origin browser client is accepted; DNS-rebinding protection targets *cross-origin* attackers, so a page served by the app itself should pass without extra configuration. |
| **Actual result** | Browsers attach an `Origin` header to **same-origin POST fetches**, and the SDK's `TransportSecurityMiddleware` rejects any Origin not in `allowed_origins` with **403 "Invalid Origin header"** (`mcp/server/transport_security.py`). The page worked on `127.0.0.1` (which matched the default allow-list) and failed on the real App Runner URL — the failure only appeared in the deployed environment. |
| **Severity** | High — the browser simulator (and any web-served voice adapter) is unusable on the public deployment until fixed; nothing failed locally. |
| **Workaround used** | `scripts/deploy_aws.sh` now pins `MCP_ALLOWED_ORIGINS` to the service URL in the same step that pins `MCP_ALLOWED_HOSTS` (`source_config_json … "https://$SERVICE_HOST"`), and the page's client transparently re-initializes on 404 session errors (`server/simulator.py`, `post()`). `apprunner.yaml` documents the same-lists-both rule. |
| **Actionable suggestion** | Document a "serving a first-party web client" pattern in the Streamable HTTP security guidance — either a documented `allowed_origins: ["self"]` shorthand or an explicit note that same-origin POST `fetch()` always carries `Origin`. Discovering this required reading the middleware source, after a deployed-only failure. |

## 2. Stateful sessions silently expire in 30 minutes — mid-practice, not mid-request

| Field | Value |
| --- | --- |
| **Task attempted** | Keep a voice practice session usable across the natural pauses of clinical teaching: a learner can pause between turns for minutes (or a coach can step away and return), then continue the same encounter. |
| **Steps taken** | 1. Start a stateful session (`stateless_http=False`, `Mcp-Session-Id` returned by `initialize`). 2. Leave the session idle for the SDK's default window (30 minutes; `DEFAULT_SESSION_IDLE_TIMEOUT` in `mcp/server/streamable_http_manager.py`). 3. Send the next `tools/call` with the stored session id. |
| **Expected result** | Either the session is still valid, or the client gets a typed, discoverable signal that it must re-initialize before its next call. |
| **Actual result** | The manager closes the idle session and the next request returns **404 "unknown or expired session ID"** — the transport session and its id are gone, with no notice at expiry time and no way to learn the timeout from the `initialize` result. A voice client that cached the session id speaks an error instead of continuing the encounter. |
| **Severity** | Medium — intermittent and only reproducible by waiting; worse for voice UX than for interactive clients, because the failure surfaces as a broken conversation. |
| **Workaround used** | The clinical encounter is deliberately keyed by an application-level `session_id` (stable across MCP sessions, `server/main.py`), so an MCP re-initialize with the same id resumes the exact transcript, rapport, and disclosed facts — optionally persisted across restarts via `SESSION_DB_PATH`. The simulator page auto-detects the 404, re-initializes once, and retries the call (`server/simulator.py`, `post()`), so the learner never notices. |
| **Actionable suggestion** | Expose the negotiated idle timeout (or an `expires` hint) in the `initialize` response so clients can re-initialize proactively, and document the 404-on-expiry behavior as part of the Streamable HTTP spec's session lifecycle section. |

## 3. `tools/list` ships ~30 KB of Pydantic schema before the first turn is spoken

| Field | Value |
| --- | --- |
| **Task attempted** | Give an Alexa+ agent a compact, low-latency tool surface: the agent discovers six tools, then runs a scenario. |
| **Steps taken** | 1. Register six tools with `@mcp.tool(structured_output=True)` returning typed Pydantic models (`server/mcp_server.py`). 2. Measure the wire cost of discovery by calling `tools/list` through the transport and summing the response (the discovery flow is exercised end-to-end in `tests/test_mcp_protocol.py`). |
| **Expected result** | A tool listing scales with the tool *inputs* (short strings) plus a brief description of the result shape. |
| **Actual result** | Measured **30,628 bytes** for the six-tool `tools/list` response, of which **29,477 bytes (96%) is JSON Schema**. The largest single tool, `send_practitioner_turn`, weighs 7,346 bytes because its `structuredContent` schema embeds the full nested `SimulationResponse` — transcript turns, evaluation metrics, evidence, coaching, learner progress — recursively described on a tool whose arguments are two short strings. An agent pays this discovery cost on every session before a single clinical turn, and the schema competes with conversation history for prompt budget. |
| **Severity** | Medium — a schema-serialization latency and token-budget cost on every agent session; scales linearly as tools are added. |
| **Workaround used** | Kept tool *inputs* deliberately tiny (short validated strings — `server/mcp_server.py` tool signatures), moved all rich structure into responses, and gave the browser simulator a first-class inspector that renders the same calls compactly (`server/simulator.py`) so the payload is a feature for humans and a known cost for agents. |
| **Actionable suggestion** | Offer schema compression options in the MCP Python SDK: progressive disclosure (a `results` URL or a `tools/list` variant that omits `outputSchema` until requested), or a shared `$defs` block to deduplicate the nested models that repeat across every tool. |

## 4. A Bedrock Guardrail block surfaces as *missing content*, not as an error

| Field | Value |
| --- | --- |
| **Task attempted** | Apply a Bedrock Guardrail to every persona turn on the primary path — the scenario library legitimately discusses suicide risk, chest pain, and addiction, so the guardrail (not the prompt) is the safety net for a jailbreak or an off-script turn. |
| **Steps taken** | 1. Configure a guardrail in the Bedrock console with content filters and a pinned numbered version (never `DRAFT`). 2. Set `BEDROCK_GUARDRAIL_ID`/`BEDROCK_GUARDRAIL_VERSION`; `server/agents/llm_persona.py` attaches blanket `guardrailConfig` to every Converse call (`_build_bedrock_request`). 3. Probe with an input that trips the guardrail. |
| **Expected result** | A typed, catchable "guardrail intervened" signal from boto3, like the typed exceptions other services raise. |
| **Actual result** | The call *succeeds* HTTP-wise: `stopReason` becomes `guardrail_intervened` and the `output.content` list is empty. The pre-fix code path `response["output"]["message"]["content"][0]["text"]` then dies with `IndexError` — an unrelated-looking crash that says nothing about the guardrail. The only way to learn *which* filter fired is enabling `trace`, which returns the offending content in the API response and is therefore unusable in production for a clinical workload. |
| **Severity** | High — a safety control that fails as a confusing crash invites developers to remove it; and without trace there is no production-safe way to distinguish "blocked by policy" from "model glitch". |
| **Workaround used** | `_complete_bedrock` (`server/agents/llm_persona.py`) now checks `stopReason` and empty content explicitly, counts `bedrock_guardrail_interventions_total` in the Prometheus registry, and raises a named error; the provider chain degrades to the deterministic, scenario-constrained persona so the learner's session continues inside its safety envelope. `trace` defaults to `"disabled"` and logs a warning when overridden. Covered by `tests/test_llm_persona_bedrock.py`. |
| **Actionable suggestion** | Have boto3 raise a typed `GuardrailIntervenedError` (with the intervention *category*, without the matched content) when `stopReason == "guardrail_intervened"`, and document the guardrail interruption response shape in the Converse API reference — including a production-safe summary that does not require `trace: enabled`. |

## 5. Streaming tokens cannot be spoken: Converse has no structured output, so the voice path is all-or-nothing

| Field | Value |
| --- | --- |
| **Task attempted** | Make the persona's reply feel conversational on voice: start speaking as soon as the patient's first sentence is available. |
| **Steps taken** | 1. Evaluate `ConverseStream` for the persona. 2. Compare with the non-streaming `Converse` path in `_complete_bedrock` (`server/agents/llm_persona.py`). 3. Bound the reply for latency (`maxTokens: 300`) and timeouts (`INFERENCE_TIMEOUT=15`). |
| **Expected result** | Streaming gives first-audio advantage for a voice persona, the way it does for chat UIs. |
| **Actual result** | The persona's contract is a single JSON envelope (`{"content", "emotional_state", "disclosed_facts"}`), and Converse has no JSON/structured-output mode — the shape is prompt-driven. Streamed tokens are *fragments of JSON*, unparseable (and unspeakable) until the object completes, so `ConverseStream` delivers bytes but no speakable audio any earlier. The emotion-driven prosody wrapper (`server/voice.py`, `speak()`) also needs the full sentence to choose rate/pitch. |
| **Severity** | Medium — a voice-latency ceiling of one model round-trip per turn (~1–3 s with a 300-token cap), not a correctness bug. |
| **Workaround used** | Keep non-streaming `Converse` (simpler error handling, exact quota reservation via `maxTokens`), cap replies at 300 tokens and ~35 words via the system prompt's voice rules, and return pre-rendered SSML (`ssml`, `spoken_summary`) so any TTS adapter — Polly, Nova Sonic, or the browser's `speechSynthesis` in `server/simulator.py` — starts speaking immediately on receipt. |
| **Actionable suggestion** | Add a first-class structured-output mode to Converse/ConverseStream (the OpenAI-compatible surface on `bedrock-mantle` has one; Converse does not). Combined with per-sentence stream events, a voice persona could then emit speakable SSML chunks as they complete — and sync-mode guardrails would still hold for compliance-sensitive turns. |

## 6. The first request after an App Runner update can land on a cold instance

| Field | Value |
| --- | --- |
| **Task attempted** | Deploy a new image and hand judges (and Alexa+) an endpoint whose *first* interaction is as fast as its hundredth — voice turns make cold-start latency audible. |
| **Steps taken** | 1. Push a uniquely tagged image to ECR and call `update-service` (`scripts/deploy_aws.sh`). 2. Poll `describe-service` until `RUNNING` plus the latest operation `SUCCEEDED`. 3. Immediately open a new MCP session and run the first `tools/call`. |
| **Expected result** | `RUNNING` means the new revision is serving requests at full speed. |
| **Actual result** | The first request(s) after an update can land on an instance that is still starting its Python process — importing the MCP SDK, building the Pydantic tool schemas (see entry 3), and loading 14 scenarios — so the first `initialize` observes a multi-second tail the steady state never shows. `describe-service` reports `RUNNING` either way, so the deploy pipeline alone cannot detect the warm-up gap. |
| **Severity** | Low–Medium — a one-time latency penalty per deployment/scale-out, but it lands exactly on the first impression (a judge's first click, or the first spoken turn of a session). |
| **Workaround used** | `scripts/deploy_aws.sh` now probes `GET /ready` after the update settles (warm-up loop after `wait_for_running`), so the pipeline itself absorbs the cold start; the client side already has adaptive retries (boto3 `Config(retries=…, mode="adaptive")`) and the simulator re-initializes transparently on 404s. |
| **Actionable suggestion** | Let App Runner mark a service "ready" only after a configurable readiness probe passes on a *new* instance (or expose a first-request-metric in CloudWatch), so deploy tooling — and not the first user — pays the cold start. |

## 7. GitHub OIDC → IAM trust broke twice: the `sub` claim changed shape and the provider thumbprint rotated

| Field | Value |
| --- | --- |
| **Task attempted** | Let the GitHub Actions deploy pipeline (`.github/workflows/deploy.yml`) assume an IAM role via OIDC — no long-lived AWS keys in CI. |
| **Steps taken** | 1. Create an IAM OIDC provider for `token.actions.githubusercontent.com` with the documented thumbprint. 2. Write the role trust policy with `sub: repo:owner/repo:*` and `aud: sts.amazonaws.com`. 3. Push, and let the workflow call `sts:AssumeRoleWithWebIdentity`. |
| **Expected result** | The documented trust policy matches GitHub's token and the role is assumed. |
| **Actual result** | Two independent failures. (a) `AssumeRoleWithWebIdentity` was denied with the trust policy seemingly correct: the live token's `sub` claim now embeds owner/repo ids (`repo:owner@<id>/repo@<id>:ref:…`), which the documented `repo:owner/repo:*` condition silently stops matching. (b) The stored provider thumbprint no longer matched, because GitHub's token endpoint had rotated to a different certificate chain, so STS rejected the provider itself. Each failure surfaced as a generic "not authorized to perform sts:AssumeRoleWithWebIdentity" with no hint of which of the two mechanisms failed. |
| **Severity** | High — blocked every deploy; multi-hour diagnosis because the error message does not distinguish "token claims didn't match the trust policy" from "provider verification failed". |
| **Workaround used** | Decode the *live* token (its JWT payload) and write the condition against the actual `sub`/`aud` format; recompute the TLS chain thumbprints (root + intermediate + leaf) for the provider; pin `sub` by the workflow's exact ref path rather than a broad wildcard. |
| **Actionable suggestion** | In the STS error for `AssumeRoleWithWebIdentity`, distinguish claim-mismatch from provider-trust failure (e.g., "trust policy `sub` condition did not match token claim"), and document in the IAM OIDC provider guide that GitHub's `sub` format embeds numeric ids and that thumbprints must be re-verified when the IdP rotates certificates. |

---

## Net

Two themes repeat across these seven entries. **Failure surfaces far from its
cause**: a 403 Origin rejection appears only once deployed (1), a guardrail
block appears as an `IndexError` (4), an OIDC claim-format change appears as a
generic deny (7), and a cold instance appears as a slow first request (6).
And **discovery payloads and session lifecycle are invisible contracts**: the
30 KB schema bill (3) and the silent 30-minute session expiry (2) are both
behaviors a builder only learns by measuring or by being woken by them. In
every case the fix was an explicit, test-covered workaround in this repo —
and in every case a small platform-side signal (a typed error, a documented
hint, a readiness probe) would have removed the hunt entirely.

## References

[1]: https://amazonappdev2026.devpost.com/rules "Build, Ship, Shape: Amazon Developer Hackathon Official Rules"
[2]: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports "Model Context Protocol: Transports — Streamable HTTP"
