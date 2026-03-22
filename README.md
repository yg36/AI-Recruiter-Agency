🧠 AI Recruiter Agent
Local RAG + Multi-Agent Resume Analysis System

An intelligent, fully local AI-powered recruiter assistant that analyzes resumes, enhances candidate profiles, and generates insights using LLMs, RAG (Retrieval-Augmented Generation), and agent-based architecture — all powered by Ollama (no external APIs required).

🚀 Features
📄 Resume Parsing
Extract structured data (skills, experience, roles) from PDF resumes
🧠 AI Profile Enhancement Agent
Generates improved summaries and insights from extracted data
🔍 RAG-based Question Answering
Ask questions about resumes using vector search + LLM reasoning
🤖 Multi-Agent System
Modular agents (Orchestrator, Profile Enhancer, etc.) for scalable workflows
🏠 Fully Local LLM (Ollama)
Runs completely offline — no OpenAI API required
⚡ Interactive UI (Streamlit)
Upload resumes and query insights in a simple web interface
🏗️ Tech Stack
LLM: Ollama (Llama3, Mistral, etc.)
Embeddings: nomic-embed-text
Framework: LangChain
Vector Database: ChromaDB
Frontend: Streamlit
PDF Processing: Unstructured, pdfminer
Agents: Custom modular agent architecture
🧩 Architecture
PDF Resume
    ↓
Document Loader (Unstructured)
    ↓
Text Splitting (Chunks)
    ↓
Embeddings (Ollama)
    ↓
Vector DB (Chroma)
    ↓
Retriever (RAG)
    ↓
LLM (Ollama)
    ↓
Agent System (Enhancer / Orchestrator)
    ↓
Final Output (Insights + Summary)
💡 Use Cases
AI-powered resume screening
Candidate profile enhancement
HR automation tools
Personal career assistant
Document-based Q&A system
⚙️ Installation & Setup
1. Clone the repository
git clone https://github.com/<your-username>/ai-recruiter-agent.git
cd ai-recruiter-agent
2. Create virtual environment (Python 3.10 recommended)
python3.10 -m venv venv
venv\Scripts\activate
3. Install dependencies
pip install -r requirements.txt
4. Install & Run Ollama

Download Ollama: https://ollama.com

Pull required models:

ollama pull llama3
ollama pull nomic-embed-text
5. Run the application
streamlit run app.py

Open in browser:

http://localhost:8501
📁 Project Structure
AI-Recruiter-Agent/
│
├── app.py                     # Streamlit UI
├── agents/
│   ├── base_agent.py
│   ├── orchestrator.py
│   └── profile_enhancer.py
│
├── data/
│   └── sample_resume.pdf
│
├── chroma_db/                # Vector database
├── requirements.txt
└── README.md
🔮 Future Improvements
Resume scoring & ranking system (ATS-style)
Job description matching
Memory-enabled agents
Multi-candidate comparison dashboard
Docker deployment
API backend (FastAPI)
⚠️ Notes
Ensure Ollama is running locally (http://localhost:11434)
Use Python 3.10 for best compatibility
Avoid mixing OpenAI API unless explicitly needed
⭐ Why This Project Stands Out

Unlike basic chatbot projects, this system combines:

RAG (Retrieval-Augmented Generation)
Multi-agent architecture
Fully local LLM execution
Real-world use case (recruitment automation)

👉 End-to-end pipeline: PDF → Insights → AI-enhanced profile

👨‍💻 Author

Built with focus on:

AI systems engineering
LLM applications
Real-world ML use cases
