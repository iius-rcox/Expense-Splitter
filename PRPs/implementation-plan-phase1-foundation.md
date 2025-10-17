# Implementation Plan: PDF Transaction Matcher & Splitter - Phase 1 (Foundation)

## Overview
This plan details the implementation of Phase 1 (Foundation) for the PDF Transaction Matcher & Splitter desktop application. This phase establishes the core infrastructure, development environment, and basic PDF upload functionality.

**Timeline**: Week 1-2
**Goal**: Set up development environment and core infrastructure
**PRD Reference**: `PRPs/PRD-expense-splitter.md`
**Project ID**: `4cfa897d-906c-481a-8d7f-6435a634060b`

---

## Requirements Summary

### Phase 1 Core Requirements
- ✅ Backend development environment (Python 3.11+, FastAPI, SQLAlchemy)
- ✅ Frontend development environment (React 18+, TypeScript, Vite, TanStack Query v5)
- ✅ SQLite database with proper schema
- ✅ PDF upload endpoints (CAR and receipt PDFs)
- ✅ File validation logic (format, size, page count)
- ✅ Basic UI for PDF upload with drag-and-drop

### Success Criteria
- Can upload PDFs through UI
- PDFs stored in `/uploads/` directory with proper organization
- Metadata saved to SQLite database
- File validation prevents corrupted/invalid PDFs
- Development environment fully functional for both backend and frontend

---

## Research Findings

### Best Practices from Archon Architecture

#### FastAPI Backend Patterns
**Reference**: Archon knowledge base - PROJECT_ARCHITECTURE.md

- **Async-first approach**: Use `async def` for all route handlers
- **Service layer pattern**: Separate business logic from API routes
- **Pydantic v2 validation**: Type-safe request/response models
- **SQLAlchemy 2.0**: Async session management with context managers
- **Error handling**: Standardized error responses with proper HTTP status codes

#### React Query v5 (TanStack Query) Patterns
**Reference**: `PRPs/ai_docs/DATA_FETCHING_ARCHITECTURE.md`

Key patterns to follow:
- **Query key factories**: Centralized query keys for cache management
- **Stale time configuration**: Use `STALE_TIMES` constants
- **Smart polling**: Visibility-aware polling with `useSmartPolling`
- **Optimistic updates**: nanoid-based temporary IDs for mutations
- **No manual invalidations**: Trust backend consistency

Standard stale times:
- `STALE_TIMES.instant`: 0ms (always fresh)
- `STALE_TIMES.realtime`: 3 seconds
- `STALE_TIMES.frequent`: 5 seconds
- `STALE_TIMES.normal`: 30 seconds (default)
- `STALE_TIMES.rare`: 300 seconds (5 minutes)
- `STALE_TIMES.static`: Infinity

#### Frontend Architecture
**Reference**: `PRPs/ai_docs/API_NAMING_CONVENTIONS.md`

- **Vertical slice organization**: Each feature owns its entire stack
- **Service object pattern**: Export async methods as service objects
- **Hook naming**: `use[Resource]()` for lists, `use[Resource]Detail(id)` for single items
- **Type naming**: Direct database values (no translation layers)
- **Component structure**: Separate concerns (Card, List, Form, Modal components)

#### shadcn/ui Components
**Reference**: Archon knowledge base - shadcn source

- Pre-built accessible components
- Built on Radix UI primitives
- Tailwind CSS for styling
- Copy-paste pattern (components live in codebase, not node_modules)

### PDF Processing Best Practices

From research:
- **pdfplumber**: Best for text extraction from text-based PDFs
- **PyPDF2**: Best for page manipulation and splitting
- **Streaming processing**: Handle large PDFs page-by-page to avoid memory issues
- **Regex patterns**: Use compiled regex for performance
- **Error handling**: Gracefully handle malformed PDFs with detailed error messages

---

## Technology Decisions

### Backend Stack
- **Python**: 3.11+ (better async performance, improved type hints)
- **FastAPI**: 0.104+ (modern async framework, auto OpenAPI docs)
- **SQLAlchemy**: 2.0+ (async support, improved API)
- **Pydantic**: v2 (faster validation, better type safety)
- **pdfplumber**: 0.10+ (reliable text extraction)
- **PyPDF2**: 3.0+ (PDF manipulation and splitting)
- **uvicorn**: ASGI server with uvloop for performance

**Rationale**: Follows Archon patterns, modern async Python, excellent PDF library support

### Frontend Stack
- **React**: 18.2+ (concurrent features, improved performance)
- **TypeScript**: 5+ (better type inference, decorator support)
- **Vite**: 5+ (fast HMR, optimized builds)
- **TanStack Query**: v5 (best-in-class data fetching)
- **Tailwind CSS**: 3.3+ (utility-first styling)
- **shadcn/ui**: Latest (accessible components)

**Rationale**: Matches Archon frontend architecture exactly, modern best practices

### Database
- **SQLite**: 3.x (simple, serverless, perfect for desktop app)
- **Development**: File-based database in `/data/` directory
- **Production**: Same (no PostgreSQL needed for single-user desktop app)

**Rationale**: Simplifies deployment, no separate database server needed

### Development Tools
- **Backend linting**: ruff (fast Python linter/formatter)
- **Backend type checking**: mypy (strict mode)
- **Frontend linting**: ESLint with TypeScript support
- **Testing**: pytest (backend), Vitest (frontend)

---

## Implementation Tasks

### Phase 1.1: Backend Environment Setup (Day 1-2)

