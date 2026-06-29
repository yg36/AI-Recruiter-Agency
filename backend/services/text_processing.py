from __future__ import annotations

from collections import Counter
import re
from pathlib import Path

from pdfminer.high_level import extract_text as extract_pdfminer_text


SKILL_LIBRARY: dict[str, list[str]] = {
    "Python": ["python", "python3"],
    "JavaScript": ["javascript", "js", "ecmascript"],
    "TypeScript": ["typescript", "ts"],
    "React": ["react", "react.js", "reactjs"],
    "Next.js": ["next.js", "nextjs", "next js"],
    "Node.js": ["node.js", "nodejs", "node js"],
    "FastAPI": ["fastapi", "fast api"],
    "Flask": ["flask"],
    "Django": ["django"],
    "SQL": ["sql", "postgresql", "postgres", "mysql", "sqlite"],
    "PostgreSQL": ["postgresql", "postgres", "supabase", "neon"],
    "MongoDB": ["mongodb", "mongo"],
    "REST APIs": ["rest api", "rest apis", "restful", "api development", "apis"],
    "GraphQL": ["graphql"],
    "Docker": ["docker", "containerization"],
    "AWS": ["aws", "amazon web services"],
    "GCP": ["gcp", "google cloud"],
    "Azure": ["azure"],
    "Git": ["git", "github", "gitlab"],
    "CI/CD": ["ci/cd", "github actions", "continuous integration"],
    "LangChain": ["langchain", "lang chain"],
    "RAG": ["rag", "retrieval augmented generation", "retrieval-augmented generation"],
    "FAISS": ["faiss"],
    "Vector Search": ["vector search", "vector database", "vector db", "embeddings", "faiss"],
    "OpenAI API": ["openai", "openai api", "gpt"],
    "Gemini API": ["gemini", "gemini api"],
    "Ollama": ["ollama"],
    "Machine Learning": ["machine learning", "ml"],
    "Deep Learning": ["deep learning", "neural network", "neural networks"],
    "NLP": ["nlp", "natural language processing"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Scikit-learn": ["scikit-learn", "sklearn"],
    "PyTorch": ["pytorch", "torch"],
    "TensorFlow": ["tensorflow"],
    "Tailwind CSS": ["tailwind", "tailwind css"],
    "HTML": ["html", "html5"],
    "CSS": ["css", "css3"],
    "Testing": ["pytest", "unit testing", "integration testing", "jest", "testing"],
    "Auth": ["auth", "authentication", "authorization", "oauth", "jwt"],
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
    "you",
    "your",
}


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_resume_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        text = extract_pdfminer_text(str(file_path))
    else:
        text = file_path.read_text(encoding="utf-8", errors="ignore")

    text = clean_text(text)
    if not text:
        raise ValueError("Could not extract readable text from the uploaded resume.")
    return text


def split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+|\n+", clean_text(text))
    return [piece.strip(" -\t") for piece in pieces if len(piece.strip()) > 20]


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.:-]*", text.lower())
        if token not in STOPWORDS and len(token) > 1
    ]


def extract_skills(text: str) -> list[str]:
    lowered = f" {text.lower()} "
    found: set[str] = set()
    for canonical, aliases in SKILL_LIBRARY.items():
        for alias in aliases:
            alias_lower = alias.lower()
            if any(char in alias_lower for char in ".+#/"):
                matched = alias_lower in lowered
            else:
                matched = re.search(rf"(?<![a-z0-9+#]){re.escape(alias_lower)}(?![a-z0-9+#])", lowered)
            if matched:
                found.add(canonical)
                break
    return sorted(expand_related_skills(found))


def expand_related_skills(skills: set[str]) -> set[str]:
    expanded = set(skills)
    if expanded & {"FastAPI", "Flask", "Django", "Node.js"}:
        expanded.add("REST APIs")
    if "FAISS" in expanded:
        expanded.add("Vector Search")
    return expanded


def extract_contact(text: str) -> dict[str, str | None]:
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    phone_match = re.search(r"(?:(?:\+91[\s-]?)|0)?[6-9]\d{9}", text)
    linkedin_match = re.search(r"https?://(?:www\.)?linkedin\.com/[^\s)]+", text, re.I)
    github_match = re.search(r"https?://(?:www\.)?github\.com/[^\s)]+", text, re.I)
    return {
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0) if phone_match else None,
        "linkedin": linkedin_match.group(0) if linkedin_match else None,
        "github": github_match.group(0) if github_match else None,
    }


