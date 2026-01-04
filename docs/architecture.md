# Architecture Documentation

## System Overview

The Agentic Chatbot is a multi-agent system built with FastAPI (backend) and React (frontend), featuring a master agent that orchestrates specialized subagents for complex task completion.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Sidebar   │  │  Chat Area  │  │       Settings Modal    │  │
│  │  (Sessions) │  │  (Messages) │  │     (7 Configuration    │  │
│  └─────────────┘  └─────────────┘  │       Tabs)             │  │
│                                    └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                    SSE (Server-Sent Events)
                              │
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Master Agent                          │    │
│  │         (Orchestrates subagents, synthesizes output)     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                              │                                   │
│            ┌─────────────────┼─────────────────┐                 │
│            ▼                 ▼                 ▼                 │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
│  │   Planner       │ │  Researcher     │ │    Tools        │    │
│  │   Agent         │ │  Agent          │ │    Agent        │    │
│  │  (LangGraph)    │ │  (Tavily+Scraper)│ │  (Code+Charts) │    │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│                    ┌─────────────────┐                           │
│                    │   Database      │                           │
│                    │   Agent         │                           │
│                    │ (Data Queries)  │                           │
│                    └─────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                    SQLAlchemy (Async)
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    Database (SQLite/PostgreSQL)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ ChatSessions│  │  Messages   │  │    Working Memory       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Agent System

### Agent Responsibilities

| Agent | Purpose | Key Capabilities |
|-------|---------|------------------|
| **Master** | Orchestration | Routes to subagents, maintains working memory, handles retry logic, synthesizes final responses |
| **Planner** | Planning | Creates step-by-step execution plans, dynamic re-planning based on findings |
| **Researcher** | Web Search | Tavily API queries, intelligent URL selection, parallel web scraping with BeautifulSoup4 |
| **Tools** | Execution | Sandboxed code execution (RestrictedPython), calculations, chart generation (matplotlib/plotly) |
| **Database** | Data Queries | Data warehouse queries, schema-aware analysis, structured data for visualization |

### Working Memory Structure

The system uses a hybrid memory structure combining:

1. **Tree Structure** - Hierarchical agent execution with parent-child relationships
2. **Timeline** - Append-only execution log for UI streaming
3. **Index Map** - Fast lookup by agent/step ID

```python
working_memory = {
    "tree": {
        "root": {
            "agent": "master",
            "children": [
                {
                    "id": "plan-1",
                    "agent": "planner",
                    "children": [
                        {"id": "research-1", "agent": "researcher"}
                    ]
                }
            ]
        }
    },
    "timeline": [
        {"id": "plan-1", "agent": "planner", "timestamp": "..."},
        {"id": "research-1", "agent": "researcher", "timestamp": "..."}
    ],
    "index": {
        "plan-1": {...},
        "research-1": {...}
    }
}
```

### LangGraph State Machine

The agent workflow is implemented using LangGraph's state machine:

```python
class AgentState(TypedDict):
    user_message: str
    session_id: str
    deep_search_enabled: bool
    memory_tree: Dict
    timeline: Annotated[List[Dict], add]
    index_map: Dict
    current_plan: List[Dict]
    plan_version: int
    final_answer: str
    retry_count: int
    error_log: List[Dict]

workflow = StateGraph(AgentState)
workflow.add_node("master", master_agent)
workflow.add_node("planner", planner_agent)
workflow.add_node("researcher", researcher_agent)
workflow.add_node("tools", tools_agent)
workflow.add_node("database", database_agent)
workflow.add_conditional_edges("master", route_master, {...})
```

## Real-Time Streaming

### Server-Sent Events (SSE)

The system uses SSE for real-time updates to the frontend:

| Event Type | Description | Data |
|------------|-------------|------|
| `thought` | Agent thinking process | `{agent, content}` |
| `step_update` | Progress step status | `{step_id, status, description, logs}` |
| `message_chunk` | Streaming response | `{content}` |
| `error` | Error occurred | `{message, retry_count}` |
| `complete` | Execution finished | `{message_id, session_id}` |

### Event Flow

```
User Message → POST /api/v1/chat/message
    ↓
Returns message_id, session_id
    ↓
Client connects to GET /api/v1/chat/stream/{session_id}
    ↓
Agent executes, events pushed to queue
    ↓
SSE events stream to client
    ↓
complete event signals finish
```

## Database Schema

### Core Tables

```sql
-- Chat Sessions
chat_sessions (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    archived BOOLEAN,
    metadata JSON
)

-- Messages
messages (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES chat_sessions(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    agent_type TEXT,
    parent_message_id TEXT,
    created_at TIMESTAMP,
    metadata JSON
)

-- Working Memory (hybrid tree + timeline + index)
working_memory (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES chat_sessions(id),
    memory_tree JSON,
    timeline JSON,
    index_map JSON,
    updated_at TIMESTAMP
)

-- Agent Steps (progress tracking)
agent_steps (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES chat_sessions(id),
    message_id TEXT REFERENCES messages(id),
    step_number INTEGER,
    agent_type TEXT,
    description TEXT,
    status TEXT,
    result TEXT,
    logs TEXT
)

-- Custom Tools
custom_tools (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    code TEXT,
    enabled BOOLEAN
)
```

## Configuration System

### Configuration Priority

1. **UI Settings** - Saved to config.json
2. **config.json** - Primary configuration file
3. **.env** - Fallback for environment variables with `${VAR}` syntax

### Environment Variable Substitution

```json
{
  "api_keys": {
    "anthropic": "${ANTHROPIC_API_KEY}",
    "tavily": "${TAVILY_API_KEY}"
  }
}
```

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-...
TAVILY_API_KEY=tvly-...
```

## Technology Stack

### Backend
| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | FastAPI | Async API server |
| ORM | SQLAlchemy 2.0 (async) | Database access |
| Agent Framework | LangGraph | State machine orchestration |
| LLM SDKs | Anthropic, OpenAI | Model access |
| Web Scraping | BeautifulSoup4 + httpx | Parallel scraping |
| Streaming | SSE-Starlette | Real-time events |

### Frontend
| Component | Technology | Purpose |
|-----------|------------|---------|
| Runtime | Bun | JavaScript runtime |
| Framework | React 18 | UI components |
| State | Zustand | Client state management |
| Styling | Tailwind CSS | Utility-first styling |
| Icons | Lucide React | SVG icons |

## Security Considerations

### API Keys
- Stored in `.env` (gitignored)
- Masked in API responses
- Validated on backend only

### Code Execution
- RestrictedPython sandbox
- 30-second timeout
- No file system or network access

### Database
- Parameterized queries (SQLAlchemy)
- Connection pooling with limits
- Input validation

## Performance Targets

| Metric | Target |
|--------|--------|
| SSE Latency | < 100ms |
| Casual Response | < 2s |
| Deep Search | < 30s |
| DB Queries | < 50ms |
| Frontend FPS | 60fps |