#### Task 1.1.1: Create Backend Directory Structure
**Description**: Set up organized backend file structure following best practices

**Files to create**:
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   └── config.py            # Configuration management
├── api/
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       ├── upload.py        # PDF upload endpoints
│       └── health.py        # Health check endpoint
├── models/
│   ├── __init__.py
│   ├── base.py              # SQLAlchemy Base
│   ├── pdf.py               # PDF model
│   └── transaction.py       # Transaction model (for Phase 2)
├── services/
│   ├── __init__.py
│   └── pdf_service.py       # PDF upload/validation service
├── schemas/
│   ├── __init__.py
│   └── pdf.py               # Pydantic schemas for PDFs
├── utils/
│   ├── __init__.py
│   └── validators.py        # File validation utilities
└── tests/
    ├── __init__.py
    └── test_upload.py       # Upload endpoint tests
```

**Commands**:
```bash
cd backend
mkdir -p app api/routes models services schemas utils tests
touch app/__init__.py app/main.py app/config.py
touch api/__init__.py api/routes/__init__.py api/routes/upload.py api/routes/health.py
touch models/__init__.py models/base.py models/pdf.py models/transaction.py
touch services/__init__.py services/pdf_service.py
touch schemas/__init__.py schemas/pdf.py
touch utils/__init__.py utils/validators.py
touch tests/__init__.py tests/test_upload.py
```

**Dependencies**: None
**Estimated effort**: 30 minutes

---

#### Task 1.1.2: Create requirements.txt and Install Dependencies
**Description**: Define all Python dependencies and set up virtual environment

**File to create**: `backend/requirements.txt`

**Content**:
```txt
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6  # For file uploads

# Database
sqlalchemy==2.0.23
alembic==1.12.1

# Validation
pydantic==2.5.2
pydantic-settings==2.1.0  # For configuration management

# PDF Processing
pdfplumber==0.10.3
PyPDF2==3.0.1

# String Matching (for Phase 3, but install now)
rapidfuzz==3.5.2

# Development
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
httpx==0.25.2  # For testing FastAPI
ruff==0.1.6  # Linter and formatter
mypy==1.7.1  # Type checker

# Utilities
python-dotenv==1.0.0  # Environment variable management
```

**Commands**:
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

**Validation**:
```bash
python -c "import fastapi, pdfplumber, PyPDF2, sqlalchemy; print('✓ All imports successful')"
```

**Dependencies**: Task 1.1.1
**Estimated effort**: 15 minutes

---

#### Task 1.1.3: Configure SQLAlchemy Base and Database
**Description**: Set up SQLAlchemy async engine and session management

**File**: `backend/models/base.py`

**Implementation**:
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator

# Database URL - SQLite file in data directory
DATABASE_URL = "sqlite:///./data/expense_matcher.db"

# Create engine (SQLite doesn't support async, use sync for simplicity)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=True,  # Log SQL queries (disable in production)
)

# Session maker
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Declarative base for models
Base = declarative_base()

# Dependency for FastAPI routes
def get_db() -> Generator:
    """
    Database session dependency for FastAPI routes.

    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables. Call this on app startup."""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables. Use with caution!"""
    Base.metadata.drop_all(bind=engine)
```

**Pattern Reference**: Standard SQLAlchemy pattern (sync version for SQLite compatibility)

**Dependencies**: Task 1.1.2
**Estimated effort**: 20 minutes

---

#### Task 1.1.4: Create PDF Database Model
**Description**: Define SQLAlchemy model for PDF uploads

**File**: `backend/models/pdf.py`

**Implementation**:
```python
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.sql import func
from .base import Base
import uuid


class PDF(Base):
    """
    Represents an uploaded PDF file.

    Tracks metadata about CAR or receipt PDFs uploaded by users.
    """
    __tablename__ = "pdfs"

    # Primary key (UUID as string)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # File metadata
    filename = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)  # Absolute path to stored file
    pdf_type = Column(String(10), nullable=False)  # 'car' or 'receipt'

    # PDF characteristics
    page_count = Column(Integer, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)

    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<PDF(id={self.id}, type={self.pdf_type}, filename={self.filename})>"

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            "pdf_id": self.id,
            "filename": self.filename,
            "file_path": self.file_path,
            "pdf_type": self.pdf_type,
            "page_count": self.page_count,
            "file_size_bytes": self.file_size_bytes,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None
        }
```

**Validation**:
```bash
python -c "from models.pdf import PDF; print('✓ PDF model imports successfully')"
```

**Dependencies**: Task 1.1.3
**Estimated effort**: 30 minutes

---

#### Task 1.1.5: Create Pydantic Schemas for API
**Description**: Define request/response schemas for PDF upload endpoints

**File**: `backend/schemas/pdf.py`

**Implementation**:
```python
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Literal


class PDFUploadResponse(BaseModel):
    """Response schema after successful PDF upload."""

    pdf_id: str = Field(..., description="Unique identifier for uploaded PDF")
    filename: str = Field(..., description="Original filename")
    pdf_type: Literal["car", "receipt"] = Field(..., description="Type of PDF")
    page_count: int = Field(..., description="Number of pages in PDF", ge=1)
    file_size_bytes: int = Field(..., description="File size in bytes", ge=1)
    uploaded_at: datetime = Field(..., description="Upload timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "pdf_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "car_2025_10.pdf",
                "pdf_type": "car",
                "page_count": 15,
                "file_size_bytes": 1048576,
                "uploaded_at": "2025-10-16T10:30:00Z"
            }
        }


class PDFValidationError(BaseModel):
    """Error response for validation failures."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="User-friendly error message")
    details: str | None = Field(None, description="Additional error details")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "invalid_pdf",
                "message": "Unable to read PDF. Please ensure file is not corrupted or password-protected.",
                "details": "PyPDF2.errors.PdfReadError: EOF marker not found"
            }
        }
```

