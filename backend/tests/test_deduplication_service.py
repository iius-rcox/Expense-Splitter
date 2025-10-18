"""
Unit tests for deduplication service.

Tests core hash calculation and duplicate detection logic.
"""
import pytest
from datetime import date, datetime
from pathlib import Path
import tempfile
import hashlib

from services.deduplication_service import DeduplicationService, DuplicateDetectedError
from models.pdf import PDF
from models.transaction import Transaction


class TestFileHashing:
    """Test file hash calculation."""

    def test_calculate_file_hash_from_bytes(self):
        """Should calculate SHA-256 hash from byte content."""
        service = DeduplicationService()
        content = b"Test PDF content"

        hash_result = service.calculate_file_hash_from_bytes(content)

        # Verify it's a valid 64-character hex string
        assert len(hash_result) == 64
        assert all(c in '0123456789abcdef' for c in hash_result)

        # Verify it matches expected SHA-256
        expected = hashlib.sha256(content).hexdigest()
        assert hash_result == expected

    def test_calculate_file_hash_from_file(self):
        """Should calculate SHA-256 hash from file path."""
        service = DeduplicationService()

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            test_content = b"Test PDF file content"
            f.write(test_content)
            temp_path = Path(f.name)

        try:
            hash_result = service.calculate_file_hash(temp_path)

            # Verify hash matches expected
            expected = hashlib.sha256(test_content).hexdigest()
            assert hash_result == expected
        finally:
            temp_path.unlink()

    def test_identical_content_produces_same_hash(self):
        """Should produce identical hash for identical content."""
        service = DeduplicationService()
        content = b"Identical content"

        hash1 = service.calculate_file_hash_from_bytes(content)
        hash2 = service.calculate_file_hash_from_bytes(content)

        assert hash1 == hash2

    def test_different_content_produces_different_hash(self):
        """Should produce different hash for different content."""
        service = DeduplicationService()

        hash1 = service.calculate_file_hash_from_bytes(b"Content A")
        hash2 = service.calculate_file_hash_from_bytes(b"Content B")

        assert hash1 != hash2


