from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from server.agents.clinical_evaluator import ClinicalEvaluatorAgent
from server.agents.llm_persona import KNOWN_PROVIDERS, LLMPersonaAgent
from server.agents.patient_persona import PatientPersonaAgent, PatientState
from server.observability import JsonFormatter, registry
from server.scenarios import ScenarioDefinition, get_scenario
from server.schemas.validation import (
    CohortProgress,
    EvaluationResult,
    LearnerProgress,
    LearnerSummary,
    MetricMastery,
    PatientResponse,
    Role,
    SimulationAction,
    SimulationRequest,
    SimulationResponse,
    TranscriptTurn,
)
from server.storage import LearnerStore, SessionStore

logger = logging.getLogger("alexa_clinical_sim")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(JsonFormatter())
    logger.addHandler(_handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

# Bound the per-session idempotency cache so memory grows linearly with session
# length, not quadratically. Each cached response snapshots the transcript at
# that point; keeping only the most recent events caps the duplicate transcript
# copies while still covering realistic retries (which arrive within seconds).
_MAX_PROCESSED_EVENTS = 64


@dataclass
class Session:
    session_id: str
    scenario: ScenarioDefinition
    patient_state: PatientState
    transcript: list[TranscriptTurn] = field(default_factory=list)
    processed_events: dict[str, SimulationResponse] = field(default_factory=dict)
    status: str = "active"
    last_accessed: float = field(default_factory=time.time)
    learner_id: str | None = None


def _state_to_dict(state: PatientState) -> dict[str, Any]:
    return {
        "scenario_id": state.scenario_id,
        "scenario_version": state.scenario_version,
        "turn_count": state.turn_count,
        "disclosed_facts": sorted(state.disclosed_facts),
        "last_emotional_state": state.last_emotional_state,
    }


def _state_from_dict(data: dict[str, Any]) -> PatientState:
    return PatientState(
        scenario_id=data["scenario_id"],
        scenario_version=data["scenario_version"],
        turn_count=int(data["turn_count"]),
        disclosed_facts=set(data["disclosed_facts"]),
        last_emotional_state=data["last_emotional_state"],
    )


def _session_to_record(session: Session) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "scenario_id": session.scenario.scenario_id,
        "patient_state": _state_to_dict(session.patient_state),
        "transcript": [turn.model_dump(mode="json") for turn in session.transcript],
        "processed_events": {key: value.model_dump(mode="json") for key, value in session.processed_events.items()},
        "status": session.status,
        "last_accessed": session.last_accessed,
        "learner_id": session.learner_id,
    }


def _record_to_session(record: dict[str, Any]) -> Session:
    scenario = get_scenario(record["scenario_id"])
    patient_state = _state_from_dict(record["patient_state"])
    if patient_state.scenario_version != scenario.version:
        raise ValueError(
            f"Persisted session scenario version {patient_state.scenario_version} does not match "
            f"loaded version {scenario.version}; refusing to continue under a different rubric"
        )
    return Session(
        session_id=record["session_id"],
        scenario=scenario,
        patient_state=patient_state,
        transcript=[TranscriptTurn.model_validate(turn) for turn in record["transcript"]],
        processed_events={
            key: SimulationResponse.model_validate(value) for key, value in record["processed_events"].items()
        },
        status=record["status"],
        last_accessed=float(record["last_accessed"]),
        learner_id=record.get("learner_id"),
    )


