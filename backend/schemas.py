from typing import Any

from pydantic import BaseModel, Field


class DemoLoginResponse(BaseModel):
    user_id: str
    email: str
    name: str


class SessionSummary(BaseModel):
    id: str
    candidate_name: str
    job_title: str
    resume_filename: str
    score: int
    priority_score: int
    readiness_score: int
    readiness_label: str
    screening_checks: list[dict[str, Any]]
    next_action: dict[str, Any]
    matched_skills: list[str]
    missing_skills: list[str]
    pipeline_stage: str
    created_at: str


class AnalysisResponse(SessionSummary):
    reviewer_notes: str
    decision_memo: dict[str, Any]
    parsed_resume: dict[str, Any]
    parsed_jd: dict[str, Any]
    match_result: dict[str, Any]
    interview_plan: dict[str, Any]
    feedback_report: dict[str, Any]


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class Citation(BaseModel):
    source: str
    ordinal: int
    text: str


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]


class WorkflowUpdateRequest(BaseModel):
    pipeline_stage: str | None = Field(default=None, max_length=40)
    reviewer_notes: str | None = Field(default=None, max_length=3000)


class DashboardMetrics(BaseModel):
    total_sessions: int
    average_score: int
    strong_fit_count: int
    ready_to_interview_count: int
    open_action_count: int
    needs_review_count: int
    stage_counts: dict[str, int]
    top_missing_skills: list[dict[str, Any]]
    top_candidates: list[dict[str, Any]]
    action_queue: list[dict[str, Any]]
    quality_watchlist: list[dict[str, Any]]
    recent_risk_flags: list[dict[str, Any]]
    product_health: list[dict[str, Any]]


class ActivityEventResponse(BaseModel):
    id: int
    session_id: str
    event_type: str
    message: str
    metadata: dict[str, Any]
    created_at: str
