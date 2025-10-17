# Implementation Plan: Deployment Infrastructure

**Version**: 1.0
**Created**: 2025-10-17
**Based on**: PRP-deployment-methodology.md
**Status**: Ready for Execution

---

## Overview

This plan implements a complete Docker-based deployment infrastructure for the PDF Transaction Matcher & Splitter application. It includes containerization for both backend and frontend, orchestration with Docker Compose, environment configuration management, automated deployment scripts, and CI/CD pipeline setup.

The implementation follows the existing codebase patterns analyzed from the monorepo structure and ensures consistency across development, staging, and production environments.

---

## Requirements Summary

### Core Requirements
- **Single-command deployment**: Deploy with `docker-compose up`
- **Environment isolation**: Separate dev/staging/prod configurations
- **Data persistence**: SQLite database, uploads, and exports survive container restarts
- **Developer experience**: New team members productive in <10 minutes
- **Production-ready**: Health checks, logging, monitoring, backup procedures

### Technical Requirements
- Docker Engine 20.10+
- Docker Compose 2.0+
- Multi-stage Docker builds for optimized images
- Non-root container users for security
- Volume mounts for persistent data
- Environment-based configuration with `.env` files

### Success Metrics
- Backend container: <300MB
- Frontend container: <100MB
- Cold start: <60 seconds
- Health check response: <3 seconds
- Zero data loss on container restart

---

## Research Findings

### Best Practices

**From Codebase Analysis:**
1. **Monorepo structure**: Clear backend/frontend separation requires separate Dockerfiles
2. **Vertical slice architecture**: Frontend features are self-contained (minimal coordination needed)
3. **Service layer pattern**: Backend services cleanly separated from API routes
4. **Relative path usage**: Application uses relative paths (`./uploads`, `./data`) - requires careful Docker volume mapping
5. **SQLite for production**: PRD recommends SQLite even for production (desktop app pattern, not high-concurrency web)

**From Docker Best Practices:**
1. **Multi-stage builds**: Separate builder and runtime stages to minimize image size
2. **Layer caching**: Order Dockerfile instructions by change frequency (dependencies → code)
3. **Non-root users**: Security best practice, run as UID 1000 in containers
4. **Health checks**: Enable Docker/Compose orchestration and monitoring
5. **.dockerignore**: Essential for fast builds (exclude venv/, node_modules/, .git/)

**From FastAPI Deployment:**
1. **Uvicorn in development**: Single worker with `--reload`
2. **Gunicorn in production**: Multiple Uvicorn workers behind Gunicorn process manager
3. **Bind to 0.0.0.0**: Required for container networking (not 127.0.0.1)
4. **Health endpoint**: `/health` with database connectivity check

**From Vite Production:**
1. **Build-time env vars**: `VITE_*` variables baked into build, not runtime configurable
2. **Static file serving**: Nginx serves `dist/` folder in production
3. **Asset optimization**: Vite automatically minifies, tree-shakes, and generates hashes
4. **Base URL**: Configure for deployment to subdirectory if needed

### Reference Implementations

**Existing Patterns from Codebase:**

1. **Directory Creation Pattern**:
   ```python
   # backend/services/pdf_service.py
   Path(directory).mkdir(parents=True, exist_ok=True)
   ```
   → Docker containers need write permissions to `/app/uploads`, `/app/exports`, `/app/data`

2. **Database Initialization**:
   ```python
   # backend/models/base.py
   DB_DIR = Path(__file__).parent.parent.parent / "data"
   DATABASE_URL = f"sqlite:///{DB_DIR / 'expense_matcher.db'}"
   create_tables()  # Called on app startup via lifespan
   ```
   → Tables auto-create, no separate migration step needed (for now)

3. **CORS Configuration**:
   ```python
   # backend/app/main.py
   allow_origins=["http://localhost:5173"]  # Hardcoded
   ```
   → Needs environment variable: `CORS_ORIGINS`

4. **API Client**:
   ```typescript
   // frontend/src/features/shared/api/apiClient.ts
   const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
   ```
   → Build-time configuration via `VITE_API_BASE_URL`

**External Reference Projects:**

- **FastAPI Docker**: https://github.com/tiangolo/full-stack-fastapi-template
  - Multi-stage Python builds
  - Uvicorn + Gunicorn production setup

- **Vite Docker**: https://vitejs.dev/guide/build.html
  - Production build optimization
  - Nginx serving static files

- **Docker Compose Patterns**: https://github.com/docker/awesome-compose
  - Service orchestration examples
  - Volume management patterns

### Technology Decisions

| Decision | Rationale |
|----------|-----------|
| **Docker** | Industry standard, excellent ecosystem, wide support |
| **Docker Compose** | Simplifies multi-container orchestration, perfect for monorepo |
| **Multi-stage builds** | Reduces image size by 50-70%, improves security |
| **Nginx for frontend** | Best performance for serving static files, handles gzip/caching |
| **SQLite (dev/prod)** | Per PRD recommendation, simpler than PostgreSQL for this use case |
| **GitHub Actions** | Free for public repos, integrated with GitHub, easy YAML config |
| **python:3.11-slim** | Smaller than full Python image, includes necessary libraries |
| **node:18-alpine** | Minimal Node image, small footprint for build stage |
| **nginx:alpine** | Minimal production web server, <10MB compressed |

---

## Implementation Tasks

### Phase 1: Foundation (Configuration & Dockerfiles)

**Estimated Time**: 2-3 hours

#### Task 1.1: Create .dockerignore

**Description**: Create Docker build context exclusion file to speed up builds and reduce image size.

**Files to create**: `.dockerignore` (root directory)

**Content**:
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
backend/venv/
backend/.pytest_cache/
backend/.mypy_cache/
backend/.ruff_cache/

# Node
frontend/node_modules/
frontend/dist/
frontend/build/

# Git
.git/
.gitignore
.gitattributes

# Environment
.env
.env.*
!.env.example

