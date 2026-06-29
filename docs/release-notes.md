# Release Notes

## 0.5.0 Screening Quality Gate

- Added computed interview-readiness score and readiness label to each session.
- Added five screening checks covering must-have coverage, responsibility evidence, risk clearance, evidence depth, and decision confidence.
- Added dashboard ready-now count and quality watchlist.
- Added active-candidate screening checklist.
- Expanded API tests to cover readiness and checklist fields.

## 0.4.0 Recruiter Action Queue

- Added computed next action, urgency, and reason to every session summary.
- Added dashboard open-action count and ranked action queue.
- Added active-candidate next-action panel for recruiter decisioning.
- Expanded API tests to cover the action queue contract.

## 0.3.0 Product Operating Layer

- Added candidate identity and priority score to analysis summaries.
- Added ranked top-candidate panel to the dashboard.
- Added candidate search, stage filtering, and priority/score/newest sorting in history.
- Added session activity timeline for analysis creation, workflow updates, and report exports.
- Added activity API: `GET /api/sessions/{id}/activity`.
- Added `activity_events` database table to the PostgreSQL reference schema.
- Expanded API tests to cover priority metadata, ranked dashboard entries, and audit events.

## 0.2.0 Product Workspace

- Added workspace command center with total analyses, average score, strong fits, and review queue.
- Added top missing skill aggregation and product health indicators.
- Added persistent pipeline stages for each analysis session.
- Added reviewer notes and generated decision memo.
- Added workflow update API: `PATCH /api/sessions/{id}/workflow`.
- Added dashboard metrics API: `GET /api/dashboard`.
- Export report now includes pipeline stage, reviewer notes, and decision memo.
- Added additive database migration for existing local sessions.

## 0.1.0 Flagship MVP

- Added FastAPI backend and Next.js dashboard.
- Added resume/JD parsing, match score, cited evidence, Q&A, interview plan, feedback, export, history, and delete.
- Added docs, env template, PostgreSQL schema, and tests.
