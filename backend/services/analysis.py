from __future__ import annotations

from .text_processing import (
    chunk_sources,
    extract_skills,
    find_skill_sentence,
    parse_job_description,
    parse_resume,
    retrieve_chunks,
    tokenize,
)


def percent(part: int | float, whole: int | float) -> int:
    if not whole:
        return 100
    return min(100, round((part / whole) * 100))


def score_match(parsed_resume: dict, parsed_jd: dict, resume_text: str, jd_text: str) -> dict:
    resume_skills = set(parsed_resume["skills"])
    must_have = set(parsed_jd["must_have_skills"])
    nice_to_have = set(parsed_jd["nice_to_have_skills"])

    matched_must = sorted(resume_skills & must_have)
    missing_must = sorted(must_have - resume_skills)
    matched_nice = sorted(resume_skills & nice_to_have)
    missing_nice = sorted(nice_to_have - resume_skills)

    must_score = round((len(matched_must) / len(must_have)) * 60) if must_have else 35
    nice_score = round((len(matched_nice) / len(nice_to_have)) * 15) if nice_to_have else 10

    resume_tokens = set(tokenize(resume_text))
    responsibility_hits = 0
    responsibilities = parsed_jd.get("responsibilities", [])
    for responsibility in responsibilities:
        important_tokens = {token for token in tokenize(responsibility) if len(token) > 4}
        if important_tokens and len(important_tokens & resume_tokens) >= 2:
            responsibility_hits += 1
    responsibility_score = (
        round((responsibility_hits / len(responsibilities)) * 15) if responsibilities else 10
    )

    years = parsed_resume.get("estimated_years_experience", 0)
    seniority = parsed_jd.get("seniority", "Fresher/Junior")
    if seniority == "Senior":
        seniority_score = 10 if years >= 5 else 4
    elif seniority == "Mid-level":
        seniority_score = 10 if years >= 2 else 7
    else:
        seniority_score = 10

    score_breakdown = [
        {
            "label": "Must-have skills",
            "earned": must_score,
            "max": 60,
            "detail": f"{len(matched_must)}/{len(must_have)} required skills matched",
        },
        {
            "label": "Nice-to-have skills",
            "earned": nice_score,
            "max": 15,
            "detail": f"{len(matched_nice)}/{len(nice_to_have)} preferred skills matched",
        },
        {
            "label": "Responsibility evidence",
            "earned": responsibility_score,
            "max": 15,
            "detail": f"{responsibility_hits}/{len(responsibilities)} role responsibilities evidenced",
        },
        {
            "label": "Seniority alignment",
            "earned": seniority_score,
            "max": 10,
            "detail": f"Resume experience checked against {seniority} seniority",
        },
    ]
    score = min(100, sum(item["earned"] for item in score_breakdown))
    matched_skills = sorted((resume_skills & (must_have | nice_to_have)) or resume_skills)
    missing_skills = sorted((must_have | nice_to_have) - resume_skills)

    evidence = []
    for skill in matched_skills[:5]:
        resume_sentence = find_skill_sentence(resume_text, skill)
        jd_sentence = find_skill_sentence(jd_text, skill)
        if resume_sentence:
            evidence.append(
                {"source": "resume", "label": f"Resume evidence for {skill}", "text": resume_sentence}
            )
        if jd_sentence:
            evidence.append(
                {
                    "source": "job_description",
                    "label": f"JD evidence for {skill}",
                    "text": jd_sentence,
                }
            )

    if score >= 75:
        fit_label = "Strong fit"
    elif score >= 55:
        fit_label = "Moderate fit"
    else:
        fit_label = "Needs focused improvement"

    risk_flags = build_risk_flags(
        parsed_resume=parsed_resume,
        parsed_jd=parsed_jd,
        missing_must=missing_must,
        missing_nice=missing_nice,
        responsibility_hits=responsibility_hits,
    )
    confidence = estimate_analysis_confidence(
        resume_text=resume_text,
        jd_text=jd_text,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
    )

    return {
        "score": int(score),
        "fit_label": fit_label,
        "confidence": confidence,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "matched_must_have": matched_must,
        "missing_must_have": missing_must,
        "matched_nice_to_have": matched_nice,
        "missing_nice_to_have": missing_nice,
        "explanation": (
            f"{fit_label}: matched {len(matched_must)}/{len(must_have)} must-have skills "
            f"and {len(matched_nice)}/{len(nice_to_have)} nice-to-have skills."
        ),
        "score_breakdown": score_breakdown,
        "coverage": {
            "must_have": percent(len(matched_must), len(must_have)),
            "nice_to_have": percent(len(matched_nice), len(nice_to_have)),
            "responsibilities": percent(responsibility_hits, len(responsibilities)),
        },
        "risk_flags": risk_flags,
        "evidence": evidence[:8],
    }


