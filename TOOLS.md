# MCP tool reference

Generated from the MCP server tool schemas by `scripts/gen_tool_reference.py`.
Do not edit by hand; regenerate after changing a tool signature.

## `list_simulation_scenarios`

List the available educational simulation scenarios and their rubric versions.

No input parameters.

## `start_simulation`

Start an educational patient communication simulation session.

| Parameter | Type | Required | Default |
| --- | --- | --- | --- |
| `session_id` | string | yes | — |
| `scenario_id` | string | no | `chest-pain-basic` |

## `send_practitioner_turn`

Send the learner's next practitioner utterance and receive the simulated patient's response.

| Parameter | Type | Required | Default |
| --- | --- | --- | --- |
| `session_id` | string | yes | — |
| `practitioner_message` | string | yes | — |
| `client_event_id` | string | null | no | — |
| `scenario_id` | string | null | no | — |

## `evaluate_simulation`

Evaluate the current session using the active scenario's versioned rubric.

| Parameter | Type | Required | Default |
| --- | --- | --- | --- |
| `session_id` | string | yes | — |
| `scenario_id` | string | null | no | — |

## `end_simulation`

End a simulation and return its final evidence-linked evaluation.

| Parameter | Type | Required | Default |
| --- | --- | --- | --- |
| `session_id` | string | yes | — |
| `scenario_id` | string | null | no | — |