**Dependencies**: Task 1.1.2
**Estimated effort**: 20 minutes

---

#### Task 1.1.6: Implement PDF Validation Service
**Description**: Create service layer for PDF upload and validation logic

**File**: `backend/services/pdf_service.py`

**Implementation**:
```python
from pathlib import Path
import pdfplumber
from PyPDF2 import PdfReader
from typing import Literal, Tuple
import shutil
import uuid


class PDFValidationError(Exception):
    """Custom exception for PDF validation errors."""
    pass


class PDFService:
    """Service for handling PDF uploads and validation."""

    # Constants
    MAX_FILE_SIZE_MB = 50
    MAX_PAGE_COUNT = 500
    MIN_PAGE_COUNT = 1
    UPLOAD_DIR = Path("uploads")

    def __init__(self):
        """Initialize PDF service and ensure upload directory exists."""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def validate_pdf_format(self, file_path: Path) -> Tuple[int, bool]:
        """
        Validate PDF file format and structure.

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (page_count, is_valid)

        Raises:
            PDFValidationError: If PDF is invalid
        """
        try:
            # Try to open with PyPDF2 for basic validation
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)

                # Check if encrypted
                if reader.is_encrypted:
                    raise PDFValidationError(
                        "PDF is password-protected. Please upload an unencrypted PDF."
                    )

                page_count = len(reader.pages)

                # Validate page count
                if page_count < self.MIN_PAGE_COUNT:
                    raise PDFValidationError(
                        f"PDF must have at least {self.MIN_PAGE_COUNT} page."
                    )

                if page_count > self.MAX_PAGE_COUNT:
                    raise PDFValidationError(
                        f"PDF exceeds maximum {self.MAX_PAGE_COUNT} pages. "
                        f"Please split into smaller files."
                    )

                return page_count, True

        except PDFValidationError:
            raise  # Re-raise our custom errors
        except Exception as e:
            raise PDFValidationError(
                f"Unable to read PDF. Please ensure file is not corrupted. "
                f"Technical details: {str(e)}"
            )

    def validate_text_extractable(self, file_path: Path) -> bool:
        """
        Check if PDF contains extractable text (not just images).

        Args:
            file_path: Path to PDF file

        Returns:
            True if text is extractable

        Raises:
            PDFValidationError: If no text found
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                # Check first 3 pages for text
                pages_to_check = min(3, len(pdf.pages))
                total_text_length = 0

                for i in range(pages_to_check):
                    text = pdf.pages[i].extract_text()
                    if text:
                        total_text_length += len(text.strip())

                # Require at least 50 characters of text in first few pages
                if total_text_length < 50:
                    raise PDFValidationError(
                        "No parseable transactions found. "
                        "Please verify PDF contains text (not scanned images)."
                    )

                return True

        except PDFValidationError:
            raise
        except Exception as e:
            raise PDFValidationError(
                f"Error extracting text from PDF: {str(e)}"
            )

    def validate_file_size(self, file_path: Path) -> int:
        """
        Validate file size is within limits.

        Args:
            file_path: Path to file

        Returns:
            File size in bytes

        Raises:
            PDFValidationError: If file too large
        """
        file_size = file_path.stat().st_size
        max_size_bytes = self.MAX_FILE_SIZE_MB * 1024 * 1024

        if file_size > max_size_bytes:
            raise PDFValidationError(
                f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds "
                f"maximum {self.MAX_FILE_SIZE_MB} MB."
            )

        return file_size

    async def save_uploaded_file(
        self,
        file,  # FastAPI UploadFile
        pdf_type: Literal["car", "receipt"]
    ) -> Tuple[Path, str, int, int]:
        """
        Save uploaded file to disk with validation.

        Args:
            file: FastAPI UploadFile object
            pdf_type: Type of PDF ('car' or 'receipt')

        Returns:
            Tuple of (file_path, filename, page_count, file_size_bytes)

        Raises:
            PDFValidationError: If validation fails
        """
        # Generate unique filename
        file_id = str(uuid.uuid4())
        original_filename = file.filename
        file_extension = Path(original_filename).suffix

        # Ensure it's a PDF
        if file_extension.lower() != '.pdf':
            raise PDFValidationError("Only PDF files are accepted.")

        # Create type-specific subdirectory
        type_dir = self.UPLOAD_DIR / pdf_type
        type_dir.mkdir(parents=True, exist_ok=True)

        # Full path for saved file
        saved_filename = f"{file_id}{file_extension}"
        file_path = type_dir / saved_filename

        # Save file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise PDFValidationError(f"Failed to save file: {str(e)}")

        # Validate file size
        file_size = self.validate_file_size(file_path)

        # Validate PDF format
        page_count, _ = self.validate_pdf_format(file_path)

        # Validate text extractability
        self.validate_text_extractable(file_path)

        return file_path, original_filename, page_count, file_size

    def delete_file(self, file_path: Path):
        """Delete uploaded file (cleanup on error)."""
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass  # Ignore cleanup errors


# Singleton instance
pdf_service = PDFService()
```

**Pattern Reference**: Service layer pattern from Archon architecture