def build_risk_flags(
    parsed_resume: dict,
    parsed_jd: dict,
    missing_must: list[str],
    missing_nice: list[str],
    responsibility_hits: int,
) -> list[dict]:
    flags: list[dict] = []
    responsibilities = parsed_jd.get("responsibilities", [])
    contact = parsed_resume.get("personal_info", {})

    if missing_must:
        flags.append(
            {
                "severity": "high",
                "title": "Missing must-have evidence",
                "detail": "Add concrete resume/project proof for " + ", ".join(missing_must[:4]) + ".",
            }
        )
    if responsibilities and responsibility_hits < max(1, len(responsibilities) // 2):
        flags.append(
            {
                "severity": "medium",
                "title": "Weak responsibility coverage",
                "detail": "The resume does not clearly mirror enough day-to-day responsibilities from the JD.",
            }
        )
    if not parsed_resume.get("projects"):
        flags.append(
            {
                "severity": "medium",
                "title": "Project section is thin",
                "detail": "Add 1-2 shipped projects with stack, architecture, deployment, and measurable impact.",
            }
        )
    if not contact.get("email") or not contact.get("github"):
        flags.append(
            {
                "severity": "low",
                "title": "Contact proof can improve",
                "detail": "Include email plus GitHub or portfolio link so a reviewer can verify work quickly.",
            }
        )
    if len(missing_nice) >= 3:
        flags.append(
            {
                "severity": "low",
                "title": "Preferred skills gap",
                "detail": "Preferred skills are not blockers, but they are useful tie-breakers in fresher hiring.",
            }
        )

    return flags


def estimate_analysis_confidence(
    resume_text: str,
    jd_text: str,
    matched_skills: list[str],
    missing_skills: list[str],
) -> int:
    confidence = 55
    if len(resume_text) > 500:
        confidence += 15
    if len(jd_text) > 250:
        confidence += 10
    if matched_skills:
        confidence += 10
    if len(matched_skills) + len(missing_skills) >= 5:
        confidence += 10
    return min(confidence, 95)


def generate_interview_plan(parsed_resume: dict, parsed_jd: dict, match_result: dict) -> dict:
    matched = match_result["matched_skills"]
    missing = match_result["missing_skills"]
    role_title = parsed_jd.get("title", "this role")
    primary_skills = (matched + parsed_jd.get("must_have_skills", []))[:5]

    technical = [
        f"Explain how you used {skill} in a project and what tradeoff you made."
        for skill in primary_skills[:4]
    ]
    technical += [
        f"What would you learn or build first to close the gap in {skill}?"
        for skill in missing[:3]
    ]

    project_context = parsed_resume.get("projects") or [parsed_resume.get("summary", "your main project")]
    project = project_context[0][:120]

    return {
        "technical": technical[:6],
        "project": [
            f"Walk me through the architecture of {project}.",
            "Where did you handle failure states, validation, or logging?",
            "How would you measure retrieval or matching quality for this project?",
        ],
        "behavioral": [
            "Tell me about a time you learned a technical topic quickly under time pressure.",
            "How do you prioritize when project work, internship tasks, and preparation overlap?",
            "Describe a situation where feedback changed your implementation.",
        ],
        "ai_application": [
            "How do embeddings, chunking, and vector search work together in a RAG system?",
            "How would you reduce hallucinations in a recruiter assistant?",
            f"What would you monitor after deploying an AI assistant for {role_title} screening?",
        ],
    }


def generate_feedback(parsed_resume: dict, parsed_jd: dict, match_result: dict) -> dict:
    matched = match_result["matched_skills"]
    missing = match_result["missing_skills"]
    strengths = [
        f"Strong evidence for {skill}." for skill in matched[:5]
    ] or ["Resume has enough text to begin structured screening."]
    weaknesses = [
        f"Add project or work evidence for {skill}." for skill in missing[:5]
    ] or ["No major must-have skill gaps detected by the parser."]
    next_steps = [
        "Add quantified bullets that mention architecture, API routes, database schema, and deployment.",
        "Prepare one clear story for RAG quality: chunking, retrieval, citations, and failure handling.",
        "Keep a concise exportable report for recruiter review.",
    ]
    if missing:
        next_steps.insert(0, f"Build a small proof around {missing[0]} and add it to the project README.")

    role_title = parsed_jd.get("title", "the role")
    top_matched = matched[:3] or parsed_resume.get("skills", [])[:3]
    primary_gap = missing[0] if missing else "deployment polish"
    project = (parsed_resume.get("projects") or ["AI recruiter workflow"])[0]
    tailored_resume_bullets = [
        (
            f"Built an AI recruiter assistant for {role_title} workflows using "
            f"{', '.join(top_matched) or 'full-stack AI tooling'}, producing cited match reports and interview plans."
        ),
        (
            f"Improved candidate screening explainability with structured skill matching, evidence snippets, "
            f"risk flags, and exportable recruiter summaries."
        ),
        (
            f"Extended {project[:90]} with backend validation, SQL persistence, and privacy-first session deletion."
        ),
    ]
    outreach_message = (
        f"Hi, I built a full-stack AI recruiter assistant aligned with {role_title} work: resume/JD parsing, "
        f"evidence-based scoring, grounded Q&A, interview planning, and exportable feedback. "
        f"My strongest overlap is {', '.join(top_matched) if top_matched else 'AI application development'}, "
        f"and I am currently strengthening {primary_gap}. I would value a chance to discuss the project."
    )
    learning_plan = build_learning_plan(missing)

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "next_steps": next_steps,
        "tailored_resume_bullets": tailored_resume_bullets,
        "outreach_message": outreach_message,
        "learning_plan": learning_plan,
        "role_fit_summary": (
            f"{match_result['fit_label']} for {parsed_jd.get('title', 'the role')} "
            f"with a {match_result['score']}% evidence-based score."
        ),
    }


