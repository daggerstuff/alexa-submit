# Clinical Conversation Coach for Alexa+

This repository is a local-development starter for a **scenario-based clinical communication simulator** exposed through a self-hosted MCP server for Alexa+. It helps learners practice structured patient interviews and receive transparent, evidence-linked feedback.

> **Educational safety boundary:** This project is not a medical device, diagnostic system, triage service, or substitute for supervised clinical education. Use synthetic scenarios only. Do not use it with real patient data or for real-time clinical decision-making.

## Amazon AppDev 2026 positioning

The project is designed for the **Alexa+ primary track** of the Amazon AppDev 2026 hackathon. It includes a self-hosted MCP server using the official Python MCP SDK and Streamable HTTP transport, with task-oriented tools for discovering scenarios, starting sessions, conducting practitioner turns, and requesting evaluation.

The hackathon requires an Alexa+ working Agent Skill or self-hosted MCP server using MCP version 2025-11-25 or later over Streamable HTTP. The repository also includes a conventional FastAPI development API for local testing, but the MCP server is the track-facing integration surface.

See [`HACKATHON_STRATEGY.md`](HACKATHON_STRATEGY.md) for the submission strategy, judging alignment, three-minute demo plan, product feedback template, and remaining checklist.

## Architecture

| Layer                | Responsibility                                           | Implementation                                 |
| -------------------- | -------------------------------------------------------- | ---------------------------------------------- |
| Alexa+/MCP transport | Expose agent-callable operations over Streamable HTTP    | `server/mcp_server.py`, `/mcp` on port 8001    |
| Development API      | Provide easy local REST testing                          | `server/main.py`, `/mcp/simulate` on port 8000 |
| Session              | Lifecycle, transcript, retries, and scenario consistency | `SimulationOrchestrator`                       |
| Scenario             | Facts, disclosure rules, safety terms, and rubric        | `server/scenarios.py`                          |
| Patient policy       | Stateful, scenario-constrained responses                 | `PatientPersonaAgent`                          |
| Evaluation policy    | Versioned scoring with transcript evidence               | `ClinicalEvaluatorAgent`                       |

## Quick start

```bash
chmod +x scripts/*.sh
./scripts/initialize.sh
source .venv/bin/activate
```

Start the development REST API:

```bash
uvicorn server.main:app --host 127.0.0.1 --port 8000 --reload
```

Start the Alexa+ MCP server in another terminal:

```bash
./scripts/start_mcp_server.sh
```

The script applies localhost binding, the `/mcp` path, and local host/origin allowlists by default. You can override them with `MCP_HOST`, `MCP_PORT`, `MCP_PATH`, `MCP_ALLOWED_HOSTS`, and `MCP_ALLOWED_ORIGINS`.

The MCP endpoint is `http://127.0.0.1:8001/mcp`. The development REST API is available at `http://127.0.0.1:8000`, with interactive documentation at `/docs`.

For a hosted development demo, put the MCP endpoint behind HTTPS and an authenticated reverse proxy. Do not expose the unauthenticated local server directly to the public internet.

## MCP tool surface

The MCP server exposes five agent-callable tools:

| Tool                        | Purpose                                                             |
| --------------------------- | ------------------------------------------------------------------- |
| `list_simulation_scenarios` | Lists scenario IDs, versions, titles, and rubric metric IDs         |
| `start_simulation`          | Starts a scenario and returns the patient opening response          |
| `send_practitioner_turn`    | Processes a learner utterance and returns the next patient response |
| `evaluate_simulation`       | Returns evidence-linked rubric feedback without ending the session  |
| `end_simulation`            | Returns the final evaluation and locks the session                  |

These tools are deliberately higher-level than internal REST routes. An Alexa+ agent can orchestrate a complete session without knowing the implementation details of transcript storage or scenario matching.

## Local REST flow

Start a session:

```bash
curl -s http://127.0.0.1:8000/mcp/simulate \
  -H 'content-type: application/json' \
  -d '{"session_id":"demo-1","action":"start","scenario_id":"chest-pain-basic"}'
```

Send a practitioner turn. Use `client_event_id` for retry-safe behavior:

```bash
curl -s http://127.0.0.1:8000/mcp/simulate \
  -H 'content-type: application/json' \
  -d '{"session_id":"demo-1","action":"message","client_event_id":"turn-1","practitioner_message":"My name is Alex. Where is the pain, are you short of breath, and what medications do you take?"}'
```

Evaluate the session:

```bash
curl -s http://127.0.0.1:8000/mcp/simulate \
  -H 'content-type: application/json' \
  -d '{"session_id":"demo-1","action":"evaluate"}'
```

## Scenario and evaluator model

`server/scenarios.py` is the scenario registry. Each `ScenarioDefinition` contains a stable scenario ID, version, opening statement, disclosure rules, safety terms, and rubric metrics.

`PatientPersonaAgent` applies disclosure rules to the active scenario and tracks disclosed facts and emotional state. An optional LLM-backed adapter (`LLMPersonaAgent`) can generate more natural patient responses using any OpenAI-compatible chat completions API. The scenario registry — not the model — remains the authority over which facts may be disclosed. The LLM adapter enforces scenario constraints and falls back to the deterministic agent when the LLM is unavailable or returns invalid output.

To enable the LLM adapter, set these environment variables:

```bash
INFERENCE_PROVIDER=llm
INFERENCE_BASE_URL=https://integrate.api.nvidia.com/v1
INFERENCE_API_KEY=your-key
INFERENCE_MODEL=mistralai/mistral-nemotron
INFERENCE_TIMEOUT=60
```

`ClinicalEvaluatorAgent` produces `MetricScore` objects containing a metric ID, score, maximum score, transcript evidence, and rationale. The final evaluation includes the rubric version, overall score, strengths, improvements, and educational disclaimer.

## Security boundaries

The MCP transport runs on `127.0.0.1` by default, following the Streamable HTTP guidance to bind local servers to localhost. Before public hosting, add HTTPS, strict origin validation, authentication, rate limiting, and a secure reverse proxy.

The REST API supports an optional `DEV_API_KEY` environment variable. When set, `/alexa`, `/mcp/simulate`, and session deletion require the `X-API-Key` header. CORS is restricted to local development origins. Session IDs cannot switch scenarios, ended sessions reject further messages, and client event IDs prevent duplicate processing after retries.

## Testing

```bash
source .venv/bin/activate
pytest -q
python -m compileall -q server tests
```

The tests cover scenario versioning, patient disclosures, the five-metric rubric, idempotent retries, session locking, multi-topic disclosure matching, the MCP tool workflow (start → send → evaluate → end), and all three scenarios. The MCP server entrypoint is smoke-tested via the Streamable HTTP test app.

## Lint

```bash
source .venv/bin/activate
ruff check server tests
ruff format --check server tests
```

## Docker

```bash
docker build -t clinical-sim .
docker run -p 8001:8001 clinical-sim
```

The MCP endpoint is available at `http://localhost:8001/mcp`.

## AWS App Runner deployment

For the AWS Builder mini-challenge, the project includes an App Runner deployment configuration (`apprunner.yaml`) and a deployment script (`scripts/deploy_aws.sh`).

```bash
# Prerequisites: AWS CLI configured, Docker installed
./scripts/deploy_aws.sh
```

The script builds the Docker image, pushes it to ECR, and creates or updates an App Runner service with HTTPS, auto-scaling, and a public MCP endpoint at `https://<random>.awsapprunner.com/mcp`.

## Hackathon submission requirements

The Alexa+ submission should include a public GitHub repository with this source, assets, setup instructions, and `LICENSE`; a public demo video shorter than three minutes showing the MCP tools and end-to-end simulation; a concise project description; product feedback for the MCP/Alexa+ developer experience; and a friction log with concrete setup or integration issues.

The AWS Builder and Open Source mini-challenges should be claimed only when their additional requirements are actually met. See `HACKATHON_STRATEGY.md` for the full submission checklist.

## Layout

```text
alexa-clinical-sim/
├── Dockerfile
├── LICENSE
├── README.md
├── REDESIGN.md
├── HACKATHON_STRATEGY.md
├── PRODUCT_FEEDBACK.md
├── hackathon_research_notes.md
├── apprunner.yaml
├── package.json
├── pyproject.toml
├── pytest.ini
├── server/
│   ├── requirements.txt
│   ├── main.py
│   ├── mcp_server.py
│   ├── scenarios.py
│   ├── agents/
│   │   ├── patient_persona.py
│   │   ├── llm_persona.py
│   │   └── clinical_evaluator.py
│   └── schemas/
├── alexa_config/
├── scripts/
│   ├── initialize.sh
│   ├── start_mcp_server.sh
│   ├── start_local_tunnel.sh
│   └── deploy_aws.sh
└── tests/
    ├── test_simulation.py
    ├── test_mcp_protocol.py
    └── test_llm_persona.py
```