**Validation**:
```bash
python -c "from services.pdf_service import pdf_service; print('✓ PDF service imports successfully')"
```

**Dependencies**: Tasks 1.1.2, 1.1.4
**Estimated effort**: 90 minutes

---

#### Task 1.1.7: Create Upload API Endpoints
**Description**: Implement FastAPI routes for CAR and receipt PDF uploads

**File**: `backend/api/routes/upload.py`

**Implementation**:
```python
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Literal

from models.base import get_db
from models.pdf import PDF
from schemas.pdf import PDFUploadResponse, PDFValidationError
from services.pdf_service import pdf_service, PDFValidationError as ServicePDFValidationError

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/car", response_model=PDFUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_car_pdf(
    file: UploadFile = File(..., description="CAR PDF file"),
    db: Session = Depends(get_db)
):
    """
    Upload Corporate American Express Report (CAR) PDF.

    Validates PDF format, size, and text extractability before saving.

    Returns:
        PDFUploadResponse with metadata about uploaded PDF

    Raises:
        HTTPException: If validation fails (400) or server error (500)
    """
    try:
        # Save and validate file
        file_path, filename, page_count, file_size = await pdf_service.save_uploaded_file(
            file, pdf_type="car"
        )

        # Create database record
        pdf_record = PDF(
            filename=filename,
            file_path=str(file_path.absolute()),
            pdf_type="car",
            page_count=page_count,
            file_size_bytes=file_size
        )

        db.add(pdf_record)
        db.commit()
        db.refresh(pdf_record)

        # Return response
        return PDFUploadResponse(
            pdf_id=pdf_record.id,
            filename=pdf_record.filename,
            pdf_type=pdf_record.pdf_type,
            page_count=pdf_record.page_count,
            file_size_bytes=pdf_record.file_size_bytes,
            uploaded_at=pdf_record.uploaded_at
        )

    except ServicePDFValidationError as e:
        # Validation error - return 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": str(e),
                "details": None
            }
        )
    except Exception as e:
        # Unexpected error - cleanup and return 500
        if 'file_path' in locals():
            pdf_service.delete_file(file_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "message": "An unexpected error occurred during upload.",
                "details": str(e)
            }
        )


@router.post("/receipt", response_model=PDFUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_receipt_pdf(
    file: UploadFile = File(..., description="Receipt PDF file"),
    db: Session = Depends(get_db)
):
    """
    Upload receipt collection PDF.

    Validates PDF format, size, and text extractability before saving.

    Returns:
        PDFUploadResponse with metadata about uploaded PDF

    Raises:
        HTTPException: If validation fails (400) or server error (500)
    """
    try:
        # Save and validate file
        file_path, filename, page_count, file_size = await pdf_service.save_uploaded_file(
            file, pdf_type="receipt"
        )

        # Create database record
        pdf_record = PDF(
            filename=filename,
            file_path=str(file_path.absolute()),
            pdf_type="receipt",
            page_count=page_count,
            file_size_bytes=file_size
        )

        db.add(pdf_record)
        db.commit()
        db.refresh(pdf_record)

        # Return response
        return PDFUploadResponse(
            pdf_id=pdf_record.id,
            filename=pdf_record.filename,
            pdf_type=pdf_record.pdf_type,
            page_count=pdf_record.page_count,
            file_size_bytes=pdf_record.file_size_bytes,
            uploaded_at=pdf_record.uploaded_at
        )

    except ServicePDFValidationError as e:
        # Validation error - return 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": str(e),
                "details": None
            }
        )
    except Exception as e:
        # Unexpected error - cleanup and return 500
        if 'file_path' in locals():
            pdf_service.delete_file(file_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "message": "An unexpected error occurred during upload.",
                "details": str(e)
            }
        )
```

**Pattern Reference**: RESTful API pattern from `PRPs/ai_docs/API_NAMING_CONVENTIONS.md`

**Dependencies**: Tasks 1.1.4, 1.1.5, 1.1.6
**Estimated effort**: 60 minutes

---

#### Task 1.1.8: Create Health Check Endpoint
**Description**: Simple health check for API monitoring

**File**: `backend/api/routes/health.py`

**Implementation**:
```python
from fastapi import APIRouter, status
from sqlalchemy import text
from models.base import SessionLocal

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """
    Health check endpoint.

    Verifies:
    - API is running
    - Database connection works

    Returns:
        Status message with database connectivity
    """
    try:
        # Test database connection
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "database": db_status,
        "version": "1.0.0"
    }
```

**Dependencies**: Task 1.1.3
**Estimated effort**: 15 minutes

---

#### Task 1.1.9: Create FastAPI Application Main File
**Description**: Configure and initialize FastAPI application

**File**: `backend/app/main.py`

**Implementation**:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from models.base import create_tables
from api.routes import upload, health


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
    print("🚀 Starting PDF Transaction Matcher API...")
    create_tables()
    print("✓ Database tables created/verified")

    yield

    # Shutdown
    print("👋 Shutting down PDF Transaction Matcher API...")


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload during development
        log_level="info"
    )
