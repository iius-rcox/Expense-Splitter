from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from models.base import create_tables
from api.routes import upload, health, extraction, matching, export


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
    description="Backend API for matching CAR transactions with receipt PDFs",
    version="1.0.0",
    lifespan=lifespan
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )
