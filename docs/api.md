# API Documentation

## Base URL

```
http://localhost:8000/api/v1
```

OpenAPI documentation available at: http://localhost:8000/docs

## Authentication

API keys are configured via environment variables and `config.json`. No authentication tokens required for API calls.

---

## Chat Endpoints

### Send Message

**POST** `/api/v1/chat/message`

Send a message to start agent processing.

**Request Body:**
```json
{
  "content": "What are the latest AI breakthroughs?",
  "deep_search": true
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| content | string | Yes | User message content |
| deep_search | boolean | No | Enable deep research mode |

**Response:**
```json
{
  "message_id": "uuid-string",
  "session_id": "uuid-string",
  "created_at": "2024-01-01T00:00:00"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{"content": "Analyze my sales data for Q4", "deep_search": false}'
```

---

### Stream Response (SSE)

**GET** `/api/v1/chat/stream/{session_id}

Connect to Server-Sent Events stream for real-time updates.

**Response Content-Type:** `text/event-stream`

**Event Types:**

| Event | Description |
|-------|-------------|
| thought | Agent thinking process |
| step_update | Progress step change |
| message_chunk | Response text chunk |
| error | Error occurred |
| complete | Execution finished |

**Example JavaScript:**
```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/v1/chat/stream/session-id'
);

eventSource.addEventListener('thought', (e) => {
  const data = JSON.parse(e.data);
  console.log(`${data.agent}: ${data.content}`);
});

eventSource.addEventListener('complete', (e) => {
  const data = JSON.parse(e.data);
  console.log('Response complete:', data.message_id);
});
```

---

### Cancel Execution

**POST** `/api/v1/chat/cancel/{session_id}`

Cancel ongoing agent execution.

**Response:**
```json
{
  "status": "cancelled",
  "session_id": "uuid-string",
  "message": "Agent execution has been cancelled"
}
```

---

### Fork Conversation

**POST** `/api/v1/chat/fork/{message_id}`

Fork conversation from a specific message, creating a new session.

**Response:**
```json
{
  "new_session_id": "uuid-string",
  "forked_from_message_id": "uuid-string",
  "message_count": 5
}
```

---

### Get Chat History

**GET** `/api/v1/chat/history/{session_id}

Get full chat history and working memory for a session.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | integer | 30 | Maximum messages |
| offset | integer | 0 | Pagination offset |

**Response:**
```json
{
  "session_id": "uuid-string",
  "title": "Conversation title",
  "messages": [
    {
      "id": "uuid",
      "role": "user|assistant",
      "content": "Message text",
      "agent_type": "master|planner|...",
      "created_at": "2024-01-01T00:00:00",
      "extra_data": {}
    }
  ],
  "working_memory": {
    "memory_tree": {},
    "timeline": [],
    "index_map": {}
  },
  "pagination": {
    "limit": 30,
    "offset": 0
  }
}
```

---

### Handle Intervention

**POST** `/api/v1/chat/intervene/{session_id}`

Handle user intervention after error (retry, skip, or abort).

**Request Body:**
```json
{
  "action": "retry|skip|abort"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Intervention 'retry' recorded",
  "session_id": "uuid-string",
  "action": "retry"
}
```

---

### Get Intervention Status

**GET** `/api/v1/chat/intervention/{session_id}

Check if session is awaiting user intervention.

**Response:**
```json
{
  "session_id": "uuid-string",
  "awaiting_response": true,
  "pending_error": {
    "message": "Error description",
    "agent": "tools",
    "retry_count": 3
  },
  "available_actions": ["retry", "skip", "abort"]
}
```

---

## Session Endpoints

### List Sessions

**GET** `/api/v1/sessions

List all chat sessions with pagination.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| archived | boolean | false | Include archived sessions |
| limit | integer | 50 | Maximum results |
| offset | integer | 0 | Pagination offset |

**Response:**
```json
{
  "sessions": [
    {
      "id": "uuid-string",
      "title": "Session title",
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00",
      "archived": false
    }
  ],
  "total": 10
}
```

---

### Create Session

**POST** `/api/v1/sessions

Create a new empty chat session.

**Request Body:**
```json
{
  "title": "Optional session title"
}
```

**Response:**
```json
{
  "id": "uuid-string",
  "title": "Session title",
  "created_at": "2024-01-01T00:00:00"
}
```

---

### Search Sessions

**GET** `/api/v1/sessions/search

Search sessions and messages with full-text search.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| q | string | - | Search query (min 2 chars) |
| limit | integer | 20 | Maximum results (max 100) |
| search_type | string | "all" | all, sessions, messages |

**Response:**
```json
{
  "query": "sales analysis",
  "results": [
    {
      "session_id": "uuid",
      "session_title": "Q4 Sales Analysis",
      "message_content": "Here are the quarterly numbers...",
      "created_at": "2024-01-01T00:00:00",
      "highlighted_content": "Here are the <em>quarterly</em> numbers...",
      "message_id": "uuid",
      "role": "assistant",
      "agent_type": "master",
      "type": "message"
    }
  ],
  "total": 1,
  "time_ms": 45.32,
  "search_type": "all"
}
```

---

### Get Session

**GET** `/api/v1/sessions/{session_id}

Get a specific session with its messages.

**Response:**
```json
{
  "session": {
    "id": "uuid-string",
    "title": "Session title",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00",
    "archived": false
  },
  "messages": [
    {
      "id": "uuid",
      "role": "user|assistant",
      "content": "Message text",
      "agent_type": "master|...",
      "created_at": "2024-01-01T00:00:00",
      "metadata": {}
    }
  ]
}
```

---

### Update Session

**PATCH** `/api/v1/sessions/{session_id}

Update session title or archive status.

**Request Body:**
```json
{
  "title": "New session title"
}
```

**Response:**
```json
{
  "id": "uuid-string",
  "title": "New session title",
  "updated_at": "2024-01-01T00:00:00"
}
```

---

### Delete/Archive Session

**DELETE** `/api/v1/sessions/{session_id}

Archive (soft delete) a session.

**Response:**
```json
{
  "status": "archived",
  "session_id": "uuid-string"
}
```

---

### Export Session

**GET** `/api/v1/sessions/{session_id}/export

Export session to PDF format.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| format | string | "pdf" | Export format (pdf only) |

**Response:** PDF file download

**Headers:**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="session-title.pdf"
```

---

## Config Endpoints

### Get Configuration

**GET** `/api/v1/config

Get current configuration (API keys masked).

**Response:**
```json
{
  "version": "1.0",
  "general": {
    "timezone": "auto",
    "theme": "light",
    "example_questions": ["Question 1", "Question 2"]
  },
  "database": {
    "type": "sqlite",
    "sqlite_path": "./data/chatbot.db",
    "pool_size": 5
  },
  "agents": {
    "master": {
      "provider": "anthropic",
      "model": "claude-3-5-sonnet-20241022",
      "max_tokens": 4096,
      "temperature": 0.7
    }
    // ... other agents
  },
  "api_keys": {
    "anthropic": "***abc123",
    "openai": "***xyz789"
  },
  "profiles": {
    "fast": {...},
    "deep": {...}
  }
}
```

---

### Update Configuration

**POST** `/api/v1/config

Update configuration settings.

**Request Body:** Partial config object matching schema.

**Response:** Updated configuration with masked API keys.

---

### Validate API Key

**POST** `/api/v1/config/validate-api-key

Validate an API key by making a test request.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| provider | string | Provider name (anthropic, openai, openrouter, tavily) |
| api_key | string | API key to validate |
| bypass_cache | boolean | Skip cache, make fresh request |

**Response (Success):**
```json
{
  "valid": true,
  "provider": "anthropic",
  "message": "API key is valid"
}
```

**Response (Failure):**
```json
{
  "valid": false,
  "provider": "anthropic",
  "message": "Invalid API key",
  "error_type": "authentication"
}
```

---

### List Profiles

**GET** `/api/v1/config/profiles

List available configuration profiles.

**Response:**
```json
{
  "profiles": {
    "fast": {
      "description": "Fast mode using smaller models",
      "settings": {
        "master_model": "gpt-3.5-turbo",
        "planner_model": "gpt-3.5-turbo"
      }
    },
    "deep": {
      "description": "Deep research mode using larger models",
      "settings": {
        "master_model": "claude-3-opus-20240229",
        "researcher_urls": 10
      }
    }
  },
  "current_profile": null
}
```

---

### Apply Profile

**POST** `/api/v1/config/profiles/{profile_name}

Apply a configuration profile (fast or deep).

**Response:** Updated configuration with masked API keys.

---

### Validate Configuration

**GET** `/api/v1/config/validate

Validate current configuration.

**Response:**
```json
{
  "valid": true,
  "message": "Configuration is valid"
}
```

---

### Validation Cache

**GET** `/api/v1/config/validation-cache/stats

Get validation cache statistics.

**POST** `/api/v1/config/validation-cache/clear

Clear the validation cache.

---

## Health Endpoints

### Health Check

**GET** `/api/v1/health

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected"
}
```

---

### Root Endpoint

**GET** `/

API information.

**Response:**
```json
{
  "name": "Agentic Chatbot API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/api/v1/health"
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "error": "Error type",
  "detail": "Detailed error message",
  "status_code": 400
}
```

### Common Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid API key |
| 404 | Not Found - Resource doesn't exist |
| 429 | Rate Limited - Too many requests |
| 500 | Internal Server Error |

---

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| /api/v1/chat/message | 100 | minute |
| /api/v1/config/validate-api-key | 10 | minute |

---

## WebSocket vs SSE

This API uses **Server-Sent Events (SSE)** instead of WebSockets for streaming because:
- Simpler protocol (HTTP-based)
- Automatic reconnection
- Native browser support
- Unidirectional (server to client)
