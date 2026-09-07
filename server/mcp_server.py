from __future__ import annotations

import os
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from server.main import orchestrator
from server.scenarios import SCENARIOS
from server.schemas.validation import SimulationAction, SimulationRequest


mcp = MCPServer(
    name="clinical-conversation-coach",
    title="Clinical Conversation Coach",
    version="0.3.0",
    description=(
        "A scenario-based clinical communication simulator for educational practice. "
        "It returns simulated patient turns and evidence-linked rubric feedback."
    ),
    instructions=(
        "Use only for educational simulation. Never use this server for real patient care, "
        "diagnosis, triage, or treatment decisions."
    ),
)


def _serialize(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump(mode="json")
    return response


@mcp.tool(
    description="List the available educational simulation scenarios and their rubric versions.",
    structured_output=True,
)
def list_simulation_scenarios() -> dict[str, Any]:
    return {
        "scenarios": [
            {
                "scenario_id": scenario.scenario_id,
                "version": scenario.version,
                "title": scenario.title,
                "metric_ids": [metric.metric_id for metric in scenario.metrics],
            }
            for scenario in SCENARIOS.values()
        ],
        "disclaimer": "Educational simulation only; do not use for real patient care.",
    }


@mcp.tool(
    description="Start an educational patient communication simulation session.",
    structured_output=True,
)
def start_simulation(session_id: str, scenario_id: str = "chest-pain-basic") -> dict[str, Any]:
    response = orchestrator.handle(
        SimulationRequest(session_id=session_id, scenario_id=scenario_id, action=SimulationAction.start)
    )
    return _serialize(response)


@mcp.tool(
    description="Send the learner's next practitioner utterance and receive the simulated patient's response.",
    structured_output=True,
)
def send_practitioner_turn(
    session_id: str,
    practitioner_message: str,
    client_event_id: str | None = None,
    scenario_id: str = "chest-pain-basic",
) -> dict[str, Any]:
    response = orchestrator.handle(
        SimulationRequest(
            session_id=session_id,
            scenario_id=scenario_id,
            action=SimulationAction.message,
            practitioner_message=practitioner_message,
            client_event_id=client_event_id,
        )
    )
    return _serialize(response)


@mcp.tool(
    description="Evaluate the current session using the active scenario's versioned rubric.",
    structured_output=True,
)
def evaluate_simulation(session_id: str, scenario_id: str = "chest-pain-basic") -> dict[str, Any]:
    response = orchestrator.handle(
        SimulationRequest(session_id=session_id, scenario_id=scenario_id, action=SimulationAction.evaluate)
    )
    return _serialize(response)


@mcp.tool(
    description="End a simulation and return its final evidence-linked evaluation.",
    structured_output=True,
)
def end_simulation(session_id: str, scenario_id: str = "chest-pain-basic") -> dict[str, Any]:
    response = orchestrator.handle(
        SimulationRequest(session_id=session_id, scenario_id=scenario_id, action=SimulationAction.end)
    )
    return _serialize(response)


if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8001"))
    allowed_hosts = [item.strip() for item in os.getenv("MCP_ALLOWED_HOSTS", f"{host}:*").split(",") if item.strip()]
    allowed_origins = [item.strip() for item in os.getenv("MCP_ALLOWED_ORIGINS", "http://127.0.0.1:*,http://localhost:*").split(",") if item.strip()]
    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        streamable_http_path=os.getenv("MCP_PATH", "/mcp"),
        json_response=True,
        stateless_http=False,
        transport_security=transport_security,
    )
