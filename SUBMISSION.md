# Submission Guide — Amazon AppDev 2026

This file is the fill-in-the-form companion for the Devpost submission
(**amazonappdev2026.devpost.com**, deadline **Oct 23, 2026 @ 12:00 pm PDT**).
Copy the ready-to-paste blocks below into the matching "Enter a Submission"
fields. Everything here is also committed to the repo so judges can trace every
claim.

---

## 1. Project title & tagline

- **Title:** Clinical Conversation Coach for Alexa+
- **Tagline:** Rehearse the hard conversations before they're with a real patient.

---

## 2. Primary track

**Alexa+** — self-hosted MCP server, implementing MCP `2025-11-25` over
Streamable HTTP.

---

## 3. Mini challenges

- **AWS Builder** — Amazon Bedrock (Converse API), Amazon ECR, AWS App Runner.
- **Open Source** — new public, MIT-licensed repository created during the
  hackathon window (details in §8).

---

## 4. Text description

> **Clinical Conversation Coach for Alexa+** turns Alexa+ into a simulated
> patient so clinicians, medical students, and communication coaches can
> rehearse difficult patient conversations — safely and repeatably — instead of
> practicing live on a real patient.
>
> **The problem:** hard conversations (acute chest pain, a depression
> screening, breaking bad news) are usually practiced for the first time on a
> real patient. There is no safe, repeatable way to rehearse the interview
> first.
>
> **What it is:** a self-hosted MCP server (MCP `2025-11-25`, Streamable HTTP)
> exposing six core agent-callable tools — `list_simulation_scenarios`,
> `start_simulation`, `send_practitioner_turn`, `evaluate_simulation`,
> `end_simulation`, and `validate_scenario` — plus gated authoring tools
> (`create_scenario`, `delete_scenario`). Alexa+ supplies the voice (ASR/TTS)
> and the conversation loop; the MCP server supplies the patient, the scenario
> rules, and the scoring.
>
> **How it works:**
> - **Fourteen authorable scenarios** spanning basic→advanced difficulty (chest
>   pain, abdominal pain, depression screening, migraine, back pain, syncope, a
>   diabetic chest-pain case, suicide-risk screening, pediatric fever, stroke
>   FAST, medication reconciliation, alcohol screening, panic attack, and
>   adolescent vaping), each
>   with a clinical goal, a patient persona, disclosure rules, safety terms, and
>   a scoring rubric.
> - **A browser-based Alexa+ voice simulator** (`GET /simulator`, served by the
>   same app): a split screen where the left pane is the voice experience —
>   animated Alexa+ orb, spoken practitioner turns via the Web Speech API,
>   patient replies read aloud with the same emotion→prosody mapping the server
>   uses for SSML — and the right pane is a live MCP inspector showing every
>   JSON-RPC call, the rapport meter, disclosed facts, and the rubric
>   checkboxes lighting up on evaluation. Judges can run a clinical scenario in
>   a browser in about 10 seconds with zero setup.
> - **Stateful sessions** hold scenario state and a transcript across turns; the
>   patient only discloses facts whose trigger terms appear in the learner's
>   question.
> - **Evidence-linked evaluation** grades each metric with partial credit and
>   shows exactly which words earned each point, then returns a spoken takeaway
>   telling the learner what to ask next.
> - **A safety boundary** flags dismissal language ("go home and rest") and
>   pushes back so learners don't normalize under-response to a potentially
>   serious presentation.
> - **Cross-session coaching:** an optional `learner_id` makes the coach remember
>   a learner across sessions — per-metric mastery, which skills improved, and a
>   recommended next focus — so Alexa+ can greet a returning learner and steer
>   their next practice session (a context-aware, state-across-sessions
>   workflow).
> - **An LLM patient persona on a provider chain** — Amazon Bedrock Converse
>   (with **Amazon Bedrock Guardrails** attached to every turn, and a safe
>   fallback to the deterministic persona when the guardrail intervenes) with
>   Cloudflare Workers AI as an OpenAI-compatible fallback — plus JSON-mode
>   responses, a tolerant parser, per-provider retry, and a deterministic
>   final fallback (`server/agents/llm_persona.py`).
> - **Production posture:** bearer/API-key auth, per-IP rate limiting, idle TTL
>   with a bounded session cache, optional SQLite persistence, structured JSON
>   logging, and Prometheus metrics — deployed on AWS (ECR + App Runner +
>   CloudWatch).
>
> **Why it matters:** it gives clinical education programs a repeatable,
> evidence-linked surface for practicing patient interviews, and it demonstrates
> a stateful multi-tool Alexa+ workflow that maintains learner state across
> sessions — not a single-turn Q&A bot.

