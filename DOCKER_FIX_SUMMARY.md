# Docker Path Configuration Fix

## Issue

After adding `backend/uploads/` to `.dockerignore` (to exclude 3.1GB of PDFs from build context), PDF uploads failed with 500 Internal Server Error.

## Root Cause

The backend code had **hardcoded relative paths** that didn't respect Docker environment variables:

**Before (hardcoded):**
```python
# pdf_service.py
UPLOAD_DIR = Path("uploads")  # Creates /app/uploads

# splitting_service.py  
EXPORT_DIR = Path("exports")  # Creates /app/exports

# health.py
required_dirs = {
    "data": Path("data"),
    "uploads": Path("uploads"),
    "exports": Path("exports")
}
```

**Problem:**
- Docker volumes were mounted at root level: `/uploads`, `/exports`, `/data`
- Code tried to use `/app/uploads`, `/app/exports`, `/app/data`
- Environment variables in docker-compose.yml (`UPLOAD_DIR=/uploads`) were **ignored**

## Solution

Updated all services to read from environment variables with fallback defaults:

**After (environment-aware):**
```python
import os

# pdf_service.py
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))

# splitting_service.py
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "exports"))

# health.py
required_dirs = {
    "dir_data": Path(os.getenv("DATA_DIR", "data")),
    "dir_uploads": Path(os.getenv("UPLOAD_DIR", "uploads")),
    "dir_exports": Path(os.getenv("EXPORT_DIR", "exports"))
}
```

## Files Modified

1. `backend/services/pdf_service.py` - Line 23
2. `backend/services/splitting_service.py` - Line 17
3. `backend/api/routes/health.py` - Lines 43-45

## Verification

```bash
# Check paths are correct
docker-compose exec backend python -c "from services.pdf_service import PDFService; ps = PDFService(); print(ps.UPLOAD_DIR.absolute())"
# Output: /uploads ✅

# Health check
curl http://localhost:8000/api/health
# All directories: "ok" ✅
```

## Benefits

1. **Container portability** - Works with any volume mount configuration
2. **Development flexibility** - Can use relative paths locally, absolute in containers
3. **Best practice** - Configuration via environment variables (12-factor app)
4. **Backward compatible** - Fallback to relative paths if env vars not set

## Deployment Status

✅ Fixed and deployed
✅ Backend restarted
✅ All health checks passing
✅ Ready for PDF uploads

---

**Date:** 2025-10-18  
**Impact:** Critical fix for Docker deployment
