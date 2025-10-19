"""
Pydantic schemas for deduplication responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


class DuplicatePDFInfo(BaseModel):
    """Information about a duplicate PDF."""
    pdf_id: str
    filename: str
    uploaded_at: datetime
    transaction_count: int
    pdf_type: Literal["car", "receipt"]

    class Config:
        json_schema_extra = {
            "example": {
                "pdf_id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "car_report_march.pdf",
                "uploaded_at": "2025-10-17T10:30:00Z",
                "transaction_count": 50,
                "pdf_type": "car"
            }
        }


class DuplicateAction(BaseModel):
    """Available action for resolving duplicate."""
    action: str
    description: str
    endpoint: str
    method: str = "GET"
    warning: Optional[str] = None


class DuplicateCheckResponse(BaseModel):
    """Response from duplicate check."""
    is_duplicate: bool
    duplicate_pdf: Optional[DuplicatePDFInfo] = None

    class Config:
        json_schema_extra = {
            "example": {
                "is_duplicate": True,
                "duplicate_pdf": {
                    "pdf_id": "550e8400-...",
                    "filename": "car_report.pdf",
                    "uploaded_at": "2025-10-17T10:30:00Z",
                    "transaction_count": 50,
                    "pdf_type": "car"
                }
            }
        }
