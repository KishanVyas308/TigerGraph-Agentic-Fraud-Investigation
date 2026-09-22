# Local Setup & Development Guide

This guide describes how to run the TigerGraph Agentic Fraud Investigation project locally.

## Prerequisites

- **Python**: 3.11+ (Python 3.11 recommended)
- **uv**: Modern fast Python package manager (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh`)
- **Node.js**: v18+ (Node v20+ recommended)
- **TigerGraph**: Savanna cloud instance or local Docker Community Edition

## 1. Backend Setup

1. Create and activate a Python 3.11 virtual environment:
   ```bash
   uv venv --python 3.11
   source .venv/bin/activate
   ```

2. Install dependencies in editable mode:
   ```bash
   uv pip install -e ".[dev]" --python .venv/bin/python
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your TigerGraph credentials, Groq API key, and Gemini API key
   ```

4. Run unit tests:
   ```bash
   .venv/bin/pytest tests/unit -v
   ```

5. Start the FastAPI development server:
   ```bash
   .venv/bin/python -m uvicorn backend.app.main:app --reload --port 8000
   ```
   - Health check: `http://localhost:8000/health`
   - Interactive OpenAPI docs: `http://localhost:8000/docs`

## 2. Frontend Setup

1. Install frontend dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Run type checking:
   ```bash
   npm run typecheck
   ```

3. Start the Next.js dev server:
   ```bash
   npm run dev
   ```
   - Frontend console: `http://localhost:3000`

## 3. Project Structure

- `backend/app/`: FastAPI application, LangGraph agents, TigerGraph clients, RAG, and policy logic.
- `frontend/`: Next.js analyst dashboard, Cytoscape graph visualization, SSE timeline.
- `gsql/`: GSQL schemas, loading jobs, and queries.
- `data/`: Raw dataset (`data/raw/`), preprocessed Parquet tables (`data/processed/`), policies (`data/policies/`), and benchmark cases (`data/benchmark/`).
- `scripts/`: Dataset inspection, preprocessing, and benchmark runner scripts.
- `tests/`: Unit, integration, and benchmark tests.
- `outputs/`: Output traces, SAR reports, and benchmark answer files.
