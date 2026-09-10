from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from server.agents.clinical_evaluator import ClinicalEvaluatorAgent
from server.agents.llm_persona import LLMPersonaAgent
from server.agents.patient_persona import PatientPersonaAgent, PatientState
from server.scenarios import ScenarioDefinition, get_scenario
from server.schemas.validation import (
    PatientResponse,
    Role,
    SimulationAction,
    SimulationRequest,
    SimulationResponse,
    TranscriptTurn,
)

logger = logging.getLogger("alexa_clinical_sim")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())


@dataclass
class Session:
    session_id: str
    scenario: ScenarioDefinition
    patient_state: PatientState
    transcript: list[TranscriptTurn] = field(default_factory=list)
    processed_events: dict[str, SimulationResponse] = field(default_factory=dict)
    status: str = "active"


class SimulationOrchestrator:
    def __init__(self) -> None:
        self.sessions: dict[str, Session] = {}
        provider = os.getenv("INFERENCE_PROVIDER", "mock")
        if provider == "llm":
            self.patient_agent = LLMPersonaAgent()
        else:
            self.patient_agent = PatientPersonaAgent()
        self.evaluator_agent = ClinicalEvaluatorAgent()

    def get_or_create(self, request: SimulationRequest) -> Session:
        session = self.sessions.get(request.session_id)
        if session is not None:
            if request.scenario_id is not None and session.scenario.scenario_id != request.scenario_id:
                raise HTTPException(status_code=409, detail="Session cannot switch scenarios")
            return session
        scenario_id = request.scenario_id or "chest-pain-basic"
        try:
            scenario = get_scenario(scenario_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        session = Session(
            session_id=request.session_id,
            scenario=scenario,
            patient_state=PatientState(scenario_id=scenario.scenario_id, scenario_version=scenario.version),
        )
        self.sessions[request.session_id] = session
        return session

    @staticmethod
    def _turn(role: Role, content: str) -> TranscriptTurn:
        return TranscriptTurn(role=role, content=content, timestamp=datetime.now(UTC).isoformat())

    def _response(self, request: SimulationRequest, session: Session, **kwargs: Any) -> SimulationResponse:
        return SimulationResponse(
            request_id=str(uuid4()),
            session_id=session.session_id,
            scenario_id=session.scenario.scenario_id,
            scenario_version=session.scenario.version,
            action=request.action.value,
            transcript=session.transcript,
            status=session.status,
            **kwargs,
        )

    def handle(self, request: SimulationRequest) -> SimulationResponse:
        session = self.get_or_create(request)
        if request.client_event_id and request.client_event_id in session.processed_events:
            return session.processed_events[request.client_event_id]
        if session.status == "ended":
            raise HTTPException(status_code=409, detail="Session has ended")

        if request.action == SimulationAction.start:
            if session.transcript:
                response = self._response(request, session, patient=None)
            else:
                patient = PatientResponse(
                    content=session.scenario.opening,
                    emotional_state="anxious",
                    disclosed_facts=[],
                    safety_note=None,
                    scenario_id=session.scenario.scenario_id,
                    scenario_version=session.scenario.version,
                )
                session.transcript.append(self._turn(Role.patient, patient.content))
                response = self._response(request, session, patient=patient)
        elif request.action == SimulationAction.message:
            if not request.practitioner_message or not request.practitioner_message.strip():
                raise HTTPException(
                    status_code=422,
                    detail="practitioner_message is required for action=message",
                )
            session.transcript.append(self._turn(Role.practitioner, request.practitioner_message.strip()))
            patient = self.patient_agent.respond(session.patient_state, session.scenario, request.practitioner_message)
            session.transcript.append(self._turn(Role.patient, patient.content))
            response = self._response(request, session, patient=patient)
        elif request.action == SimulationAction.evaluate:
            evaluation = self.evaluator_agent.evaluate(session.transcript, session.scenario)
            session.status = "evaluated"
            response = self._response(request, session, evaluation=evaluation)
        elif request.action == SimulationAction.end:
            evaluation = self.evaluator_agent.evaluate(session.transcript, session.scenario)
            session.status = "ended"
            response = self._response(request, session, evaluation=evaluation)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported action: {request.action}")

        if request.client_event_id:
            session.processed_events[request.client_event_id] = response
        logger.info(
            "simulation_request session_id=%s action=%s status=%s",
            session.session_id,
            request.action.value,
            session.status,
        )
        return response


app = FastAPI(title="Alexa+ Clinical Simulation Node", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["content-type", "x-api-key"],
)
orchestrator = SimulationOrchestrator()


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("DEV_API_KEY")
    if expected and x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "alexa-clinical-sim",
        "active_sessions": len(orchestrator.sessions),
        "version": app.version,
    }


@app.post(
    "/mcp/simulate",
    response_model=SimulationResponse,
    dependencies=[Depends(require_api_key)],
)
def simulate(request: SimulationRequest) -> SimulationResponse:
    return orchestrator.handle(request)


@app.post("/alexa", response_model=SimulationResponse, dependencies=[Depends(require_api_key)])
def alexa_passthrough(request: SimulationRequest) -> SimulationResponse:
    """Development passthrough endpoint for an Alexa/MCP adapter."""
    return orchestrator.handle(request)


@app.delete("/sessions/{session_id}", dependencies=[Depends(require_api_key)])
def delete_session(session_id: str) -> dict[str, str]:
    if session_id not in orchestrator.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    del orchestrator.sessions[session_id]
    return {"status": "deleted", "session_id": session_id}
