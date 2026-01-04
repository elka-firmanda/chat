# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds

---

# 🤖 Agentic Chatbot Project

## 📋 Project Overview

**Goal:** Build a multi-agent chatbot system with deep research capabilities and a Claude-like UI.

**Key Features:**
- Master agent orchestrating 4 specialized subagents
- Dynamic planning with re-planning capability
- Deep search (Tavily API → intelligent scraping → analysis)
- Code execution, calculations, chart generation
- Data warehouse querying with custom schema
- Conversation forking and session management
- Real-time streaming updates (SSE)
- Claude-inspired responsive UI with dark mode
- Multi-LLM provider support (Anthropic, OpenAI, OpenRouter)

---

## 🏗️ Technology Stack

### Backend
- **Framework:** FastAPI (async/await native)
- **ORM:** SQLAlchemy 2.0 (async mode)
- **Database:** SQLite (default) + PostgreSQL support with auto-migration
- **Migrations:** Alembic
- **Agent Framework:** LangGraph (state machine orchestration)
- **LLM SDKs:** Anthropic SDK, OpenAI SDK
- **Web Scraping:** BeautifulSoup4 + httpx (async)
- **Tools:** Tavily (search), RestrictedPython (code sandbox), matplotlib/plotly (charts)
- **Streaming:** SSE-Starlette (Server-Sent Events)

### Frontend
- **Runtime:** Bun (no npm)
- **Framework:** React 18
- **Build Tool:** Vite
- **State Management:** Zustand
- **UI Components:** shadcn/ui (Radix UI primitives)
- **Styling:** Tailwind CSS
- **Routing:** React Router v6
- **HTTP Client:** Axios
- **Real-time:** EventSource API (SSE)

### Deployment
- **Primary:** Docker + Docker Compose
- **Testing:** Manual setup (requirements.txt + bun)
- **Future:** Google App Engine or Vercel

---

## 📁 Project Structure

```
agentic-chatbot/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config/
│   │   │   ├── settings.py         # Pydantic settings
│   │   │   ├── config_manager.py   # config.json + .env handler
│   │   │   └── schema.py           # Config validation
│   │   ├── agents/
│   │   │   ├── master.py           # Master orchestrator
│   │   │   ├── planner.py          # Planning agent
│   │   │   ├── researcher.py       # Tavily + scraping
│   │   │   ├── tools.py            # Code exec, calculations
│   │   │   ├── database.py         # Data warehouse queries
│   │   │   ├── graph.py            # LangGraph state machine
│   │   │   └── memory.py           # Working memory (hybrid tree)
│   │   ├── api/routes/
│   │   │   ├── chat.py             # Chat + SSE endpoints
│   │   │   ├── sessions.py         # Session CRUD
│   │   │   ├── config.py           # Settings API
│   │   │   └── health.py           # Health checks
│   │   ├── db/
│   │   │   ├── models.py           # SQLAlchemy models
│   │   │   ├── session.py          # DB session manager
│   │   │   └── repositories/       # Data access layer
│   │   ├── llm/
│   │   │   ├── providers.py        # LLM provider abstraction
│   │   │   ├── anthropic.py
│   │   │   ├── openai.py
│   │   │   └── openrouter.py
│   │   ├── tools/
│   │   │   ├── tavily.py           # Search integration
│   │   │   ├── scraper.py          # Parallel web scraping
│   │   │   ├── code_executor.py    # Sandboxed execution
│   │   │   ├── calculator.py
│   │   │   ├── chart_generator.py
│   │   │   └── custom_tools.py     # User-defined tools
│   │   └── utils/
│   │       ├── datetime.py         # Timezone utilities
│   │       ├── validators.py
│   │       └── streaming.py        # SSE helpers
│   ├── tests/
│   ├── requirements.txt
│   └── alembic.ini
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx     # Session list + new chat
│   │   │   │   ├── ChatContainer.tsx
│   │   │   │   └── Header.tsx      # Theme + settings icons
│   │   │   ├── chat/
│   │   │   │   ├── MessageList.tsx
│   │   │   │   ├── Message.tsx
│   │   │   │   ├── ThinkingBlock.tsx      # Collapsible thoughts
│   │   │   │   ├── ProgressSteps.tsx      # Steps with checkmarks
│   │   │   │   ├── InputBox.tsx           # Text + deep search toggle
│   │   │   │   └── ExampleCards.tsx       # 4 example questions
│   │   │   ├── session/
│   │   │   │   ├── SessionList.tsx
│   │   │   │   └── SessionItem.tsx
│   │   │   ├── settings/
│   │   │   │   ├── SettingsModal.tsx
│   │   │   │   └── tabs/
│   │   │   │       ├── GeneralTab.tsx
│   │   │   │       ├── DatabaseTab.tsx
│   │   │   │       ├── MasterAgentTab.tsx
│   │   │   │       ├── PlannerTab.tsx
│   │   │   │       ├── ResearcherTab.tsx
│   │   │   │       ├── ToolsTab.tsx
│   │   │   │       └── DatabaseAgentTab.tsx
│   │   │   └── ui/                        # shadcn/ui components
│   │   ├── hooks/
│   │   │   ├── useSSE.ts
│   │   │   ├── useChat.ts
│   │   │   └── useSettings.ts
│   │   ├── stores/
│   │   │   ├── chatStore.ts               # Zustand state
│   │   │   └── settingsStore.ts
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   └── sse.ts
│   │   └── types/
│   │       ├── chat.ts
│   │       ├── agent.ts
│   │       └── config.ts
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
│
├── .env.example
├── .gitignore
├── config.json.example
└── README.md
```