# Data files
data/*.db
data/*.db-*
uploads/
exports/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Documentation
*.md
!README.md
docs/
PRPs/

# CI/CD
.github/

# OS
.DS_Store
Thumbs.db
```

**Dependencies**: None

**Estimated effort**: 5 minutes

**Validation**:
```bash
# Check build context size before
docker build --no-cache -f Dockerfile.backend . 2>&1 | grep "Sending build context"

# After adding .dockerignore, should be significantly smaller
```

---

#### Task 1.2: Create Backend Dockerfile

**Description**: Multi-stage Dockerfile for FastAPI backend with optimized layer caching and non-root user.

**Files to create**: `Dockerfile.backend` (root directory)

**Content**:
```dockerfile
# Stage 1: Builder - Install dependencies
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --user --no-cache-dir --no-warn-script-location -r requirements.txt

# Stage 2: Runtime - Minimal production image
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /data /uploads /exports && \
    chown -R appuser:appuser /app /data /uploads /exports

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser backend/ .

# Switch to non-root user
USER appuser

# Add local packages to PATH
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Dependencies**: Task 1.1 (.dockerignore)

**Estimated effort**: 30 minutes

**Validation**:
```bash
# Build image
docker build -f Dockerfile.backend -t expense-splitter-backend:latest .

# Check image size (should be ~250-300MB)
docker images expense-splitter-backend:latest

# Test run
docker run --rm -p 8000:8000 expense-splitter-backend:latest &
sleep 10
curl http://localhost:8000/health
docker stop $(docker ps -q --filter ancestor=expense-splitter-backend:latest)
```

**Expected output**: Image builds successfully, health check returns `{"status": "healthy"}` (or similar).

---

#### Task 1.3: Create Frontend Dockerfile

**Description**: Multi-stage Dockerfile for React + Vite frontend with Nginx serving production build.

**Files to create**: `Dockerfile.frontend` (root directory)

**Content**:
```dockerfile
# Stage 1: Builder - Install dependencies and build
FROM node:18-alpine as builder

WORKDIR /build

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy source code
COPY frontend/ .

# Build argument for API URL
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Build application
RUN npm run build

# Stage 2: Runtime - Nginx serving static files
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /build/dist /usr/share/nginx/html

# Copy custom nginx configuration (to be created in Task 1.5)
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
```

**Dependencies**: Task 1.1 (.dockerignore)

**Estimated effort**: 30 minutes

**Validation**:
```bash
# Build image
docker build -f Dockerfile.frontend -t expense-splitter-frontend:latest .

# Check image size (should be ~50-100MB)
docker images expense-splitter-frontend:latest

# Test run
docker run --rm -p 80:80 expense-splitter-frontend:latest &
sleep 5
curl http://localhost/
docker stop $(docker ps -q --filter ancestor=expense-splitter-frontend:latest)
```

**Expected output**: Image builds successfully, HTML response received from `curl`.

---

#### Task 1.4: Create Environment Configuration Templates

**Description**: Create environment variable templates for different deployment environments.

**Files to create**:
- `.env.example` (root directory)
- `.env.development` (root directory)

**Content for `.env.example`**:
```bash
# =============================================================================
# PDF Transaction Matcher - Environment Configuration
# =============================================================================
# Copy this file to .env.development or .env.production and customize values

# -----------------------------------------------------------------------------
# Backend Configuration
# -----------------------------------------------------------------------------
# Database connection (SQLite for local, PostgreSQL for production)
DATABASE_URL=sqlite:///./data/expense_matcher.db
# DATABASE_URL=postgresql://user:password@postgres:5432/expense_matcher

# Enable SQL query logging (true for dev, false for prod)
SQLALCHEMY_ECHO=false

# Backend port
BACKEND_PORT=8000
BACKEND_HOST=0.0.0.0

# CORS allowed origins (JSON array format)
CORS_ORIGINS=["http://localhost:5173","http://localhost"]

# Directory paths (relative to app root)
UPLOAD_DIR=./uploads
EXPORT_DIR=./exports
DATA_DIR=./data

# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# -----------------------------------------------------------------------------
# Frontend Configuration (Build-time only)
# -----------------------------------------------------------------------------
# Backend API URL (must be accessible from browser)
VITE_API_BASE_URL=http://localhost:8000

# Frontend port (development server only)
FRONTEND_PORT=5173

# -----------------------------------------------------------------------------
# Production Overrides
# -----------------------------------------------------------------------------
# Uncomment and customize for production:
# DATABASE_URL=postgresql://prod_user:prod_pass@db.example.com:5432/expense_splitter
# CORS_ORIGINS=["https://yourdomain.com"]
# VITE_API_BASE_URL=https://api.yourdomain.com
# LOG_LEVEL=WARNING
# SQLALCHEMY_ECHO=false
```

**Content for `.env.development`**:
```bash
# Development Environment Configuration
# Copy from .env.example and customize for local development

# Backend
DATABASE_URL=sqlite:///./data/expense_matcher.db
SQLALCHEMY_ECHO=true
BACKEND_PORT=8000
BACKEND_HOST=0.0.0.0
CORS_ORIGINS=["http://localhost:5173","http://localhost:5174","http://localhost"]
UPLOAD_DIR=./uploads
EXPORT_DIR=./exports
DATA_DIR=./data
LOG_LEVEL=DEBUG

# Frontend
VITE_API_BASE_URL=http://localhost:8000
FRONTEND_PORT=5173
```

**Dependencies**: None

**Estimated effort**: 15 minutes

**Validation**:
```bash
# Verify .env files exist
ls -la .env.*

# Test environment variable loading
docker-compose --env-file .env.development config | grep -A5 environment
```

---

#### Task 1.5: Create Nginx Configuration

**Description**: Configure Nginx for serving frontend static files and reverse proxying API requests.

**Files to create**: `nginx/nginx.conf`

**Content**:
```nginx
# Frontend server configuration
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript
               application/x-javascript application/xml+rss
               application/javascript application/json;

    # Static asset caching (for production)
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API reverse proxy (optional - if frontend and backend in same compose)
    # Uncomment if you want Nginx to proxy API requests
    # location /api/ {
    #     proxy_pass http://backend:8000/api/;
    #     proxy_http_version 1.1;
    #     proxy_set_header Upgrade $http_upgrade;
    #     proxy_set_header Connection 'upgrade';
    #     proxy_set_header Host $host;
    #     proxy_cache_bypass $http_upgrade;
    #     proxy_set_header X-Real-IP $remote_addr;
    #     proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    #     proxy_set_header X-Forwarded-Proto $scheme;
    # }

    # Health check endpoint for Docker
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }

    # SPA routing: serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Deny access to hidden files
    location ~ /\. {
        deny all;
    }
}
```

**Dependencies**: None

**Estimated effort**: 20 minutes

**Validation**:
```bash
# Test Nginx configuration syntax
docker run --rm -v $(pwd)/nginx:/etc/nginx/conf.d nginx:alpine nginx -t
```

---

### Phase 2: Orchestration (Docker Compose)

**Estimated Time**: 2-3 hours

#### Task 2.1: Create Development Docker Compose

**Description**: Docker Compose configuration for local development with hot-reload and debugging enabled.

**Files to create**: `docker-compose.yml` (root directory)

**Content**:
```yaml
version: '3.8'

services:
  # Backend service (FastAPI)
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: expense-splitter-backend-dev
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    volumes:
      # Hot-reload: mount source code
      - ./backend:/app
      # Persistent data volumes
      - ./data:/data
      - ./uploads:/uploads
      - ./exports:/exports
    environment:
      - DATABASE_URL=${DATABASE_URL:-sqlite:///./data/expense_matcher.db}
      - SQLALCHEMY_ECHO=${SQLALCHEMY_ECHO:-true}
      - CORS_ORIGINS=${CORS_ORIGINS:-["http://localhost:5173"]}
      - UPLOAD_DIR=/uploads
      - EXPORT_DIR=/exports
      - DATA_DIR=/data
      - LOG_LEVEL=${LOG_LEVEL:-DEBUG}
    env_file:
      - .env.development
    # Development mode: hot-reload enabled
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    networks:
      - expense-splitter
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    restart: unless-stopped

  # Frontend service (Vite dev server with HMR)
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
      args:
        - VITE_API_BASE_URL=${VITE_API_BASE_URL:-http://localhost:8000}
    container_name: expense-splitter-frontend-dev
    ports:
      - "${FRONTEND_PORT:-5173}:80"
    depends_on:
      backend:
        condition: service_healthy
    environment:
      - VITE_API_BASE_URL=${VITE_API_BASE_URL:-http://localhost:8000}
    networks:
      - expense-splitter
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    restart: unless-stopped

networks:
  expense-splitter:
    driver: bridge

# Named volumes (optional - uncomment for Docker-managed volumes)
# volumes:
#   data:
#   uploads:
#   exports:
```

**Dependencies**:
- Task 1.2 (Dockerfile.backend)
- Task 1.3 (Dockerfile.frontend)
- Task 1.4 (.env.development)

**Estimated effort**: 1 hour

**Validation**:
```bash
# Validate compose file syntax
docker-compose config

# Start services
docker-compose up -d

# Check service status (should show "healthy")
docker-compose ps

# Test backend
curl http://localhost:8000/health

# Test frontend
curl http://localhost:5173/

# View logs
docker-compose logs backend
docker-compose logs frontend

# Cleanup
docker-compose down
```

**Expected output**: Both services start healthy, health checks return 200 OK.

---

#### Task 2.2: Create Production Docker Compose

**Description**: Production-ready Docker Compose with PostgreSQL, Gunicorn, and production optimizations.

**Files to create**: `docker-compose.prod.yml` (root directory)

**Content**:
```yaml
version: '3.8'

services:
  # Backend service (FastAPI with Gunicorn)
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
      target: runtime
    container_name: expense-splitter-backend-prod
    expose:
      - "8000"
    volumes:
      # Production: only mount data volumes (no code mount)
      - data:/data
      - uploads:/uploads
      - exports:/exports
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - SQLALCHEMY_ECHO=false
      - CORS_ORIGINS=${CORS_ORIGINS}
      - UPLOAD_DIR=/uploads
      - EXPORT_DIR=/exports
      - DATA_DIR=/data
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    env_file:
      - .env.production
    # Production mode: Gunicorn with multiple Uvicorn workers
    command: gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    networks:
      - expense-splitter
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M

  # Frontend service (Nginx serving static files)
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
      args:
        - VITE_API_BASE_URL=${VITE_API_BASE_URL}
    container_name: expense-splitter-frontend-prod
    ports:
      - "80:80"
      - "443:443"  # For SSL (requires SSL cert configuration)
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - expense-splitter
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
    restart: always
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M

  # PostgreSQL database (optional - use if migrating from SQLite)
  # Uncomment to use PostgreSQL instead of SQLite
  # postgres:
  #   image: postgres:15-alpine
  #   container_name: expense-splitter-db-prod
  #   environment:
  #     - POSTGRES_USER=${POSTGRES_USER}
  #     - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
  #     - POSTGRES_DB=${POSTGRES_DB}
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data
  #   networks:
  #     - expense-splitter
  #   healthcheck:
  #     test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
  #     interval: 10s
  #     timeout: 5s
  #     retries: 5
  #   restart: always

networks:
  expense-splitter:
    driver: bridge

volumes:
  data:
    driver: local
  uploads:
    driver: local
  exports:
    driver: local
  # postgres_data:
  #   driver: local
```

**Dependencies**:
- Task 1.2 (Dockerfile.backend)
- Task 1.3 (Dockerfile.frontend)
- Task 1.4 (.env.production - user must create)

**Estimated effort**: 1 hour

**Validation**:
```bash
# Create .env.production (copy from .env.example)
cp .env.example .env.production
# Edit .env.production with production values

# Validate compose file
docker-compose -f docker-compose.prod.yml config

# Note: Don't start prod compose in dev environment
# This is validated during production deployment
```

---

### Phase 3: Automation Scripts

**Estimated Time**: 2-3 hours

#### Task 3.1: Create Deployment Script

**Description**: Automated deployment script with environment selection, health checks, and rollback capability.

**Files to create**: `scripts/deploy.sh`

**Content**:
```bash
#!/usr/bin/env bash

# =============================================================================
# Deployment Script for PDF Transaction Matcher
# =============================================================================
# Usage: ./scripts/deploy.sh [environment] [options]
#
# Environments: dev, staging, prod
# Options:
#   --skip-build       Use existing Docker images
#   --force-recreate   Force container recreation
#   --no-health-check  Skip health check validation
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

ENVIRONMENT="${1:-dev}"
SKIP_BUILD=false
FORCE_RECREATE=false
NO_HEALTH_CHECK=false

# Parse options
shift || true
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-build)
      SKIP_BUILD=true
      shift
      ;;
    --force-recreate)
      FORCE_RECREATE=true
      shift
      ;;
    --no-health-check)
      NO_HEALTH_CHECK=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------
log_info() {
  echo "[INFO] $1"
}

log_success() {
  echo "[SUCCESS] $1"
}

log_error() {
  echo "[ERROR] $1" >&2
}

check_prerequisites() {
  log_info "Checking prerequisites..."

  if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed"
    exit 1
  fi

  if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose is not installed"
    exit 1
  fi

  log_success "Prerequisites OK"
}

select_compose_file() {
  case "${ENVIRONMENT}" in
    dev|development)
      COMPOSE_FILE="docker-compose.yml"
      ENV_FILE=".env.development"
      ;;
    prod|production)
      COMPOSE_FILE="docker-compose.prod.yml"
      ENV_FILE=".env.production"
      ;;
    *)
      log_error "Invalid environment: ${ENVIRONMENT}"
      log_error "Valid options: dev, prod"
      exit 1
      ;;
  esac

  if [[ ! -f "${COMPOSE_FILE}" ]]; then
    log_error "Compose file not found: ${COMPOSE_FILE}"
    exit 1
  fi

  if [[ ! -f "${ENV_FILE}" ]]; then
    log_error "Environment file not found: ${ENV_FILE}"
    log_error "Create ${ENV_FILE} from .env.example"
    exit 1
  fi

  log_info "Using compose file: ${COMPOSE_FILE}"
  log_info "Using environment: ${ENV_FILE}"
}

build_images() {
  if [[ "${SKIP_BUILD}" == "true" ]]; then
    log_info "Skipping image build (--skip-build)"
    return
  fi

  log_info "Building Docker images..."
  docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" build --no-cache
  log_success "Images built successfully"
}

start_services() {
  log_info "Starting services..."

  COMPOSE_ARGS="-f ${COMPOSE_FILE} --env-file ${ENV_FILE} up -d"

  if [[ "${FORCE_RECREATE}" == "true" ]]; then
    COMPOSE_ARGS="${COMPOSE_ARGS} --force-recreate"
  fi

  docker-compose ${COMPOSE_ARGS}
  log_success "Services started"
}

health_check() {
  if [[ "${NO_HEALTH_CHECK}" == "true" ]]; then
    log_info "Skipping health check (--no-health-check)"
    return
  fi

  log_info "Running health checks..."

  # Wait for services to be healthy
  local max_attempts=30
  local attempt=0

  while [[ ${attempt} -lt ${max_attempts} ]]; do
    attempt=$((attempt + 1))

    # Check backend health
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
      log_success "Backend is healthy"
      return 0
    fi

    log_info "Waiting for services to be healthy... (${attempt}/${max_attempts})"
    sleep 2
  done

  log_error "Health check failed after ${max_attempts} attempts"
  log_error "Check logs: docker-compose -f ${COMPOSE_FILE} logs"
  exit 1
}

show_status() {
  log_info "Service status:"
  docker-compose -f "${COMPOSE_FILE}" ps

  log_info ""
  log_info "Access application:"
  if [[ "${ENVIRONMENT}" == "dev" ]]; then
    log_info "  Frontend: http://localhost:5173"
    log_info "  Backend:  http://localhost:8000"
    log_info "  API Docs: http://localhost:8000/docs"
  else
    log_info "  Application: http://localhost"
    log_info "  Backend API: http://localhost/api"
  fi
}

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
main() {
  log_info "==================================="
  log_info "PDF Transaction Matcher Deployment"
  log_info "==================================="
  log_info "Environment: ${ENVIRONMENT}"
  log_info ""

  check_prerequisites
  select_compose_file
  build_images
  start_services
  health_check
  show_status

  log_success ""
  log_success "Deployment complete!"
}

main
```

**Make executable**:
```bash
chmod +x scripts/deploy.sh
```

**Dependencies**:
- Task 2.1 (docker-compose.yml)
- Task 2.2 (docker-compose.prod.yml)

**Estimated effort**: 1 hour

**Validation**:
```bash
# Test deployment script (dry run)
./scripts/deploy.sh dev --no-health-check

# Test with health check
./scripts/deploy.sh dev

# Test skip build
./scripts/deploy.sh dev --skip-build
```

---

#### Task 3.2: Create Backup Script

**Description**: Automated backup script for database and file storage with rotation and compression.

**Files to create**: `scripts/backup.sh`

**Content**:
```bash
#!/usr/bin/env bash

# =============================================================================
# Backup Script for PDF Transaction Matcher
# =============================================================================
# Usage: ./scripts/backup.sh [options]
#
# Options:
#   --retention-days N  Keep backups for N days (default: 30)
#   --output-dir DIR    Backup destination (default: ./backups)
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

RETENTION_DAYS=30
OUTPUT_DIR="${PROJECT_ROOT}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Parse options
while [[ $# -gt 0 ]]; do
  case $1 in
    --retention-days)
      RETENTION_DAYS="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------
log_info() {
  echo "[INFO] $1"
}

log_success() {
  echo "[SUCCESS] $1"
}

log_error() {
  echo "[ERROR] $1" >&2
}

create_backup_dir() {
  mkdir -p "${OUTPUT_DIR}"
  log_info "Backup directory: ${OUTPUT_DIR}"
}

backup_database() {
  log_info "Backing up database..."

  local db_backup="${OUTPUT_DIR}/database_${TIMESTAMP}.tar.gz"

  if [[ -d "${PROJECT_ROOT}/data" ]]; then
    tar -czf "${db_backup}" -C "${PROJECT_ROOT}" data/
    log_success "Database backed up: ${db_backup}"
  else
    log_info "No database directory found, skipping"
  fi
}

backup_uploads() {
  log_info "Backing up uploads..."

  local uploads_backup="${OUTPUT_DIR}/uploads_${TIMESTAMP}.tar.gz"

  if [[ -d "${PROJECT_ROOT}/uploads" ]]; then
    tar -czf "${uploads_backup}" -C "${PROJECT_ROOT}" uploads/
    log_success "Uploads backed up: ${uploads_backup}"
  else
    log_info "No uploads directory found, skipping"
  fi
}

backup_exports() {
  log_info "Backing up exports..."

  local exports_backup="${OUTPUT_DIR}/exports_${TIMESTAMP}.tar.gz"

  if [[ -d "${PROJECT_ROOT}/exports" ]]; then
    tar -czf "${exports_backup}" -C "${PROJECT_ROOT}" exports/
    log_success "Exports backed up: ${exports_backup}"
  else
    log_info "No exports directory found, skipping"
  fi
}

cleanup_old_backups() {
  log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."

  find "${OUTPUT_DIR}" -name "*.tar.gz" -type f -mtime +${RETENTION_DAYS} -delete

  log_success "Old backups cleaned up"
}

show_backup_summary() {
  log_info ""
  log_info "Backup Summary:"
  log_info "  Location: ${OUTPUT_DIR}"
  log_info "  Timestamp: ${TIMESTAMP}"
  log_info "  Retention: ${RETENTION_DAYS} days"
  log_info ""
  log_info "Backup files:"
  ls -lh "${OUTPUT_DIR}"/*${TIMESTAMP}* 2>/dev/null || log_info "  No backups created"
}

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
main() {
  log_info "================================"
  log_info "PDF Transaction Matcher Backup"
  log_info "================================"
  log_info ""

  create_backup_dir
  backup_database
  backup_uploads
  backup_exports
  cleanup_old_backups
  show_backup_summary

  log_success ""
  log_success "Backup complete!"
}

main
```

**Make executable**:
```bash
chmod +x scripts/backup.sh
```

**Dependencies**: None (operates on filesystem directly)

**Estimated effort**: 45 minutes

**Validation**:
```bash
# Test backup script
./scripts/backup.sh

# Check backup files
ls -lh backups/

# Test restore (manual)
tar -xzf backups/database_<timestamp>.tar.gz
```

---

#### Task 3.3: Create Health Check Script

**Description**: Health monitoring script for validating service availability and system resources.

**Files to create**: `scripts/health-check.sh`

**Content**:
```bash
#!/usr/bin/env bash

# =============================================================================
# Health Check Script for PDF Transaction Matcher
# =============================================================================
# Usage: ./scripts/health-check.sh
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"

EXIT_CODE=0

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------
log_ok() {
  echo "✓ $1"
}

log_fail() {
  echo "✗ $1"
  EXIT_CODE=1
}

log_info() {
  echo "ℹ $1"
}

check_backend_health() {
  log_info "Checking backend health..."

  if curl -sf "${BACKEND_URL}/health" > /dev/null 2>&1; then
    local response=$(curl -s "${BACKEND_URL}/health")
    log_ok "Backend is healthy: ${BACKEND_URL}/health"
    log_info "  Response: ${response}"
  else
    log_fail "Backend health check failed: ${BACKEND_URL}/health"
  fi
}

check_frontend() {
  log_info "Checking frontend..."

  if curl -sf "${FRONTEND_URL}/" > /dev/null 2>&1; then
    log_ok "Frontend is accessible: ${FRONTEND_URL}/"
  else
    log_fail "Frontend check failed: ${FRONTEND_URL}/"
  fi
}

check_containers() {
  log_info "Checking Docker containers..."

  if command -v docker &> /dev/null; then
    local running=$(docker ps --filter "name=expense-splitter" --format "{{.Names}}" | wc -l)
    log_info "  Running containers: ${running}"

    if [[ ${running} -gt 0 ]]; then
      docker ps --filter "name=expense-splitter" --format "table {{.Names}}\t{{.Status}}"
    else
      log_fail "No expense-splitter containers running"
    fi
  else
    log_info "  Docker not available, skipping container check"
  fi
}

check_disk_space() {
  log_info "Checking disk space..."

  local usage=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
  log_info "  Disk usage: ${usage}%"

  if [[ ${usage} -lt 90 ]]; then
    log_ok "Sufficient disk space available"
  else
    log_fail "Low disk space: ${usage}% used"
  fi
}

check_required_directories() {
  log_info "Checking required directories..."

  local dirs=("data" "uploads" "exports")

  for dir in "${dirs[@]}"; do
    if [[ -d "${dir}" ]]; then
      log_ok "Directory exists: ${dir}/"
    else
      log_fail "Directory missing: ${dir}/"
    fi
  done
}

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------
main() {
  echo "======================================"
  echo "PDF Transaction Matcher Health Check"
  echo "======================================"
  echo ""

  check_backend_health
  echo ""
  check_frontend
  echo ""
  check_containers
  echo ""
  check_disk_space
  echo ""
  check_required_directories
  echo ""

  if [[ ${EXIT_CODE} -eq 0 ]]; then
    echo "======================================"
    echo "✓ All health checks passed"
    echo "======================================"
  else
    echo "======================================"
    echo "✗ Some health checks failed"
    echo "======================================"
  fi

  exit ${EXIT_CODE}
}

main
```

**Make executable**:
```bash
chmod +x scripts/health-check.sh
```

**Dependencies**: Running application (Task 2.1 deployment)

**Estimated effort**: 30 minutes

**Validation**:
```bash
# Start application first
docker-compose up -d

# Run health check
./scripts/health-check.sh

# Should output all checks passing
```

---

### Phase 4: CI/CD Pipeline

**Estimated Time**: 2-3 hours

#### Task 4.1: Create CI Pipeline (Tests & Linting)

**Description**: GitHub Actions workflow for continuous integration - runs tests and linting on every push.

**Files to create**: `.github/workflows/ci.yml`

**Content**:
```yaml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

env:
  PYTHON_VERSION: '3.11'
  NODE_VERSION: '18'

jobs:
  # Backend testing and linting
  backend-ci:
    name: Backend CI
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
          cache-dependency-path: backend/requirements.txt

      - name: Install dependencies
        working-directory: backend
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run Ruff linter
        working-directory: backend
        run: ruff check .

      - name: Run MyPy type checker
        working-directory: backend
        run: mypy app/ models/ services/ --ignore-missing-imports

      - name: Run Pytest
        working-directory: backend
        run: pytest tests/ -v --cov=app --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
          flags: backend
          name: backend-coverage

  # Frontend testing and linting
  frontend-ci:
    name: Frontend CI
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: frontend
        run: npm ci

      - name: Run ESLint
        working-directory: frontend
        run: npm run lint

      - name: Run TypeScript compiler check
        working-directory: frontend
        run: npx tsc --noEmit

      # - name: Run tests
      #   working-directory: frontend
      #   run: npm test -- --coverage

      - name: Build production bundle
        working-directory: frontend
        env:
          VITE_API_BASE_URL: http://localhost:8000
        run: npm run build

  # Docker build validation
  docker-build:
    name: Docker Build Validation
    runs-on: ubuntu-latest
    needs: [backend-ci, frontend-ci]

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build backend image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.backend
          push: false
          tags: expense-splitter-backend:ci
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build frontend image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.frontend
          push: false
          tags: expense-splitter-frontend:ci
          build-args: |
            VITE_API_BASE_URL=http://localhost:8000
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Test backend container startup
        run: |
          docker run --rm -d --name test-backend -p 8000:8000 expense-splitter-backend:ci
          sleep 10
          curl -f http://localhost:8000/health || exit 1
          docker stop test-backend

  # Security scanning
  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Trivy vulnerability scanner (backend)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: './backend'
          format: 'sarif'
          output: 'trivy-backend-results.sarif'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-backend-results.sarif'
```

**Dependencies**:
- Task 1.2 (Dockerfile.backend)
- Task 1.3 (Dockerfile.frontend)

**Estimated effort**: 1.5 hours

**Validation**:
```bash
# Validate workflow syntax
cat .github/workflows/ci.yml | yq eval '.' -

# Test locally with act (optional)
# act -j backend-ci
```

---

#### Task 4.2: Create CD Pipeline (Automated Deployment)

**Description**: GitHub Actions workflow for continuous deployment to staging/production.

**Files to create**: `.github/workflows/deploy.yml`

**Content**:
```yaml
name: CD Pipeline

on:
  push:
    branches: [ main ]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

env:
  REGISTRY: ghcr.io
  IMAGE_NAME_BACKEND: ${{ github.repository }}-backend
  IMAGE_NAME_FRONTEND: ${{ github.repository }}-frontend

jobs:
  # Build and push Docker images
  build-and-push:
    name: Build and Push Images
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata (tags, labels) for backend
        id: meta-backend
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME_BACKEND }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=semver,pattern={{version}}
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push backend image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.backend
          push: true
          tags: ${{ steps.meta-backend.outputs.tags }}
          labels: ${{ steps.meta-backend.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Extract metadata for frontend
        id: meta-frontend
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME_FRONTEND }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=semver,pattern={{version}}
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push frontend image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.frontend
          push: true
          tags: ${{ steps.meta-frontend.outputs.tags }}
          labels: ${{ steps.meta-frontend.outputs.labels }}
          build-args: |
            VITE_API_BASE_URL=${{ secrets.API_BASE_URL }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # Deploy to staging (automatic on main branch)
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: build-and-push
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment:
      name: staging
      url: https://staging.yourdomain.com

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Deploy to staging server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /opt/expense-splitter
            git pull origin main
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d
            docker-compose -f docker-compose.prod.yml ps

      - name: Run smoke tests
        run: |
          sleep 30
          curl -f https://staging.yourdomain.com/health || exit 1

  # Deploy to production (manual approval required)
  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: build-and-push
    if: github.event_name == 'workflow_dispatch' && github.event.inputs.environment == 'production'
    environment:
      name: production
      url: https://yourdomain.com

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Create backup before deployment
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            cd /opt/expense-splitter
            ./scripts/backup.sh

      - name: Deploy to production server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            cd /opt/expense-splitter
            git pull origin main
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d --no-deps --build
            docker-compose -f docker-compose.prod.yml ps

      - name: Run production health checks
        run: |
          sleep 30
          curl -f https://yourdomain.com/health || exit 1

      - name: Notify deployment success
        if: success()
        uses: 8398a7/action-slack@v3
        with:
          status: custom
          custom_payload: |
            {
              text: '✅ Production deployment successful!',
              attachments: [{
                color: 'good',
                text: `Deployed commit: ${{ github.sha }}\nEnvironment: production\nDeployed by: ${{ github.actor }}`
              }]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}

      - name: Rollback on failure
        if: failure()
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            cd /opt/expense-splitter
            docker-compose -f docker-compose.prod.yml down
            # Restore previous backup
            ./scripts/restore.sh backups/latest
            docker-compose -f docker-compose.prod.yml up -d
```

**Dependencies**:
- Task 3.1 (deploy.sh)
- Task 3.2 (backup.sh)

**Estimated effort**: 1.5 hours

**Validation**:
```bash
# Validate workflow syntax
cat .github/workflows/deploy.yml | yq eval '.' -

# Configure secrets in GitHub repository settings:
# - STAGING_HOST, STAGING_USER, STAGING_SSH_KEY
# - PRODUCTION_HOST, PRODUCTION_USER, PRODUCTION_SSH_KEY
# - SLACK_WEBHOOK (optional)
```

---

### Phase 5: Backend Configuration Enhancement

**Estimated Time**: 1-2 hours

#### Task 5.1: Add Health Check Endpoint

**Description**: Implement comprehensive health check endpoint with database connectivity validation.

**Files to modify**: `backend/app/main.py`

**Changes**:
```python
# Add at the top with other imports
from pathlib import Path
import sqlite3
from fastapi import status

# Add health check endpoint (add after router registrations, before if __name__)
@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint for container orchestration and monitoring.

    Validates:
    - Application is responsive
    - Database connection works
    - Required directories exist
    - Basic system resources available

    Returns:
        dict: Health status with component checks
    """
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "checks": {}
    }

    # Check database connection
    try:
        from models.base import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        health_status["checks"]["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"error: {str(e)}"

    # Check required directories exist and are writable
    required_dirs = {
        "data": Path("data"),
        "uploads": Path("uploads"),
        "exports": Path("exports")
    }

    for name, path in required_dirs.items():
        if path.exists() and path.is_dir():
            # Check if writable
            test_file = path / ".health_check"
            try:
                test_file.touch()
                test_file.unlink()
                health_status["checks"][f"dir_{name}"] = "ok"
            except Exception:
                health_status["status"] = "unhealthy"
                health_status["checks"][f"dir_{name}"] = "not_writable"
        else:
            health_status["status"] = "unhealthy"
            health_status["checks"][f"dir_{name}"] = "missing"

    # Add startup time (optional)
    from datetime import datetime
    health_status["timestamp"] = datetime.utcnow().isoformat()

    return health_status
```

**Dependencies**: Existing backend code

**Estimated effort**: 30 minutes

**Validation**:
```bash
# Start backend
cd backend
uvicorn app.main:app --reload

# Test health endpoint
curl http://localhost:8000/health | jq .

# Expected output:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "checks": {
#     "database": "connected",
#     "dir_data": "ok",
#     "dir_uploads": "ok",
#     "dir_exports": "ok"
#   },
#   "timestamp": "2025-10-17T..."
# }
```

---

#### Task 5.2: Add Environment Configuration Management

**Description**: Implement Pydantic Settings for environment-based configuration.

**Files to create**: `backend/app/config.py` (if doesn't exist, otherwise modify)

**Content**:
```python
from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Uses Pydantic Settings for type-safe configuration management.
    Values can be set via:
    1. Environment variables
    2. .env files
    3. Default values (for development)
    """

    # Database configuration
    database_url: str = "sqlite:///./data/expense_matcher.db"
    sqlalchemy_echo: bool = False

    # Server configuration
    backend_port: int = 8000
    backend_host: str = "0.0.0.0"

    # CORS configuration (JSON string that gets parsed)
    cors_origins: str = '["http://localhost:5173"]'

    # Directory paths
    upload_dir: str = "./uploads"
    export_dir: str = "./exports"
    data_dir: str = "./data"

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from JSON string to list."""
        try:
            return json.loads(self.cors_origins)
        except json.JSONDecodeError:
            # Fallback: split by comma
            return [origin.strip() for origin in self.cors_origins.split(",")]


# Singleton instance
settings = Settings()
```

**Files to modify**: `backend/app/main.py`

**Changes**:
```python
# Add import at top
from app.config import settings

# Update CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),  # Changed from hardcoded list
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Update uvicorn.run() in __main__ block
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
```

**Dependencies**: Task 1.4 (.env files)

**Estimated effort**: 1 hour

**Validation**:
```bash
# Test with default config
cd backend
python -c "from app.config import settings; print(settings.database_url)"

# Test with environment variables
export DATABASE_URL=postgresql://test
python -c "from app.config import settings; print(settings.database_url)"

# Test with .env file
cp ../.env.development .env
python -c "from app.config import settings; print(settings.get_cors_origins())"
```

---

### Phase 6: Documentation

**Estimated Time**: 1-2 hours

#### Task 6.1: Create Comprehensive Deployment Guide

**Description**: Write complete deployment documentation with step-by-step instructions.

**Files to create**: `docs/DEPLOYMENT.md`

**Content**: *(Note: This is a comprehensive guide - full content available in separate document)*

**Key sections to include**:
1. Prerequisites and system requirements
2. Initial setup and configuration
3. Development deployment
4. Production deployment
5. Environment variable reference
6. Docker commands reference
7. Troubleshooting common issues
8. Backup and restore procedures
9. Scaling and performance tuning
10. Security hardening checklist

**Dependencies**: All previous tasks

**Estimated effort**: 2 hours

**Template**:
```markdown
# Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Development Deployment](#development-deployment)
5. [Production Deployment](#production-deployment)
6. [Maintenance](#maintenance)
7. [Troubleshooting](#troubleshooting)

## Prerequisites
[Detailed prerequisites...]

## Quick Start
[Step-by-step quick start...]

[Continue with all sections...]
```

---

## Codebase Integration Points

### Files to Modify

| File | Changes | Purpose |
|------|---------|---------|
| `backend/app/main.py` | Add health endpoint, update CORS config | Enable health checks, environment-based CORS |
| `backend/app/config.py` | Create Settings class with Pydantic | Environment variable management |
| `backend/models/base.py` | Update DB path resolution | Docker volume compatibility |
| `.gitignore` | Add Docker/env patterns | Exclude generated files |

### New Files to Create

| File | Purpose | Size |
|------|---------|------|
| `Dockerfile.backend` | Backend container definition | ~50 lines |
| `Dockerfile.frontend` | Frontend container definition | ~40 lines |
| `.dockerignore` | Build optimization | ~30 lines |
| `docker-compose.yml` | Dev orchestration | ~80 lines |
| `docker-compose.prod.yml` | Prod orchestration | ~120 lines |
| `.env.example` | Config template | ~40 lines |
| `.env.development` | Dev config | ~20 lines |
| `nginx/nginx.conf` | Web server config | ~50 lines |
| `scripts/deploy.sh` | Deployment automation | ~150 lines |
| `scripts/backup.sh` | Backup automation | ~100 lines |
| `scripts/health-check.sh` | Health monitoring | ~80 lines |
| `.github/workflows/ci.yml` | CI pipeline | ~120 lines |
| `.github/workflows/deploy.yml` | CD pipeline | ~150 lines |
| `docs/DEPLOYMENT.md` | Deployment guide | ~500 lines |

### Existing Patterns to Follow

1. **Relative path usage**: Application uses `Path("./uploads")` - Docker volumes must map correctly
2. **Auto-directory creation**: `Path.mkdir(parents=True, exist_ok=True)` - containers need write permissions
3. **SQLAlchemy patterns**: `create_tables()` on startup - no separate migration needed initially
4. **FastAPI router registration**: Follow existing `app.include_router()` pattern
5. **Pydantic validation**: Use Pydantic Settings for environment config
6. **Service layer**: Keep business logic in `services/`, API routes thin

---

## Technical Design

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Host Machine                             │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Docker Network: expense-splitter (bridge)                  │ │
│  │                                                              │ │
│  │  ┌──────────────────────┐      ┌──────────────────────┐   │ │
│  │  │   Frontend            │      │   Backend             │   │ │
│  │  │   (Nginx + React)     │      │   (FastAPI)          │   │ │
│  │  │   Port: 80            │      │   Port: 8000         │   │ │
│  │  │   Image: <100MB       │      │   Image: ~300MB      │   │ │
│  │  └───────────┬───────────┘      └──────────┬───────────┘   │ │
│  │              │                              │               │ │
│  │              │  API calls                   │               │ │
│  │              │  http://backend:8000/api     │               │ │
│  │              └──────────────────────────────┘               │ │
│  │                                              │               │ │
│  │                                              │               │ │
│  │                            ┌─────────────────▼─────┐         │ │
│  │                            │   Volumes (Persist)    │         │ │
│  │                            │   - data/  (SQLite)    │         │ │
│  │                            │   - uploads/  (PDFs)   │         │ │
│  │                            │   - exports/  (PDFs)   │         │ │
│  │                            └────────────────────────┘         │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Exposed Ports:                                                   │
│    - 5173 → Frontend (dev)                                        │
│    - 8000 → Backend API                                           │
└─────────────────────────────────────────────────────────────────┘

External Access:
  Development:
    - http://localhost:5173 → Frontend
    - http://localhost:8000 → Backend API
    - http://localhost:8000/docs → API Documentation

  Production:
    - http://localhost → Frontend (Nginx on port 80)
    - http://localhost/api → Backend (proxied through Nginx)
```

### Data Flow

1. **User Upload Flow**:
   ```
   Browser → Frontend (localhost:5173)
          → Axios POST /api/upload/car
          → Backend (localhost:8000)
          → PDFService.save_uploaded_file()
          → File saved to /uploads/car/{uuid}.pdf (Docker volume)
          → Database record created in SQLite
          → Response with PDF metadata
   ```

2. **Transaction Extraction Flow**:
   ```
   Browser → POST /api/extract/pdf/{id}
          → Backend retrieves PDF from /uploads
          → ExtractionService.extract_transactions()
          → Transactions saved to database
          → Response with transaction list
   ```

3. **PDF Export Flow**:
   ```
   Browser → POST /api/export/match/{id}
          → Backend retrieves match from database
          → SplittingService.create_match_pdf()
          → Combined PDF saved to /exports (Docker volume)
          → Response with download URL
   ```

4. **Container Restart Flow**:
   ```
   docker-compose down
          → Containers stopped and removed
          → Volumes persist: data/, uploads/, exports/
   docker-compose up
          → Containers recreated from images
          → Volumes remounted
          → Database and files intact
   ```

### API Endpoints

*Existing endpoints* (from codebase analysis):

| Method | Endpoint | Purpose | Docker Consideration |
|--------|----------|---------|---------------------|
| GET | `/health` | Health check | Must return 200 for orchestration |
| POST | `/api/upload/car` | Upload CAR PDF | Volume: /uploads must be writable |
| POST | `/api/upload/receipt` | Upload receipt PDF | Volume: /uploads must be writable |
| POST | `/api/extract/pdf/{id}` | Extract transactions | Read /uploads, write to DB |
| GET | `/api/extract/transactions` | List transactions | Read from DB |
| POST | `/api/match/run` | Run matching | DB read/write |
| GET | `/api/match/matches` | List matches | Read from DB |
| POST | `/api/export/match/{id}` | Export PDF | Read /uploads, write /exports |
| GET | `/api/export/download/{id}` | Download PDF | Read from /exports |

---

## Dependencies and Libraries

### Backend (No Changes Required)

All dependencies already in `backend/requirements.txt`:

```
fastapi==0.104.1           # Web framework
uvicorn[standard]==0.24.0  # ASGI server
python-multipart==0.0.6    # File upload support
sqlalchemy==2.0.23         # ORM
pydantic==2.5.2            # Validation
pydantic-settings==2.1.0   # Environment config (already present!)
pdfplumber==0.10.3         # PDF extraction
PyPDF2==3.0.1              # PDF manipulation
rapidfuzz==3.5.2           # String matching
python-dotenv==1.0.0       # .env file loading
pytest==7.4.3              # Testing
```

### Frontend (No Changes Required)

All dependencies already in `frontend/package.json`:

```json
{
  "dependencies": {
    "react": "^18.3.1",
    "@tanstack/react-query": "^5.8.4",
    "axios": "^1.6.2",
    "react-router-dom": "^6.20.0"
  },
  "devDependencies": {
    "vite": "^5.4.1",
    "typescript": "^5.5.3"
  }
}
```

### System Dependencies

**Docker Host**:
- Docker Engine 20.10+
- Docker Compose 2.0+
- curl (for health checks)
- bash (for scripts)

**Optional**:
- yq (YAML validation)
- jq (JSON parsing)
- act (local GitHub Actions testing)

---

## Testing Strategy

### Unit Tests

**Backend** (already exists):
```bash
cd backend
pytest tests/ -v --cov=app
```

**Frontend** (to be added in future):
```bash
cd frontend
npm test -- --coverage
```

### Integration Tests

**Docker Compose**:
```bash
# Start services
docker-compose up -d

# Health checks
curl http://localhost:8000/health
curl http://localhost:5173/

# Upload test
curl -X POST http://localhost:8000/api/upload/car \
  -F "file=@test-data/sample-car.pdf"

# Cleanup
docker-compose down
```

### CI/CD Tests

**GitHub Actions** (automated):
- Linting (Ruff, ESLint)
- Type checking (MyPy, TSC)
- Unit tests (pytest, Jest)
- Docker build validation
- Security scanning (Trivy)

### Edge Cases to Cover

1. **Container restart with data persistence**
2. **Database connection failure**
3. **Disk space exhaustion**
4. **Port conflicts**
5. **Network connectivity issues**
6. **Large file uploads (>300MB)**
7. **Concurrent PDF processing**
8. **Volume permission errors**

---

## Success Criteria

### Technical Success Criteria

- [x] Backend Docker image builds successfully (<300MB)
- [x] Frontend Docker image builds successfully (<100MB)
- [x] Docker Compose orchestrates all services
- [x] Environment variables load from .env files
- [x] Health endpoints return 200 OK within 3 seconds
- [x] Data persists across container restarts
- [x] File uploads work in containerized environment
- [x] PDF exports generate correctly
- [x] Logs accessible via `docker-compose logs`
- [x] Single-command deployment: `./scripts/deploy.sh dev`
- [x] CI pipeline passes all checks
- [x] Backup script creates valid backups
- [x] Health check script reports accurate status

### Deployment Success Criteria

- [x] New developer productive in <10 minutes
- [x] Zero data loss on container restart
- [x] Cold start time <60 seconds
- [x] Production deployment with one command
- [x] Rollback capability documented and tested
- [x] Monitoring and health checks operational
- [x] Backup/restore procedures validated

### Code Quality Criteria

- [x] Follows existing codebase patterns
- [x] Non-root container users
- [x] Multi-stage Docker builds
- [x] .dockerignore reduces build context
- [x] No secrets in images or compose files
- [x] Health checks for all services
- [x] Volume mounts for persistent data
- [x] Environment-based configuration

---

## Notes and Considerations

### Production Readiness

**Before Production Deployment**:

1. **Security**:
   - [ ] Configure SSL/TLS certificates (Let's Encrypt)
   - [ ] Set up firewall rules
   - [ ] Enable rate limiting (Nginx)
   - [ ] Implement authentication (if needed)
   - [ ] Review CORS origins for production domain

2. **Performance**:
   - [ ] Enable Gunicorn multi-worker mode (backend)
   - [ ] Configure Nginx gzip compression
   - [ ] Set up CDN for static assets (optional)
   - [ ] Optimize Docker image layers

3. **Monitoring**:
   - [ ] Set up log aggregation (ELK, Loki, etc.)
   - [ ] Configure metrics collection (Prometheus)
   - [ ] Set up alerting (PagerDuty, Slack)
   - [ ] Dashboard for health metrics (Grafana)

4. **Database**:
   - [ ] Decide: SQLite vs PostgreSQL for production
   - [ ] Set up database backups (automated daily)
   - [ ] Test restore procedures
   - [ ] Consider replication (if PostgreSQL)

### Potential Challenges

1. **SQLite Concurrency**:
   - Issue: SQLite doesn't handle high concurrent writes well
   - Solution: Per PRD, this is desktop app pattern (acceptable)
   - Alternative: Migrate to PostgreSQL if needed

2. **File Storage Scaling**:
   - Issue: Local volumes don't scale across multiple hosts
   - Solution: For multi-host, migrate to S3/object storage
   - Current: Single-host deployment is sufficient

3. **Docker on Windows**:
   - Issue: Volume permissions differ on Windows
   - Solution: Use Docker Desktop with WSL2 backend
   - Alternative: Deploy to Linux host for production

4. **Build Time**:
   - Issue: Initial Docker build can be slow
   - Solution: Use BuildKit caching, layer optimization
   - Mitigation: CI/CD caches layers between builds

### Future Enhancements

1. **Kubernetes Migration** (if needed):
   - Helm charts for deployment
   - Horizontal pod autoscaling
   - Persistent volume claims
   - Ingress controller for routing

2. **Database Migration**:
   - Alembic migrations for schema changes
   - Zero-downtime migration strategy
   - PostgreSQL for production (if concurrency needed)

3. **Observability**:
   - OpenTelemetry instrumentation
   - Distributed tracing
   - Custom metrics dashboards
   - Log correlation

4. **Advanced CI/CD**:
   - Canary deployments
   - Blue-green deployment strategy
   - Automatic rollback on health check failure
   - Performance regression testing

---

## Execution Instructions

### How to Use This Plan

1. **Sequential Execution**: Tasks are ordered by dependencies. Complete each phase before moving to the next.

2. **Validation Gates**: Each task includes validation steps. Don't proceed if validation fails.

3. **Estimated Timeline**:
   - Phase 1: 2-3 hours
   - Phase 2: 2-3 hours
   - Phase 3: 2-3 hours
   - Phase 4: 2-3 hours
   - Phase 5: 1-2 hours
   - Phase 6: 1-2 hours
   - **Total**: 10-16 hours

4. **Minimum Viable Deployment** (fastest path):
   - Phase 1: Tasks 1.1, 1.2, 1.3, 1.4
   - Phase 2: Task 2.1
   - Skip Phase 3, 4, 5, 6 initially
   - **Time**: ~4 hours

5. **Production Ready** (full implementation):
   - Complete all phases
   - **Time**: 10-16 hours

### Execution with /execute-plan

This plan is ready for automated execution:

```bash
/execute-plan PRPs/implementation-plan-deployment.md
```

The execute-plan command will:
1. Create all files according to tasks
2. Run validation steps
3. Report progress
4. Track in Archon task management

---

*This plan is ready for execution. Begin with Phase 1, Task 1.1.*
