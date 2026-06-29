from __future__ import annotations

from contextlib import asynccontextmanager
from collections import Counter
from datetime import datetime
from pathlib import Path
import re
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from .config import get_settings
from .database import (
    ActivityEvent,
    AnalysisSession,
    EvidenceChunk,
    SessionLocal,
    User,
    ensure_demo_user,
    get_db,
    init_db,
)
from .schemas import (
    ActivityEventResponse,
    AnalysisResponse,
    AskRequest,
    AskResponse,
    DashboardMetrics,
    DemoLoginResponse,
    SessionSummary,
    WorkflowUpdateRequest,
)
from .services.analysis import analyze_application, answer_question, export_report
from .services.text_processing import extract_resume_text


settings = get_settings()
PIPELINE_STAGES = {"new", "review", "shortlisted", "interview", "offer", "rejected"}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def safe_filename(filename: str) -> str:
    name = Path(filename).name or "resume.pdf"
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def candidate_name_from_session(session: AnalysisSession) -> str:
    personal_info = session.parsed_resume.get("personal_info", {}) if session.parsed_resume else {}
    name = personal_info.get("name") if isinstance(personal_info, dict) else None
    return name or session.resume_filename


def priority_score_for_session(session: AnalysisSession) -> int:
    score = int(session.match_result.get("score", 0))
    risk_flags = session.match_result.get("risk_flags", [])
    risk_penalty = sum({"high": 15, "medium": 7, "low": 3}.get(risk.get("severity"), 0) for risk in risk_flags)
    stage_bonus = {
        "shortlisted": 10,
        "interview": 15,
        "offer": 20,
        "review": 3,
        "rejected": -30,
    }.get(session.pipeline_stage, 0)
    return max(0, min(100, score + stage_bonus - risk_penalty))


def next_action_for_session(session: AnalysisSession) -> dict:
    score = int(session.match_result.get("score", 0))
    confidence = int(session.match_result.get("confidence", 0))
    risk_flags = session.match_result.get("risk_flags", [])
    high_risks = [risk for risk in risk_flags if risk.get("severity") == "high"]
    missing_skills = session.match_result.get("missing_skills", [])
    has_notes = bool(session.reviewer_notes.strip())

    if session.pipeline_stage == "rejected":
        return {
            "label": "Archive after candidate communication",
            "urgency": "done",
            "reason": "The candidate is already marked rejected.",
        }
    if session.pipeline_stage == "offer":
        return {
            "label": "Prepare offer packet",
            "urgency": "medium",
            "reason": "Candidate is in the offer stage and needs closing materials.",
        }
    if session.pipeline_stage == "interview":
        return {
            "label": "Capture interview feedback",
            "urgency": "high" if not has_notes else "medium",
            "reason": "Interview-stage candidates need feedback recorded before the next decision.",
        }
    if session.pipeline_stage == "shortlisted":
        gap_detail = ", ".join(missing_skills[:3]) if missing_skills else "role-specific depth"
        return {
            "label": "Schedule focused interview",
            "urgency": "high",
            "reason": f"Use the interview plan to validate {gap_detail}.",
        }
    if high_risks:
        return {
            "label": "Resolve high-risk screening flags",
            "urgency": "high",
            "reason": high_risks[0].get("detail", "A high-severity risk needs reviewer attention."),
        }
    if score >= 75:
        return {
            "label": "Shortlist for recruiter review",
            "urgency": "high",
            "reason": f"Strong score of {score}% with enough evidence to move forward.",
        }
    if score >= 60:
        gap_detail = ", ".join(missing_skills[:3]) if missing_skills else "remaining evidence gaps"
        return {
            "label": "Review gaps before advancing",
            "urgency": "medium",
            "reason": f"Validate {gap_detail} before changing the pipeline stage.",
        }
    if confidence < 60:
        return {
            "label": "Request stronger resume evidence",
            "urgency": "medium",
            "reason": "Low confidence suggests the resume or JD lacks enough explicit evidence.",
        }
    return {
        "label": "Send feedback or reject",
        "urgency": "low",
        "reason": "The current match is weak enough that recruiter closure is the next step.",
    }