class TestTransactionFingerprinting:
    """Test transaction fingerprint calculation."""

    def test_calculate_fingerprint_with_all_fields(self):
        """Should calculate fingerprint from business key fields."""
        service = DeduplicationService()

        transaction_data = {
            'date': date(2025, 1, 15),
            'amount': 123.45,
            'employee_id': 'EMP001',
            'transaction_type': 'car'
        }

        fingerprint = service.calculate_transaction_fingerprint(transaction_data)

        # Verify it's a valid 64-character hex string
        assert len(fingerprint) == 64
        assert all(c in '0123456789abcdef' for c in fingerprint)

    def test_identical_transactions_produce_same_fingerprint(self):
        """Should produce same fingerprint for identical transactions."""
        service = DeduplicationService()

        trans1 = {
            'date': date(2025, 1, 15),
            'amount': 123.45,
            'employee_id': 'EMP001',
            'transaction_type': 'car'
        }

        trans2 = {
            'date': date(2025, 1, 15),
            'amount': 123.45,
            'employee_id': 'EMP001',
            'transaction_type': 'car'
        }

        fp1 = service.calculate_transaction_fingerprint(trans1)
        fp2 = service.calculate_transaction_fingerprint(trans2)

        assert fp1 == fp2

    def test_amount_rounding_normalization(self):
        """Should normalize amounts to 2 decimal places."""
        service = DeduplicationService()

        trans1 = {
            'date': date(2025, 1, 15),
            'amount': 123.456789,  # Many decimals
            'employee_id': 'EMP001',
            'transaction_type': 'car'
        }

        trans2 = {
            'date': date(2025, 1, 15),
            'amount': 123.46,  # Rounded to 2 decimals
            'employee_id': 'EMP001',
            'transaction_type': 'car'
        }

        fp1 = service.calculate_transaction_fingerprint(trans1)
        fp2 = service.calculate_transaction_fingerprint(trans2)

        assert fp1 == fp2

    def test_date_string_vs_date_object(self):
        """Should handle both date objects and ISO strings."""
        service = DeduplicationService()

        trans1 = {
            'date': date(2025, 1, 15),
            'amount': 100.00,
            'employee_id': 'EMP001',
            'transaction_type': 'car'
        }

        trans2 = {
            'date': '2025-01-15',
            'amount': 100.00,
            'employee_id': 'EMP001',
            'transaction_type': 'car'
        }

        fp1 = service.calculate_transaction_fingerprint(trans1)
        fp2 = service.calculate_transaction_fingerprint(trans2)

        assert fp1 == fp2

    def test_different_dates_produce_different_fingerprints(self):
        """Should produce different fingerprint for different dates."""
        service = DeduplicationService()

        trans1 = {
            'date': date(2025, 1, 15),
            'amount': 100.00,
            'employee_id': 'EMP001',
            'transaction_type': 'car'
        }

        trans2 = {
            'date': date(2025, 1, 16),  # Different date
            'amount': 100.00,
            'employee_id': 'EMP001',
            'transaction_type': 'car'
        }

        fp1 = service.calculate_transaction_fingerprint(trans1)
        fp2 = service.calculate_transaction_fingerprint(trans2)

        assert fp1 != fp2

    def test_different_amounts_produce_different_fingerprints(self):
        """Should produce different fingerprint for different amounts."""
        service = DeduplicationService()

        trans1 = {
            'date': date(2025, 1, 15),
            'amount': 100.00,
            'employee_id': 'EMP001',
            'transaction_type': 'car'
        }

        trans2 = {
            'date': date(2025, 1, 15),
            'amount': 200.00,  # Different amount
            'employee_id': 'EMP001',
            'transaction_type': 'car'
        }

        fp1 = service.calculate_transaction_fingerprint(trans1)
        fp2 = service.calculate_transaction_fingerprint(trans2)

        assert fp1 != fp2

    def test_different_employee_ids_produce_different_fingerprints(self):
        """Should produce different fingerprint for different employee IDs."""
        service = DeduplicationService()

        trans1 = {
            'date': date(2025, 1, 15),
            'amount': 100.00,
            'employee_id': 'EMP001',
            'transaction_type': 'car'
        }

        trans2 = {
            'date': date(2025, 1, 15),
            'amount': 100.00,
            'employee_id': 'EMP002',  # Different employee
            'transaction_type': 'car'
        }

        fp1 = service.calculate_transaction_fingerprint(trans1)
        fp2 = service.calculate_transaction_fingerprint(trans2)

        assert fp1 != fp2

    def test_different_transaction_types_produce_different_fingerprints(self):
        """Should produce different fingerprint for different transaction types."""
        service = DeduplicationService()

        trans1 = {
            'date': date(2025, 1, 15),
            'amount': 100.00,
            'employee_id': 'EMP001',
            'transaction_type': 'car'
        }

        trans2 = {
            'date': date(2025, 1, 15),
            'amount': 100.00,
            'employee_id': 'EMP001',
            'transaction_type': 'receipt'  # Different type
        }

        fp1 = service.calculate_transaction_fingerprint(trans1)
        fp2 = service.calculate_transaction_fingerprint(trans2)

        assert fp1 != fp2

    def test_handles_missing_fields(self):
        """Should handle missing or None fields gracefully."""
        service = DeduplicationService()

        # Empty transaction
        trans = {
            'date': None,
            'amount': None,
            'employee_id': None,
            'transaction_type': ''
        }

        # Should not raise error
        fingerprint = service.calculate_transaction_fingerprint(trans)
        assert len(fingerprint) == 64

    def test_merchant_field_not_included_in_fingerprint(self):
        """Should NOT include merchant in fingerprint (not part of business key)."""
        service = DeduplicationService()

        trans1 = {
            'date': date(2025, 1, 15),
            'amount': 100.00,
            'employee_id': 'EMP001',
            'transaction_type': 'car',
            'merchant': 'Merchant A'
        }

        trans2 = {
            'date': date(2025, 1, 15),
            'amount': 100.00,
            'employee_id': 'EMP001',
            'transaction_type': 'car',
            'merchant': 'Merchant B'  # Different merchant
        }

        fp1 = service.calculate_transaction_fingerprint(trans1)
        fp2 = service.calculate_transaction_fingerprint(trans2)

        # Should be SAME because merchant is not part of business key
        assert fp1 == fp2