---

## 5. Code repository & license

- **Repository URL:** https://github.com/daggerstuff/alexa-submit
- **License:** MIT (in the repo About section, plus `LICENSE` at the root).
- **Runtime technology hook:** the MCP server is imported and actually called in
  `server/mcp_server.py` (the `mcp` SDK's `streamable_http_app()` factory +
  `@mcp.tool()` registrations), not just named in the README.

---

## 6. Demonstration video

- **URL:** `<!-- PASTE YOUR PUBLIC YOUTUBE/VIMEO LINK HERE -->`
- **File:** `demo-v2.mp4` (1:20, 1080p30) — opens with the problem, then shows
  the project functioning on its intended interface **in the first 45
  seconds**: the `/simulator` voice experience (Alexa+ orb, spoken turns,
  rapport meter, disclosed facts, the graded rubric with 13/20 and the spoken
  takeaway), then the agent's protocol view: `tools/list` → the 14-scenario
  library → the dismissal safety boundary → `end_simulation`.
- **Upload checklist:** YouTube or Vimeo, **public**, under 3 minutes, English.
  Suggested title: *"Clinical Conversation Coach — Alexa+ MCP demo"*.
  Suggested description: *"An Alexa+ self-hosted MCP server that turns Alexa+
  into a simulated patient for safe, repeatable clinical-conversation practice,
  with a browser voice simulator served by the same server. Built for the
  Amazon AppDev 2026 hackathon (Alexa+ track)."*

### Gallery images (for the Devpost media section)

Four 1080p stills are committed to `assets/gallery/` for the submission
gallery. After re-rendering the updated video, regenerate them from the new
beats (timestamps from `demo-video/src/DemoVideo.tsx`):

| File | Beat | Suggested timestamp |
| --- | --- | --- |
| `assets/gallery/01-problem.png` | The problem card ("rehearse hard conversations on real patients") | ~0:04 |
| `assets/gallery/02-scenarios.png` | The simulator voice pane + MCP inspector mid-conversation | ~0:23 |
| `assets/gallery/03-evaluation.png` | The rubric checkboxes lighting up (13/20 + spoken takeaway) | ~0:38 |
| `assets/gallery/04-safety.png` | The dismissal safety boundary (`safety_flags: ["go home"]`) | ~1:08 |

Regenerate with
`ffmpeg -ss <seconds> -i demo-v2.mp4 -frames:v 1 assets/gallery/<n>-<name>.png`.

---

## 7. "Existed before" — significant update explanation

