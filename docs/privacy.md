# Privacy And Data Handling

## Stored Data

Each analysis session stores:

- Uploaded resume file under `UPLOAD_DIR`.
- Extracted resume text.
- Job description text.
- Parsed resume and JD JSON.
- Match, interview, feedback, and evidence chunks.
- Session activity events for analysis creation, workflow updates, and report exports.

This is intentional for history, report export, and cited Q&A.

## Delete Flow

`DELETE /api/sessions/{id}` removes:

- The database session.
- Related evidence chunks.
- Related activity events.
- The uploaded resume file.

The frontend exposes this as `Delete Session`.

## Secrets

API keys and database URLs must stay in `.env` or deployment secret managers. The frontend only receives `NEXT_PUBLIC_API_BASE`; no LLM or database key should be exposed to browser code.

## Production Hardening

Before using real candidate data in production:

- Add real authentication and user-level authorization on every session route.
- Move uploaded files to object storage with signed URLs.
- Add retention policies and automatic deletion.
- Add workspace-level audit logs for delete actions that must survive session removal.
- Add a user-visible privacy policy.
