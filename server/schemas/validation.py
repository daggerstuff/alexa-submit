from __future__ import annotations

from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Role(StrEnum):
    practitioner = "practitioner"
    patient = "patient"
    system = "system"


class SimulationAction(StrEnum):
    start = "start"
    message = "message"
    evaluate = "evaluate"
    end = "end"


class SimulationRequest(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=128)
    action: SimulationAction = SimulationAction.message
    scenario_id: str | None = Field(default=None, max_length=128)
    practitioner_message: str | None = Field(default=None, max_length=4000)
    client_event_id: str | None = Field(default=None, max_length=128)
    learner_id: str | None = Field(default=None, max_length=128)


class TranscriptTurn(BaseModel):
    role: Role
    content: str = Field(min_length=1, max_length=4000)
    timestamp: str
    turn_id: str = Field(default_factory=lambda: str(uuid4()))


class PatientResponse(BaseModel):
    content: str
    emotional_state: str
    disclosed_facts: list[str] = Field(default_factory=list)
    safety_note: str | None = None
    scenario_id: str
    scenario_version: str


class MetricScore(BaseModel):
    metric_id: str
    metric: str
    score: int = Field(ge=0)
    max_score: int = Field(ge=1)
    evidence: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)
    rationale: str


class CoachingSuggestion(BaseModel):
    metric_id: str
    metric: str
    suggestion: str


class EvaluationResult(BaseModel):
    rubric_version: str
    overall_score: int = Field(ge=0)
    max_score: int = Field(ge=1)
    metrics: list[MetricScore]
    strengths: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    coaching: list[CoachingSuggestion] = Field(default_factory=list)
    safety_flags: list[str] = Field(default_factory=list)
    summary: str = ""
    disclaimer: str = "Simulation feedback is educational and is not a substitute for supervised clinical assessment."


class MetricMastery(BaseModel):
    """Cross-session mastery of one rubric metric for one learner."""

    scenario_id: str
    metric_id: str
    metric: str
    best_score: int = Field(ge=0)
    max_score: int = Field(ge=1)
    latest_score: int = Field(ge=0)
    attempts: int = Field(ge=1)


class LearnerProgress(BaseModel):
    """A learner's accumulated progress across simulation sessions."""

    learner_id: str
    sessions_completed: int = Field(ge=0)
    metrics: list[MetricMastery] = Field(default_factory=list)
    improved_this_session: list[str] = Field(default_factory=list)
    focus_next: str = ""
    adaptive_note: str = ""


class SimulationResponse(BaseModel):
    request_id: str
    session_id: str
    scenario_id: str
    scenario_version: str
    goal: str = ""
    action: str
    patient: PatientResponse | None = None
    evaluation: EvaluationResult | None = None
    transcript: list[TranscriptTurn]
    status: Literal["active", "evaluated", "ended"]
    learner_progress: LearnerProgress | None = None
    disclaimer: str = "Educational simulation only; do not use for real patient care."