def build_learning_plan(missing: list[str]) -> list[dict]:
    focus_items = missing[:4] or ["deployment", "testing", "retrieval evaluation", "system design"]
    return [
        {
            "day": index + 1,
            "focus": skill,
            "output": f"Add one concrete proof point for {skill} to the project or README.",
        }
        for index, skill in enumerate(focus_items)
    ]


def analyze_application(resume_text: str, jd_text: str) -> dict:
    parsed_resume = parse_resume(resume_text)
    parsed_jd = parse_job_description(jd_text)
    chunks = chunk_sources(resume_text, jd_text)
    match_result = score_match(parsed_resume, parsed_jd, resume_text, jd_text)
    interview_plan = generate_interview_plan(parsed_resume, parsed_jd, match_result)
    feedback_report = generate_feedback(parsed_resume, parsed_jd, match_result)

    return {
        "parsed_resume": parsed_resume,
        "parsed_jd": parsed_jd,
        "chunks": chunks,
        "match_result": match_result,
        "interview_plan": interview_plan,
        "feedback_report": feedback_report,
    }


def answer_question(question: str, chunks: list[dict], session_context: dict | None = None) -> dict:
    lowered = question.lower()
    if session_context:
        match = session_context.get("match_result", {})
        feedback = session_context.get("feedback_report", {})
        if any(word in lowered for word in ("score", "fit", "match")):
            return {
                "answer": (
                    f"The current match is {match.get('score', 0)}% ({match.get('fit_label', 'unknown')}). "
                    f"{match.get('explanation', '')} Analysis confidence is {match.get('confidence', 0)}%."
                ),
                "citations": [],
            }
        if any(word in lowered for word in ("gap", "missing", "weak", "improve")):
            missing = match.get("missing_skills", [])
            next_steps = feedback.get("next_steps", [])
            answer = "Main gaps: " + (", ".join(missing) if missing else "no major required skill gaps detected")
            if next_steps:
                answer += f". Best next step: {next_steps[0]}"
            return {"answer": answer, "citations": []}
        if any(word in lowered for word in ("resume bullet", "rewrite", "bullet")):
            bullets = feedback.get("tailored_resume_bullets", [])
            return {
                "answer": " ".join(f"{index + 1}. {bullet}" for index, bullet in enumerate(bullets)),
                "citations": [],
            }

    citations = retrieve_chunks(question, chunks)
    if not citations:
        return {
            "answer": "I could not find enough resume or job-description evidence to answer that.",
            "citations": [],
        }

    resume_points = [chunk["text"] for chunk in citations if chunk["source"] == "resume"]
    jd_points = [chunk["text"] for chunk in citations if chunk["source"] == "job_description"]
    parts = []
    if resume_points:
        parts.append(f"Resume evidence: {resume_points[0]}")
    if jd_points:
        parts.append(f"JD evidence: {jd_points[0]}")
    if len(citations) > 1:
        parts.append("The remaining cited snippets add supporting context for the same answer.")

    return {"answer": " ".join(parts), "citations": citations}


