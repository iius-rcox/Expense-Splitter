from pydantic import BaseModel, Field
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
    is_duplicate: bool = Field(default=False, description="Whether this is a duplicate upload")
    transaction_count: int = Field(default=0, description="Number of transactions already extracted")
    matches_cleared: int = Field(default=0, description="Number of matches cleared for re-processing")

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
