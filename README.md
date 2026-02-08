# 🕵️‍♂️ Consigliere - Your Private AI Data Analyst
![Consigliere Landing Page](image.png)

**Consigliere** is a self-hosted, open-source AI data analyst designed for absolute privacy. It solves the security risk of uploading sensitive company files to public chatbots like ChatGPT. Instead of sending your data to the cloud, it runs **locally** on your machine or private server.

## 🎯 Why Consigliere?

- **⚡ Zero-Cloud Dependency**: Only schema (column names) sent to AI
- **💬 Natural Language**: Chat with your data using plain English
- **📊 Smart Visualizations**: AI generates charts and tables automatically
- **🏠 Self-Hosted**: Run locally or on your private server
- **🔒 Absolute Privacy**: Your data never leaves your environment
- **🔐 Enterprise Security**: JWT authentication with user isolation

## 🚀 Key Features

### **Privacy-First Architecture**
- **Local Processing**: All computations happen on your infrastructure
- **Schema-Only AI**: Only column names and structure sent to external AI
- **Read-Only Operations**: Your original datasets are never modified
- **Secure Code Execution**: Sandboxed Python environment with security controls

### **AI-Powered Analysis**
- **Multi-LLM Support**: OpenRouter, Google Gemini, local models via LiteLLM
- **Intent Classification**: Smart routing between data analysis and general chat
- **Context Awareness**: Follow-up questions with conversation history
- **Dynamic Code Generation**: Python/pandas code written and executed securely

### **Data Intelligence**
- **Automated Dossiers**: Instant data profiling with insights
- **Interactive Tables**: Sort, filter, and export query results
- **Smart Visualizations**: Automatic chart generation with proper labels
- **Multiple Formats**: Support for CSV, Excel files with Parquet optimization

### **Enterprise Features**
- **Multi-User Support**: JWT authentication with bcrypt security
- **Data Isolation**: User-specific access controls
- **PostgreSQL Backend**: Scalable database with UUID-based architecture
- **Modern UI**: React 19 with TypeScript and Tailwind CSS

## 🏗️ Architecture

```
Consigliere/
├── app/                    # FastAPI Backend
│   ├── api/               # API Routes (auth, chats, files, messages)
│   ├── services/          # Core Services (agent, ingestion, cache)
│   ├── database/          # PostgreSQL Schema
│   └── main.py           # FastAPI Application Entry
├── frontend/              # Next.js/React Frontend
│   ├── src/
│   │   ├── components/   # React Components
│   │   ├── pages/       # Application Pages
│   │   └── hooks/       # Custom Hooks
├── data/                 # User Data (Parquet format)
├── static/               # Generated Visualizations
└── docker-compose.yml    # Development Infrastructure
```

## 🛠️ Technology Stack

### **Backend**
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Primary database with UUID extensions
- **SQLAlchemy** - ORM and database operations
- **LiteLLM** - Multi-provider LLM integration
- **Pandas/NumPy** - Data manipulation and analysis
- **Matplotlib** - Visualization generation
- **PyArrow** - Parquet file format support

### **Frontend**
- **React 19** with TypeScript
- **Vite** - Build tool and development server
- **React Router** - Client-side routing
- **Tailwind CSS** - Utility-first styling
- **Lucide React** - Icon library
- **Axios** - HTTP client for API communication

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- PostgreSQL 15+
- Docker & Docker Compose

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/qassem0x/consigliere.git
   cd consigliere
   ```

2. **Set up the backend**
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start the database**
   ```bash
   docker-compose up -d
   ```

5. **Run the backend**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Set up the frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

7. **Access Consigliere**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## ⚙️ Configuration

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/consigliere

# Authentication
SECRET_KEY=your-super-secret-jwt-key

# AI Providers (choose one or more)
OPENROUTER_API_KEY=your-openrouter-key
GOOGLE_API_KEY=your-google-ai-key

# Model Configuration
MODEL_NAME=gemini/gemma-3-27b-it
```

### AI Provider Setup

#### OpenRouter (Recommended)
1. Sign up at [OpenRouter](https://openrouter.ai/)
2. Get your API key
3. Set `OPENROUTER_API_KEY` in your environment
4. Use models like `anthropic/claude-3-haiku` or `openai/gpt-4o-mini`

#### Google AI (Gemini)
1. Get API key from [Google AI Studio](https://aistudio.google.com/)
2. Set `GOOGLE_API_KEY` in your environment
3. Use models like `gemini/gemma-3-27b-it`

## 📖 Usage Guide

### 1. **Upload Your Data**
- Supported formats: CSV, Excel (.xlsx, .xls)
- Files are automatically converted to optimized Parquet format
- Data profiling generates instant insights

### 2. **Start Conversations**
```text
"Show me top sales by region"
"What's the average order value?"
"Create a chart of monthly revenue"
"Find customers with highest lifetime value"
```

### 3. **Export Results**
- Download query results as CSV
- Save generated visualizations
- Export data intelligence dossiers

### 4. **Collaborate**
- Multiple users with separate accounts
- Chat history and session management
- Share insights within your organization

## 🔒 Security Features

### **Data Protection**
- **Local Processing**: No data sent to external services
- **Schema-Only AI**: Only structure information shared with LLMs
- **Encryption**: JWT tokens and bcrypt password hashing
- **Isolation**: User-specific data access controls

### **Code Execution Security**
- **Sandboxed Environment**: Restricted Python execution
- **Banned Operations**: File access, system calls, network operations
- **Input Validation**: Comprehensive parameter checking
- **Error Handling**: Graceful failure with security logging

### **Access Control**
- **JWT Authentication**: Token-based user sessions
- **Role-Based Access**: Configurable user permissions
- **Audit Trail**: Complete conversation and action logging

## 🐳 Docker Deployment

### Production Docker Setup
```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Configuration
```yaml
# docker-compose.prod.yml
services:
  backend:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY=${SECRET_KEY}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    ports:
      - "8000:8000"
```

## 🔧 Development

### Backend Development
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Code formatting
black app/
isort app/
```

### Frontend Development
```bash
# Install dependencies
npm install

# Development server
npm run dev

# Build for production
npm run build

# Linting and formatting
npm run lint
npm run format
```

## 📊 API Documentation

### Authentication Endpoints
- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - User information

### Data Management
- `POST /api/files/upload` - Upload data files
- `GET /api/files/` - List uploaded files
- `DELETE /api/files/{id}` - Delete files

### Chat & Analysis
- `POST /api/chats/` - Create new chat session
- `POST /api/messages/` - Send messages and get AI responses
- `GET /api/chats/{id}/messages` - Get chat history

### Data Intelligence
- `GET /api/dossiers/{file_id}` - Get data intelligence report
- `POST /api/export/{chat_id}` - Export query results

---

**Consigliere** - Your trusted advisor for data insights, built with privacy in mind. 🕵️‍♂️

*"Your data, your rules, zero leaks."*