def export_report(session: dict) -> str:
    match = session["match_result"]
    feedback = session["feedback_report"]
    interview = session["interview_plan"]
    parsed_jd = session["parsed_jd"]
    decision = session.get("decision_memo", {})
    screening_check_lines = [
        f"- [{item['status'].upper()}] {item['label']}: {item['detail']}"
        for item in session.get("screening_checks", [])
    ]
    breakdown_lines = [
        f"- {item['label']}: {item['earned']}/{item['max']} - {item['detail']}"
        for item in match.get("score_breakdown", [])
    ]
    risk_lines = [
        f"- [{item['severity'].upper()}] {item['title']}: {item['detail']}"
        for item in match.get("risk_flags", [])
    ] or ["No major risk flags detected."]
    tailored_bullet_lines = [
        f"- {item}" for item in feedback.get("tailored_resume_bullets", [])
    ]

    lines = [
        f"# AI Recruiter Report: {parsed_jd.get('title', session['job_title'])}",
        "",
        f"Match score: {match['score']}% ({match['fit_label']})",
        f"Readiness score: {session.get('readiness_score', 0)}% ({session.get('readiness_label', 'not_ready').replace('_', ' ')})",
        f"Pipeline stage: {session.get('pipeline_stage', 'new')}",
        "",
        "## Decision Memo",
        f"Recommendation: {decision.get('recommendation', 'not_generated')}",
        f"Rationale: {decision.get('rationale', 'No rationale generated.')}",
        "Conditions:",
        *[f"- {item}" for item in decision.get("conditions", [])],
        "",
        "Reviewer notes:",
        session.get("reviewer_notes") or "No reviewer notes.",
        "",
        "## Screening Checklist",
        *screening_check_lines,
        "",
        "## Match Summary",
        match["explanation"],
        "",
        "## Score Breakdown",
        *breakdown_lines,
        "",
        "## Risk Flags",
        *risk_lines,
        "",
        "## Matched Skills",
        ", ".join(match["matched_skills"]) or "None detected",
        "",
        "## Missing Skills",
        ", ".join(match["missing_skills"]) or "None detected",
        "",
        "## Feedback",
        feedback["role_fit_summary"],
        "",
        "Strengths:",
        *[f"- {item}" for item in feedback["strengths"]],
        "",
        "Gaps:",
        *[f"- {item}" for item in feedback["weaknesses"]],
        "",
        "Next steps:",
        *[f"- {item}" for item in feedback["next_steps"]],
        "",
        "Tailored resume bullets:",
        *tailored_bullet_lines,
        "",
        "Outreach message:",
        feedback.get("outreach_message", "Not generated."),
        "",
        "## Interview Plan",
    ]
    for category, questions in interview.items():
        lines.append(f"### {category.replace('_', ' ').title()}")
        lines.extend(f"- {question}" for question in questions)
        lines.append("")
    return "\n".join(lines).strip() + "\n"
