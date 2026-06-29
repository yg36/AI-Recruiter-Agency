# Architecture Notes

## Runtime Shape

The app is split into a Next.js frontend and a FastAPI backend.

- `frontend/` owns the dashboard, upload form, session history, Q&A, interview plan, feedback, and report actions.
- `backend/main.py` exposes the HTTP API.
- `backend/services/text_processing.py` owns parsing, skill extraction, chunking, and retrieval.
- `backend/services/analysis.py` owns matching, interview generation, feedback, Q&A, and report export.
- `backend/database.py` owns SQLAlchemy models and persistence.

## Data Model

The core tables are:

- `users`: demo or future authenticated users.
- `analysis_sessions`: resume/JD text, parsed JSON, match JSON, interview JSON, and feedback JSON.
- `analysis_sessions.pipeline_stage`: recruiter workflow state for new, review, shortlisted, interview, offer, and rejected.
- `analysis_sessions.reviewer_notes`: human review notes that turn analysis into a decision workflow.
- `analysis_sessions.decision_memo`: generated recruiter recommendation, rationale, and follow-up conditions.
- `activity_events`: append-only session timeline for analysis creation, workflow updates, and report exports.
- `evidence_chunks`: resume and JD chunks used by the Q&A retrieval flow.

SQLite is the default local database. PostgreSQL is supported through SQLAlchemy by setting `DATABASE_URL`; a deploy reference schema lives in `backend/schema.postgres.sql`.

## Matching Strategy

The current scoring layer is deterministic so the demo remains reliable without API keys:

- Must-have skill overlap contributes the largest weight.
- Nice-to-have skill overlap contributes a smaller weight.
- Responsibility overlap checks whether the resume has enough evidence for JD work areas.
- Seniority score prevents fresher resumes from being scored as senior-ready without evidence.

The result includes matched skills, missing skills, an explanation, and short evidence snippets from the resume and JD.

## RAG Strategy

The app chunks resume and JD text, then retrieves chunks using token overlap plus skill overlap. Answers are intentionally extractive: they summarize the strongest cited snippets instead of inventing details.

This makes the first version explainable and predictable. A future LLM provider can rewrite the answer, but citations should continue to come from retrieved chunks.

## Deployment Shape

- Frontend: Vercel.
- Backend: Render, Railway, or Fly.
- Database: Neon or Supabase PostgreSQL.
- File storage: local disk for MVP; object storage such as Supabase Storage or S3 for production.

## Product Workflow

The product now separates AI analysis from recruiter decisioning:

- Analysis services generate evidence, scores, risks, feedback, and interview plans.
- Workflow APIs persist human review state and notes.
- Dashboard metrics aggregate priority candidates, interview readiness, quality watchlist, action queue, repeated gaps, review load, pipeline counts, and product health.
- Next-action logic is computed from score, stage, confidence, risk flags, and reviewer notes so existing sessions gain operational guidance without a migration.
- Screening checks are computed from coverage, risk flags, evidence depth, confidence, and score so the quality gate stays explainable.
- Activity APIs expose session-level audit history for the recruiter workspace.
- Export combines AI evidence and reviewer state into a decision artifact.
