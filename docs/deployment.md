# Deployment Documentation

## Overview

The Agentic Chatbot can be deployed using Docker Compose or manually. Docker is recommended for production.

## Prerequisites

### Common Requirements
- API keys for at least one LLM provider (Anthropic, OpenAI, or OpenRouter)
- Tavily API key for deep search functionality

### Docker Deployment
- Docker Engine 20.10+
- Docker Compose v2.0+

### Manual Deployment
- Python 3.11+
- Node.js runtime (Bun 1.0+ recommended)
- SQLite (default) or PostgreSQL 14+

---

## Docker Deployment (Recommended)

### 1. Clone Repository

```bash
git clone <repo-url>
cd agentic-chatbot
```

### 2. Configure Environment

```bash
# Copy environment files
cp .env.example .env

# Edit with your API keys
nano .env
```

**.env file:**
```bash
# Required: At least one LLM provider
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
OPENROUTER_API_KEY=sk-or-...

# Required for deep search
TAVILY_API_KEY=tvly-...

# Optional: Custom database URL
# DATABASE_URL=postgresql://user:pass@host:5432/chatbot

# Optional: CORS origins (comma-separated)
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### 3. Start Services

```bash
docker-compose up --build
```

This starts:
- Frontend at http://localhost:3000
- Backend at http://localhost:8000
- API docs at http://localhost:8000/docs

### 4. View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 5. Stop Services

```bash
docker-compose down

# Stop and remove volumes (data loss!)
docker-compose down -v
```

### Docker Configuration

Edit `docker-compose.yml` to customize:

```yaml
services:
  backend:
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
    volumes:
      - ./data:/app/data  # Persist database

  frontend:
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
```

---

## Manual Deployment

### Backend Setup

#### 1. Clone and Setup Python Environment

```bash
git clone <repo-url>
cd agentic-chatbot/backend

# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Environment

```bash
cp ../.env.example .env
# Edit .env with your API keys

cp ../config.json.example config.json
# Edit config.json as needed
```

#### 3. Initialize Database

```bash
# Run migrations
alembic upgrade head
```

#### 4. Start Backend

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

For production (no reload):
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend Setup

#### 1. Setup Node/Bun

```bash
cd agentic-chatbot/frontend

# Install dependencies
bun install

# Copy environment
cp ../.env.example .env.local
# Edit .env.local if needed
```

#### 2. Start Development Server

```bash
bun run dev
```

Access at http://localhost:5173

#### 3. Build for Production

```bash
bun run build
```

Static files in `dist/` can be served by any web server (Nginx, Apache, etc.).

---

## Production Deployment

### Using Nginx

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend
    location / {
        root /var/www/agentic-chatbot/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # SSE endpoint
    location /api/v1/chat/stream/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_buffering off;
        proxy_read_timeout 300    }
}
```

### Using systemd

Create `/;
etc/systemd/system/agentic-chatbot.service`:

```ini
[Unit]
Description=Agentic Chatbot Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/agentic-chatbot/backend
Environment="PATH=/opt/agentic-chatbot/backend/venv/bin"
ExecStart=/opt/agentic-chatbot/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable agentic-chatbot
sudo systemctl start agentic-chatbot
```

### PostgreSQL Setup

For production, use PostgreSQL instead of SQLite:

```bash
# Create database
sudo -u postgres createdb chatbot

# Update config.json
{
  "database": {
    "type": "postgresql",
    "postgresql_connection": "postgresql://user:pass@localhost:5432/chatbot",
    "pool_size": 10
  }
}

# Run migrations
alembic upgrade head
```

---

## Environment Variables

### Backend (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes* | Anthropic API key |
| `OPENAI_API_KEY` | Yes* | OpenAI API key |
| `OPENROUTER_API_KEY` | Yes* | OpenRouter API key |
| `TAVILY_API_KEY` | Yes | Tavily API key for search |
| `DATABASE_URL` | No | PostgreSQL connection string |
| `CORS_ORIGINS` | No | Comma-separated CORS origins |
| `DEBUG` | No | Enable debug mode |

*At least one LLM provider required.

### Frontend (.env.local)

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | http://localhost:8000 | Backend API URL |

---

## Configuration

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
      "temperature": 0.7
    },
    "planner": {...},
    "researcher": {...},
    "tools": {...},
    "database": {...}
  },
  "api_keys": {
    "anthropic": "${ANTHROPIC_API_KEY}",
    "openai": "${OPENAI_API_KEY}",
    "openrouter": "${OPENROUTER_API_KEY}",
    "tavily": "${TAVILY_API_KEY}"
  },
  "profiles": {
    "fast": {...},
    "deep": {...}
  }
}
```

### Configuration Profiles

| Profile | Description | Use Case |
|---------|-------------|----------|
| `fast` | Uses smaller/faster models | Quick queries, lower cost |
| `deep` | Uses larger models, more URLs | Complex research tasks |

---

## Troubleshooting

### Backend Won't Start

```bash
# Check if port is in use
lsof -i :8000

# Check Python version
python --version  # Must be 3.11+

# Check dependencies
pip install -r requirements.txt

# Check logs
docker-compose logs backend
```

### Frontend Not Loading

```bash
# Check browser console for errors

# Verify API URL matches backend
echo $VITE_API_URL

# Rebuild frontend
cd frontend
bun run build
```

### Database Errors

```bash
# Reset database (dev only)
rm -f data/chatbot.db
alembic upgrade head

# Check database connection
sqlite3 data/chatbot.db ".tables"
```

### SSE Not Working

```bash
# Verify CORS is configured
# Check browser network tab for SSE connection
# Ensure proxy is not buffering (Nginx: proxy_buffering off)
```

### API Key Validation Fails

```bash
# Verify key is correct
echo $ANTHROPIC_API_KEY

# Check provider support
# Anthropic, OpenAI, OpenRouter, Tavily supported

# Clear validation cache
curl -X POST http://localhost:8000/api/v1/config/validation-cache/clear
```

### Docker Issues

```bash
# Clear containers and rebuild
docker-compose down
docker-compose up --build --no-cache

# Check disk space
df -h

# Check Docker logs
docker-compose logs
```

---

## Security Checklist

- [ ] Use strong API keys
- [ ] Configure CORS origins
- [ ] Enable HTTPS in production
- [ ] Use PostgreSQL for production
- [ ] Set appropriate connection pool size
- [ ] Configure rate limiting (future feature)
- [ ] Regularly update dependencies
- [ ] Backup database regularly

---

## Performance Optimization

### Backend
- Use PostgreSQL instead of SQLite for concurrent access
- Increase `pool_size` for high traffic
- Use `workers` flag with uvicorn for multiple processes

### Frontend
- Build for production (`bun run build`)
- Serve static files with CDN
- Configure browser caching

### Database
- Regular VACUUM ANALYZE for PostgreSQL
- Consider database connection pooling (PgBouncer)