def extract_name(text: str) -> str | None:
    for line in clean_text(text).splitlines()[:8]:
        candidate = line.strip(" |-\t")
        if (
            2 <= len(candidate.split()) <= 4
            and not re.search(r"@|http|resume|curriculum|developer|engineer", candidate, re.I)
            and re.search(r"[A-Za-z]", candidate)
        ):
            return candidate
    return None


def section_lines(text: str, keywords: tuple[str, ...], limit: int = 8) -> list[str]:
    lines = [line.strip(" -\t") for line in clean_text(text).splitlines() if line.strip()]
    matches: list[str] = []
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            matches.append(line)
        if len(matches) >= limit:
            break
    return matches


def estimate_years(text: str) -> float:
    year_matches = re.findall(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs|year)", text, re.I)
    if not year_matches:
        return 0.0
    return max(float(value) for value in year_matches)


def parse_resume(text: str) -> dict:
    skills = extract_skills(text)
    return {
        "personal_info": {
            "name": extract_name(text),
            **extract_contact(text),
        },
        "skills": skills,
        "experience": section_lines(
            text,
            ("experience", "intern", "engineer", "developer", "worked", "built", "implemented"),
        ),
        "education": section_lines(text, ("education", "b.tech", "btech", "bachelor", "cgpa", "gpa", "university")),
        "projects": section_lines(text, ("project", "rag", "ai", "ml", "application", "platform", "dashboard")),
        "estimated_years_experience": estimate_years(text),
        "summary": clean_text(text)[:700],
    }


def sentence_skills(sentence: str) -> set[str]:
    return set(extract_skills(sentence))


def parse_job_description(text: str) -> dict:
    sentences = split_sentences(text)
    all_skills = set(extract_skills(text))
    must_keywords = ("must", "required", "requirement", "need", "strong", "proficient", "mandatory")
    nice_keywords = ("nice", "preferred", "bonus", "good to have", "plus")

    must_have: set[str] = set()
    nice_to_have: set[str] = set()
    responsibilities: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        skills = sentence_skills(sentence)
        if skills and any(keyword in lowered for keyword in must_keywords):
            must_have.update(skills)
        if skills and any(keyword in lowered for keyword in nice_keywords):
            nice_to_have.update(skills)
        if re.search(r"\b(build|develop|design|integrate|deploy|maintain|own|collaborate|implement)\b", lowered):
            responsibilities.append(sentence)

    if not must_have:
        must_have = set(sorted(all_skills)[:8])
    nice_to_have = nice_to_have - must_have

    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "Untitled role")
    title = re.sub(r"^(job title|role|position)\s*[:\-]\s*", "", first_line, flags=re.I)[:120]

    lowered = text.lower()
    if re.search(r"\b(senior|lead|5\+|6\+|7\+)\b", lowered):
        seniority = "Senior"
    elif re.search(r"\b(mid|2\+|3\+|4\+)\b", lowered):
        seniority = "Mid-level"
    else:
        seniority = "Fresher/Junior"

    return {
        "title": title or "Untitled role",
        "must_have_skills": sorted(must_have),
        "nice_to_have_skills": sorted(nice_to_have),
        "all_detected_skills": sorted(all_skills),
        "responsibilities": responsibilities[:8],
        "seniority": seniority,
        "summary": clean_text(text)[:700],
    }


def chunk_sources(resume_text: str, jd_text: str, max_chars: int = 550) -> list[dict]:
    chunks: list[dict] = []
    for source, text in (("resume", resume_text), ("job_description", jd_text)):
        current = ""
        ordinal = 1
        for sentence in split_sentences(text):
            if current and len(current) + len(sentence) + 1 > max_chars:
                chunks.append({"source": source, "ordinal": ordinal, "text": current.strip()})
                ordinal += 1
                current = ""
            current = f"{current} {sentence}".strip()
        if current:
            chunks.append({"source": source, "ordinal": ordinal, "text": current.strip()})
    return chunks


def retrieve_chunks(question: str, chunks: list[dict], limit: int = 4) -> list[dict]:
    question_tokens = Counter(tokenize(question))
    if not question_tokens:
        return chunks[:limit]

    scored: list[tuple[float, dict]] = []
    for chunk in chunks:
        chunk_tokens = Counter(tokenize(chunk["text"]))
        overlap = sum(min(count, chunk_tokens[token]) for token, count in question_tokens.items())
        skill_bonus = len(set(extract_skills(question)) & set(extract_skills(chunk["text"])))
        score = overlap + (skill_bonus * 3)
        if score:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:limit]] or chunks[:limit]


def find_skill_sentence(text: str, skill: str) -> str | None:
    for sentence in split_sentences(text):
        if skill in extract_skills(sentence):
            return sentence
    return None