---

## 🗄️ Database Schema

### SQLite/PostgreSQL Tables

```sql
-- Chat Sessions
CREATE TABLE chat_sessions (
    id TEXT PRIMARY KEY,                    -- UUID
    title TEXT,                             -- Auto-generated
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived BOOLEAN DEFAULT FALSE,
    metadata JSON
);

-- Messages
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,                     -- 'user', 'assistant'
    content TEXT NOT NULL,
    agent_type TEXT,                        -- 'master', 'planner', etc.
    parent_message_id TEXT,                 -- For conversation forking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON,                          -- tokens, cost, model, duration
    INDEX idx_session_created (session_id, created_at)
);

-- Working Memory (hybrid tree + timeline + index)
CREATE TABLE working_memory (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES chat_sessions(id) ON DELETE CASCADE,
    memory_tree JSON,                       -- Hierarchical structure
    timeline JSON,                          -- Flat execution log (for UI)
    index_map JSON,                         -- Quick lookup by ID
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id)
);

-- Agent Steps (progress tracking)
CREATE TABLE agent_steps (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES chat_sessions(id) ON DELETE CASCADE,
    message_id TEXT REFERENCES messages(id) ON DELETE CASCADE,
    step_number INTEGER,
    agent_type TEXT,
    description TEXT,
    status TEXT,                            -- 'pending', 'running', 'completed', 'failed'
    result TEXT,
    logs TEXT,                              -- Expandable dropdown logs
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    INDEX idx_session_message (session_id, message_id)
);

-- Custom Tools
CREATE TABLE custom_tools (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    code TEXT,                              -- Python code
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🤖 Agent Architecture

### Working Memory Structure (Hybrid)

```python
working_memory = {
    "tree": {
        "root": {
            "agent": "master",
            "children": [
                {
                    "id": "plan-1",
                    "agent": "planner",
                    "steps": [...],
                    "children": [
                        {
                            "id": "research-1",
                            "agent": "researcher",
                            "parent": "plan-1",
                            "step_ref": 2
                        }
                    ]
                },
                {
                    "id": "plan-2",  # Re-planning
                    "agent": "planner",
                    "triggered_by": "research-1"
                }
            ]
        }
    },
    "timeline": [  # For UI streaming
        {"id": "plan-1", "agent": "planner", "timestamp": "..."},
        {"id": "research-1", "agent": "researcher", "timestamp": "..."}
    ],
    "index": {  # Fast lookup
        "plan-1": {...},
        "research-1": {...}
    }
}
```

### LangGraph State Machine

```python
from typing import TypedDict, Annotated, List, Dict
from langgraph.graph import StateGraph
from operator import add

