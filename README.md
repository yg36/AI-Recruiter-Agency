# AI Recruiter Agency

Local multi-agent resume analysis and candidate screening system built for recruiter-style workflows.

This project is a practical AI/ML portfolio piece: it combines resume parsing, structured profile extraction, agent orchestration, candidate-job matching, screening recommendations, local LLM usage, and a Streamlit interface.

## Why This Project Matters

Recruiters do not only need a chatbot. They need a workflow that can read messy resumes, extract structured signals, compare candidates with job criteria, explain gaps, and produce usable screening output. This repo models that workflow as a set of focused agents instead of one large prompt.

## Core Capabilities

- Resume parsing and profile extraction from candidate documents
- Multi-agent orchestration for extraction, analysis, matching, screening, and recommendations
- Local LLM workflow designed around Ollama, so sensitive resumes do not need external APIs
- Candidate-job matching against a seeded job database
- Streamlit UI for uploading resumes and reviewing structured outputs
- Logging/error-handling utilities separated from agent logic

## Agent Architecture

- Extractor agent: converts resume text into structured candidate data
- Analyzer agent: identifies skills, experience, education, strengths, and gaps
- Matcher agent: compares candidate profile against job requirements
- Screener agent: produces screening-oriented decisions and notes
- Recommender agent: suggests profile and role-fit improvements
- Orchestrator agent: coordinates the end-to-end workflow

## Tech Stack

Python, Streamlit, Ollama/local LLMs, SQLite schema/seed scripts, modular agent classes, structured logging.

## Repository Map

```text
agents/   Agent classes and orchestration logic
data/     Job data access helpers
db/       Schema and seed scripts for local job data
tools/    Supporting utilities for workflow execution
utils/    Logging and custom exceptions
app.py    Streamlit application entrypoint
```

## Run Locally

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Start Ollama locally and make sure the model used by the app is available.

3. Seed or initialize the local job database if needed:

```bash
python db/seed_jobs.py
```

4. Run the Streamlit app:

```bash
streamlit run app.py
```

## Recruiter Notes

This repo demonstrates AI system design more than UI polish: decomposition into agents, local LLM workflow design, structured candidate analysis, and a recruiter-facing product flow.

## Cleanup Done

Runtime artifacts such as virtual environments, Python caches, logs, generated results, and local SQLite files should not be committed. The repo is configured to keep source code and reproducible setup files only.
