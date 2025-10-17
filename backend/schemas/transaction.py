from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Optional


class TransactionBase(BaseModel):
    """Base schema for transaction data."""

    transaction_type: Literal["car", "receipt"]
    date: Optional[datetime] = None
    amount: Optional[float] = None
    employee_id: Optional[str] = None
    employee_name: Optional[str] = None
    merchant: Optional[str] = None
    card_number: Optional[str] = None
    receipt_id: Optional[str] = None
    page_number: int
    raw_text: Optional[str] = None
    extraction_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class TransactionCreate(TransactionBase):
    """Schema for creating a new transaction."""
    pdf_id: str


class TransactionResponse(TransactionBase):
    """Schema for transaction API responses."""

    transaction_id: str = Field(validation_alias="id", serialization_alias="transaction_id")
    pdf_id: str
    is_matched: bool
    extracted_at: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "transaction_id": "550e8400-e29b-41d4-a716-446655440000",
                "pdf_id": "660e8400-e29b-41d4-a716-446655440001",
                "transaction_type": "car",
                "date": "2025-10-15T00:00:00",
                "amount": 123.45,
                "employee_id": "12345",
                "employee_name": "SMITH, JOHN",
                "merchant": "ACME CORP",
                "card_number": "XXXXXXXXXXXX1234",
                "page_number": 3,
                "extraction_confidence": 0.95,
                "is_matched": False,
                "extracted_at": "2025-10-16T10:30:00Z",
                "created_at": "2025-10-16T10:30:00Z"
            }
        }


class TransactionListResponse(BaseModel):
    """Schema for list of transactions."""

    transactions: list[TransactionResponse]
    total_count: int
    car_count: int
    receipt_count: int
    unmatched_count: int

    class Config:
        json_schema_extra = {
            "example": {
                "transactions": [],
                "total_count": 50,
                "car_count": 25,
                "receipt_count": 25,
                "unmatched_count": 10
            }
        }


class MatchBase(BaseModel):
    """Base schema for match data."""

    car_transaction_id: str
    receipt_transaction_id: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    date_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    amount_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    employee_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    merchant_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class MatchCreate(MatchBase):
    """Schema for creating a new match."""
    pass


class MatchUpdate(BaseModel):
    """Schema for updating a match."""

    status: Optional[Literal["pending", "approved", "rejected", "exported"]] = None
    manually_reviewed: Optional[bool] = None
    review_notes: Optional[str] = None


class MatchResponse(MatchBase):
    """Schema for match API responses."""

    match_id: str
    status: str
    manually_reviewed: bool
    review_notes: Optional[str] = None
    exported: bool
    export_path: Optional[str] = None
    exported_at: Optional[datetime] = None
    matched_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "match_id": "770e8400-e29b-41d4-a716-446655440002",
                "car_transaction_id": "550e8400-e29b-41d4-a716-446655440000",
                "receipt_transaction_id": "880e8400-e29b-41d4-a716-446655440003",
                "confidence_score": 0.87,
                "date_score": 0.95,
                "amount_score": 1.0,
                "employee_score": 1.0,
                "merchant_score": 0.75,
                "status": "pending",
                "manually_reviewed": False,
                "exported": False,
                "matched_at": "2025-10-16T10:35:00Z"
            }
        }


class MatchWithTransactionsResponse(MatchResponse):
    """Schema for match with full transaction details."""

    car_transaction: TransactionResponse
    receipt_transaction: TransactionResponse

    class Config:
        from_attributes = True


class MatchListResponse(BaseModel):
    """Schema for list of matches."""

    matches: list[MatchWithTransactionsResponse]
    total_count: int
    pending_count: int
    approved_count: int
    exported_count: int

    class Config:
        json_schema_extra = {
            "example": {
                "matches": [],
                "total_count": 20,
                "pending_count": 15,
                "approved_count": 3,
                "exported_count": 2
            }
        }
