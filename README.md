
# IntervAI-RAG

# IntervAI-RAG: Intelligent Interviewer using Retrieval-Augmented Generation

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2014-black.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An end-to-end, adaptive, and context-aware technical interview and assessment platform powered by **Retrieval-Augmented Generation (RAG)**, hybrid vector search, and local/cloud LLMs.

---

## 🌟 Key Features

- **Hybrid RAG Pipeline**: Combines dense vector retrieval via **FAISS** with sparse retrieval via **BM25**, unified through **Reciprocal Rank Fusion (RRF)** across 8 technical domains.
- **Adaptive Difficulty Engine**: Dynamically shifts question complexity in real-time based on candidate performance metrics.
- **9-Layer Resume Validation**: Thorough parsing and multi-step validation pipeline to extract verified technical skills and project context.
- **Dual Evaluation System**:
  - **Fast Offline Semantic Evaluation**: Cosine similarity via embeddings and keyword coverage.
  - **Deep LLM Evaluation**: In-depth code logic, syntax, and conceptual reasoning assessments.
- **Three Interview Modes**:
  - Resume-Driven Technical Round
  - Manual Profile-Based Interview
  - Interactive Live Coding Assessment
- **Voice-Enabled**: Speech-to-text input with the Web Speech API.
- **Anti-Cheat & Proctoring Engine**: Monitors tab switching, copy-paste attempts, multi-display configurations, and DevTools inspections with admin violation logs.
- **Low Latency**: Background pre-generation cache for seamless question transitions.

---

## 🏗️ Architecture

```
IntervAI-RAG/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routes & endpoints
│   │   ├── core/            # Config, security, database
│   │   ├── rag/             # FAISS + BM25 Hybrid RAG engine
│   │   ├── evaluation/      # LLM & semantic grading modules
│   │   └── services/        # Resume validation & question caching
│   └── data/                # Domain documents & vector indexes
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js 14 App Router pages
│   │   ├── components/      # UI components & proctoring monitors
│   │   └── hooks/           # Voice recognition & timer hooks
├── docs/                    # Architectural diagrams & project reports
├── docker-compose.yml       # Containerized deployment
└── setup.bat / setup.sh     # Quick start scripts
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Node.js 18+** & npm / yarn
- **LM Studio** / **Ollama** (or OpenAI / Groq API key)

### Automated Setup

**Windows:**
```bat
setup.bat
```

**Linux / macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

### Manual Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Sujan0310/IntervAI-RAG.git
   cd IntervAI-RAG
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## 👥 Authors

Developed as part of the Engineering degree at **NMAM Institute of Technology, Nitte**:
- **Sujan S** ([@Sujan0310](https://github.com/Sujan0310))
- **Dhanya Kunder**
- **K Chinmaya Sharma**
- **Niharika Shetty**



---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

