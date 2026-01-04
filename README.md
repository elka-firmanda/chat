# Agentic Chatbot

A multi-agent chatbot system with deep research capabilities and a Claude-like UI. Built with FastAPI, React, and LangGraph.

## Features

- **Multi-Agent Architecture**: Master agent orchestrates 4 specialized subagents (planner, researcher, tools, database)
- **Deep Research**: Tavily API integration with intelligent web scraping and parallel URL processing
- **Code Execution**: Sandboxed Python execution with RestrictedPython, chart generation with matplotlib/plotly
- **Real-Time Streaming**: Server-Sent Events (SSE) for instant agent updates and progress visualization
- **Conversation Management**: Session history, forking, searching, and PDF export
- **Claude-Inspired UI**: Dark/light theme, collapsible thinking blocks, color-coded agent thoughts
- **Full Configuration**: 7-tab settings modal for all agent parameters and API keys
- **Multi-LLM Support**: Anthropic, OpenAI, and OpenRouter providers

## Quick Start

### Prerequisites

- Python 3.11+
- Bun 1.0+
- At least one LLM API key (Anthropic, OpenAI, or OpenRouter)
- Tavily API key for deep search

### Docker (Recommended)

```bash
# Clone and configure
git clone <repo-url>
cd agentic-chatbot
cp .env.example .env
# Edit .env with your API keys

# Start services
docker-compose up --build

# Access:
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Manual Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env with API keys
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
bun install
bun run dev
```

## Project Structure

```
agentic-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── agents/              # Agent system (master, planner, researcher, tools, database)
│   │   ├── api/routes/          # API endpoints (chat, sessions, config, health)
│   │   ├── config/              # Configuration management
│   │   ├── db/                  # SQLAlchemy models and repositories
│   │   ├── llm/                 # LLM provider abstraction
│   │   └── tools/               # Tool implementations (tavily, scraper, code executor)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/          # React components (chat, layout, settings)
│       ├── hooks/               # Custom React hooks
│       ├── stores/              # Zustand state stores
│       └── services/            # API and SSE services
├── docs/                        # Documentation
│   ├── architecture.md          # System architecture guide
│   ├── api.md                   # API documentation
│   └── deployment.md            # Deployment guide
├── docker/                      # Docker configuration
├── config.json.example          # Configuration template
└── .env.example                 # Environment template
```

## Documentation

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | Agent system, working memory, state machine |
| [docs/api.md](docs/api.md) | Complete API endpoint reference |
| [docs/deployment.md](docs/deployment.md) | Docker, manual, and production deployment |
| [AGENTS.md](AGENTS.md) | Development notes and implementation guide |

## API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/chat/message` | POST | Send message, start agent |
| `/api/v1/chat/stream/{id}` | GET | SSE stream for real-time updates |
| `/api/v1/chat/fork/{id}` | POST | Fork conversation from message |
| `/api/v1/sessions` | GET/POST | List/create sessions |
| `/api/v1/sessions/search` | GET | Full-text search |
| `/api/v1/config` | GET/POST | Configuration management |

See [docs/api.md](docs/api.md) for complete documentation.

## Configuration

Edit `config.json` to customize:

```json
{
  "general": {
    "timezone": "auto",
    "theme": "light"
  },
  "agents": {
    "master": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022"
    }
  },
  "profiles": {
    "fast": { "master": {"model": "gpt-3.5-turbo"} },
    "deep": { "researcher": {"max_urls_to_scrape": 10} }
  }
}
```

API keys should be set in `.env` using `${VAR}` syntax:

```json
"api_keys": {
  "anthropic": "${ANTHROPIC_API_KEY}"
}
```

## License

MIT
