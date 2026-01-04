# Agentic Chatbot

A multi-agent chatbot system with deep research capabilities and a Claude-like UI.

## Features

- 🤖 Master agent orchestrating 4 specialized subagents
- 🔍 Deep search with Tavily API and intelligent scraping
- 💻 Code execution, calculations, and chart generation
- 📊 Data warehouse querying
- 📝 Conversation forking and session management
- 🎨 Claude-inspired responsive UI with dark mode
- ⚡ Real-time streaming updates (SSE)
- 🔧 Full configuration via settings UI

## Quick Start

### Prerequisites

- Python 3.11+
- Bun 1.0+
- API keys for at least one LLM provider

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd agentic-chatbot

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup (new terminal)
cd frontend
bun install

# Copy and configure environment
cp .env.example .env
cp config.json.example config.json
# Edit .env and config.json with your API keys

# Run migrations
cd backend
alembic upgrade head

# Start backend
uvicorn app.main:app --reload --port 8000

# Start frontend (new terminal)
cd frontend
bun run dev
```

### Docker

```bash
docker-compose up --build
```

## Documentation

See [AGENTS.md](AGENTS.md) for detailed architecture and implementation guide.

## License

MIT