class TestDatabaseDuplicateChecks:
    """Test duplicate checking against database."""

    def test_check_duplicate_pdf_finds_existing(self, db_session):
        """Should find existing PDF with same hash."""
        service = DeduplicationService()

        # Create existing PDF
        existing_pdf = PDF(
            filename="original.pdf",
            file_path="/path/to/original.pdf",
            file_hash="abc123hash",
            pdf_type="car",
            page_count=5,
            file_size_bytes=1000
        )
        db_session.add(existing_pdf)
        db_session.commit()

        # Check for duplicate
        result = service.check_duplicate_pdf("abc123hash", db_session)

        assert result is not None
        assert result.id == existing_pdf.id

    def test_check_duplicate_pdf_returns_none_when_not_found(self, db_session):
        """Should return None when no duplicate exists."""
        service = DeduplicationService()

        result = service.check_duplicate_pdf("nonexistent_hash", db_session)

        assert result is None

    def test_check_duplicate_transaction_by_fingerprint(self, db_session):
        """Should find existing transaction with same fingerprint."""
        service = DeduplicationService()

        # Create existing transaction
        existing = Transaction(
            pdf_id="pdf-123",
            transaction_type="car",
            date=date(2025, 1, 15),
            amount=100.00,
            employee_id="EMP001",
            page_number=1,
            content_fingerprint="fingerprint123"
        )
        db_session.add(existing)
        db_session.commit()

        # Check for duplicate
        result = service.check_duplicate_transaction("fingerprint123", db_session)

        assert result is not None
        assert result.id == existing.id

    def test_check_duplicate_transaction_by_fields(self, db_session):
        """Should find duplicate by business key fields."""
        service = DeduplicationService()

        # Create existing transaction
        existing = Transaction(
            pdf_id="pdf-123",
            transaction_type="car",
            date=date(2025, 1, 15),
            amount=100.00,
            employee_id="EMP001",
            page_number=1
        )
        db_session.add(existing)
        db_session.commit()

        # Check for duplicate by fields
        result = service.check_duplicate_transaction_by_fields(
            date_val=date(2025, 1, 15),
            amount=100.00,
            employee_id="EMP001",
            transaction_type="car",
            db=db_session
        )

        assert result is not None
        assert result.id == existing.id

    def test_mark_as_duplicate(self, db_session):
        """Should mark transaction as duplicate of another."""
        service = DeduplicationService()

        # Create original transaction
        original = Transaction(
            pdf_id="pdf-1",
            transaction_type="car",
            date=date(2025, 1, 15),
            amount=100.00,
            employee_id="EMP001",
            page_number=1,
            content_fingerprint="fp123"
        )

        # Create duplicate with DIFFERENT business key to avoid unique constraint
        # (In real scenario, duplicates would be detected before insertion)
        duplicate = Transaction(
            pdf_id="pdf-2",
            transaction_type="car",
            date=date(2025, 1, 16),  # Different date to avoid constraint
            amount=200.00,  # Different amount to avoid constraint
            employee_id="EMP002",  # Different employee to avoid constraint
            page_number=1,
            content_fingerprint="fp456",  # Different fingerprint
            is_duplicate=False
        )

        db_session.add_all([original, duplicate])
        db_session.commit()

        # Mark as duplicate (simulating post-detection marking)
        service.mark_as_duplicate(duplicate, original, db_session)

        # Verify
        db_session.refresh(duplicate)
        assert duplicate.is_duplicate is True
        assert duplicate.duplicate_of_id == original.id


# Pytest fixtures
@pytest.fixture
def db_session():
    """Create in-memory SQLite session for testing."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.base import Base

    # Create in-memory database
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)

    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
