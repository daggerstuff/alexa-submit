# Clinical Conversation Coach for Alexa+ — Complete Upgrade Plan

Scope: the `alexa-submit` repository and its deployed MCP server. Current state is a
working, 25-test, deployed v0.3.0 with three scenarios, deterministic + LLM patient
personas, a deterministic rubric evaluator, and an in-memory session store.

Priorities: **P0** correctness/safety · **P1** quality/fidelity · **P2** product/integration
· **P3** delivery/polish. Each item names the file and the specific defect or gap.

---

## P0 — Correctness & safety (do first)

### 1. Fix the LLM-fallback double turn-count
`server/agents/llm_persona.py:58` increments `state.turn_count` inside `_llm_respond`
*before* the HTTP call; on failure `respond()` falls back to
`server/agents/patient_persona.py:27`, which increments it *again*. One failed LLM turn
= two turns. Move the increment out of the persona agents into the orchestrator
(`server/main.py:113`) so the turn is counted exactly once regardless of which agent
answered.

### 2. Session lifecycle: TTL, eviction, cap
`server/main.py:41-48` keeps every session forever in a plain dict. A public endpoint
with no expiry is an unbounded-memory leak, and `processed_events` (idempotency cache)
grows per unique `client_event_id` with no bound. Add: per-session TTL (env-driven, e.g.
`SESSION_TTL_SECONDS`), a max-session cap with LRU eviction, and an idle/absolute expiry
check on `handle()`.

### 3. Rate limiter + auth hardening
- `server/mcp_server.py:168-172` trusts the **first** `x-forwarded-for` hop, which a
  client can spoof when the proxy appends rather than overwrites. Key on the
  rightmost-trusted hop (or pin App Runner/ALB to overwrite XFF) and document it.
- The limiter is per-process in-memory; either enforce single-worker (document it) or
  back it with a shared store when scaling past one worker.
- `server/mcp_server.py:159` compares the bearer key with `!=` — use
  `hmac.compare_digest` for constant-time comparison.

### 4. LLM persona: schema-enforced output + retry
`server/agents/llm_persona.py:143` does `json.loads(raw)` and treats any non-JSON as a
hard failure → silent fallback to the deterministic agent. Add: request
`response_format={"type":"json_object"}` (Featherless/Qwen supports it), a tolerant
parse (strip prose fences), one retry, and log *why* the fallback fired instead of only
a warning line.

### 5. CI: tests + lint on push
There is no `.github/workflows/`. Add a minimal workflow: `ruff check server tests` +
`pytest -q` on push/PR, on the pinned Python 3.13.

---

## P1 — Quality & fidelity

### 6. Graded evaluator instead of binary max-or-1
`server/agents/clinical_evaluator.py:19-29` scores a metric `max_score` if *any*
trigger term matches, else `1`. "Where is the pain?" earns the same 4/4 as a full
characterization. Add partial credit: score by count/distinct-evidence bands (0–max),
keep the matched practitioner turn as evidence, and add a per-metric `matched_terms`
field so the rationale is self-explanatory.

### 7. Scenarios and rubrics as data, not 330 lines of dataclasses
`server/scenarios.py` hardcodes three scenarios. Move each `ScenarioDefinition` to a
versioned JSON/YAML file with load-time validation (pydantic), so non-engineers can
author scenarios and rubrics and version them independently of code. Keep the current
three as the seed fixtures.

### 8. Single source of truth for the product version
`0.3.0` is hardcoded in `server/mcp_server.py:22`, `server/main.py:138`, and
`package.json`. Centralize (a `server/_version.py` or `[project] version` in
`pyproject.toml`) and read it everywhere.

### 9. Session persistence + session management tools
Optional but valuable: SQLite-backed sessions (survive restart, App Runner
redeploys kill all sessions today). Then add `list_sessions` / `delete_session` MCP
tools — gated so a session list is only exposed when explicitly enabled, since it
leaks session IDs to any API-key holder.

### 10. Observability
Structured JSON logs, propagate the `request_id` from `SimulationResponse` into logs,
split `/health` (liveness) from a `/ready` (readiness), and add `/metrics` (request
count, rate-limit 429s, active sessions, LLM fallback count).

### 11. Packaging
`pyproject.toml` holds only ruff config — the server isn't installable. Add a
`[project]` block (name, version, deps, `server` entry points) and commit a
`uv.lock`; keep `requirements.txt` for the Docker image but generate it from the lock.

---

## P2 — Product & integration

### 12. Resolve the stale Alexa path
`alexa_config/skill.json` is a leftover: old name ("Clinical Simulation Node"),
placeholder tunnel URL, and `/alexa` is a "development passthrough". The submission is
the **MCP** path, which satisfies the rules. Decide: build a real Alexa skill (ASK SDK
→ calls the MCP server) as a second surface, or **retire** `alexa_config/` + `/alexa`
and make MCP the sole, clearly-documented integration. Don't leave it ambiguous.

### 13. Back the "voice-first" claim
The pitch says voice-first, but the server is text-in/text-out with no TTS/ASR. Alexa+
provides the speech layer natively, so either (a) state that explicitly and demo
through Alexa+, or (b) add a TTS/ASR loop for a self-contained demo. Pick one; the
claim and the artifact must match.

### 14. Learner coaching loop
Beyond the rubric, add "next-step" guidance: for each unmet metric, return a concrete
suggested question or action derived from the metric's trigger terms. Small change to
the evaluator output, large demo value.

### 15. More scenarios + an authoring guide
Add 2–3 scenarios (e.g. medication counseling, breaking-bad-news) and a short
`SCENARIOS.md` authoring guide once item 7 lands.

---

## P3 — Delivery & polish

### 16. Automated deploy pipeline
Replace the manual `scripts/deploy_aws.sh` run with a GitHub Actions workflow
(build → ECR → update App Runner) on tag, pulling `MCP_API_KEY` / `INFERENCE_API_KEY`
from AWS Secrets Manager via `{{resolve:secretsmanager:…}}` / `asm-exec` (also closes
the secret-handling gap flagged in the workspace `AGENTS.md`).

### 17. Doc consolidation + generated tool reference
Nine markdown files is sprawl. Consolidate the redundant architecture docs, and add a
generated MCP tool reference (from `tools/list` schemas) so the tool surface is
documented from the source of truth.

### 18. Ship the submission
Publish `demo.mp4` to YouTube/Vimeo, fill the Devpost form (meaningful-update +
product-feedback + open-source fields are already drafted in `HACKATHON_STRATEGY.md`),
and submit.

---

## Explicitly not doing now

- **Redis / multi-instance scaling** — overkill for a hackathon; a single worker with
  SQLite + TTL (items 2, 9) covers the real risks.
- **Fine-tuning an evaluator model** — the deterministic, transparent rubric *is* the
  differentiator; replacing it with an opaque LLM score would weaken the submission.
- **Multi-tenant auth (per-user keys, OAuth)** — out of scope until there are real
  users; the single bearer key + rate limit is the right size for this stage.

---

**Suggested order of execution:** 1 → 5 → 2 → 3 → 4 (P0), then 6 → 7 → 8 (P1),
then 18 (unblocks submission), then 12 → 13 → 14 (P2), with 16/17 as time permits.