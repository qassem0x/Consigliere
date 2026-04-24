# Consigliere 🌹 

![Consigliere](image.png)

<p>
Private AI data analyst for structured data.  
Upload files or connect a database, then ask questions in natural language and receive streamed, step-by-step analysis.
</p>


<div align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-111?logo=python" />
  <img src="https://img.shields.io/badge/FastAPI-111?logo=fastapi" />
  <img src="https://img.shields.io/badge/Docker-111?logo=docker" />
  <img src="https://img.shields.io/badge/License-MIT-111" />
</div>

## What It Does

- Conversational analytics over files and SQL databases
- Structured planning + execution pipeline (plan, query, chart, summary)
- Zero-leaks mode for privacy-sensitive outputs
- Message history, chat memory, and token accounting
- Read-focused execution and query safety checks

## Feature Highlights

- **Dual data sources:** Analyze uploaded files (CSV/XLSX -> parquet) and live SQL databases in one interface.
- **Agentic analysis workflow:** Each question is broken into steps (metrics, tables, charts, summary) before execution.
- **Streaming responses:** Results are returned progressively so users see progress in real time, not only at completion.
- **Chart generation:** The system can turn query outputs into visualizations and serve them from `static/plots`.
- **Chat-level controls:** Per-chat settings support `zero_leaks_mode`, row limits, and optional custom analysis prompt.
- **Persistent context:** Chats retain message history and rolling summary so follow-up questions stay contextual.
- **Token usage tracking:** Prompt/completion/total token counts are stored per assistant response.
- **Safety guardrails:** Query sanitization and read-only intent reduce risky SQL operations.

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy, Alembic
- **Data execution:** DuckDB (files), SQLAlchemy engines (databases)
- **LLM routing:** LiteLLM
- **Frontend:** React (in `frontend/`)
- **Infra:** Docker + docker-compose

## Quick Start (Docker)

1) Clone the repo:

```bash
git clone https://github.com/qassem0x/Consigliere.git
cd Consigliere
```

2) Create `.env`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/consigliere
SECRET_KEY=replace-with-a-long-random-secret
ENCRYPTION_KEY=replace-with-a-valid-fernet-key
MODEL_NAME=openai/gpt-4o
OPENAI_API_KEY=your-key
```

3) Run:

```bash
docker-compose up -d
```

4) Open:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Local Development

### Backend

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Model Configuration

Consigliere uses LiteLLM.  
Set `MODEL_NAME` and the matching provider API key in `.env`.

For provider-specific setup and model naming, use LiteLLM docs directly:

- [LiteLLM providers](https://docs.litellm.ai/docs/providers)
- [LiteLLM model catalog](https://models.litellm.ai/)

## Core API Routes

- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- `POST /files/upload`, `POST /files/{file_id}/analyze`
- `POST /connections`
- `GET /chats`, `POST /chats`, `PATCH /chats/{chat_id}/settings`
- `GET /messages/{chat_id}`, `POST /messages/{chat_id}` (streaming response)
- `GET /model`

## Backend Layout (`app/`)

- `app/main.py` - FastAPI app, middleware, router wiring
- `app/api/` - HTTP endpoints
- `app/core/` - config, auth, DB session, LLM wrappers, shared utilities
- `app/models/` - SQLAlchemy + request/response models
- `app/agent/` - planning, SQL generation, execution, rendering, memory
- `app/services/` - ingestion pipeline (file -> parquet)

## Typical User Flow

1. User signs in.
2. User uploads a file or creates a DB connection.
3. System builds an initial dossier.
4. User sends a message to a chat.
5. Agent plans steps, executes queries, renders charts (if needed), and streams final answer.

## Notes

- Uploaded data is processed into parquet in `data/`.
- Generated plots are served from `static/plots`.

