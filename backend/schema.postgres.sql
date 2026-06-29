CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(120) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analysis_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resume_filename VARCHAR(255) NOT NULL,
    resume_storage_path VARCHAR(500) NOT NULL,
    job_title VARCHAR(255) NOT NULL,
    resume_text TEXT NOT NULL,
    jd_text TEXT NOT NULL,
    parsed_resume JSONB NOT NULL,
    parsed_jd JSONB NOT NULL,
    match_result JSONB NOT NULL,
    interview_plan JSONB NOT NULL,
    feedback_report JSONB NOT NULL,
    pipeline_stage VARCHAR(40) NOT NULL DEFAULT 'new',
    reviewer_notes TEXT NOT NULL DEFAULT '',
    decision_memo JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_sessions_user_created
    ON analysis_sessions(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_analysis_sessions_user_stage
    ON analysis_sessions(user_id, pipeline_stage);

CREATE TABLE IF NOT EXISTS activity_events (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    event_type VARCHAR(60) NOT NULL,
    message VARCHAR(500) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_events_session_created
    ON activity_events(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_activity_events_type
    ON activity_events(event_type);

CREATE TABLE IF NOT EXISTS evidence_chunks (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES analysis_sessions(id) ON DELETE CASCADE,
    source VARCHAR(30) NOT NULL,
    ordinal INTEGER NOT NULL,
    text TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evidence_chunks_session
    ON evidence_chunks(session_id, ordinal);
