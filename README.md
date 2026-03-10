# 🌹 Consigliere

![Consigliere](image.png)

Your private AI data analyst. Upload files or connect databases, then query your data using natural language.

## Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/qassem0x/Consigliere.git
cd Consigliere
```

### 2. Environment Variables

Create a `.env` file:

```env
# Required
DATABASE_URL=postgresql://user:password@localhost:5432/consigliere
SECRET_KEY=your-secret-key-min-32-chars-long-here
ENCRYPTION_KEY=your-encryption-key-exactly-32-chars

# LLM Configuration (LiteLLM supports 100+ models)
# See full model list: https://docs.litellm.ai/docs/providers
MODEL_NAME=openai/gpt-4o

# Provider API Keys (at least one required based on your model)
OPENAI_API_KEY=your-openai-key
# or
ANTHROPIC_API_KEY=your-anthropic-key
# or
GEMINI_API_KEY=your-gemini-key
# or
DEEPSEEK_API_KEY=your-deepseek-key
# or
MISTRAL_API_KEY=your-mistral-key
# or
XAI_API_KEY=your-xai-key
```

### 3. Run with Docker

```bash
docker-compose up -d
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- pgAdmin: http://localhost:5050 (admin@admin.com / admin)

### 4. Or Run Locally

**Backend:**
```bash
pip install -r requirements.txt
python -m app.database.schema   # Run schema.sql in your DB
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Usage

1. Register a new account
2. Upload an Excel/CSV/Parquet file or connect a database
3. Ask questions in natural language

## Features

- **Zero-Leaks Mode**: Prevents sensitive data from appearing in AI responses
- **Streaming Responses**: See results in real-time
- **Conversation History**: Maintains context across queries
- **SQL Database Support**: Connect directly to PostgreSQL and MySQL (Read-Only Connection)

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | JWT signing key (32+ chars) |
| `ENCRYPTION_KEY` | Yes | Data encryption key (32 chars) |
| `MODEL_NAME` | No | LLM model (default: openai/gpt-4o) |
| `OPENAI_API_KEY` | No | OpenAI API key |
| `ANTHROPIC_API_KEY` | No | Anthropic API key |
| `GEMINI_API_KEY` | No | Google Gemini API key |
| `DEEPSEEK_API_KEY` | No | DeepSeek API key |
| `MISTRAL_API_KEY` | No | Mistral API key |
| `XAI_API_KEY` | No | xAI (Grok) API key |
| `CORS_ORIGINS` | No | Allowed origins (comma-separated) |

## Supported Models

Consigliere uses LiteLLM to support 100+ models. Here are the 10 most popular ones:

| # | Model | LiteLLM Name |
|---|-------|--------------|
| 1 | OpenAI GPT-4o | `openai/gpt-4o` |
| 2 | OpenAI GPT-4o-mini | `openai/gpt-4o-mini` |
| 3 | Anthropic Claude Sonnet 4.5 | `anthropic/claude-sonnet-4-5` |
| 4 | Anthropic Claude Haiku 4 | `anthropic/claude-haiku-4-5` |
| 5 | Google Gemini 2.0 Flash | `google/gemini-2.0-flash-001` |
| 6 | Google Gemini 1.5 Pro | `google/gemini-1.5-pro` |
| 7 | Meta Llama 3.3 70B | `meta-llama/llama-3.3-70b-instruct` |
| 8 | DeepSeek V3 | `deepseek/deepseek-chat` |
| 9 | Mistral Large | `mistral/mistral-large` |
| 10 | xAI Grok 3 | `xai/grok-3` |

For the complete list of 100+ models, visit: https://models.litellm.ai/
