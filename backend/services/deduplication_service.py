"""
Deduplication service for PDF and transaction duplicate detection.
"""
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models.pdf import PDF
from models.transaction import Transaction


class DuplicateDetectedError(Exception):
    """Raised when a duplicate is detected."""
    def __init__(self, message: str, duplicate_record=None):
        super().__init__(message)
        self.duplicate_record = duplicate_record


class DeduplicationService:
    """Service for detecting and handling duplicate PDFs and transactions."""

    def calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            64-character hex digest

        Raises:
            IOError: If file cannot be read
        """
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            # Read in 8KB chunks to handle large files
            while chunk := f.read(8192):
                sha256.update(chunk)

        return sha256.hexdigest()

    def calculate_file_hash_from_bytes(self, content: bytes) -> str:
        """
        Calculate SHA-256 hash from file bytes.

        Useful for uploaded files before they're written to disk.

        Args:
            content: File content as bytes

        Returns:
            64-character hex digest
        """
        return hashlib.sha256(content).hexdigest()

    def calculate_transaction_fingerprint(self, transaction_data: Dict) -> str:
        """
        Calculate content fingerprint for a transaction.

        Uses business keys: date, amount, employee_id, transaction_type

        Args:
            transaction_data: Dict with transaction fields

        Returns:
            64-character hex digest
        """
        # Normalize components
        date_str = ""
        if transaction_data.get('date'):
            if isinstance(transaction_data['date'], date):
                date_str = transaction_data['date'].isoformat()
            elif isinstance(transaction_data['date'], str):
                date_str = transaction_data['date']

        amount_str = ""
        if transaction_data.get('amount') is not None:
            # Round to 2 decimal places for consistent comparison
            amount_str = f"{float(transaction_data['amount']):.2f}"

        employee_id = transaction_data.get('employee_id') or ""
        transaction_type = transaction_data.get('transaction_type') or ""

        # Combine with delimiter
        fingerprint_str = f"{date_str}|{amount_str}|{employee_id}|{transaction_type}"

        return hashlib.sha256(fingerprint_str.encode('utf-8')).hexdigest()

    def check_duplicate_pdf(self, file_hash: str, db: Session) -> Optional[PDF]:
        """
        Check if a PDF with the same hash already exists.

        Args:
            file_hash: SHA-256 hash of PDF content
            db: Database session

        Returns:
            Existing PDF record if found, None otherwise
        """
        return db.query(PDF).filter(PDF.file_hash == file_hash).first()

    def check_duplicate_transaction(
        self,
        fingerprint: str,
        db: Session
    ) -> Optional[Transaction]:
        """
        Check if a transaction with the same fingerprint exists.

        Args:
            fingerprint: Content fingerprint hash
            db: Database session

        Returns:
            Existing transaction if found, None otherwise
        """
        return db.query(Transaction).filter(
            Transaction.content_fingerprint == fingerprint
        ).first()

    def check_duplicate_transaction_by_fields(
        self,
        date_val: Optional[date],
        amount: Optional[float],
        employee_id: Optional[str],
        transaction_type: str,
        db: Session
    ) -> Optional[Transaction]:
        """
        Check for duplicate transaction by business key fields.

        Useful when fingerprint hasn't been calculated yet.

        Args:
            date_val: Transaction date
            amount: Transaction amount
            employee_id: Employee ID
            transaction_type: 'car' or 'receipt'
            db: Database session

        Returns:
            Existing transaction if found, None otherwise
        """
        return db.query(Transaction).filter(
            and_(
                Transaction.date == date_val,
                Transaction.amount == amount,
                Transaction.employee_id == employee_id,
                Transaction.transaction_type == transaction_type
            )
        ).first()

    def find_all_duplicates(self, db: Session) -> List[Tuple[str, List[Transaction]]]:
        """
        Find all duplicate transaction groups.

        Returns:
            List of (fingerprint, [transactions]) tuples
        """
        from sqlalchemy import func

        # Find fingerprints with multiple transactions
        duplicate_fingerprints = db.query(
            Transaction.content_fingerprint,
            func.count(Transaction.id).label('count')
        ).group_by(
            Transaction.content_fingerprint
        ).having(
            func.count(Transaction.id) > 1
        ).all()

        result = []
        for fingerprint, count in duplicate_fingerprints:
            transactions = db.query(Transaction).filter(
                Transaction.content_fingerprint == fingerprint
            ).all()
            result.append((fingerprint, transactions))

        return result

    def mark_as_duplicate(
        self,
        transaction: Transaction,
        original_transaction: Transaction,
        db: Session
    ):
        """
        Mark a transaction as duplicate of another.

        Args:
            transaction: Transaction to mark as duplicate
            original_transaction: Original transaction
            db: Database session
        """
        transaction.is_duplicate = True
        transaction.duplicate_of_id = original_transaction.id
        db.commit()


# Singleton instance
deduplication_service = DeduplicationService()
