# Docker Deployment Guide

This guide explains how to deploy the Expense Splitter application using Docker Desktop.

## Prerequisites

- Docker Desktop installed and running
- At least 2GB of available RAM
- Ports 8000 and 5173 available (or configure different ports in `.env.development`)

## Quick Start

### 1. Build and Start Services

```bash
docker-compose up --build
```

This will:
- Build the backend (FastAPI) container
- Build the frontend (React/Nginx) container
- Create necessary volumes for data persistence
- Start both services with health checks

### 2. Access the Application

- **Frontend UI**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

### 3. Stop Services

```bash
docker-compose down
```

To remove all data (including uploaded PDFs and database):
```bash
docker-compose down -v
```

## Configuration

### Environment Variables

Edit `.env.development` to customize:

```env
# Change ports
BACKEND_PORT=8000
FRONTEND_PORT=5173

# Database (SQLite by default)
DATABASE_URL=sqlite:///./data/expense_matcher.db

# API URL for frontend
VITE_API_BASE_URL=http://localhost:8000
```

### Using PostgreSQL (Optional)

To use PostgreSQL instead of SQLite:

1. Uncomment PostgreSQL configuration in `.env.development`:
```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/expense_matcher
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=expense_matcher
```

2. Add PostgreSQL service to `docker-compose.yml`:
```yaml
  db:
    image: postgres:15-alpine
    container_name: expense-splitter-db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-expense_matcher}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - expense-splitter
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

3. Update backend service to depend on db:
```yaml
  backend:
    depends_on:
      db:
        condition: service_healthy
```

## Development Mode

The current setup includes hot-reloading for the backend:

- Backend changes: Edit files in `backend/` - uvicorn will auto-reload
- Frontend changes: Requires rebuild (`docker-compose up --build frontend`)

### Watch Mode for Frontend Development

For frontend hot-reloading, you can run it outside Docker:

```bash
# Stop frontend container
docker-compose stop frontend

# Run frontend locally
cd frontend
npm install
npm run dev
```

Keep backend running in Docker for API access.

## Troubleshooting

### Port Already in Use

If ports 8000 or 5173 are taken:

1. Edit `.env.development`:
```env
BACKEND_PORT=8001
FRONTEND_PORT=5174
```

2. Update `VITE_API_BASE_URL` if changing backend port:
```env
VITE_API_BASE_URL=http://localhost:8001
```

3. Rebuild:
```bash
docker-compose up --build
```

### Container Fails Health Check

Check logs:
```bash
docker-compose logs backend
docker-compose logs frontend
```

### Permission Issues (Linux/Mac)

If you encounter permission issues with volumes:
```bash
sudo chown -R $USER:$USER data/ uploads/ exports/
```

### Clear All Data and Restart

```bash
docker-compose down -v
rm -rf data/* uploads/* exports/*
docker-compose up --build
```

## Production Deployment

For production deployment, consider:

1. **Use PostgreSQL** instead of SQLite
2. **Enable HTTPS** with a reverse proxy (nginx/traefik)
3. **Set secure environment variables**:
   - Use `.env.production` instead of `.env.development`
   - Set `LOG_LEVEL=INFO`
   - Set `SQLALCHEMY_ECHO=false`
4. **Configure backup volumes**:
   - Regular database backups
   - Backup uploaded PDFs and exports
5. **Resource limits** in docker-compose:
```yaml
  backend:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
```

## Container Management

### View Running Containers
```bash
docker-compose ps
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Execute Commands in Container
```bash
# Backend shell
docker-compose exec backend bash

# Run database migrations
docker-compose exec backend alembic upgrade head

# Run tests
docker-compose exec backend pytest
```

## Data Persistence

The following directories are mounted as volumes:
- `./data/` - SQLite database
- `./uploads/` - Uploaded PDF files
- `./exports/` - Generated split PDFs

These directories persist between container restarts unless you use `docker-compose down -v`.

## Health Checks

Both services include health checks:

- **Backend**: Checks `/api/health` endpoint every 30s
- **Frontend**: Checks nginx is serving files every 30s

View health status:
```bash
docker-compose ps
```

Healthy containers show `(healthy)` in the status column.

## Next Steps

1. Upload CAR and receipt PDFs via the UI
2. Extract transactions
3. Review matches with confidence scores
4. Generate split PDFs
5. Download matched pairs

For API usage, visit http://localhost:8000/docs for interactive documentation.
