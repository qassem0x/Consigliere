# Consigliere

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

# LLM Provider (at least one required)
GROQ_API_KEY=your-groq-key          # Recommended: groq/llama-3.3-70b-versatile
# or
OPENROUTER_API_KEY=your-openrouter-key
# or
GEMINI_API_KEY=your-gemini-key
# or
GOOGLE_API_KEY=your-google-key
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
- **SQL Database Support**: Connect directly to PostgreSQL, MySQL, SQLite

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SECRET_KEY` | Yes | JWT signing key (32+ chars) |
| `ENCRYPTION_KEY` | Yes | Data encryption key (32 chars) |
| `MODEL_NAME` | No | LLM model (default: groq/llama-3.3-70b-versatile) |
| `GROQ_API_KEY` | No | Groq API key |
| `OPENROUTER_API_KEY` | No | OpenRouter API key |
| `GEMINI_API_KEY` | No | Google Gemini API key |
| `CORS_ORIGINS` | No | Allowed origins (comma-separated) |
