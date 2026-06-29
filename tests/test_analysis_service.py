from backend.services.analysis import analyze_application, answer_question


RESUME_TEXT = """
Yogita Gupta
yogita@example.com
B.Tech Computer Science, GPA 8.72
Built a RAG interview assistant with Python, FastAPI, React, LangChain, FAISS, SQL, and OpenAI API.
Worked as AI/ML intern and implemented dashboards with Next.js and Tailwind CSS.
"""

JD_TEXT = """
Role: AI Application Engineer
Required skills: Python, FastAPI, React, SQL, RAG, vector search, REST APIs.
Preferred: PostgreSQL, Docker, testing.
Build, deploy, and maintain LLM-powered recruiter workflows with citations and feedback reports.
"""


def test_analyze_application_returns_grounded_match():
    result = analyze_application(RESUME_TEXT, JD_TEXT)

    assert result["match_result"]["score"] >= 70
    assert "Python" in result["match_result"]["matched_skills"]
    assert "FastAPI" in result["parsed_jd"]["must_have_skills"]
    assert result["match_result"]["score_breakdown"]
    assert result["match_result"]["confidence"] >= 70
    assert "risk_flags" in result["match_result"]
    assert result["feedback_report"]["tailored_resume_bullets"]
    assert result["feedback_report"]["outreach_message"]
    assert result["feedback_report"]["learning_plan"]
    assert result["interview_plan"]["technical"]
    assert result["feedback_report"]["role_fit_summary"]
    assert result["chunks"]


def test_answer_question_returns_citations():
    result = analyze_application(RESUME_TEXT, JD_TEXT)
    answer = answer_question("What RAG experience does the candidate have?", result["chunks"])

    assert "Resume evidence" in answer["answer"]
    assert answer["citations"]
    assert answer["citations"][0]["source"] in {"resume", "job_description"}


def test_answer_question_uses_session_context_for_gaps():
    result = analyze_application(RESUME_TEXT, JD_TEXT)
    context = {
        "match_result": result["match_result"],
        "feedback_report": result["feedback_report"],
    }
    answer = answer_question("What are the missing gaps?", result["chunks"], context)

    assert "Main gaps" in answer["answer"]
    assert answer["citations"] == []
