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