class AgentState(TypedDict):
    user_message: str
    session_id: str
    deep_search_enabled: bool
    
    # Working memory
    memory_tree: Dict
    timeline: Annotated[List[Dict], add]  # Append-only
    index_map: Dict
    
    # Current execution
    current_plan: List[Dict]
    plan_version: int
    active_step: int
    
    # Agent results
    planner_output: Dict
    researcher_output: Dict
    tools_output: Dict
    database_output: Dict
    
    final_answer: str
    retry_count: int
    error_log: List[Dict]

# Graph
workflow = StateGraph(AgentState)
workflow.add_node("master", master_agent)
workflow.add_node("planner", planner_agent)
workflow.add_node("researcher", researcher_agent)
workflow.add_node("tools", tools_agent)
workflow.add_node("database", database_agent)

workflow.set_entry_point("master")
workflow.add_conditional_edges("master", route_master, {...})
workflow.add_edge("planner", "master")
workflow.add_edge("researcher", "master")
workflow.add_edge("tools", "master")
workflow.add_edge("database", "master")

app = workflow.compile()
```

### Agent Responsibilities

1. **Master Agent:**
   - Orchestrates all subagents
   - Maintains working memory (tree + timeline + index)
   - Routes to appropriate subagent based on plan
   - Detects when re-planning needed
   - Handles retry logic (3 attempts before user intervention)
   - Synthesizes final response

2. **Planner Agent:**
   - Creates step-by-step execution plans
   - Can modify plans dynamically based on findings
   - Returns structured plan with step types (research, code, database)
   - Triggered by master at start or when re-planning needed

3. **Researcher Agent:**
   - Queries Tavily API for search results
   - Intelligently selects top N URLs to scrape
   - Parallel web scraping (BeautifulSoup4)
   - 600-second timeout
   - Flags interesting findings that may require re-planning
   - Only receives relevant context from master

4. **Tools Agent:**
   - Code execution (RestrictedPython sandbox)
   - Calculations
   - Chart generation (matplotlib/plotly)
   - Custom user-defined tools
   - 30-second execution timeout
   - No network access from executed code

5. **Database Agent:**
   - Queries data warehouse
   - Separate from tools agent to avoid system prompt conflicts
   - Data warehouse schema provided in system prompt
   - Performs analysis on query results
   - Returns structured data for visualization

---

## 🔌 API Endpoints

### Chat Endpoints

```python
POST   /api/v1/chat/message              # Send message (returns message_id)
GET    /api/v1/chat/stream/{session_id}  # SSE stream for real-time updates
POST   /api/v1/chat/cancel/{session_id}  # Cancel mid-execution
POST   /api/v1/chat/fork/{message_id}    # Fork conversation from message
```

### Session Endpoints

```python
GET    /api/v1/sessions                  # List sessions (paginated)
POST   /api/v1/sessions                  # Create new session
GET    /api/v1/sessions/{id}             # Get session with messages
PATCH  /api/v1/sessions/{id}             # Update title/archive
GET    /api/v1/sessions/{id}/export      # Export to PDF
GET    /api/v1/sessions/search?q=...     # Search historical chats
```

### Config Endpoints

```python
GET    /api/v1/config                    # Get config (masked API keys)
POST   /api/v1/config                    # Update config
POST   /api/v1/config/validate-api-key   # Test API key
GET    /api/v1/config/profiles           # List profiles
```

### SSE Event Types

```javascript
// Events streamed to frontend
{
  event: "thought",          // Agent thinking process
  data: {
    agent: "master|planner|researcher|tools|database",
    content: "thinking text..."
  }
}