def screening_checks_for_session(session: AnalysisSession) -> list[dict]:
    match = session.match_result or {}
    coverage = match.get("coverage", {})
    risk_flags = match.get("risk_flags", [])
    score = int(match.get("score", 0))
    confidence = int(match.get("confidence", 0))
    evidence_count = len(match.get("evidence", []))
    matched_skills = len(match.get("matched_skills", []))
    must_have = int(coverage.get("must_have", 0))
    responsibilities = int(coverage.get("responsibilities", 0))
    high_risks = [risk for risk in risk_flags if risk.get("severity") == "high"]

    def status(value: int, warn_at: int, pass_at: int) -> str:
        if value >= pass_at:
            return "pass"
        if value >= warn_at:
            return "watch"
        return "fail"

    return [
        {
            "label": "Must-have coverage",
            "status": status(must_have, 55, 75),
            "detail": f"{must_have}% of must-have requirements are evidenced.",
        },
        {
            "label": "Responsibility evidence",
            "status": status(responsibilities, 45, 70),
            "detail": f"{responsibilities}% responsibility coverage from resume/JD evidence.",
        },
        {
            "label": "Risk clearance",
            "status": "fail" if high_risks else "watch" if risk_flags else "pass",
            "detail": (
                f"{len(high_risks)} high-risk flags need resolution."
                if high_risks
                else f"{len(risk_flags)} non-blocking risk flags found."
                if risk_flags
                else "No major screening risks detected."
            ),
        },
        {
            "label": "Evidence depth",
            "status": "pass" if evidence_count >= 4 and matched_skills >= 4 else "watch" if evidence_count >= 2 else "fail",
            "detail": f"{evidence_count} evidence snippets and {matched_skills} matched skills available.",
        },
        {
            "label": "Decision confidence",
            "status": status(min(confidence, score), 55, 72),
            "detail": f"{confidence}% confidence with {score}% overall match score.",
        },
    ]


def readiness_score_from_checks(checks: list[dict]) -> int:
    weights = {"pass": 20, "watch": 10, "fail": 0}
    return sum(weights.get(check.get("status"), 0) for check in checks)


def readiness_label(score: int) -> str:
    if score >= 80:
        return "interview_ready"
    if score >= 55:
        return "needs_validation"
    return "not_ready"


def serialize_session(session: AnalysisSession) -> dict:
    score = int(session.match_result.get("score", 0))
    checks = screening_checks_for_session(session)
    readiness_score = readiness_score_from_checks(checks)
    return {
        "id": session.id,
        "candidate_name": candidate_name_from_session(session),
        "job_title": session.job_title,
        "resume_filename": session.resume_filename,
        "score": score,
        "priority_score": priority_score_for_session(session),
        "readiness_score": readiness_score,
        "readiness_label": readiness_label(readiness_score),
        "screening_checks": checks,
        "next_action": next_action_for_session(session),
        "matched_skills": session.match_result.get("matched_skills", []),
        "missing_skills": session.match_result.get("missing_skills", []),
        "pipeline_stage": session.pipeline_stage,
        "reviewer_notes": session.reviewer_notes,
        "decision_memo": session.decision_memo or {},
        "created_at": session.created_at.isoformat() if session.created_at else "",
        "parsed_resume": session.parsed_resume,
        "parsed_jd": session.parsed_jd,
        "match_result": session.match_result,
        "interview_plan": session.interview_plan,
        "feedback_report": session.feedback_report,
    }


def serialize_activity_event(event: ActivityEvent) -> dict:
    return {
        "id": event.id,
        "session_id": event.session_id,
        "event_type": event.event_type,
        "message": event.message,
        "metadata": event.payload or {},
        "created_at": event.created_at.isoformat() if event.created_at else "",
    }