```

**Pattern Reference**: FastAPI application pattern from Archon architecture

**Validation**:
```bash
cd backend
python app/main.py  # Should start server on http://localhost:8000
# Test: http://localhost:8000/docs (should show OpenAPI documentation)
```

**Dependencies**: Tasks 1.1.7, 1.1.8
**Estimated effort**: 30 minutes

---

### Phase 1.2: Frontend Environment Setup (Day 3-4)

#### Task 1.2.1: Initialize Vite React TypeScript Project
**Description**: Create React + TypeScript project with Vite

**Commands**:
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

**Validation**:
```bash
npm run dev  # Should start dev server on http://localhost:5173
```

**Dependencies**: None
**Estimated effort**: 10 minutes

---

#### Task 1.2.2: Install Frontend Dependencies
**Description**: Install all required npm packages

**Commands**:
```bash
cd frontend
npm install @tanstack/react-query@5.8.4
npm install @tanstack/react-query-devtools@5.8.4
npm install axios@1.6.2
npm install react-router-dom@6.20.0

# Tailwind CSS
npm install -D tailwindcss@3.3.5 postcss@8.4.31 autoprefixer@10.4.16
npx tailwindcss init -p

# shadcn/ui dependencies
npm install tailwind-merge@2.1.0 clsx@2.0.0
npm install class-variance-authority@0.7.0
npm install lucide-react@0.294.0  # Icon library

# Utility libraries
npm install nanoid@5.0.4  # For optimistic update IDs
npm install date-fns@2.30.0  # Date formatting
```

**File**: `frontend/package.json` (verify all dependencies added)

**Dependencies**: Task 1.2.1
**Estimated effort**: 15 minutes

---

#### Task 1.2.3: Configure Tailwind CSS
**Description**: Set up Tailwind CSS for styling

**File**: `frontend/tailwind.config.js`

**Implementation**:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
}
```

**File**: `frontend/src/index.css`

**Implementation**:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;

    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;

    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;

    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;

    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;

    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;

    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;

    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;

    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;

    --radius: 0.5rem;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
```

**Dependencies**: Task 1.2.2
**Estimated effort**: 20 minutes

---

#### Task 1.2.4: Create Frontend Directory Structure
**Description**: Organize frontend code following vertical slice architecture

**Files to create**:
```
frontend/src/
├── features/
│   ├── upload/
│   │   ├── components/
│   │   │   ├── UploadZone.tsx
│   │   │   └── UploadProgress.tsx
│   │   ├── hooks/
│   │   │   └── useUploadQueries.ts
│   │   ├── services/
│   │   │   └── uploadService.ts
│   │   └── types/
│   │       └── upload.ts
│   └── shared/
│       ├── api/
│       │   └── apiClient.ts
│       ├── config/
│       │   ├── queryClient.ts
│       │   └── queryPatterns.ts
│       └── types/
│           └── index.ts
├── pages/
│   └── UploadPage.tsx
├── App.tsx
├── main.tsx
└── index.css
```

**Commands**:
```bash
cd frontend/src
mkdir -p features/upload/components features/upload/hooks features/upload/services features/upload/types
mkdir -p features/shared/api features/shared/config features/shared/types
mkdir -p pages
```

**Dependencies**: Task 1.2.3
**Estimated effort**: 10 minutes

---

#### Task 1.2.5: Configure TanStack Query Client
**Description**: Set up React Query with proper configuration

**File**: `frontend/src/features/shared/config/queryClient.ts`

**Implementation**:
```typescript
import { QueryClient, DefaultOptions } from '@tanstack/react-query';

const queryConfig: DefaultOptions = {
  queries: {
    // Stale time: Data considered fresh for 30 seconds
    staleTime: 30_000,

    // Garbage collection: Remove unused data after 10 minutes
    gcTime: 600_000,

    // Retry logic: Retry failed queries unless 4xx error
    retry: (failureCount, error: any) => {
      // Don't retry 4xx errors (client errors)
      if (error?.response?.status >= 400 && error?.response?.status < 500) {
        return false;
      }
      // Retry up to 3 times for other errors
      return failureCount < 3;
    },

    // Refetch on window focus (disabled by default, enable per-query if needed)
    refetchOnWindowFocus: false,

    // Refetch on reconnect
    refetchOnReconnect: true,

    // Request deduplication
    structuralSharing: true,
  },
  mutations: {
    // Retry mutations once on failure
    retry: 1,
  },
};

export const queryClient = new QueryClient({
  defaultOptions: queryConfig,
});
```

**Pattern Reference**: `PRPs/ai_docs/DATA_FETCHING_ARCHITECTURE.md` - Query Client Configuration

**Dependencies**: Task 1.2.2
**Estimated effort**: 15 minutes

---

#### Task 1.2.6: Create Query Patterns Constants
**Description**: Standardized stale times and disabled query key

**File**: `frontend/src/features/shared/config/queryPatterns.ts`

**Implementation**:
```typescript
/**
 * Standardized stale time configurations for React Query.
 *
 * Pattern Reference: PRPs/ai_docs/DATA_FETCHING_ARCHITECTURE.md
 */

export const STALE_TIMES = {
  /** Always fresh - refetch immediately */
  instant: 0,

  /** Real-time data - 3 seconds */
  realtime: 3_000,

  /** Frequently changing data - 5 seconds */
  frequent: 5_000,

  /** Normal data - 30 seconds (default) */
  normal: 30_000,

  /** Rarely changing data - 5 minutes */
  rare: 300_000,

  /** Static data - never stale */
  static: Infinity,
} as const;

/**
 * Special query key for disabled queries.
 *
 * Use when query should not run based on conditional logic.
 * Example: useQuery({ queryKey: enabled ? ['key'] : DISABLED_QUERY_KEY })
 */