{
  event: "step_update",      // Progress step status change
  data: {
    step_id: "...",
    status: "pending|running|completed|failed",
    description: "...",
    logs: "..."
  }
}

{
  event: "message_chunk",    // Streaming final response
  data: {
    content: "partial text..."
  }
}

{
  event: "error",            // Error occurred
  data: {
    message: "...",
    retry_count: 2
  }
}

{
  event: "complete",         // Execution finished
  data: {
    message_id: "..."
  }
}
```

---

## ⚙️ Configuration System

### config.json Structure

```json
{
  "version": "1.0",
  "general": {
    "timezone": "auto",
    "theme": "light",
    "example_questions": [
      "What are the latest AI breakthroughs?",
      "Analyze my sales data for Q4"
    ]
  },
  "database": {
    "type": "sqlite",
    "sqlite_path": "./data/chatbot.db",
    "postgresql_connection": null,
    "pool_size": 5
  },
  "agents": {
    "master": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "max_tokens": 4096,
      "temperature": 0.7,
      "system_prompt": "You are a master orchestrator..."
    },
    "planner": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "max_tokens": 2048,
      "system_prompt": "You create step-by-step plans..."
    },
    "researcher": {
      "provider": "openai",
      "model": "gpt-4-turbo",
      "max_tokens": 4096,
      "tavily_api_key": "${TAVILY_API_KEY}",
      "max_urls_to_scrape": 5,
      "scraping_timeout": 600,
      "system_prompt": "You are a research specialist..."
    },
    "tools": {
      "provider": "openai",
      "model": "gpt-4-turbo",
      "max_tokens": 2048,
      "enabled_tools": ["code_executor", "calculator", "chart_generator"],
      "sandbox_enabled": true,
      "system_prompt": "You execute code and calculations..."
    },
    "database": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "max_tokens": 4096,
      "data_warehouse_schema": "...",
      "system_prompt": "You query a data warehouse..."
    }
  },
  "api_keys": {
    "anthropic": "${ANTHROPIC_API_KEY}",
    "openai": "${OPENAI_API_KEY}",
    "openrouter": "${OPENROUTER_API_KEY}",
    "tavily": "${TAVILY_API_KEY}"
  },
  "profiles": {
    "fast": {
      "master": {"model": "gpt-3.5-turbo"},
      "planner": {"model": "gpt-3.5-turbo"}
    },
    "deep": {
      "master": {"model": "claude-3-opus-20240229"},
      "researcher": {"max_urls_to_scrape": 10}
    }
  }
}
```

### .env File

```bash
# API Keys (gitignored)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...
TAVILY_API_KEY=tvly-...

# Database (optional)
DATABASE_URL=postgresql://user:pass@localhost:5432/chatbot

