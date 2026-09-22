# MCP tool reference

Generated from the MCP server tool schemas by `scripts/gen_tool_reference.py`.
Do not edit by hand; regenerate after changing a tool signature.

## `list_simulation_scenarios`

List the available educational simulation scenarios and their rubric versions.

No input parameters.

Output: structured `ScenarioListResult`.

## `validate_scenario`

Validate an educator-authored scenario definition (JSON) without creating it. Returns schema errors (which block creation) and authoring warnings such as unreachable rapport gates or duplicate fact/metric ids.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `scenario_json` | string (maxLength=100000) | yes | — | A scenario definition as a JSON string. |

Output: structured `ScenarioValidation`.

## `create_scenario`

Validate and register an educator-authored scenario so it can be started in a new session. Persists across restarts and rejects scenario ids that collide with built-ins.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `scenario_json` | string (maxLength=100000) | yes | — | A scenario definition as a JSON string. |

Output: structured `CreateScenarioResult`.

## `delete_scenario`

Remove a previously created custom scenario. Built-in scenarios cannot be deleted.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `scenario_id` | string (maxLength=128) | yes | — | The custom scenario id to delete. |

Output: structured `DeleteScenarioResult`.

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
