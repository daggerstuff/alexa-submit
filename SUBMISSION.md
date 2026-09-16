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
> exposing five agent-callable tools — `list_simulation_scenarios`,
> `start_simulation`, `send_practitioner_turn`, `evaluate_simulation`, and
> `end_simulation`. Alexa+ supplies the voice (ASR/TTS) and the conversation
> loop; the MCP server supplies the patient, the scenario rules, and the
> scoring.
>
> **How it works:**
> - **Twelve authorable scenarios** spanning basic→advanced difficulty (chest
>   pain, abdominal pain, depression screening, migraine, back pain, syncope, a
>   diabetic chest-pain case, suicide-risk screening, pediatric fever, stroke
>   FAST, medication reconciliation, and alcohol screening), each with a
>   clinical goal, a patient persona, disclosure rules, safety terms, and a
>   scoring rubric.
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
> - **Optional LLM persona** (Featherless Qwen or Amazon Bedrock Converse) with
>   JSON-mode responses, a tolerant parser, automatic retry, and a deterministic
>   fallback.
> - **Production posture:** bearer/API-key auth, per-IP rate limiting, idle TTL
>   with a bounded session cache, optional SQLite persistence, structured JSON
>   logging, and Prometheus metrics — deployed on AWS (ECR + App Runner).
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
- **File:** `demo-v2.mp4` (1:42, 1080p30) — opens with the problem, then shows a
  live MCP flow: `tools/list` → scenario library → `start_simulation` → a
  four-turn chest-pain conversation → graded evaluation (11/20 + spoken
  takeaway) → the dismissal safety boundary → `end_simulation`.
- **Upload checklist:** YouTube or Vimeo, **public**, under 3 minutes, English.
  Suggested title: *"Clinical Conversation Coach — Alexa+ MCP demo"*.
  Suggested description: *"An Alexa+ self-hosted MCP server that turns Alexa+
  into a simulated patient for safe, repeatable clinical-conversation practice.
  Built for the Amazon AppDev 2026 hackathon (Alexa+ track)."*

### Gallery images (for the Devpost media section)

Four 1080p stills extracted from the final render are committed to
`assets/gallery/` for the submission gallery:

| File | Beat |
| --- | --- |
| `assets/gallery/01-problem.png` | The problem card ("rehearse hard conversations on real patients") |
| `assets/gallery/02-scenarios.png` | `list_simulation_scenarios` → the scenario library |
| `assets/gallery/03-evaluation.png` | `evaluate_simulation` → evidence-linked rubric (11/20) |
| `assets/gallery/04-safety.png` | The dismissal safety boundary (`safety_flags: ["go home"]`) |

Regenerate them from `demo-v2.mp4` with
`ffmpeg -ss <seconds> -i demo-v2.mp4 -frames:v 1 assets/gallery/<n>-<name>.png`.

---

## 7. "Existed before" — significant update explanation

> This repository existed before the hackathon window as a local FastAPI
> clinical-simulation prototype (a mock `/alexa` passthrough and a deterministic
> patient Q&A, with no MCP surface and no deployment). The significant update
> made during the submission period is the Alexa+ integration itself:
>
> - A self-hosted MCP server (`server/mcp_server.py`) implementing MCP
>   `2025-11-25` over Streamable HTTP, exposing five tools.
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
> - An optional LLM patient persona (Featherless `Qwen/Qwen2.5-14B-Instruct` or
>   Amazon Bedrock Converse) with JSON-mode responses, tolerant parsing,
>   automatic retry, and a deterministic fallback.
> - Bearer/API-key auth and proxy-safe per-IP rate limiting.
> - Session lifecycle controls, a bounded cache with LRU eviction, and optional
>   SQLite persistence.
> - Twelve authorable scenarios across basic/intermediate/advanced difficulty.
> - Observability (`/health`, `/ready`, `/metrics`), CI, and an automated deploy
>   pipeline (GitHub Actions → ECR → App Runner).

(The pre-existing mock passthrough and placeholder skill config were removed;
the MCP server, evaluator, security layer, LLM persona, deployment, and docs
were added during the window.)

---

## 8. Open Source mini-challenge

- **Contribution URL:** https://github.com/daggerstuff/alexa-submit
- **Project repository URL:** https://github.com/daggerstuff/alexa-submit
- **GitHub username:** daggerstuff
- **What was done:** built a self-hosted MCP server (MCP `2025-11-25`,
  Streamable HTTP) exposing a clinical-communication simulation as five
  agent-callable tools, with a versioned evidence-linked evaluator, twelve
  authorable scenarios, cross-session learner progress, an optional LLM patient
  persona, and security + persistence.
- **How it works:** the five tools run over `/mcp`; each session holds scenario
  state and a transcript; the patient is scenario-constrained; evaluation
  returns rubric scores with transcript evidence.
- **Why it matters:** repeatable, safe, evidence-linked interview practice for
  clinical learners, and a stateful multi-tool Alexa+ workflow.

---

## 9. AWS Builder mini-challenge — services used & how

- **Amazon Bedrock** — optional LLM patient persona via the Converse API
  (`bedrock-runtime`), selected with `INFERENCE_PROVIDER=bedrock`
  (`BEDROCK_MODEL_ID` + AWS credentials). See `server/agents/llm_persona.py`.
- **Amazon ECR** — container image registry for the deploy pipeline.
- **AWS App Runner** — managed hosting for the public `/mcp` endpoint
  (`apprunner.yaml`, `scripts/deploy_aws.sh`).
- **GitHub Actions** — CI (lint + test) and the ECR/App Runner deploy pipeline.

Full "what worked / what needs work / onboarding / build again" answers are in
[`PRODUCT_FEEDBACK.md`](PRODUCT_FEEDBACK.md).

---

## 10. Product feedback, feature requests, friction log

All three submission artifacts live in
[`PRODUCT_FEEDBACK.md`](PRODUCT_FEEDBACK.md):

- **Product feedback** answers every required question for each tool/API/SDK:
  which tools and for what, what worked well, what needs work, onboarding
  experience (zero → hello world), and would-we-build-again (Yes/No + why).
- **Feature requests** carry the required priority rating
  (Critical / Important / Nice-to-have).
- **Friction log** (8 entries) includes the required fields — task attempted,
  steps taken, expected vs. actual result, severity, workaround, and actionable
  suggestion — for the up-to-10% Stage One bonus.

---

## 11. Testing instructions for judges

**Local (no keys required — deterministic path):**

```bash
./scripts/initialize.sh
./scripts/start_mcp_server.sh        # http://127.0.0.1:8001/mcp
.venv/bin/pytest                     # 74 tests, incl. full MCP-protocol flow + learner progress
```

**Live (auth-protected):**

- Endpoint: `https://9jj4zdyhu2.us-east-2.awsapprunner.com/mcp`
- The endpoint requires an `MCP_API_KEY` (not published in the repo). The demo
  video shows the live flow end-to-end; the unauthenticated local path above is
  fully functional for judging and testing.