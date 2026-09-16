# MCP tool reference

Generated from the MCP server tool schemas by `scripts/gen_tool_reference.py`.
Do not edit by hand; regenerate after changing a tool signature.

## `list_simulation_scenarios`

List the available educational simulation scenarios and their rubric versions.

No input parameters.

Output: structured `ScenarioListResult`.

## `start_simulation`

Start an educational patient communication simulation session.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `session_id` | string (maxLength=128) | yes | — | Stable application session identifier. |
| `scenario_id` | string (maxLength=128) | no | `chest-pain-basic` | Scenario id to start; defaults to chest-pain-basic. |
| `learner_id` | string | null | no | — | Optional stable learner identifier for cross-session progress tracking. |

Output: structured `SimulationResponse`.

## `send_practitioner_turn`

Send the learner's next practitioner utterance and receive the simulated patient's response.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `session_id` | string (maxLength=128) | yes | — | Stable application session identifier. |
| `practitioner_message` | string (maxLength=4000) | yes | — | The learner's next utterance. |
| `client_event_id` | string | null | no | — | Idempotency key; a retried key is not reprocessed. |
| `scenario_id` | string | null | no | — | Must match the session's scenario when provided. |
| `learner_id` | string | null | no | — | Optional stable learner identifier for cross-session progress tracking. |

Output: structured `SimulationResponse`.

## `evaluate_simulation`

Evaluate the current session using the active scenario's versioned rubric.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `session_id` | string (maxLength=128) | yes | — | Stable application session identifier. |
| `scenario_id` | string | null | no | — | Must match the session's scenario when provided. |
| `learner_id` | string | null | no | — | Optional stable learner identifier for cross-session progress tracking. |

Output: structured `SimulationResponse`.

## `end_simulation`

End a simulation and return its final evidence-linked evaluation.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `session_id` | string (maxLength=128) | yes | — | Stable application session identifier. |
| `scenario_id` | string | null | no | — | Must match the session's scenario when provided. |
| `learner_id` | string | null | no | — | Optional stable learner identifier for cross-session progress tracking. |

Output: structured `SimulationResponse`.
