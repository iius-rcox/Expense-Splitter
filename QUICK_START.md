# Quick Start - Docker Deployment

## ✅ Deployment Successful!

Your Expense Splitter application is now running in Docker Desktop.

### Access URLs

- **Frontend UI**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

### Container Status

Check container health:
```bash
docker-compose ps
```

View logs:
```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend
```

### Quick Commands

**Stop containers:**
```bash
docker-compose down
```

**Restart containers:**
```bash
docker-compose restart
```

**View real-time logs:**
```bash
docker-compose logs -f
```

**Rebuild and restart:**
```bash
docker-compose up --build -d
```

### Current Configuration

- **Backend**: FastAPI running on port 8000 with hot-reload enabled
- **Frontend**: React app served by Nginx on port 5173
- **Database**: SQLite at `./data/expense_matcher.db`
- **Uploads**: Stored in `./uploads/`
- **Exports**: Stored in `./exports/`

### Next Steps

1. Open http://localhost:5173 in your browser
2. Upload CAR and receipt PDFs
3. Extract transactions
4. Review matches
5. Generate split PDFs

### Troubleshooting

**If containers won't start:**
```bash
# Check Docker Desktop is running
docker-compose down
docker-compose up --build -d
docker-compose logs
```

**If ports are in use:**
Edit `.env.development` and change:
- `BACKEND_PORT=8001`
- `FRONTEND_PORT=5174`
- `VITE_API_BASE_URL=http://localhost:8001`

Then rebuild:
```bash
docker-compose up --build -d
```

### Full Documentation

See `DOCKER_DEPLOYMENT.md` for comprehensive deployment guide and advanced configuration options.

---

**Status**: ✅ All systems operational
- Backend: Healthy
- Frontend: Running
- Database: Connected
- Volumes: Configured