# CORS (optional)
CORS_ORIGINS=http://localhost:3000
```

### Priority Order
1. UI settings (saved to config.json)
2. config.json values
3. .env values (fallback for ${VAR} placeholders)

---

## 🎨 UI/UX Design Principles

### Layout (Claude-like)

1. **Sidebar (Left):**
   - New Chat button (top)
   - Session list (scrollable)
   - Archived chats (collapsible)
   - Auto-generated session titles

2. **Main Chat Area:**
   - Message list (scrollable)
   - User messages (right-aligned)
   - Agent responses (left-aligned)
   - Collapsible thinking blocks (different colors per agent)
   - Progress steps (checkmarks, expandable logs)
   - Show More button (every 30 lines)

3. **Input Area (Bottom):**
   - Text input (multi-line, auto-expand)
   - Deep Search toggle (visual on/off indicator)
   - Send button

4. **Header (Top Right):**
   - Theme toggle (light/dark)
   - Settings icon (opens modal)

### Settings Modal (7 Tabs)

1. **General:** Timezone, theme, example questions
2. **Database Connection:** SQLite/PostgreSQL config
3. **Master Agent:** Provider, model, tokens, system prompt
4. **Planner Agent:** Same fields
5. **Researcher Agent:** Same + Tavily config + scraping settings
6. **Tools Agent:** Same + enabled tools + custom tools
7. **Database Agent:** Same + data warehouse schema

### Visual Indicators

- **Agent thoughts:** Color-coded borders (master=purple, planner=blue, researcher=green, tools=orange, database=pink)
- **Progress steps:** ✓ (completed), ⟳ (running), ✗ (failed)
- **Deep search toggle:** Clear visual feedback when enabled
- **Theme:** Persistent across sessions
- **Loading:** Smooth skeleton screens, no jarring spinners

### Responsive Design

- Mobile: Sidebar becomes drawer (hamburger menu)
- Tablet: Side-by-side layout
- Desktop: Full 3-column (sidebar, chat, potential info panel)

---

## 🚀 Development Workflow

### Setup (Manual - Testing)

```bash
# Clone repo
git clone <repo-url>
cd agentic-chatbot

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with API keys
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd ../frontend
bun install
cp .env.example .env.local
bun run dev
```

### Setup (Docker)

```bash
docker-compose up --build

# Access:
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Git Workflow

```bash
# Feature branch
git checkout -b feature/agent-orchestration

# Commit often
git add .
git commit -m "feat: implement master agent routing"

# Push and create PR
git push -u origin feature/agent-orchestration
```

---

## 📦 Key Dependencies

### Backend (requirements.txt)

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-dotenv==1.0.0
sqlalchemy[asyncio]==2.0.25
alembic==1.13.1
asyncpg==0.29.0
aiosqlite==0.19.0
anthropic==0.18.0
openai==1.12.0
langchain==0.1.6
langgraph==0.0.20
tavily-python==0.3.0
beautifulsoup4==4.12.3
httpx==0.26.0
RestrictedPython==6.2
matplotlib==3.8.2
plotly==5.18.0
pandas==2.2.0
sse-starlette==1.8.2
pydantic==2.6.0
pydantic-settings==2.1.0
```

### Frontend (package.json)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.3",
    "zustand": "^4.5.0",
    "axios": "^1.6.7",
    "@radix-ui/react-collapsible": "^1.0.3",
    "@radix-ui/react-dialog": "^1.0.5",
    "@radix-ui/react-tabs": "^1.0.4",
    "lucide-react": "^0.323.0",
    "tailwindcss": "^3.4.1"
  }
}
```

---

## 🔒 Security Considerations

1. **API Keys:**
   - Store in .env (gitignored)
   - Mask in UI (show `***abc123`)
   - Validate on backend only
   - Support multiple keys per provider

2. **Code Execution:**
   - RestrictedPython sandbox
   - 30-second timeout
   - No file system access
   - No network access
   - Resource limits

3. **Database:**
   - Parameterized queries (SQLAlchemy)
   - Connection pooling with limits
   - Input validation

4. **Input:**
   - Sanitize user messages
   - 10,000 character limit
   - Rate limiting (future)

---

## 🎯 Implementation Phases

### Phase 1: Foundation (Week 1-2)
- Project structure setup
- Database schema + migrations
- Config system (config.json + .env)
- Basic FastAPI app with health endpoint
- React + Vite + Bun setup
- Basic UI layout (sidebar, chat, header)

### Phase 2: Core Agent System (Week 3-4)
- LLM provider abstraction
- Master agent (simple routing)
- Planner agent (LangGraph)
- Working memory manager (hybrid tree)
- Basic chat endpoint + SSE
- Frontend SSE integration