> This repository existed before the hackathon window as a local FastAPI
> clinical-simulation prototype (a mock `/alexa` passthrough and a deterministic
> patient Q&A, with no MCP surface and no deployment). The significant update
> made during the submission period is the Alexa+ integration itself:
>
> - A self-hosted MCP server (`server/mcp_server.py`) implementing MCP
>   `2025-11-25` over Streamable HTTP, exposing six core tools plus gated
>   authoring and analytics tools.
> - A stateful, scenario-constrained simulation engine with versioned,
>   evidence-linked rubric evaluation (partial credit + matched-term evidence).
> - A coaching loop that returns concrete next-step questions for metrics not yet
>   demonstrated, plus a spoken takeaway.
> - Cross-session learner progress: an optional `learner_id` persists per-metric
>   mastery, per-session improvement, and a recommended next focus across
>   sessions (with a gated `get_learner_progress` tool).
> - Cohort reporting: a gated `list_cohort_progress` tool aggregates per-learner
>   mastery and the metrics a cohort most often needs to work on, for
>   faculty/coach use.
> - Voice-tuned persona: the LLM patient persona is prompted and validated for
>   spoken delivery (short first-person sentences, no lists or role-break), with
>   a deterministic fallback when output would not read aloud naturally.
> - An optional LLM patient persona (Amazon Bedrock Converse or Cloudflare
>   Workers AI, tried as a fallback chain) with JSON-mode responses,
>   tolerant parsing, per-provider retry, and a deterministic fallback.
> - Bearer/API-key auth and proxy-safe per-IP rate limiting.
> - Session lifecycle controls, a bounded cache with LRU eviction, and optional
>   SQLite persistence.
> - Fourteen authorable scenarios across basic/intermediate/advanced difficulty.
> - Observability (`/health`, `/ready`, `/metrics`), CI, and an automated deploy
>   pipeline (GitHub Actions → ECR → App Runner).
> - A browser-based Alexa+ multimodal simulator served at `GET /simulator` by
>   the same app — voice input via the Web Speech API, prosody-matched TTS
>   from the server's own emotion→prosody table, and a live MCP inspector
>   pane showing every JSON-RPC call, the rapport meter, disclosed facts, and
>   the rubric.
> - Amazon Bedrock Guardrails wired into the primary persona execution path
>   (blanket `guardrailConfig`, pinned version, safe degradation on
>   intervention), plus the App Runner origin-allow-list pinning and
>   post-deploy warm-up probe that make the served simulator reliable.

(The pre-existing mock passthrough and placeholder skill config were removed;
the MCP server, evaluator, security layer, LLM persona, deployment, and docs
were added during the window.)

---

## 8. Open Source mini-challenge

- **Contribution URL:** https://github.com/daggerstuff/alexa-submit
- **Project repository URL:** https://github.com/daggerstuff/alexa-submit
- **GitHub username:** daggerstuff
- **What was done:** built a self-hosted MCP server (MCP `2025-11-25`,
  Streamable HTTP) exposing a clinical-communication simulation as six core
  agent-callable tools (plus gated authoring and analytics tools), with a
  versioned evidence-linked evaluator, fourteen authorable scenarios,
  cross-session learner progress, an optional LLM patient persona, and security
  + persistence.
- **How it works:** the core tools run over `/mcp`; each session holds scenario
  state and a transcript; the patient is scenario-constrained; evaluation
  returns rubric scores with transcript evidence.
- **Why it matters:** repeatable, safe, evidence-linked interview practice for
  clinical learners, and a stateful multi-tool Alexa+ workflow.

---

## 9. AWS Builder mini-challenge — services used & how

- **Amazon Bedrock** — the LLM patient persona via the Converse API
  (`bedrock-runtime`), first on the provider chain, selected with
  `INFERENCE_PROVIDER=bedrock` (`BEDROCK_MODEL_ID` + AWS credentials). See
  `server/agents/llm_persona.py`.
- **Amazon Bedrock Guardrails** — on the primary execution path: every
  Converse turn carries a blanket `guardrailConfig` (pinned numbered version,
  `trace: disabled`); a blocked turn (`stopReason: guardrail_intervened`) is
  counted in `bedrock_guardrail_interventions_total` and degrades to the
  deterministic persona. A guardrail is provisioned in the account
  (`clinical-persona-guardrail`, us-east-2, version 1 — verified with
  `ApplyGuardrail`: a jailbreak turn is blocked, clinical turns including
  suicide-risk screening pass) and is wired into the deploy pipeline via the
  `BEDROCK_GUARDRAIL_ID` secret. See `tests/test_llm_persona_bedrock.py` and
  `FRICTION_LOG.md` entry 4.
