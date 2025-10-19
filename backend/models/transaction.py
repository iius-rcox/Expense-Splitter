from sqlalchemy import Column, String, Integer, Float, DateTime, Date, Text, ForeignKey, Boolean, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
import uuid


class Transaction(Base):
    """
    Represents a transaction extracted from a PDF.

    Can be from either a CAR (Corporate American Express Report) or receipt PDF.
    Stores all extracted fields needed for matching.
    """
    __tablename__ = "transactions"

    # Primary key (UUID as string)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Link to source PDF (with cascade delete)
    pdf_id = Column(String(36), ForeignKey("pdfs.id", ondelete="CASCADE"), nullable=False)
    pdf = relationship("PDF", backref="transactions")

    # Transaction type
    transaction_type = Column(String(10), nullable=False)  # 'car' or 'receipt'

    # Core transaction data
    date = Column(Date, nullable=True)  # Transaction date (changed to Date for day-level deduplication)
    amount = Column(Float, nullable=True)  # Transaction amount in dollars
    employee_id = Column(String(50), nullable=True)  # Employee ID
    employee_name = Column(String(255), nullable=True)  # Employee name
    merchant = Column(String(255), nullable=True)  # Merchant/vendor name

    # Additional CAR-specific fields
    card_number = Column(String(50), nullable=True)  # Last 4 digits or masked number

    # Additional receipt-specific fields
    receipt_id = Column(String(100), nullable=True)  # Receipt identifier if available

    # Page location in source PDF
    page_number = Column(Integer, nullable=False)  # Which page this transaction was on

    # Raw extracted text (for debugging/manual review)
    raw_text = Column(Text, nullable=True)

    # Deduplication fields
    content_fingerprint = Column(String(64), nullable=True, index=True)  # SHA-256 of business key
    is_duplicate = Column(Boolean, default=False)  # Flag for detected duplicates
    duplicate_of_id = Column(String(36), ForeignKey("transactions.id"), nullable=True)  # Reference to original

    # Extraction metadata
    extraction_confidence = Column(Float, nullable=True)  # 0.0 to 1.0 confidence score
    extracted_at = Column(DateTime(timezone=True), server_default=func.now())

    # Matching status
    is_matched = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Table constraints
    __table_args__ = (
        UniqueConstraint(
            'date', 'amount', 'employee_id', 'transaction_type',
            name='uq_transaction_content'
        ),
        Index('idx_content_fingerprint', 'content_fingerprint'),
    )

    def __repr__(self):
        return (
            f"<Transaction(id={self.id}, type={self.transaction_type}, "
            f"date={self.date}, amount=${self.amount}, merchant={self.merchant})>"
        )

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            "transaction_id": self.id,
            "pdf_id": self.pdf_id,
            "transaction_type": self.transaction_type,
            "date": self.date.isoformat() if self.date else None,
            "amount": self.amount,
            "employee_id": self.employee_id,
            "employee_name": self.employee_name,
            "merchant": self.merchant,
            "card_number": self.card_number,
            "receipt_id": self.receipt_id,
            "page_number": self.page_number,
            "raw_text": self.raw_text,
            "content_fingerprint": self.content_fingerprint,
            "is_duplicate": self.is_duplicate,
            "duplicate_of_id": self.duplicate_of_id,
            "extraction_confidence": self.extraction_confidence,
            "is_matched": self.is_matched,
            "extracted_at": self.extracted_at.isoformat() if self.extracted_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Match(Base):
    """
    Represents a matched pair of CAR transaction and receipt transaction.

    Stores the confidence score and matching metadata.
    Used to generate split PDFs with matched pairs.
    """
    __tablename__ = "matches"

    # Primary key (UUID as string)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Matched transactions
    car_transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=False)
    receipt_transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=False)

    # Relationships
    car_transaction = relationship("Transaction", foreign_keys=[car_transaction_id], backref="car_matches")
    receipt_transaction = relationship("Transaction", foreign_keys=[receipt_transaction_id], backref="receipt_matches")

    # Matching metadata
    confidence_score = Column(Float, nullable=False)  # 0.0 to 1.0 overall match confidence

    # Component scores (for transparency and debugging)
    date_score = Column(Float, nullable=True)  # Date proximity score
    amount_score = Column(Float, nullable=True)  # Amount match score
    employee_score = Column(Float, nullable=True)  # Employee ID match score
    merchant_score = Column(Float, nullable=True)  # Merchant fuzzy match score

    # Match status
    status = Column(String(20), default="pending")  # 'pending', 'approved', 'rejected', 'exported'

    # Manual review
    manually_reviewed = Column(Boolean, default=False)
    review_notes = Column(Text, nullable=True)

    # Export tracking
    exported = Column(Boolean, default=False)
    export_path = Column(Text, nullable=True)  # Path to generated split PDF
    exported_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    matched_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return (
            f"<Match(id={self.id}, confidence={self.confidence_score:.2f}, "
            f"status={self.status})>"
        )

    def to_dict(self):
        """Convert model to dictionary for API responses."""
        return {
            "match_id": self.id,
            "car_transaction_id": self.car_transaction_id,
            "receipt_transaction_id": self.receipt_transaction_id,
            "confidence_score": self.confidence_score,
            "date_score": self.date_score,
            "amount_score": self.amount_score,
            "employee_score": self.employee_score,
            "merchant_score": self.merchant_score,
            "status": self.status,
            "manually_reviewed": self.manually_reviewed,
            "review_notes": self.review_notes,
            "exported": self.exported,
            "export_path": self.export_path,
            "exported_at": self.exported_at.isoformat() if self.exported_at else None,
            "matched_at": self.matched_at.isoformat() if self.matched_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
