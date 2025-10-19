from fastapi import APIRouter, status
from sqlalchemy import text
from models.base import SessionLocal
from pathlib import Path
from datetime import datetime
import os

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """
    Health check endpoint for container orchestration and monitoring.

    Verifies:
    - API is running
    - Database connection works
    - Required directories exist and are writable

    Returns:
        Status message with component health checks
    """
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # Test database connection
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["checks"]["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"error: {str(e)}"

    # Check required directories exist and are writable
    required_dirs = {
        "dir_data": Path(os.getenv("DATA_DIR", "data")),
        "dir_uploads": Path(os.getenv("UPLOAD_DIR", "uploads")),
        "dir_exports": Path(os.getenv("EXPORT_DIR", "exports"))
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

    return health_status