def record_activity(
    db: Session,
    session_id: str,
    event_type: str,
    message: str,
    payload: dict | None = None,
) -> ActivityEvent:
    event = ActivityEvent(
        session_id=session_id,
        event_type=event_type,
        message=message,
        payload=payload or {},
    )
    db.add(event)
    return event


def build_decision_memo(session_data: dict, reviewer_notes: str = "") -> dict:
    score = int(session_data.get("score", 0))
    match = session_data.get("match_result", {})
    risks = match.get("risk_flags", [])
    high_risks = [risk for risk in risks if risk.get("severity") == "high"]
    missing = match.get("missing_skills", [])

    if score >= 80 and not high_risks:
        recommendation = "advance_to_interview"
        rationale = "Strong evidence match and no high-severity screening risks."
    elif score >= 60:
        recommendation = "review_with_conditions"
        rationale = "Candidate has useful overlap, but gaps or risks need targeted review."
    else:
        recommendation = "do_not_advance_yet"
        rationale = "The current evidence does not meet enough role requirements."

    conditions = []
    if missing:
        conditions.append("Validate missing skills: " + ", ".join(missing[:4]) + ".")
    if high_risks:
        conditions.append("Resolve high-risk flags before interview scheduling.")
    if reviewer_notes.strip():
        conditions.append("Reviewer note captured for follow-up.")

    return {
        "recommendation": recommendation,
        "rationale": rationale,
        "conditions": conditions or ["No blocking conditions detected."],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def get_session_or_404(db: Session, session_id: str) -> AnalysisSession:
    session = db.get(AnalysisSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Analysis session not found")
    return session


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "ai_provider": settings.ai_provider}


@app.post("/api/auth/demo-login", response_model=DemoLoginResponse)
def demo_login(db: Session = Depends(get_db)) -> DemoLoginResponse:
    user = ensure_demo_user(db)
    return DemoLoginResponse(user_id=user.id, email=user.email, name=user.name)


@app.get("/api/sessions", response_model=list[SessionSummary])
def list_sessions(user_id: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    if not user_id:
        user_id = ensure_demo_user(db).id
    sessions = (
        db.query(AnalysisSession)
        .filter(AnalysisSession.user_id == user_id)
        .order_by(AnalysisSession.created_at.desc())
        .all()
    )
    return [serialize_session(session) for session in sessions]


@app.get("/api/dashboard", response_model=DashboardMetrics)
def dashboard_metrics(user_id: str | None = None, db: Session = Depends(get_db)) -> dict:
    if not user_id:
        user_id = ensure_demo_user(db).id
    sessions = (
        db.query(AnalysisSession)
        .filter(AnalysisSession.user_id == user_id)
        .order_by(AnalysisSession.created_at.desc())
        .all()
    )
    serialized = [serialize_session(session) for session in sessions]
    total = len(serialized)
    scores = [session["score"] for session in serialized]
    missing_counter = Counter(
        skill for session in serialized for skill in session.get("missing_skills", [])
    )
    stage_counts = Counter(session.get("pipeline_stage", "new") for session in serialized)
    recent_risk_flags = []
    for session in serialized[:8]:
        for risk in session.get("match_result", {}).get("risk_flags", [])[:2]:
            recent_risk_flags.append(
                {
                    "session_id": session["id"],
                    "job_title": session["job_title"],
                    "severity": risk.get("severity", "low"),
                    "title": risk.get("title", "Risk flag"),
                    "detail": risk.get("detail", ""),
                }
            )

    product_health = [
        {"label": "History", "status": "ready", "detail": f"{total} saved sessions"},
        {"label": "Export", "status": "ready", "detail": "Markdown decision reports enabled"},
        {"label": "Privacy", "status": "ready", "detail": "Session delete removes metadata and uploaded file"},
        {"label": "Audit trail", "status": "ready", "detail": "Analysis, workflow, and export events are tracked"},
        {"label": "AI provider", "status": settings.ai_provider, "detail": "Deterministic fallback keeps demos stable"},
    ]
    ranked_candidates = sorted(
        serialized,
        key=lambda session: (session["priority_score"], session["score"]),
        reverse=True,
    )
    urgency_rank = {"high": 3, "medium": 2, "low": 1, "done": 0}
    action_queue = sorted(
        [
            session
            for session in serialized
            if session.get("next_action", {}).get("urgency") != "done"
        ],
        key=lambda session: (
            urgency_rank.get(session.get("next_action", {}).get("urgency"), 0),
            session["priority_score"],
            session["score"],
        ),
        reverse=True,
    )
    quality_watchlist = sorted(
        [
            {
                **session,
                "blocking_checks": [
                    check
                    for check in session.get("screening_checks", [])
                    if check.get("status") in {"fail", "watch"}
                ],
            }
            for session in serialized
            if session.get("readiness_label") != "interview_ready"
        ],
        key=lambda session: (session["readiness_score"], -session["priority_score"]),
    )

    return {
        "total_sessions": total,
        "average_score": round(sum(scores) / total) if total else 0,
        "strong_fit_count": len([score for score in scores if score >= 75]),
        "ready_to_interview_count": len(
            [session for session in serialized if session.get("readiness_label") == "interview_ready"]
        ),
        "open_action_count": len(action_queue),
        "needs_review_count": len(
            [
                session
                for session in serialized
                if session["pipeline_stage"] in {"new", "review"}
                and (session["score"] < 75 or session.get("match_result", {}).get("risk_flags"))
            ]
        ),
        "stage_counts": dict(stage_counts),
        "top_missing_skills": [
            {"skill": skill, "count": count} for skill, count in missing_counter.most_common(6)
        ],
        "top_candidates": [
            {
                "session_id": session["id"],
                "candidate_name": session["candidate_name"],
                "job_title": session["job_title"],
                "score": session["score"],
                "priority_score": session["priority_score"],
                "readiness_score": session["readiness_score"],
                "pipeline_stage": session["pipeline_stage"],
            }
            for session in ranked_candidates[:5]
        ],
        "action_queue": [
            {
                "session_id": session["id"],
                "candidate_name": session["candidate_name"],
                "job_title": session["job_title"],
                "priority_score": session["priority_score"],
                "pipeline_stage": session["pipeline_stage"],
                "next_action": session["next_action"],
            }
            for session in action_queue[:6]
        ],
        "quality_watchlist": [
            {
                "session_id": session["id"],
                "candidate_name": session["candidate_name"],
                "job_title": session["job_title"],
                "readiness_score": session["readiness_score"],
                "readiness_label": session["readiness_label"],
                "blocking_checks": session["blocking_checks"][:3],
            }
            for session in quality_watchlist[:6]
        ],
        "recent_risk_flags": recent_risk_flags[:8],
        "product_health": product_health,
    }


@app.post("/api/sessions/analyze", response_model=AnalysisResponse)
async def analyze_session(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    user_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if not job_description.strip():
        raise HTTPException(status_code=422, detail="Job description is required")

    user = ensure_demo_user(db) if not user_id else db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    filename = safe_filename(resume.filename or "resume.pdf")
    if not filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(status_code=422, detail="Upload a PDF or TXT resume")

    storage_path = settings.upload_dir / f"{uuid4()}_{filename}"
    storage_path.write_bytes(await resume.read())

    try:
        resume_text = extract_resume_text(storage_path)
        analysis = analyze_application(resume_text, job_description)
    except Exception as exc:
        storage_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    session = AnalysisSession(
        user_id=user.id,
        resume_filename=filename,
        resume_storage_path=str(storage_path),
        job_title=analysis["parsed_jd"].get("title", "Untitled role"),
        resume_text=resume_text,
        jd_text=job_description,
        parsed_resume=analysis["parsed_resume"],
        parsed_jd=analysis["parsed_jd"],
        match_result=analysis["match_result"],
        interview_plan=analysis["interview_plan"],
        feedback_report=analysis["feedback_report"],
    )
    session.decision_memo = build_decision_memo(
        {
            "score": analysis["match_result"]["score"],
            "match_result": analysis["match_result"],
        }
    )
    db.add(session)
    db.flush()

    for chunk in analysis["chunks"]:
        db.add(
            EvidenceChunk(
                session_id=session.id,
                source=chunk["source"],
                ordinal=chunk["ordinal"],
                text=chunk["text"],
            )
        )
    record_activity(
        db,
        session.id,
        "analysis_created",
        f"Analysis created for {candidate_name_from_session(session)}",
        {"score": analysis["match_result"]["score"], "job_title": session.job_title},
    )
    db.commit()
    db.refresh(session)
    return serialize_session(session)


@app.get("/api/sessions/{session_id}", response_model=AnalysisResponse)
def get_session(session_id: str, db: Session = Depends(get_db)) -> dict:
    return serialize_session(get_session_or_404(db, session_id))


@app.patch("/api/sessions/{session_id}/workflow", response_model=AnalysisResponse)
def update_session_workflow(
    session_id: str,
    request: WorkflowUpdateRequest,
    db: Session = Depends(get_db),
) -> dict:
    session = get_session_or_404(db, session_id)
    previous_stage = session.pipeline_stage
    if request.pipeline_stage is not None:
        if request.pipeline_stage not in PIPELINE_STAGES:
            raise HTTPException(status_code=422, detail="Invalid pipeline stage")
        session.pipeline_stage = request.pipeline_stage
    if request.reviewer_notes is not None:
        session.reviewer_notes = request.reviewer_notes.strip()

    session.decision_memo = build_decision_memo(serialize_session(session), session.reviewer_notes)
    record_activity(
        db,
        session.id,
        "workflow_updated",
        f"Workflow updated from {previous_stage} to {session.pipeline_stage}",
        {
            "previous_stage": previous_stage,
            "pipeline_stage": session.pipeline_stage,
            "has_reviewer_notes": bool(session.reviewer_notes),
        },
    )
    db.commit()
    db.refresh(session)
    return serialize_session(session)


@app.get("/api/sessions/{session_id}/activity", response_model=list[ActivityEventResponse])
def session_activity(session_id: str, db: Session = Depends(get_db)) -> list[dict]:
    get_session_or_404(db, session_id)
    events = (
        db.query(ActivityEvent)
        .filter(ActivityEvent.session_id == session_id)
        .order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
        .all()
    )
    return [serialize_activity_event(event) for event in events]


@app.post("/api/sessions/{session_id}/ask", response_model=AskResponse)
def ask_session(session_id: str, request: AskRequest, db: Session = Depends(get_db)) -> dict:
    session = get_session_or_404(db, session_id)
    chunks = [
        {"source": chunk.source, "ordinal": chunk.ordinal, "text": chunk.text}
        for chunk in session.chunks
    ]
    return answer_question(request.question, chunks, serialize_session(session))


@app.get("/api/sessions/{session_id}/export", response_class=PlainTextResponse)
def export_session(session_id: str, db: Session = Depends(get_db)) -> PlainTextResponse:
    session = get_session_or_404(db, session_id)
    record_activity(
        db,
        session.id,
        "report_exported",
        "Decision report exported",
        {"pipeline_stage": session.pipeline_stage, "score": session.match_result.get("score", 0)},
    )
    db.commit()
    db.refresh(session)
    report = export_report(serialize_session(session))
    return PlainTextResponse(
        content=report,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{session_id}-report.md"'},
    )


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)) -> dict:
    session = get_session_or_404(db, session_id)
    storage_path = Path(session.resume_storage_path)
    db.delete(session)
    db.commit()
    storage_path.unlink(missing_ok=True)
    return {"status": "deleted", "session_id": session_id}


if __name__ == "__main__":
    init_db()
    with SessionLocal() as local_db:
        user = ensure_demo_user(local_db)
        print(f"Demo user ready: {user.email}")