- **Live-persona note:** the live deployment currently runs the Cloudflare
  Workers AI provider because this AWS account's Bedrock model access is not
  yet enabled (a console-only step). The Bedrock + Guardrails path is fully
  wired, tested, and deploy-ready: enable model access for a model (e.g. a
  Qwen or Claude model in us-east-2), set the `BEDROCK_MODEL_ID` secret, and
  flip the `INFERENCE_PROVIDER` variable to `bedrock,cloudflare` — one
  deploy later the persona runs Bedrock-first with the guardrail on every
  turn, and Cloudflare remains the fallback.
- **Amazon ECR** — container image registry for the deploy pipeline.
- **AWS App Runner** — managed hosting for the public `/mcp` endpoint **and
  the `/simulator` voice page** (`apprunner.yaml`, `scripts/deploy_aws.sh`,
  which pins host + origin allow-lists to the service URL and runs a
  post-deploy `/ready` warm-up probe).
- **Amazon CloudWatch** — structured JSON request logs from App Runner plus
  the Prometheus `/metrics` surface (sessions, tool traffic, rate-limit and
  guardrail counters). The full architecture diagram is in
  `PRODUCT_FEEDBACK.md` ("AWS architecture").
- **GitHub Actions** — CI (lint + test) and the ECR/App Runner deploy pipeline.

Full "what worked / what needs work / onboarding / build again" answers are in
[`PRODUCT_FEEDBACK.md`](PRODUCT_FEEDBACK.md).

---

## 10. Product feedback, feature requests, friction log

All three submission artifacts live in the repo:

- **Product feedback** — [`PRODUCT_FEEDBACK.md`](PRODUCT_FEEDBACK.md) answers
  every required question for each tool/API/SDK: which tools and for what,
  what worked well, what needs work, onboarding experience (zero → hello
  world), and would-we-build-again (Yes/No + why), plus the exact AWS
  architecture (App Runner + Bedrock + Guardrails + CloudWatch).
- **Feature requests** carry the required priority rating
  (Critical / Important / Nice-to-have).
- **Friction log** — [`FRICTION_LOG.md`](FRICTION_LOG.md) is the canonical
  log: seven entries, each with the six required fields (task attempted,
  steps taken, expected vs. actual result, severity, workaround referencing
  the shipped code, and actionable suggestion), covering MCP Streamable HTTP
  edge cases, the `tools/list` schema weight, Bedrock Guardrail and
  Converse-streaming behavior in voice contexts, the App Runner cold start,
  and the GitHub OIDC trust break. An earlier deployment-infrastructure
  archive (11 rubric-formatted entries) is preserved in
  `PRODUCT_FEEDBACK.md`, for the up-to-10% Stage One bonus.

---

## 11. Testing instructions for judges

**Local (no keys required — deterministic path):**

```bash
./scripts/initialize.sh
./scripts/start_mcp_server.sh        # http://127.0.0.1:8001/mcp
# then open the voice simulator in a browser:
open http://127.0.0.1:8001/simulator # (or just visit http://127.0.0.1:8001/ — it redirects)
.venv/bin/pytest                     # 151 tests, incl. full MCP-protocol flow + SSE stream + simulator page
```

The simulator needs no setup: pick a scenario, press **Start**, and speak or
type practitioner turns (voice input uses the browser's Web Speech API;
Chrome/Edge recommended for the microphone).

**Live (auth-protected):**

- Endpoint: `https://9jj4zdyhu2.us-east-2.awsapprunner.com/mcp`
- Voice simulator: `https://9jj4zdyhu2.us-east-2.awsapprunner.com/simulator`
  — enter the `MCP_API_KEY` in the page's API-key field (it is stored locally
  in the browser and sent as `Authorization: Bearer` + `X-API-Key`).
- The endpoints require an `MCP_API_KEY` (not published in the repo). The
  demo video shows the live flow end-to-end; the unauthenticated local path
  above is fully functional for judging and testing.