import importlib
import sys

from fastapi.testclient import TestClient

from tests.test_analysis_service import JD_TEXT, RESUME_TEXT


def load_isolated_app(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.sqlite3'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))

    for module_name in ("backend.main", "backend.database"):
        sys.modules.pop(module_name, None)

    import backend.config as config

    config.get_settings.cache_clear()
    import backend.main as main

    return importlib.reload(main)


def test_full_api_workflow(tmp_path, monkeypatch):
    main = load_isolated_app(tmp_path, monkeypatch)

    with TestClient(main.app) as client:
        login = client.post("/api/auth/demo-login")
        assert login.status_code == 200
        user_id = login.json()["user_id"]

        analysis = client.post(
            "/api/sessions/analyze",
            data={"job_description": JD_TEXT, "user_id": user_id},
            files={"resume": ("resume.txt", RESUME_TEXT, "text/plain")},
        )
        assert analysis.status_code == 200
        payload = analysis.json()
        assert payload["score"] >= 70
        assert payload["candidate_name"]
        assert payload["priority_score"] >= 0
        assert 0 <= payload["readiness_score"] <= 100
        assert payload["readiness_label"] in {"interview_ready", "needs_validation", "not_ready"}
        assert len(payload["screening_checks"]) == 5
        assert {check["status"] for check in payload["screening_checks"]} <= {"pass", "watch", "fail"}
        assert payload["next_action"]["label"]
        assert payload["next_action"]["urgency"] in {"high", "medium", "low", "done"}
        assert payload["pipeline_stage"] == "new"
        assert payload["decision_memo"]["recommendation"]
        assert payload["match_result"]["evidence"]
        assert payload["match_result"]["score_breakdown"]
        assert payload["feedback_report"]["tailored_resume_bullets"]

        activity = client.get(f"/api/sessions/{payload['id']}/activity")
        assert activity.status_code == 200
        assert [event["event_type"] for event in activity.json()] == ["analysis_created"]

        dashboard = client.get(f"/api/dashboard?user_id={user_id}")
        assert dashboard.status_code == 200
        metrics = dashboard.json()
        assert metrics["total_sessions"] == 1
        assert metrics["average_score"] >= 70
        assert metrics["stage_counts"]["new"] == 1
        assert metrics["ready_to_interview_count"] >= 0
        assert metrics["open_action_count"] == 1
        assert metrics["top_candidates"][0]["session_id"] == payload["id"]
        assert metrics["top_candidates"][0]["priority_score"] == payload["priority_score"]
        assert metrics["top_candidates"][0]["readiness_score"] == payload["readiness_score"]
        assert metrics["action_queue"][0]["session_id"] == payload["id"]
        assert metrics["action_queue"][0]["next_action"]["label"]
        assert "quality_watchlist" in metrics

        workflow = client.patch(
            f"/api/sessions/{payload['id']}/workflow",
            json={
                "pipeline_stage": "shortlisted",
                "reviewer_notes": "Strong project proof; validate Docker in interview.",
            },
        )
        assert workflow.status_code == 200
        updated = workflow.json()
        assert updated["pipeline_stage"] == "shortlisted"
        assert updated["next_action"]["label"] == "Schedule focused interview"
        assert "Docker" in updated["reviewer_notes"]
        assert updated["decision_memo"]["conditions"]

        activity = client.get(f"/api/sessions/{payload['id']}/activity")
        assert activity.status_code == 200
        assert [event["event_type"] for event in activity.json()] == [
            "workflow_updated",
            "analysis_created",
        ]

        question = client.post(
            f"/api/sessions/{payload['id']}/ask",
            json={"question": "What RAG evidence does the resume show?"},
        )
        assert question.status_code == 200
        assert question.json()["citations"]

        gap_question = client.post(
            f"/api/sessions/{payload['id']}/ask",
            json={"question": "What are the missing gaps?"},
        )
        assert gap_question.status_code == 200
        assert gap_question.json()["citations"] == []

        exported = client.get(f"/api/sessions/{payload['id']}/export")
        assert exported.status_code == 200
        assert "AI Recruiter Report" in exported.text
        assert "Decision Memo" in exported.text
        assert "Pipeline stage" in exported.text
        assert "Readiness score" in exported.text
        assert "Screening Checklist" in exported.text
        assert "Score Breakdown" in exported.text
        assert "Outreach message" in exported.text

        activity = client.get(f"/api/sessions/{payload['id']}/activity")
        assert activity.status_code == 200
        assert [event["event_type"] for event in activity.json()] == [
            "report_exported",
            "workflow_updated",
            "analysis_created",
        ]

        deleted = client.delete(f"/api/sessions/{payload['id']}")
        assert deleted.status_code == 200
        assert deleted.json()["status"] == "deleted"
