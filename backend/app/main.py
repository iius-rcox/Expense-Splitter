from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import traceback
import logging

import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from models.base import create_tables
from api.routes import upload, health, extraction, matching, export, deduplication

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Changed from DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reduce verbosity of third-party libraries
logging.getLogger('pdfminer').setLevel(logging.WARNING)
logging.getLogger('PIL').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events.

    Startup:
    - Create database tables if they don't exist
    - Initialize services

    Shutdown:
    - Clean up resources
    """
    # Startup
    print("Starting PDF Transaction Matcher API...")
    create_tables()
    print("Database tables created/verified")

    yield

    # Shutdown
    print("Shutting down PDF Transaction Matcher API...")


# Create FastAPI application
app = FastAPI(
    title="PDF Transaction Matcher API",
    description="""
    Extract, match, and split PDF transactions.

    **New in v1.1: Deduplication**
    - Automatic detection of duplicate PDFs
    - Transaction-level deduplication
    - Force re-extraction capability
    """,
    version="1.1.0",
    lifespan=lifespan
)

# Add exception handler middleware for debugging
@app.middleware("http")
async def log_exceptions(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Unhandled exception: {type(e).__name__}: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "server_error",
                "message": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        )

# Configure CORS (allow frontend to make requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(extraction.router)
app.include_router(matching.router)
app.include_router(export.router)
app.include_router(deduplication.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )
