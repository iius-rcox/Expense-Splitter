# Deployment Quick Start Guide

This guide will help you deploy the PDF Transaction Matcher application quickly.

## Prerequisites

- Docker Engine 20.10+ installed
- Docker Compose 2.0+ installed
- 2GB free disk space (more if processing large PDFs)
- Ports 8000 and 5173 available

## Quick Start (Development)

### 1. Clone and Configure

```bash
# Clone repository (if not already done)
git clone <your-repo-url>
cd Expense-Splitter

# Copy environment template
cp .env.example .env.development

# Edit .env.development if needed (defaults should work for local dev)
```

### 2. Deploy with Docker Compose

```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Access Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 4. Test the Application

```bash
# Check health
curl http://localhost:8000/health

# Upload a test PDF (replace with your test file)
curl -X POST http://localhost:8000/api/upload/car \
  -F "file=@path/to/test-car.pdf"
```

## Common Commands

### Start Services

```bash
docker-compose up -d
```

### Stop Services

```bash
docker-compose down
```

### Restart Services

```bash
docker-compose restart
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Rebuild After Code Changes

```bash
# Rebuild and restart
docker-compose up -d --build

# Force recreation
docker-compose up -d --force-recreate
```

### Access Container Shell

```bash
# Backend
docker-compose exec backend /bin/bash

# Frontend
docker-compose exec frontend /bin/sh
```

### Clean Everything (Fresh Start)

```bash
# Stop and remove containers, networks
docker-compose down

# Remove volumes (WARNING: deletes data!)
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Full cleanup
docker-compose down -v --rmi all --remove-orphans
```

## Troubleshooting

### Port Already in Use

```bash
# Find what's using the port
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000

# Change port in docker-compose.yml or stop conflicting service
```

### Permission Denied (uploads/exports)

```bash
# Fix directory permissions
chmod -R 777 uploads exports data

# Or use specific user
chown -R 1000:1000 uploads exports data
```

### Database Not Initialized

```bash
# Recreate database
docker-compose down
rm -rf data/*.db
docker-compose up -d
```

### Container Won't Start

```bash
# Check logs
docker-compose logs backend

# Check container status
docker ps -a

# Remove and recreate
docker-compose rm backend
docker-compose up -d backend
```

### Build Fails

```bash
# Clear build cache
docker builder prune

# Build with no cache
docker-compose build --no-cache

# Check Dockerfile syntax
docker build -f Dockerfile.backend .
```

## Production Deployment

For production deployment, see the full [DEPLOYMENT.md](./DEPLOYMENT.md) guide which covers:
- PostgreSQL setup
- Nginx reverse proxy
- SSL certificates
- Environment-specific configuration
- Database migrations
- Backup and restore procedures
- Monitoring setup

## Quick Production Deploy

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d

# Run backup
./scripts/backup.sh

# Check health
./scripts/health-check.sh
```

## Environment Variables

Key variables to configure in `.env.development` or `.env.production`:

```bash
# Backend
BACKEND_PORT=8000
DATABASE_URL=sqlite:///./data/expense_matcher.db
CORS_ORIGINS=["http://localhost:5173"]

# Frontend
VITE_API_BASE_URL=http://localhost:8000
FRONTEND_PORT=5173

# File Storage
UPLOAD_DIR=./uploads
EXPORT_DIR=./exports
```

## Next Steps

1. **Configure Environment**: Customize `.env.development` for your setup
2. **Test Upload**: Try uploading CAR and receipt PDFs
3. **Run Extraction**: Test transaction extraction
4. **Test Matching**: Verify matching algorithm works
5. **Export PDFs**: Generate split PDFs

For detailed implementation steps, see [PRP-deployment-methodology.md](../PRPs/PRP-deployment-methodology.md).

## Support

- Check logs: `docker-compose logs -f`
- Health check: `curl http://localhost:8000/health`
- API documentation: http://localhost:8000/docs
- See troubleshooting section above
- Review full deployment guide in docs/DEPLOYMENT.md
