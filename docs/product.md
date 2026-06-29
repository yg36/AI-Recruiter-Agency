# Product Brief

## Product Positioning

AI Recruiter Interview Assistant is a lightweight screening workspace for small teams, founders, recruiters, and candidates who need fast, explainable resume-to-role review.

It is not positioned as an enterprise ATS. The product promise is narrower and stronger: upload a resume and JD, get a grounded fit report, ask evidence-based questions, generate interview prep, and carry the candidate through a simple review pipeline.

## Core User Loop

1. Recruiter uploads a resume and job description.
2. Product generates score, evidence, gaps, risks, feedback, and interview plan.
3. Recruiter reviews decision memo and moves the candidate through a pipeline stage.
4. Recruiter records notes, reviews the activity timeline, and exports a report.
5. Workspace dashboard highlights priority candidates, aggregate gaps, review load, and product health.

## Product Capabilities

- Resume/JD parsing and structured skill extraction.
- Evidence-based match scoring with component breakdown.
- Grounded profile Q&A with citations.
- Risk flags and confidence score.
- Mock interview plan and candidate feedback.
- Tailored resume bullets and outreach copy.
- Persistent analysis history.
- Pipeline stages: new, review, shortlisted, interview, offer, rejected.
- Reviewer notes and generated decision memo.
- Priority score, top-candidate ranking, search, stage filter, and sort controls.
- Recruiter action queue with next action, urgency, and reason for each active candidate.
- Interview-readiness score, screening checklist, and quality watchlist for candidates that need validation.
- Session activity timeline for analysis creation, workflow updates, and report exports.
- Workspace metrics: analyses, average score, strong fits, interview-ready candidates, open actions, review queue, top candidates, top gaps.
- Privacy delete for uploaded resume and session metadata.

## Release Readiness

MVP-ready:

- Deterministic fallback analysis for reliable demos.
- Local SQLite with PostgreSQL-ready schema.
- Exportable Markdown reports.
- Tests for analysis, API workflow, dashboard metrics, and export.
- Responsive dashboard verified on desktop and mobile.

Before production with real candidate data:

- Add authenticated multi-user workspaces.
- Add row-level authorization on every session.
- Move files to object storage with signed URLs.
- Add retention policies and workspace-level delete audit.
- Add provider adapters for OpenAI/Gemini/Ollama with cost controls.
- Add monitoring around parse failures, analysis latency, and export/delete actions.

## Product Metrics

- Activation: first completed resume/JD analysis.
- Core value: report exported or candidate moved from new to review/shortlisted.
- Quality: percentage of answers with citations, low parse-failure rate, reviewer acceptance of decision memo.
- Retention: repeat analyses per workspace.
- Trust: deletion success rate and no secret exposure.