class SimulationOrchestrator:
    def __init__(self, db_path: str | None = None, patient_agent: Any = None) -> None:
        self.sessions: dict[str, Session] = {}
        self._registry_lock = threading.RLock()
        self._session_locks: dict[str, threading.RLock] = {}
        self._session_locks_guard = threading.Lock()
        self.session_ttl = float(os.getenv("SESSION_TTL_SECONDS", "1800"))
        self.max_sessions = int(os.getenv("SESSION_MAX_SESSIONS", "1000"))
        path = db_path if db_path is not None else os.getenv("SESSION_DB_PATH", "")
        self.store = SessionStore(path) if path else None
        self.learners: dict[str, dict[str, Any]] = {}
        self.learner_store = LearnerStore(path) if path else None
        if patient_agent is not None:
            self.patient_agent = patient_agent
        elif {p.strip().lower() for p in os.getenv("INFERENCE_PROVIDER", "mock").split(",") if p.strip()} & set(
            KNOWN_PROVIDERS
        ):
            self.patient_agent = LLMPersonaAgent()
        else:
            self.patient_agent = PatientPersonaAgent()
        self.evaluator_agent = ClinicalEvaluatorAgent()

    def _session_lock(self, session_id: str) -> threading.RLock:
        with self._session_locks_guard:
            lock = self._session_locks.get(session_id)
            if lock is None:
                lock = threading.RLock()
                self._session_locks[session_id] = lock
            return lock

    def _is_expired(self, session: Session) -> bool:
        return self.session_ttl > 0 and (time.time() - session.last_accessed) > self.session_ttl

    def _evict_expired(self) -> None:
        if self.session_ttl <= 0:
            return
        now = time.time()
        expired = [sid for sid, sess in self.sessions.items() if now - sess.last_accessed > self.session_ttl]
        for sid in expired:
            self._delete_session(sid)
        if self.store is not None:
            self.store.delete_expired(now - self.session_ttl)

    def _evict_lru(self) -> None:
        oldest = min(self.sessions, key=lambda sid: self.sessions[sid].last_accessed)
        self._delete_session(oldest)

    def _load_session(self, session_id: str) -> Session | None:
        if self.store is None:
            return None
        record = self.store.get(session_id)
        if record is None:
            return None
        try:
            session = _record_to_session(record)
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning("Dropping unreadable persisted session %s: %s", session_id, exc)
            self.store.delete(session_id)
            return None
        self.sessions[session_id] = session
        return session

    def _persist(self, session: Session) -> None:
        if self.store is not None:
            self.store.upsert(_session_to_record(session))

    def _delete_session(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)
        if self.store is not None:
            self.store.delete(session_id)
        with self._session_locks_guard:
            self._session_locks.pop(session_id, None)

    def remove_session(self, session_id: str) -> bool:
        with self._session_lock(session_id):
            with self._registry_lock:
                present = session_id in self.sessions
                if not present and self.store is not None:
                    present = self.store.get(session_id) is not None
                self._delete_session(session_id)
            return present

    def list_sessions(self) -> list[dict[str, Any]]:
        with self._registry_lock:
            return [
                {
                    "session_id": session_id,
                    "scenario_id": sess.scenario.scenario_id,
                    "status": sess.status,
                    "turn_count": sess.patient_state.turn_count,
                }
                for session_id, sess in self.sessions.items()
            ]

    def _load_learner(self, learner_id: str) -> dict[str, Any]:
        if learner_id in self.learners:
            return self.learners[learner_id]
        if self.learner_store is not None:
            record = self.learner_store.get(learner_id)
            if record is not None:
                self.learners[learner_id] = record
                return record
        return {"learner_id": learner_id, "sessions_completed": 0, "metrics": {}}

    def _persist_learner(self, learner_id: str, record: dict[str, Any]) -> None:
        self.learners[learner_id] = record
        if self.learner_store is not None:
            self.learner_store.upsert(learner_id, record)

    def _record_progress(
        self, learner_id: str, session: Session, evaluation: EvaluationResult
    ) -> LearnerProgress:
        """Fold a completed session's rubric into the learner's cross-session record."""
        record = self._load_learner(learner_id)
        improved: list[str] = []
        metrics = record.setdefault("metrics", {})
        for item in evaluation.metrics:
            key = f"{session.scenario.scenario_id}:{item.metric_id}"
            prev = metrics.get(key)
            if prev is not None and item.score > prev["best_score"]:
                improved.append(item.metric)
            metrics[key] = {
                "scenario_id": session.scenario.scenario_id,
                "metric_id": item.metric_id,
                "metric": item.metric,
                "best_score": max(item.score, prev["best_score"]) if prev is not None else item.score,
                "max_score": item.max_score,
                "latest_score": item.score,
                "attempts": (prev["attempts"] + 1) if prev is not None else 1,
            }
        record["sessions_completed"] = record.get("sessions_completed", 0) + 1
        record["last_scenario_id"] = session.scenario.scenario_id
        record["last_improved"] = improved
        record["updated_at"] = time.time()
        self._persist_learner(learner_id, record)
        return self._build_learner_progress(learner_id, record)

    def _build_learner_progress(self, learner_id: str, record: dict[str, Any]) -> LearnerProgress:
        mastery = [MetricMastery(**item) for item in record.get("metrics", {}).values()]
        # Weakest mastery first; ties broken by fewest attempts, then name.
        ranked = sorted(mastery, key=lambda m: (m.best_score / m.max_score, m.attempts, m.metric))
        focus = ranked[0].metric if ranked else ""
        improved = record.get("last_improved", [])
        completed = int(record.get("sessions_completed", 0))
        note = f"Session {completed} complete."
        if improved:
            note += f" Improved: {', '.join(improved)}."
        if focus:
            note += f" Focus next: {focus}."
        return LearnerProgress(
            learner_id=learner_id,
            sessions_completed=completed,
            metrics=mastery,
            improved_this_session=improved,
            focus_next=focus,
            adaptive_note=note,
        )

    def get_learner_progress(self, learner_id: str) -> LearnerProgress:
        record = self._load_learner(learner_id)
        return self._build_learner_progress(learner_id, record)

    def cohort_progress(self) -> CohortProgress:
        """Aggregate every learner's progress into a faculty/coach cohort view."""
        records: dict[str, dict[str, Any]] = {}
        if self.learner_store is not None:
            records.update(self.learner_store.list())
        records.update(self.learners)  # in-memory overlay may be newer than the store

        summaries: list[LearnerSummary] = []
        weakest_counter: dict[str, int] = {}
        for learner_id, record in records.items():
            progress = self._build_learner_progress(learner_id, record)
            mastery = [MetricMastery(**item) for item in record.get("metrics", {}).values()]
            average = (
                sum(item.best_score / item.max_score for item in mastery) / len(mastery)
                if mastery
                else 0.0
            )
            summaries.append(
                LearnerSummary(
                    learner_id=learner_id,
                    sessions_completed=progress.sessions_completed,
                    metrics_attempted=len(mastery),
                    mastery=round(average, 3),
                    focus_next=progress.focus_next,
                )
            )
            if progress.focus_next:
                weakest_counter[progress.focus_next] = weakest_counter.get(progress.focus_next, 0) + 1

        summaries.sort(key=lambda item: (-item.sessions_completed, item.learner_id))
        weakest = sorted(weakest_counter, key=lambda name: (-weakest_counter[name], name))
        return CohortProgress(
            learner_count=len(summaries),
            total_sessions=sum(item.sessions_completed for item in summaries),
            learners=summaries,
            cohort_weakest_metrics=weakest,
        )

    def get_or_create(self, request: SimulationRequest) -> Session:
        with self._session_lock(request.session_id):
            return self._get_or_create(request)

    def _get_or_create(self, request: SimulationRequest) -> Session:
        session_id = request.session_id
        with self._registry_lock:
            session = self.sessions.get(session_id)
            if session is not None and self._is_expired(session):
                self._delete_session(session_id)
                session = None
            if session is None:
                session = self._load_session(session_id)
        if session is not None:
            if request.scenario_id is not None and session.scenario.scenario_id != request.scenario_id:
                raise HTTPException(status_code=409, detail="Session cannot switch scenarios")
            if request.learner_id is not None and session.learner_id is None:
                session.learner_id = request.learner_id
            session.last_accessed = time.time()
            self._persist(session)
            return session

        with self._registry_lock:
            self._evict_expired()
            if self.max_sessions > 0 and len(self.sessions) >= self.max_sessions:
                self._evict_lru()
            scenario_id = request.scenario_id or "chest-pain-basic"
            try:
                scenario = get_scenario(scenario_id)
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            session = Session(
                session_id=session_id,
                scenario=scenario,
                patient_state=PatientState(scenario_id=scenario.scenario_id, scenario_version=scenario.version),
                learner_id=request.learner_id,
            )
            self.sessions[session_id] = session
            registry.incr("sessions_created_total")
        self._persist(session)
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
            goal=session.scenario.goal,
            action=request.action.value,
            transcript=session.transcript,
            status=session.status,
            **kwargs,
        )

    def handle(self, request: SimulationRequest) -> SimulationResponse:
        with self._session_lock(request.session_id):
            return self._handle_locked(request)

    def _handle_locked(self, request: SimulationRequest) -> SimulationResponse:
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
            session.patient_state.turn_count += 1
            try:
                patient = self.patient_agent.respond(
                    session.patient_state, session.scenario, request.practitioner_message
                )
            except Exception:
                session.transcript.pop()
                session.patient_state.turn_count -= 1
                raise
            if len(patient.content) > 4000:
                patient.content = patient.content[:4000]
            session.transcript.append(self._turn(Role.patient, patient.content))
            response = self._response(request, session, patient=patient)
        elif request.action == SimulationAction.evaluate:
            evaluation = self.evaluator_agent.evaluate(session.transcript, session.scenario)
            session.status = "evaluated"
            response = self._response(request, session, evaluation=evaluation)
        elif request.action == SimulationAction.end:
            evaluation = self.evaluator_agent.evaluate(session.transcript, session.scenario)
            session.status = "ended"
            learner_id = request.learner_id or session.learner_id
            learner_progress = self._record_progress(learner_id, session, evaluation) if learner_id else None
            response = self._response(request, session, evaluation=evaluation, learner_progress=learner_progress)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported action: {request.action}")

        if request.client_event_id:
            session.processed_events[request.client_event_id] = response
            while len(session.processed_events) > _MAX_PROCESSED_EVENTS:
                session.processed_events.pop(next(iter(session.processed_events)))
        self._persist(session)
        logger.info(
            "simulation_request session_id=%s action=%s status=%s",
            session.session_id,
            request.action.value,
            session.status,
        )
        return response


orchestrator = SimulationOrchestrator()