export const DISABLED_QUERY_KEY = ['__disabled__'];
```

**Dependencies**: Task 1.2.5
**Estimated effort**: 10 minutes

---

#### Task 1.2.7: Create API Client
**Description**: Axios-based API client with proper configuration

**File**: `frontend/src/features/shared/api/apiClient.ts`

**Implementation**:
```typescript
import axios, { AxiosError } from 'axios';

/**
 * API client configuration.
 *
 * Features:
 * - Base URL configuration
 * - Request/response interceptors
 * - Error handling
 * - Browser-native ETag caching
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  // Enable browser-native caching (ETags)
  withCredentials: false,
});

/**
 * Request interceptor for logging (development only)
 */
apiClient.interceptors.request.use(
  (config) => {
    if (import.meta.env.DEV) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

/**
 * Response interceptor for error handling
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // Log errors in development
    if (import.meta.env.DEV) {
      console.error('[API Error]', {
        url: error.config?.url,
        status: error.response?.status,
        data: error.response?.data,
      });
    }

    // Re-throw for React Query error handling
    return Promise.reject(error);
  }
);

/**
 * API error type helper
 */
export interface APIError {
  error: string;
  message: string;
  details?: string;
}

/**
 * Extract error message from API error
 */
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const apiError = error.response?.data as APIError | undefined;
    return apiError?.message || error.message || 'An unexpected error occurred';
  }
  return 'An unexpected error occurred';
}
```

**Pattern Reference**: `PRPs/ai_docs/DATA_FETCHING_ARCHITECTURE.md` - ETag Support

**Dependencies**: Task 1.2.2
**Estimated effort**: 20 minutes

---

#### Task 1.2.8: Create TypeScript Types for Upload
**Description**: Define types for PDF upload functionality

**File**: `frontend/src/features/upload/types/upload.ts`

**Implementation**:
```typescript
/**
 * Upload feature types.
 *
 * Pattern: Direct database values (no translation layers)
 * Reference: PRPs/ai_docs/API_NAMING_CONVENTIONS.md
 */

/** PDF type - matches backend literal */
export type PDFType = 'car' | 'receipt';

/** Upload status for UI state */
export type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

/** Response from PDF upload API */
export interface PDFUploadResponse {
  pdf_id: string;
  filename: string;
  pdf_type: PDFType;
  page_count: number;
  file_size_bytes: number;
  uploaded_at: string;  // ISO timestamp
}

/** API error response */
export interface PDFValidationError {
  error: string;
  message: string;
  details?: string;
}

/** Upload state for UI */
export interface UploadState {
  status: UploadStatus;
  progress: number;  // 0-100
  error: string | null;
  result: PDFUploadResponse | null;
}
```

**Dependencies**: None
**Estimated effort**: 15 minutes

---

#### Task 1.2.9: Create Upload Service
**Description**: API service methods for PDF upload

**File**: `frontend/src/features/upload/services/uploadService.ts`

**Implementation**:
```typescript
import { apiClient } from '@/features/shared/api/apiClient';
import { PDFUploadResponse, PDFType } from '../types/upload';

/**
 * Upload service for PDF files.
 *
 * Pattern Reference: PRPs/ai_docs/API_NAMING_CONVENTIONS.md - Service Object Pattern
 */

