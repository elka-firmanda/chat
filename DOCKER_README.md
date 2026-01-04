# Docker Deployment Guide for Agentic Chatbot

This guide covers how to deploy the Agentic Chatbot using Docker Compose.

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys and configuration

cp config.json.example config.json
# Edit config.json as needed
```

### 2. Start with PostgreSQL (Recommended)

```bash
# Development mode with hot reload
docker-compose up -d

# Or for production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 3. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Configuration Options

### Using SQLite (No PostgreSQL)

For development without PostgreSQL, use the sqlite profile:

```bash
docker-compose --profile sqlite up -d
```

### Custom Ports

Edit `.env` to customize ports:

```bash
BACKEND_PORT=8000
FRONTEND_PORT=3000
POSTGRES_PORT=5432
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | postgresql://user:pass@postgres:5432/chatbot | Database connection string |
| `POSTGRES_USER` | user | PostgreSQL username |
| `POSTGRES_PASSWORD` | pass | PostgreSQL password |
| `POSTGRES_DB` | chatbot | PostgreSQL database name |
| `BACKEND_PORT` | 8000 | Backend API port |
| `FRONTEND_PORT` | 3000 | Frontend port |
| `LOG_LEVEL` | info | Logging level (debug, info, warning, error) |
| `VITE_API_URL` | http://localhost:8000 | API URL for frontend |

## Development Mode

For development with hot reload:

```bash
# Start development services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Development mode features:
- Backend code changes auto-reload
- Frontend uses Vite dev server with HMR
- Source code mounted as volumes
- Debug logging enabled

## Production Mode

For production deployment:

```bash
# Build and start production services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# View logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down
```

Production features:
- Optimized Docker builds
- Resource limits configured
- Production nginx serving frontend
- No source code mounts

## Service Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     chatbot-network                      │
│                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  postgres   │    │   backend   │    │  frontend   │  │
│  │   :5432     │───>│   :8000     │<───│    :80      │  │
│  └─────────────┘    └─────────────┘    └─────────────┘  │
│       (DB)              (API)              (Nginx)      │
└─────────────────────────────────────────────────────────┘
```

## Volume Mounts

| Volume | Description |
|--------|-------------|
| `postgres_data` | PostgreSQL data persistence |
| `backend_data` | Application data (uploads, etc.) |
| `backend_logs` | Application logs |
| `./backend:/app` | Development: Backend source code |
| `./frontend:/app` | Development: Frontend source code |

## Database Initialization

Custom SQL initialization scripts can be placed in `init-scripts/`. They run alphabetically when PostgreSQL first initializes.

## Troubleshooting

### Frontend not loading
Ensure backend is healthy: `docker-compose ps` should show backend as "healthy"

### Database connection errors
Check PostgreSQL logs: `docker-compose logs postgres`

### Port already in use
Change ports in `.env` file

### Clear all data and start fresh
```bash
docker-compose down -v
docker-compose up -d
```

## Scaling

For horizontal scaling, consider:
- Using a managed PostgreSQL service
- Running multiple backend replicas behind a load balancer
- Using a Redis cache for session storage

## Security Notes

- Change default PostgreSQL credentials in `.env`
- Never commit `.env` to version control
- Use secrets management for production deployments
- Configure CORS properly for your domain