### Phase 3: Subagents (Week 5-6)
- Researcher agent (Tavily + parallel scraping)
- Tools agent (code execution, calculator)
- Database agent
- Parallel execution logic
- Re-planning logic

### Phase 4: UI/UX (Week 7-8)
- Progress steps visualization
- Thinking blocks (collapsible, color-coded)
- Settings modal (7 tabs)
- Theme toggle (light/dark)
- Deep search toggle
- Example question cards (customizable)

### Phase 5: Advanced Features (Week 9-10)
- Conversation forking
- Session search
- PDF export
- Error handling + retry (3x + user intervention)
- Custom tools support
- API key validation

### Phase 6: Polish & Deploy (Week 11-12)
- Responsive design (mobile/tablet)
- PostgreSQL support + auto-migration
- Docker setup
- Documentation
- Testing (unit, integration, E2E)
- Performance optimization

---

## 📊 Performance Targets

- **SSE Latency:** < 100ms for agent updates
- **Message Response:** < 2s (casual), < 30s (deep search)
- **UI:** 60fps animations
- **Bundle Size:** < 500KB (frontend)
- **DB Queries:** < 50ms (session load)

---

## 🧪 Testing Strategy

1. **Backend:**
   - Unit tests (pytest)
   - Integration tests (API endpoints)
   - E2E (agent workflows)

2. **Frontend:**
   - Component tests (Vitest + Testing Library)
   - E2E (Playwright)

3. **Manual:**
   - Cross-browser (Chrome, Firefox, Safari)
   - Mobile responsive
   - Dark/light theme

---

## 📝 Issue Tracking

All implementation tasks tracked in **beads** (bd). See issues for:
- Detailed acceptance criteria
- Dependencies between tasks
- Progress tracking

Run `bd ready` to see available work.

---

## 🔮 Future Enhancements

- Multi-user support
- Cloud deployment (Google App Engine / Vercel)
- Plugin/extension system for custom subagents
- Voice input/output
- Image generation integration
- Long-term memory across sessions

<!-- bv-agent-instructions-v1 -->

---

## Beads Workflow Integration

This project uses [beads_viewer](https://github.com/Dicklesworthstone/beads_viewer) for issue tracking. Issues are stored in `.beads/` and tracked in git.

### Essential Commands

```bash
# View issues (launches TUI - avoid in automated sessions)
bv

# CLI commands for agents (use these instead)
bd ready              # Show issues ready to work (no blockers)
bd list --status=open # All open issues
bd show <id>          # Full issue details with dependencies
bd create --title="..." --type=task --priority=2
bd update <id> --status=in_progress
bd close <id> --reason="Completed"
bd close <id1> <id2>  # Close multiple issues at once
bd sync               # Commit and push changes
```

### Workflow Pattern

1. **Start**: Run `bd ready` to find actionable work
2. **Claim**: Use `bd update <id> --status=in_progress`
3. **Work**: Implement the task
4. **Complete**: Use `bd close <id>`
5. **Sync**: Always run `bd sync` at session end

### Key Concepts

- **Dependencies**: Issues can block other issues. `bd ready` shows only unblocked work.
- **Priority**: P0=critical, P1=high, P2=medium, P3=low, P4=backlog (use numbers, not words)
- **Types**: task, bug, feature, epic, question, docs
- **Blocking**: `bd dep add <issue> <depends-on>` to add dependencies

### Session Protocol

**Before ending any session, run this checklist:**

```bash
git status              # Check what changed
git add <files>         # Stage code changes
bd sync                 # Commit beads changes
git commit -m "..."     # Commit code
bd sync                 # Commit any new beads changes
git push                # Push to remote
```

### Best Practices

- Check `bd ready` at session start to find available work
- Update status as you work (in_progress → closed)
- Create new issues with `bd create` when you discover tasks
- Use descriptive titles and set appropriate priority/type
- Always `bd sync` before ending session

<!-- end-bv-agent-instructions -->