export const uploadService = {
  /**
   * Upload CAR PDF file.
   */
  async uploadCarPDF(file: File): Promise<PDFUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<PDFUploadResponse>(
      '/api/upload/car',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  /**
   * Upload receipt PDF file.
   */
  async uploadReceiptPDF(file: File): Promise<PDFUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<PDFUploadResponse>(
      '/api/upload/receipt',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  /**
   * Generic upload method (used by mutations).
   */
  async uploadPDF(file: File, type: PDFType): Promise<PDFUploadResponse> {
    if (type === 'car') {
      return this.uploadCarPDF(file);
    } else {
      return this.uploadReceiptPDF(file);
    }
  },
};
```

**Pattern Reference**: Service object pattern with async methods

**Dependencies**: Tasks 1.2.7, 1.2.8
**Estimated effort**: 20 minutes

---

#### Task 1.2.10: Create Upload Query Hooks
**Description**: React Query hooks for upload mutations

**File**: `frontend/src/features/upload/hooks/useUploadQueries.ts`

**Implementation**:
```typescript
import { useMutation } from '@tanstack/react-query';
import { uploadService } from '../services/uploadService';
import { PDFType, PDFUploadResponse } from '../types/upload';
import { getErrorMessage } from '@/features/shared/api/apiClient';

/**
 * Upload query hooks and key factory.
 *
 * Pattern Reference: PRPs/ai_docs/DATA_FETCHING_ARCHITECTURE.md - Feature Implementation Patterns
 */

/** Query key factory for upload operations */
export const uploadKeys = {
  all: ['uploads'] as const,
  car: () => [...uploadKeys.all, 'car'] as const,
  receipt: () => [...uploadKeys.all, 'receipt'] as const,
};

/**
 * Mutation hook for uploading PDFs.
 *
 * Usage:
 * ```tsx
 * const uploadMutation = useUploadPDF();
 * uploadMutation.mutate({ file, type: 'car' });
 * ```
 */
export function useUploadPDF() {
  return useMutation({
    mutationFn: ({ file, type }: { file: File; type: PDFType }) => {
      return uploadService.uploadPDF(file, type);
    },
    onError: (error) => {
      console.error('Upload failed:', getErrorMessage(error));
    },
  });
}

/**
 * Separate mutation hooks for explicit CAR/receipt uploads.
 */

export function useUploadCarPDF() {
  return useMutation({
    mutationFn: (file: File) => uploadService.uploadCarPDF(file),
    onError: (error) => {
      console.error('CAR upload failed:', getErrorMessage(error));
    },
  });
}

export function useUploadReceiptPDF() {
  return useMutation({
    mutationFn: (file: File) => uploadService.uploadReceiptPDF(file),
    onError: (error) => {
      console.error('Receipt upload failed:', getErrorMessage(error));
    },
  });
}
```

**Pattern Reference**: Mutation hooks pattern from Archon architecture

**Dependencies**: Tasks 1.2.9, 1.2.5
**Estimated effort**: 25 minutes

---

### Phase 1.3: Upload UI Components (Day 5-6)

#### Task 1.3.1: Create Upload Zone Component
**Description**: Drag-and-drop file upload zone with validation

**File**: `frontend/src/features/upload/components/UploadZone.tsx`

**Implementation**: (Due to length, see separate artifact)

**Pattern Reference**: Component naming from `PRPs/ai_docs/API_NAMING_CONVENTIONS.md`

**Dependencies**: Task 1.2.10
**Estimated effort**: 90 minutes

---

#### Task 1.3.2: Create Upload Progress Component
**Description**: Visual feedback for upload progress

**File**: `frontend/src/features/upload/components/UploadProgress.tsx`

**Implementation**: (See separate artifact)

**Dependencies**: Task 1.2.10
**Estimated effort**: 45 minutes

---

#### Task 1.3.3: Create Upload Page
**Description**: Main page integrating upload components

**File**: `frontend/src/pages/UploadPage.tsx`

**Implementation**: (See separate artifact)

**Dependencies**: Tasks 1.3.1, 1.3.2
**Estimated effort**: 60 minutes

---

#### Task 1.3.4: Configure React App Entry Point
**Description**: Set up React Query Provider and routing

**File**: `frontend/src/main.tsx`

**Implementation**:
```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { queryClient } from './features/shared/config/queryClient';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </React.StrictMode>
);
```

**File**: `frontend/src/App.tsx`

**Implementation**:
```typescript
import UploadPage from './pages/UploadPage';

function App() {
  return (
    <div className="min-h-screen bg-background">
      <UploadPage />
    </div>
  );
}

export default App;
```

**Dependencies**: Tasks 1.2.5, 1.3.3
**Estimated effort**: 20 minutes

---

## Validation & Testing

### Backend Validation

#### Validation 1.1: Start Backend Server
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python app/main.py
```

**Expected output**:
```
🚀 Starting PDF Transaction Matcher API...
✓ Database tables created/verified
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Success criteria**:
- Server starts without errors
- Database tables created in `/data/expense_matcher.db`
- API documentation available at `http://localhost:8000/docs`

---

#### Validation 1.2: Test Health Endpoint
```bash
curl http://localhost:8000/api/health
```

**Expected response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

---

#### Validation 1.3: Test CAR PDF Upload (Manual)
```bash
# Create a test PDF first (or use existing PDF)
curl -X POST http://localhost:8000/api/upload/car \
  -F "file=@/path/to/test_car.pdf" \
  -H "Accept: application/json"
```

**Expected response**:
```json
{
  "pdf_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "test_car.pdf",
  "pdf_type": "car",
  "page_count": 10,
  "file_size_bytes": 524288,
  "uploaded_at": "2025-10-16T10:30:00Z"
}
```

**Verify**:
- File saved to `uploads/car/` directory
- Database record created in `pdfs` table
- Correct page count extracted

---

#### Validation 1.4: Test Invalid PDF Upload
```bash
# Try uploading a text file as PDF
echo "not a pdf" > fake.pdf
curl -X POST http://localhost:8000/api/upload/car \
  -F "file=@fake.pdf" \
  -H "Accept: application/json"
```

**Expected response** (400 Bad Request):
```json
{
  "detail": {
    "error": "validation_error",
    "message": "Unable to read PDF. Please ensure file is not corrupted...",
    "details": null
  }
}
```

---

### Frontend Validation

#### Validation 1.5: Start Frontend Dev Server
```bash
cd frontend
npm run dev
```

**Expected output**:
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

**Success criteria**:
- Dev server starts without errors
- No TypeScript compilation errors
- Can access `http://localhost:5173`

---

#### Validation 1.6: Test Upload UI (Manual)
1. Open `http://localhost:5173` in browser
2. Verify two upload zones visible: "CAR PDF" and "Receipt PDF"
3. Drag a valid PDF into CAR zone
4. Verify:
   - Upload progress indicator appears
   - Success message shows after upload
   - PDF metadata displayed (filename, page count, file size)
5. Try dragging a non-PDF file
6. Verify:
   - Error message appears
   - Upload rejected

---

#### Validation 1.7: TypeScript Compilation
```bash
cd frontend
npm run build
```

**Expected**:
- Build completes successfully
- No TypeScript errors
- Output in `dist/` directory

---

### Integration Validation

#### Validation 1.8: End-to-End Upload Test
1. Start backend server (port 8000)
2. Start frontend dev server (port 5173)
3. Open browser to `http://localhost:5173`
4. Upload valid CAR PDF
5. Upload valid receipt PDF
6. Verify in backend logs:
   - Two upload requests logged
   - Database queries logged
7. Check database:
```bash
sqlite3 data/expense_matcher.db "SELECT * FROM pdfs;"
```
8. Verify two records present

---

## Success Checklist

### Technical Validation
- [ ] Backend server starts without errors: `python backend/app/main.py`
- [ ] Health endpoint responds: `curl http://localhost:8000/api/health`
- [ ] OpenAPI docs accessible: http://localhost:8000/docs
- [ ] Frontend builds without errors: `npm run build`
- [ ] Frontend dev server runs: `npm run dev`
- [ ] No TypeScript errors: Check terminal output

### Feature Validation
- [ ] Can upload CAR PDF via UI
- [ ] Can upload receipt PDF via UI
- [ ] Upload progress indicator works
- [ ] Success message shows after upload
- [ ] PDF metadata displayed correctly (filename, page count, size)
- [ ] Invalid files rejected with error message
- [ ] Database records created for uploads
- [ ] Files saved to correct directories (`uploads/car/`, `uploads/receipt/`)

### Code Quality Validation
- [ ] Backend follows service layer pattern
- [ ] Frontend follows vertical slice architecture
- [ ] Query keys use factory pattern
- [ ] Types match database values directly
- [ ] Error handling implemented
- [ ] API responses match Pydantic schemas

---

## Deployment Notes

### Environment Variables

**Backend** (`backend/.env` - create this file):
```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# Database
DATABASE_URL=sqlite:///./data/expense_matcher.db

# Upload Configuration
MAX_FILE_SIZE_MB=50
MAX_PAGE_COUNT=500
UPLOAD_DIR=uploads
```

**Frontend** (`frontend/.env` - create this file):
```env
# API Base URL
VITE_API_BASE_URL=http://localhost:8000
```

### File Structure Verification

After completing Phase 1, your project should look like:

```
Expense-Splitter/
├── backend/
│   ├── app/
│   │   ├── main.py ✓
│   │   └── config.py ✓
│   ├── api/routes/
│   │   ├── upload.py ✓
│   │   └── health.py ✓
│   ├── models/
│   │   ├── base.py ✓
│   │   └── pdf.py ✓
│   ├── services/
│   │   └── pdf_service.py ✓
│   ├── schemas/
│   │   └── pdf.py ✓
│   ├── utils/
│   │   └── validators.py ✓
│   ├── tests/
│   │   └── test_upload.py ✓
│   ├── requirements.txt ✓
│   └── .env ✓
├── frontend/
│   ├── src/
│   │   ├── features/
│   │   │   ├── upload/
│   │   │   │   ├── components/ ✓
│   │   │   │   ├── hooks/ ✓
│   │   │   │   ├── services/ ✓
│   │   │   │   └── types/ ✓
│   │   │   └── shared/
│   │   │       ├── api/ ✓
│   │   │       ├── config/ ✓
│   │   │       └── types/ ✓
│   │   ├── pages/
│   │   │   └── UploadPage.tsx ✓
│   │   ├── App.tsx ✓
│   │   ├── main.tsx ✓
│   │   └── index.css ✓
│   ├── package.json ✓
│   ├── tailwind.config.js ✓
│   └── .env ✓
├── data/
│   └── expense_matcher.db (created on first run)
├── uploads/
│   ├── car/ (created on first upload)
│   └── receipt/ (created on first upload)
├── PRPs/
│   ├── PRD-expense-splitter.md
│   └── implementation-plan-phase1-foundation.md
├── CLAUDE.md
└── README.md
```

---

## Next Phase Preview

### Phase 2: PDF Processing (Week 3-4)

After Phase 1 is complete, Phase 2 will implement:

**Backend**:
- Transaction extraction service using pdfplumber
- Regex patterns for CAR and receipt PDFs
- Transaction database model
- Transaction extraction API endpoints

**Frontend**:
- Transaction display table component
- Transaction list hooks and services
- Extraction status tracking

**Goal**: Extract and display transactions from uploaded PDFs

---

## Notes & Considerations

### Important Reminders

1. **Async vs Sync SQLite**: SQLite doesn't support true async, so we use sync SQLAlchemy instead of async. This is acceptable for desktop app use case.

2. **File Upload Security**: PDF validation is critical. The service validates:
   - File format (must be valid PDF)
   - Not encrypted
   - Page count within limits
   - File size within limits
   - Text extractability

3. **Query Key Factories**: Always use query key factories (`uploadKeys`) for cache operations. Never hardcode query keys.

4. **Error Handling**: All errors surfaced to user with friendly messages. Technical details logged but not shown to user.

5. **Development vs Production**:
   - Development: Hot reload enabled, verbose logging
   - Production: Disable reload, reduce logging, consider security hardening

### Potential Challenges

**Challenge 1**: CORS issues between frontend (5173) and backend (8000)
- **Solution**: CORS middleware configured in FastAPI to allow localhost:5173

**Challenge 2**: Large file uploads timing out
- **Solution**: Current limit is 300MB which is reasonable. If needed, increase FastAPI body limits and implement chunked uploads.

**Challenge 3**: PDF validation false negatives (rejecting valid PDFs)
- **Solution**: Test with variety of real-world CAR and receipt PDFs. Adjust validation logic as needed.

### Future Enhancements (Post-Phase 1)

- **Upload progress tracking**: Implement real-time upload progress (requires backend streaming support)
- **Batch uploads**: Allow multiple PDFs at once
- **File preview**: Show PDF preview before upload
- **Drag-and-drop reordering**: Allow user to specify page order

---

**END OF PHASE 1 IMPLEMENTATION PLAN**

---

*This plan is ready for execution with `/execute-plan PRPs/implementation-plan-phase1-foundation.md`*
