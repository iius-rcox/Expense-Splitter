# Implementation Plan: Receipt Transaction Deduplication

**Feature**: Prevent duplicate transactions from being added to the database
**Branch**: `receipt-deduplication`
**Estimated Effort**: 8-12 hours
**Created**: 2025-10-17

---

## Overview

This plan implements a comprehensive deduplication system with three layers:
1. **File-level deduplication**: SHA-256 hash of PDF content to detect duplicate uploads
2. **Transaction-level deduplication**: Content fingerprint based on business keys (date, amount, employee_id)
3. **User experience**: Clear feedback and actionable options when duplicates are detected

The implementation follows existing codebase patterns and integrates seamlessly with the current FastAPI + SQLAlchemy architecture.

---

## Requirements Summary

**Primary Requirements**:
- Same PDF uploaded twice does not create duplicate transactions
- Transactions with identical key fields are detected and prevented
- Users receive clear feedback when duplicates are detected
- Option to force re-extraction with proper cleanup
- Existing matched transactions are preserved during deduplication
- Database maintains referential integrity

**Technical Requirements**:
- Add `file_hash` column to `pdfs` table
- Add unique constraints to prevent duplicates at database level
- Implement cascade deletes for data integrity
- Create new service for deduplication logic
- Modify existing upload and extraction endpoints
- Add comprehensive error handling and user feedback

**Success Criteria**:
- [ ] Duplicate PDF upload returns 409 Conflict with actionable options
- [ ] Duplicate transactions are prevented at database level
- [ ] Force re-extraction deletes old unmatched transactions
- [ ] Matched transactions cannot be accidentally deleted
- [ ] All changes are backward compatible with existing data
- [ ] Migration script successfully backfills hashes for existing PDFs

---

## Research Findings

### Best Practices

**From Codebase Analysis**:
1. **Service Pattern**: Business logic in services (`pdf_service`, `extraction_service`), database operations in routes
2. **Error Handling**: Custom exceptions in services, HTTPException in routes with structured detail objects
3. **Validation**: Pydantic schemas for request/response, SQLAlchemy for database constraints
4. **File Management**: UUID-based filenames, type-specific subdirectories, cleanup on error
5. **Response Format**: Consistent structure with `error`, `message`, `details` fields

**Database Migration Best Practices**:
1. **Nullable First**: Add new columns as nullable initially, backfill data, then make non-nullable
2. **Unique Constraints**: Add constraints after data is clean to avoid migration failures
3. **Cascade Deletes**: Define at foreign key level to maintain referential integrity
4. **Index Strategy**: Add indexes on frequently queried columns (hashes, fingerprints)

**Deduplication Strategies**:
1. **Content Hash**: SHA-256 provides collision-resistant file identification
2. **Business Key Hash**: Composite unique constraint on natural business keys
3. **Two-Phase Check**: Database constraint as final enforcement, application logic for user feedback
4. **Soft Delete Option**: For audit trail, though not implemented in current codebase

### Reference Implementations

**Existing Code to Follow**:

1. **Model Pattern** (`backend/models/transaction.py:8-84`):
```python
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pdf_id = Column(String(36), ForeignKey("pdfs.id"), nullable=False)
    # ... fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {field: value for all fields}
```

2. **Service Pattern** (`backend/services/pdf_service.py:15-70`):
```python
class PDFService:
    MAX_FILE_SIZE_MB = 300

    def __init__(self):
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    async def save_uploaded_file(self, file, pdf_type):
        # Validation, processing, return metadata

pdf_service = PDFService()  # Singleton export
```

3. **Error Handling** (`backend/api/routes/upload.py:58-80`):
```python
except ServicePDFValidationError as e:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"error": "validation_error", "message": str(e), "details": None}
    )
except Exception as e:
    if 'file_path' in locals():
        pdf_service.delete_file(file_path)
    raise HTTPException(status_code=500, detail={...})
```

### Technology Decisions

**Database**:
- **SQLite (dev)**: Continue using for development, migration strategy must work with SQLite constraints
- **Alembic**: Use for migrations despite current programmatic table creation (installed but unused)
- **Cascade Deletes**: Use database-level cascading for automatic cleanup

**Hashing**:
- **SHA-256**: For file content hashing (collision-resistant, standard library support)
- **Python hashlib**: Built-in, no dependencies needed
- **Chunked Reading**: For large files to avoid memory issues

**Data Types**:
- **String(64)**: For SHA-256 hex digest storage (64 hex characters)
- **Date vs DateTime**: Change transaction dates to Date type for day-level deduplication
- **Float vs Decimal**: Keep Float for backward compatibility (note: Decimal preferred for production)

---

## Implementation Tasks

### Phase 1: Database Schema & Migration (2-3 hours)

#### Task 1.1: Create Alembic Configuration
**Description**: Initialize Alembic for database migrations
**Files to create**:
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`

**Actions**:
```bash
cd backend
alembic init alembic
```

**Configuration**:
```python
# alembic/env.py - Import models
from models.base import Base
from models.pdf import PDF
from models.transaction import Transaction
target_metadata = Base.metadata
```

**Dependencies**: None
**Estimated effort**: 30 minutes

---

#### Task 1.2: Modify PDF Model
**Description**: Add file_hash column to PDF model
**Files to modify**:
- `backend/models/pdf.py`

**Changes**:
```python
# After file_size_bytes, before uploaded_at
file_hash = Column(String(64), nullable=True, index=True)  # Nullable for migration

# Add table args for unique constraint (applied later in migration)
__table_args__ = (
    UniqueConstraint('file_hash', name='uq_pdf_file_hash'),
)
```

**Dependencies**: None
**Estimated effort**: 15 minutes

---

#### Task 1.3: Modify Transaction Model
**Description**: Add deduplication fields and constraints to Transaction model
**Files to modify**:
- `backend/models/transaction.py`

**Changes**:
```python
# Line 28: Change DateTime to Date for day-level comparison
date = Column(Date, nullable=True)  # Changed from DateTime(timezone=False)

# Line 21: Add cascade delete to foreign key
pdf_id = Column(String(36), ForeignKey("pdfs.id", ondelete="CASCADE"), nullable=False)

# Before created_at, add new fields:
content_fingerprint = Column(String(64), nullable=True, index=True)  # SHA-256 of business key
is_duplicate = Column(Boolean, default=False)  # Flag for detected duplicates
duplicate_of_id = Column(String(36), ForeignKey("transactions.id"), nullable=True)  # Reference to original

# Add table args for unique constraint
__table_args__ = (
    UniqueConstraint(
        'date', 'amount', 'employee_id', 'transaction_type',
        name='uq_transaction_content'
    ),
    Index('idx_content_fingerprint', 'content_fingerprint'),
)
```

**Dependencies**: Task 1.2
**Estimated effort**: 30 minutes

---

#### Task 1.4: Create Migration - Add PDF Hash
**Description**: Generate Alembic migration to add file_hash to existing PDFs
**Files to create**:
- `backend/alembic/versions/001_add_pdf_hash.py`

**Command**:
```bash
alembic revision --autogenerate -m "add_pdf_hash"
```

**Manual modifications**:
```python
def upgrade():
    # 1. Add column (nullable)
    op.add_column('pdfs', sa.Column('file_hash', sa.String(64), nullable=True))

    # 2. Add index
    op.create_index('ix_pdfs_file_hash', 'pdfs', ['file_hash'])

    # 3. Backfill hashes (data migration - see Task 1.6)
    # Will be handled by separate script

    # 4. Make non-nullable (after backfill)
    # op.alter_column('pdfs', 'file_hash', nullable=False)  # Enable after backfill

    # 5. Add unique constraint (after data cleanup)
    # op.create_unique_constraint('uq_pdf_file_hash', 'pdfs', ['file_hash'])

def downgrade():
    op.drop_constraint('uq_pdf_file_hash', 'pdfs', type_='unique')
    op.drop_index('ix_pdfs_file_hash', 'pdfs')
    op.drop_column('pdfs', 'file_hash')
```

**Dependencies**: Task 1.2
**Estimated effort**: 45 minutes

---

#### Task 1.5: Create Migration - Modify Transaction Table
**Description**: Generate migration for transaction deduplication fields
**Files to create**:
- `backend/alembic/versions/002_add_transaction_dedup.py`

**Command**:
```bash
alembic revision --autogenerate -m "add_transaction_dedup"
```

**Manual modifications**:
```python
def upgrade():
    # 1. Add new columns
    op.add_column('transactions', sa.Column('content_fingerprint', sa.String(64), nullable=True))
    op.add_column('transactions', sa.Column('is_duplicate', sa.Boolean(), default=False))
    op.add_column('transactions', sa.Column('duplicate_of_id', sa.String(36), nullable=True))

    # 2. Add indexes
    op.create_index('idx_content_fingerprint', 'transactions', ['content_fingerprint'])

    # 3. Add foreign key for duplicate_of_id
    op.create_foreign_key(
        'fk_transaction_duplicate', 'transactions', 'transactions',
        ['duplicate_of_id'], ['id']
    )

    # 4. Modify pdf_id foreign key to add cascade delete
    # SQLite doesn't support altering FK, requires table recreation
    # For SQLite: handled in Task 1.7

    # 5. Change date column from DateTime to Date
    # SQLite: requires table recreation
    # PostgreSQL: op.alter_column('transactions', 'date', type_=sa.Date())

    # 6. Add unique constraint (after data cleanup)
    # op.create_unique_constraint('uq_transaction_content', 'transactions',
    #     ['date', 'amount', 'employee_id', 'transaction_type'])

def downgrade():
    op.drop_constraint('uq_transaction_content', 'transactions', type_='unique')
    op.drop_constraint('fk_transaction_duplicate', 'transactions', type_='foreignkey')
    op.drop_index('idx_content_fingerprint', 'transactions')
    op.drop_column('transactions', 'duplicate_of_id')
    op.drop_column('transactions', 'is_duplicate')
    op.drop_column('transactions', 'content_fingerprint')
```

**Dependencies**: Task 1.3
**Estimated effort**: 1 hour

---

#### Task 1.6: Create Data Migration Script
**Description**: Script to backfill hashes for existing PDFs and transactions
**Files to create**:
- `backend/scripts/migrate_add_hashes.py`

**Implementation**:
```python
"""
Data migration: Calculate hashes for existing PDFs and transactions.
Run after applying schema migrations but before adding constraints.
"""
import hashlib
from pathlib import Path
from sqlalchemy.orm import Session
from models.base import SessionLocal
from models.pdf import PDF
from models.transaction import Transaction
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA-256 hash of file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()

def calculate_transaction_fingerprint(transaction: Transaction) -> str:
    """Calculate fingerprint from business keys."""
    parts = [
        transaction.date.isoformat() if transaction.date else "",
        f"{transaction.amount:.2f}" if transaction.amount else "",
        transaction.employee_id or "",
        transaction.transaction_type or ""
    ]
    fingerprint_str = "|".join(parts)
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()

def migrate_pdf_hashes(db: Session):
    """Backfill file_hash for existing PDFs."""
    pdfs = db.query(PDF).filter(PDF.file_hash == None).all()
    logger.info(f"Processing {len(pdfs)} PDFs without hashes")

    success_count = 0
    error_count = 0

    for pdf in pdfs:
        try:
            file_path = Path(pdf.file_path)
            if file_path.exists():
                pdf.file_hash = calculate_file_hash(file_path)
                success_count += 1
            else:
                logger.warning(f"PDF file not found: {pdf.file_path}")
                error_count += 1
        except Exception as e:
            logger.error(f"Error processing PDF {pdf.id}: {e}")
            error_count += 1

    db.commit()
    logger.info(f"PDF hash migration: {success_count} success, {error_count} errors")

def migrate_transaction_fingerprints(db: Session):
    """Backfill content_fingerprint for existing transactions."""
    transactions = db.query(Transaction).filter(Transaction.content_fingerprint == None).all()
    logger.info(f"Processing {len(transactions)} transactions without fingerprints")

    for trans in transactions:
        try:
            trans.content_fingerprint = calculate_transaction_fingerprint(trans)
        except Exception as e:
            logger.error(f"Error processing transaction {trans.id}: {e}")

    db.commit()
    logger.info(f"Transaction fingerprint migration complete")

def find_duplicates(db: Session):
    """Find and report duplicate transactions."""
    from sqlalchemy import func

    duplicates = db.query(
        Transaction.content_fingerprint,
        func.count(Transaction.id).label('count')
    ).group_by(
        Transaction.content_fingerprint
    ).having(
        func.count(Transaction.id) > 1
    ).all()

    if duplicates:
        logger.warning(f"Found {len(duplicates)} duplicate fingerprints")
        for fp, count in duplicates:
            logger.warning(f"  Fingerprint {fp[:16]}... has {count} duplicates")
    else:
        logger.info("No duplicate transactions found")

def main():
    db = SessionLocal()
    try:
        logger.info("Starting data migration...")
        migrate_pdf_hashes(db)
        migrate_transaction_fingerprints(db)
        find_duplicates(db)
        logger.info("Data migration complete")
    finally:
        db.close()

if __name__ == "__main__":
    main()
```

**Usage**:
```bash
cd backend
python scripts/migrate_add_hashes.py
```

**Dependencies**: Tasks 1.4, 1.5
**Estimated effort**: 1 hour

---

#### Task 1.7: Create SQLite Table Recreation Script
**Description**: SQLite-specific script to handle foreign key modification
**Files to create**:
- `backend/scripts/migrate_sqlite_fk.py`

**Why needed**: SQLite doesn't support ALTER COLUMN for foreign keys; requires table recreation

**Implementation**:
```python
"""
SQLite-specific migration: Recreate transactions table with cascade delete.
Only run if using SQLite (development).
"""
from alembic import op
import sqlalchemy as sa

def upgrade_sqlite_transactions():
    """Recreate transactions table with proper foreign key cascades."""

    # Create new table with correct schema
    op.create_table('transactions_new',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('pdf_id', sa.String(36), sa.ForeignKey('pdfs.id', ondelete='CASCADE'), nullable=False),
        # ... all other columns from Transaction model
        sa.Column('date', sa.Date(), nullable=True),  # Changed to Date
        # ... rest of columns
    )

    # Copy data
    op.execute('''
        INSERT INTO transactions_new
        SELECT id, pdf_id, ..., DATE(date) as date, ...
        FROM transactions
    ''')

    # Drop old table
    op.drop_table('transactions')

    # Rename new table
    op.rename_table('transactions_new', 'transactions')
```

**Dependencies**: Task 1.5
**Estimated effort**: 45 minutes

---

### Phase 2: Deduplication Service (2-3 hours)

#### Task 2.1: Create Deduplication Service
**Description**: Core service with hash calculation and duplicate detection logic
**Files to create**:
- `backend/services/deduplication_service.py`

**Implementation**:
```python
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
```

**Dependencies**: Tasks 1.2, 1.3
**Estimated effort**: 2 hours

---

#### Task 2.2: Add Tests for Deduplication Service
**Description**: Unit tests for deduplication service methods
**Files to create**:
- `backend/tests/test_deduplication_service.py`
- `backend/tests/fixtures/test_sample.pdf` (small test PDF)

**Implementation**:
```python
"""
Unit tests for deduplication service.
"""
import pytest
from pathlib import Path
from datetime import date
from services.deduplication_service import deduplication_service
from models.pdf import PDF
from models.transaction import Transaction


class TestDeduplicationService:

    def test_calculate_file_hash_consistency(self, tmp_path):
        """Test that file hash is consistent for same content."""
        test_file = tmp_path / "test.pdf"
        test_content = b"Test PDF content"
        test_file.write_bytes(test_content)

        hash1 = deduplication_service.calculate_file_hash(test_file)
        hash2 = deduplication_service.calculate_file_hash(test_file)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest length

    def test_calculate_file_hash_from_bytes(self):
        """Test hash calculation from bytes."""
        content = b"Test content"
        hash_result = deduplication_service.calculate_file_hash_from_bytes(content)

        assert len(hash_result) == 64
        assert hash_result == deduplication_service.calculate_file_hash_from_bytes(content)

    def test_calculate_transaction_fingerprint(self):
        """Test transaction fingerprint calculation."""
        trans_data = {
            'date': date(2025, 10, 15),
            'amount': 123.45,
            'employee_id': 'EMP001',
            'transaction_type': 'car'
        }

        fingerprint = deduplication_service.calculate_transaction_fingerprint(trans_data)

        assert len(fingerprint) == 64

        # Same data should produce same fingerprint
        fingerprint2 = deduplication_service.calculate_transaction_fingerprint(trans_data)
        assert fingerprint == fingerprint2

        # Different amount should produce different fingerprint
        trans_data['amount'] = 123.46
        fingerprint3 = deduplication_service.calculate_transaction_fingerprint(trans_data)
        assert fingerprint != fingerprint3

    def test_check_duplicate_pdf(self, test_db):
        """Test duplicate PDF detection."""
        # Create PDF with hash
        pdf1 = PDF(
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            pdf_type="car",
            page_count=5,
            file_size_bytes=1000
        )
        test_db.add(pdf1)
        test_db.commit()

        # Check for duplicate
        duplicate = deduplication_service.check_duplicate_pdf("abc123", test_db)
        assert duplicate is not None
        assert duplicate.id == pdf1.id

        # Check for non-existent hash
        no_duplicate = deduplication_service.check_duplicate_pdf("xyz789", test_db)
        assert no_duplicate is None

    def test_check_duplicate_transaction(self, test_db):
        """Test duplicate transaction detection."""
        # Create transaction with fingerprint
        trans1 = Transaction(
            pdf_id="pdf-123",
            transaction_type="car",
            date=date(2025, 10, 15),
            amount=100.00,
            employee_id="EMP001",
            content_fingerprint="fingerprint123",
            page_number=1
        )
        test_db.add(trans1)
        test_db.commit()

        # Check for duplicate
        duplicate = deduplication_service.check_duplicate_transaction(
            "fingerprint123", test_db
        )
        assert duplicate is not None
        assert duplicate.id == trans1.id

    def test_find_all_duplicates(self, test_db):
        """Test finding all duplicate groups."""
        # Create transactions with duplicate fingerprints
        for i in range(3):
            trans = Transaction(
                pdf_id=f"pdf-{i}",
                transaction_type="car",
                content_fingerprint="duplicate_fp",
                page_number=i
            )
            test_db.add(trans)

        # Create unique transaction
        unique_trans = Transaction(
            pdf_id="pdf-unique",
            transaction_type="car",
            content_fingerprint="unique_fp",
            page_number=1
        )
        test_db.add(unique_trans)
        test_db.commit()

        # Find duplicates
        duplicates = deduplication_service.find_all_duplicates(test_db)

        assert len(duplicates) == 1
        fingerprint, transactions = duplicates[0]
        assert fingerprint == "duplicate_fp"
        assert len(transactions) == 3


@pytest.fixture
def test_db():
    """Create in-memory test database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.base import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    yield db

    db.close()
```

**Dependencies**: Task 2.1
**Estimated effort**: 1 hour

---

### Phase 3: API Integration (3-4 hours)

#### Task 3.1: Modify PDF Upload Routes
**Description**: Add hash calculation and duplicate detection to upload endpoints
**Files to modify**:
- `backend/api/routes/upload.py`
- `backend/services/pdf_service.py`

**Changes to `pdf_service.py`**:
```python
# Add import
from services.deduplication_service import deduplication_service

# Modify save_uploaded_file to return hash
async def save_uploaded_file(
    self,
    file: UploadFile,
    pdf_type: Literal["car", "receipt"]
) -> tuple[Path, str, int, int, str]:  # Added str for hash
    """Save uploaded file and return metadata including hash."""

    # Read file content
    file_content = await file.read()

    # Calculate hash before any other operations
    file_hash = deduplication_service.calculate_file_hash_from_bytes(file_content)

    # Rewind for validation (CRITICAL)
    await file.seek(0)

    # ... existing validation code ...

    # Save to disk
    file_id = str(uuid.uuid4())
    # ... existing save logic ...

    return file_path, original_filename, page_count, file_size, file_hash

# Add method to check for duplicates
def find_duplicate_pdf(self, file_hash: str, db: Session) -> Optional[PDF]:
    """Find PDF by hash."""
    return deduplication_service.check_duplicate_pdf(file_hash, db)
```

**Changes to `upload.py`**:
```python
# Add import
from services.deduplication_service import deduplication_service
from models.transaction import Transaction

@router.post("/car", response_model=PDFUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_car_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # Save and get hash
        file_path, filename, page_count, file_size, file_hash = await pdf_service.save_uploaded_file(
            file, pdf_type="car"
        )

        # Check for duplicate BEFORE creating record
        duplicate_pdf = deduplication_service.check_duplicate_pdf(file_hash, db)

        if duplicate_pdf:
            # Delete newly saved file (it's a duplicate)
            pdf_service.delete_file(file_path)

            # Count existing transactions
            transaction_count = db.query(Transaction).filter(
                Transaction.pdf_id == duplicate_pdf.id
            ).count()

            # Return 409 Conflict with actionable information
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "duplicate_pdf",
                    "message": f"This PDF has already been uploaded as '{duplicate_pdf.filename}'.",
                    "duplicate_pdf": {
                        "pdf_id": duplicate_pdf.id,
                        "filename": duplicate_pdf.filename,
                        "uploaded_at": duplicate_pdf.uploaded_at.isoformat(),
                        "transaction_count": transaction_count,
                        "pdf_type": duplicate_pdf.pdf_type
                    },
                    "actions": [
                        {
                            "action": "view_transactions",
                            "description": "View existing transactions",
                            "endpoint": f"/api/extract/transactions?pdf_id={duplicate_pdf.id}"
                        },
                        {
                            "action": "force_reextract",
                            "description": "Delete existing data and re-extract",
                            "endpoint": f"/api/extract/force/{duplicate_pdf.id}",
                            "method": "POST",
                            "warning": "This will delete existing unmatched transactions"
                        }
                    ]
                }
            )

        # Create new PDF record with hash
        pdf_record = PDF(
            filename=filename,
            file_path=str(file_path.absolute()),
            file_hash=file_hash,  # NEW
            pdf_type="car",
            page_count=page_count,
            file_size_bytes=file_size
        )

        db.add(pdf_record)
        db.commit()
        db.refresh(pdf_record)

        return PDFUploadResponse(
            pdf_id=pdf_record.id,
            filename=pdf_record.filename,
            pdf_type=pdf_record.pdf_type,
            page_count=pdf_record.page_count,
            file_size_bytes=pdf_record.file_size_bytes,
            uploaded_at=pdf_record.uploaded_at
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions (including 409)
    except ServicePDFValidationError as e:
        # ... existing error handling ...
    except Exception as e:
        # ... existing error handling ...

# Repeat same changes for upload_receipt_pdf endpoint
```

**Dependencies**: Task 2.1
**Estimated effort**: 1.5 hours

---

#### Task 3.2: Modify Extraction Routes
**Description**: Add transaction deduplication and force re-extraction endpoint
**Files to modify**:
- `backend/api/routes/extraction.py`

**Changes**:
```python
# Add imports
from services.deduplication_service import deduplication_service
from sqlalchemy.exc import IntegrityError

@router.post("/pdf/{pdf_id}", response_model=TransactionListResponse)
async def extract_pdf_transactions(
    pdf_id: str,
    db: Session = Depends(get_db)
):
    """Extract transactions with duplicate detection."""

    # ... existing PDF validation ...

    try:
        extracted = extraction_service.extract_transactions(pdf_path, pdf_record.pdf_type)

        transaction_records = []
        duplicate_count = 0
        duplicates_info = []

        for trans in extracted:
            # Calculate fingerprint
            trans_data = {
                'date': trans.date.date() if trans.date else None,
                'amount': trans.amount,
                'employee_id': trans.employee_id,
                'transaction_type': trans.transaction_type
            }
            fingerprint = deduplication_service.calculate_transaction_fingerprint(trans_data)

            # Check for existing transaction
            existing = deduplication_service.check_duplicate_transaction(fingerprint, db)

            if existing:
                duplicate_count += 1
                duplicates_info.append({
                    'date': trans.date.isoformat() if trans.date else None,
                    'amount': trans.amount,
                    'merchant': trans.merchant,
                    'existing_transaction_id': existing.id
                })
                continue  # Skip inserting duplicate

            # Create transaction
            transaction = Transaction(
                pdf_id=pdf_id,
                transaction_type=trans.transaction_type,
                date=trans.date.date() if trans.date else None,
                amount=trans.amount,
                employee_id=trans.employee_id,
                employee_name=trans.employee_name,
                merchant=trans.merchant,
                card_number=trans.card_number,
                receipt_id=trans.receipt_id,
                page_number=trans.page_number,
                raw_text=trans.raw_text,
                extraction_confidence=trans.extraction_confidence,
                content_fingerprint=fingerprint  # NEW
            )

            db.add(transaction)
            transaction_records.append(transaction)

        db.commit()

        # Refresh all records
        for transaction in transaction_records:
            db.refresh(transaction)

        # Build response
        response = TransactionListResponse(
            transactions=[TransactionResponse.model_validate(t) for t in transaction_records],
            total_count=len(transaction_records),
            car_count=sum(1 for t in transaction_records if t.transaction_type == 'car'),
            receipt_count=sum(1 for t in transaction_records if t.transaction_type == 'receipt'),
            unmatched_count=len(transaction_records)
        )

        # Log duplicate info
        if duplicate_count > 0:
            logger.warning(
                f"Extracted {len(transaction_records)} transactions, "
                f"skipped {duplicate_count} duplicates from PDF {pdf_id}"
            )

        return response

    except ExtractionError as e:
        # ... existing error handling ...

# NEW ENDPOINT: Force re-extraction
@router.post("/force/{pdf_id}", response_model=TransactionListResponse)
async def force_reextract_transactions(
    pdf_id: str,
    delete_matched: bool = False,
    db: Session = Depends(get_db)
):
    """
    Force re-extraction of transactions from a PDF.

    Deletes existing UNMATCHED transactions and re-extracts.
    By default, will fail if any transactions are matched (safety check).

    Args:
        pdf_id: PDF UUID
        delete_matched: If True, allows deletion of matched transactions (dangerous!)

    Returns:
        TransactionListResponse with newly extracted transactions

    Raises:
        404: PDF not found
        400: Has matched transactions and delete_matched=False
    """
    import logging
    logger = logging.getLogger(__name__)

    # Validate PDF exists
    pdf_record = db.query(PDF).filter(PDF.id == pdf_id).first()
    if not pdf_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"PDF with id {pdf_id} not found",
                "details": None
            }
        )

    # Check for matched transactions
    matched_count = db.query(Transaction).filter(
        Transaction.pdf_id == pdf_id,
        Transaction.is_matched == True
    ).count()

    if matched_count > 0 and not delete_matched:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "has_matched_transactions",
                "message": f"Cannot re-extract. This PDF has {matched_count} matched transactions.",
                "suggestion": "Delete the matches first, or pass delete_matched=true to force deletion",
                "matched_count": matched_count
            }
        )

    # Delete existing transactions
    query = db.query(Transaction).filter(Transaction.pdf_id == pdf_id)
    if not delete_matched:
        query = query.filter(Transaction.is_matched == False)

    deleted_count = query.delete()
    db.commit()

    logger.info(f"Force re-extract: Deleted {deleted_count} transactions for PDF {pdf_id}")

    # Call normal extraction
    return await extract_pdf_transactions(pdf_id, db)

# NEW ENDPOINT: Check extraction status
@router.get("/status/{pdf_id}")
async def get_extraction_status(
    pdf_id: str,
    db: Session = Depends(get_db)
):
    """
    Get extraction status for a PDF.

    Returns information about whether the PDF has been extracted,
    how many transactions exist, and if it's a duplicate.
    """
    pdf_record = db.query(PDF).filter(PDF.id == pdf_id).first()
    if not pdf_record:
        raise HTTPException(status_code=404, detail="PDF not found")

    transaction_count = db.query(Transaction).filter(
        Transaction.pdf_id == pdf_id
    ).count()

    matched_count = db.query(Transaction).filter(
        Transaction.pdf_id == pdf_id,
        Transaction.is_matched == True
    ).count()

    # Check if this PDF is a duplicate of another
    duplicate_pdfs = db.query(PDF).filter(
        PDF.file_hash == pdf_record.file_hash,
        PDF.id != pdf_id
    ).all()

    return {
        "pdf_id": pdf_id,
        "filename": pdf_record.filename,
        "pdf_type": pdf_record.pdf_type,
        "is_extracted": transaction_count > 0,
        "transaction_count": transaction_count,
        "matched_count": matched_count,
        "unmatched_count": transaction_count - matched_count,
        "is_duplicate": len(duplicate_pdfs) > 0,
        "duplicate_of": [
            {
                "pdf_id": dup.id,
                "filename": dup.filename,
                "uploaded_at": dup.uploaded_at.isoformat()
            }
            for dup in duplicate_pdfs
        ] if duplicate_pdfs else []
    }
```

**Dependencies**: Task 2.1, Task 3.1
**Estimated effort**: 2 hours

---

#### Task 3.3: Create Deduplication Management Routes
**Description**: New router for deduplication-specific endpoints
**Files to create**:
- `backend/api/routes/deduplication.py`

**Implementation**:
```python
"""
API routes for deduplication management.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from models.base import get_db
from models.pdf import PDF
from models.transaction import Transaction
from services.deduplication_service import deduplication_service
from services.pdf_service import pdf_service

router = APIRouter(prefix="/api/dedup", tags=["deduplication"])


@router.post("/check-file")
async def check_file_for_duplicates(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Check if uploaded file is a duplicate WITHOUT saving it.

    Useful for client-side duplicate detection before upload.
    """
    try:
        # Read file content
        content = await file.read()

        # Calculate hash
        file_hash = deduplication_service.calculate_file_hash_from_bytes(content)

        # Check for duplicate
        duplicate_pdf = deduplication_service.check_duplicate_pdf(file_hash, db)

        if duplicate_pdf:
            transaction_count = db.query(Transaction).filter(
                Transaction.pdf_id == duplicate_pdf.id
            ).count()

            return {
                "is_duplicate": True,
                "duplicate_pdf": {
                    "pdf_id": duplicate_pdf.id,
                    "filename": duplicate_pdf.filename,
                    "uploaded_at": duplicate_pdf.uploaded_at.isoformat(),
                    "transaction_count": transaction_count
                }
            }
        else:
            return {
                "is_duplicate": False,
                "duplicate_pdf": None
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "message": "Failed to check for duplicates",
                "details": str(e)
            }
        )


@router.get("/find-duplicates")
async def find_duplicate_transactions(
    db: Session = Depends(get_db)
):
    """
    Find all duplicate transaction groups in the database.

    Returns groups of transactions with identical fingerprints.
    """
    duplicate_groups = deduplication_service.find_all_duplicates(db)

    result = []
    for fingerprint, transactions in duplicate_groups:
        result.append({
            "fingerprint": fingerprint,
            "count": len(transactions),
            "transactions": [
                {
                    "transaction_id": t.id,
                    "date": t.date.isoformat() if t.date else None,
                    "amount": t.amount,
                    "employee_id": t.employee_id,
                    "merchant": t.merchant,
                    "pdf_id": t.pdf_id,
                    "is_matched": t.is_matched
                }
                for t in transactions
            ]
        })

    return {
        "duplicate_groups": result,
        "total_groups": len(result),
        "total_duplicates": sum(len(group["transactions"]) for group in result)
    }


@router.delete("/transaction/{transaction_id}")
async def delete_duplicate_transaction(
    transaction_id: str,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """
    Delete a duplicate transaction.

    Safety check: Won't delete matched transactions unless force=True.
    """
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if transaction.is_matched and not force:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "transaction_matched",
                "message": "Cannot delete matched transaction without force=true"
            }
        )

    db.delete(transaction)
    db.commit()

    return {
        "message": "Transaction deleted successfully",
        "transaction_id": transaction_id
    }
```

**Register router in main.py**:
```python
# backend/app/main.py
from api.routes import deduplication

app.include_router(deduplication.router)
```

**Dependencies**: Task 2.1
**Estimated effort**: 1 hour

---

#### Task 3.4: Update Response Schemas
**Description**: Add/modify Pydantic schemas for deduplication responses
**Files to modify**:
- `backend/schemas/transaction.py`

**Changes**:
```python
# Add to TransactionListResponse
class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total_count: int
    car_count: int
    receipt_count: int
    unmatched_count: int
    duplicates_skipped: int = 0  # NEW field
```

**Files to create**:
- `backend/schemas/deduplication.py`

**Implementation**:
```python
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
```

**Dependencies**: Task 3.1, 3.2
**Estimated effort**: 30 minutes

---

### Phase 4: Testing & Documentation (2-3 hours)

#### Task 4.1: Create Integration Tests
**Description**: End-to-end tests for duplicate detection workflows
**Files to create**:
- `backend/tests/test_deduplication_integration.py`

**Implementation**:
```python
"""
Integration tests for deduplication workflows.
"""
import pytest
from httpx import AsyncClient
from pathlib import Path


@pytest.mark.asyncio
async def test_duplicate_pdf_upload(client, test_db, sample_pdf):
    """Test that uploading the same PDF twice returns 409."""

    # Upload first time
    with open(sample_pdf, 'rb') as f:
        response1 = await client.post(
            "/api/upload/car",
            files={"file": ("test.pdf", f, "application/pdf")}
        )

    assert response1.status_code == 201
    pdf_id1 = response1.json()["pdf_id"]

    # Upload same file again
    with open(sample_pdf, 'rb') as f:
        response2 = await client.post(
            "/api/upload/car",
            files={"file": ("test.pdf", f, "application/pdf")}
        )

    # Should return 409 Conflict
    assert response2.status_code == 409
    data = response2.json()
    assert data["error"] == "duplicate_pdf"
    assert "duplicate_pdf" in data
    assert data["duplicate_pdf"]["pdf_id"] == pdf_id1


@pytest.mark.asyncio
async def test_force_reextraction(client, test_db, sample_pdf):
    """Test force re-extraction endpoint."""

    # Upload and extract
    with open(sample_pdf, 'rb') as f:
        upload_response = await client.post(
            "/api/upload/car",
            files={"file": ("test.pdf", f, "application/pdf")}
        )

    pdf_id = upload_response.json()["pdf_id"]

    extract_response = await client.post(f"/api/extract/pdf/{pdf_id}")
    assert extract_response.status_code == 200
    original_count = extract_response.json()["total_count"]

    # Force re-extract
    reextract_response = await client.post(f"/api/extract/force/{pdf_id}")
    assert reextract_response.status_code == 200

    # Should have same number of transactions
    new_count = reextract_response.json()["total_count"]
    assert new_count == original_count


@pytest.mark.asyncio
async def test_duplicate_check_endpoint(client, test_db, sample_pdf):
    """Test the /dedup/check-file endpoint."""

    # Upload file first
    with open(sample_pdf, 'rb') as f:
        await client.post(
            "/api/upload/car",
            files={"file": ("test.pdf", f, "application/pdf")}
        )

    # Check for duplicate
    with open(sample_pdf, 'rb') as f:
        check_response = await client.post(
            "/api/dedup/check-file",
            files={"file": ("test.pdf", f, "application/pdf")}
        )

    assert check_response.status_code == 200
    data = check_response.json()
    assert data["is_duplicate"] is True
    assert data["duplicate_pdf"] is not None


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a minimal test PDF."""
    pdf_path = tmp_path / "test.pdf"
    # Create minimal valid PDF
    pdf_content = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj
4 0 obj << /Length 44 >> stream
BT /F1 12 Tf 100 700 Td (Test PDF) Tj ET
endstream endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000214 00000 n
trailer << /Size 5 /Root 1 0 R >>
startxref
307
%%EOF"""
    pdf_path.write_bytes(pdf_content)
    return pdf_path
```

**Dependencies**: Tasks 3.1, 3.2, 3.3
**Estimated effort**: 1.5 hours

---

#### Task 4.2: Update API Documentation
**Description**: Document new endpoints and error responses
**Files to modify**:
- `backend/app/main.py` (OpenAPI metadata)

**Changes**:
```python
# Update API description
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
    docs_url="/docs",
    redoc_url="/redoc"
)
```

**Files to create**:
- `docs/API_DEDUPLICATION.md`

**Implementation**:
```markdown
# Deduplication API Documentation

## Overview

The deduplication system prevents duplicate PDFs and transactions from being processed.

## Endpoints

### Check for Duplicate File
`POST /api/dedup/check-file`

Check if a file is a duplicate before uploading.

**Response (200)**:
```json
{
  "is_duplicate": true,
  "duplicate_pdf": {
    "pdf_id": "550e8400-...",
    "filename": "car_report.pdf",
    "uploaded_at": "2025-10-17T10:30:00Z",
    "transaction_count": 50
  }
}
```

### Upload with Duplicate Detection
`POST /api/upload/car` or `/api/upload/receipt`

**Response (409 Conflict)**:
```json
{
  "error": "duplicate_pdf",
  "message": "This PDF has already been uploaded",
  "duplicate_pdf": { ... },
  "actions": [
    {
      "action": "view_transactions",
      "endpoint": "/api/extract/transactions?pdf_id=..."
    },
    {
      "action": "force_reextract",
      "endpoint": "/api/extract/force/{pdf_id}",
      "warning": "Deletes existing unmatched transactions"
    }
  ]
}
```

### Force Re-extraction
`POST /api/extract/force/{pdf_id}`

**Query Parameters**:
- `delete_matched` (bool): Allow deletion of matched transactions

**Response (200)**:
```json
{
  "transactions": [...],
  "total_count": 50
}
```

**Response (400)**:
```json
{
  "error": "has_matched_transactions",
  "message": "Cannot re-extract. This PDF has 5 matched transactions.",
  "matched_count": 5
}
```

### Find All Duplicates
`GET /api/dedup/find-duplicates`

**Response**:
```json
{
  "duplicate_groups": [
    {
      "fingerprint": "abc123...",
      "count": 3,
      "transactions": [...]
    }
  ],
  "total_groups": 10,
  "total_duplicates": 25
}
```

## Error Codes

| Code | Error Type | Description |
|------|------------|-------------|
| 409 | duplicate_pdf | PDF already uploaded |
| 400 | has_matched_transactions | Cannot delete matched data |
| 400 | validation_error | Invalid request |

## Client Implementation Example

```python
import requests

# Check before upload
with open('report.pdf', 'rb') as f:
    check = requests.post(
        'http://api/dedup/check-file',
        files={'file': f}
    )

if check.json()['is_duplicate']:
    print("File already uploaded!")
    # Offer user options
else:
    # Proceed with upload
    with open('report.pdf', 'rb') as f:
        upload = requests.post(
            'http://api/upload/car',
            files={'file': f}
        )
```
```

**Dependencies**: All Phase 3 tasks
**Estimated effort**: 1 hour

---

#### Task 4.3: Create Migration and Deployment Guide
**Description**: Document how to apply migrations to existing deployments
**Files to create**:
- `docs/DEDUPLICATION_MIGRATION_GUIDE.md`

**Implementation**:
```markdown
# Deduplication Migration Guide

## Prerequisites

- Database backup created
- No active transactions processing
- Alembic installed (`pip install alembic`)

## Migration Steps

### Step 1: Backup Database

```bash
# SQLite
cp data/expense_matcher.db data/expense_matcher.db.backup

# PostgreSQL
pg_dump expense_matcher > backup.sql
```

### Step 2: Initialize Alembic (if not already done)

```bash
cd backend
alembic init alembic
```

Edit `alembic/env.py` to include models:
```python
from models.base import Base
target_metadata = Base.metadata
```

### Step 3: Apply Schema Migrations

```bash
# Generate migrations (if not using pre-created)
alembic revision --autogenerate -m "add_deduplication"

# Review migration files in alembic/versions/

# Apply migrations
alembic upgrade head
```

### Step 4: Run Data Migration

```bash
# Calculate hashes for existing data
python scripts/migrate_add_hashes.py
```

Expected output:
```
INFO - Starting data migration...
INFO - Processing 15 PDFs without hashes
INFO - PDF hash migration: 15 success, 0 errors
INFO - Processing 450 transactions without fingerprints
INFO - Transaction fingerprint migration complete
INFO - No duplicate transactions found
INFO - Data migration complete
```

### Step 5: Apply Unique Constraints

Uncomment constraint additions in migration files:
```python
# In alembic/versions/001_add_pdf_hash.py
op.alter_column('pdfs', 'file_hash', nullable=False)
op.create_unique_constraint('uq_pdf_file_hash', 'pdfs', ['file_hash'])
```

Apply:
```bash
alembic upgrade head
```

### Step 6: Verify

```bash
# Check constraints
sqlite3 data/expense_matcher.db ".schema pdfs"
sqlite3 data/expense_matcher.db ".schema transactions"

# Test duplicate detection
curl -X POST http://localhost:8000/api/dedup/find-duplicates
```

## Rollback Procedure

If migration fails:

```bash
# Rollback Alembic migrations
alembic downgrade -1

# Restore database backup
cp data/expense_matcher.db.backup data/expense_matcher.db
```

## SQLite Specific Considerations

SQLite doesn't support:
- ALTER COLUMN for foreign keys
- Modifying column types easily

Solution: Use table recreation script (Task 1.7)

## Production Checklist

- [ ] Database backup created
- [ ] Migration tested in staging environment
- [ ] All users notified of maintenance window
- [ ] Application stopped during migration
- [ ] Schema migrations applied
- [ ] Data migration completed successfully
- [ ] Constraints applied without errors
- [ ] Application restarted
- [ ] Duplicate detection verified working
- [ ] Rollback procedure documented and tested
```

**Dependencies**: All Phase 1 tasks
**Estimated effort**: 1 hour

---

## Codebase Integration Points

### Files to Modify

| File | Changes | Complexity |
|------|---------|------------|
| `backend/models/pdf.py` | Add `file_hash` column and constraint | Low |
| `backend/models/transaction.py` | Add dedup fields, change date type, cascade delete | Medium |
| `backend/services/pdf_service.py` | Add hash calculation to upload flow | Low |
| `backend/api/routes/upload.py` | Add duplicate detection before save | Medium |
| `backend/api/routes/extraction.py` | Add dedup check, force re-extract endpoint | Medium |
| `backend/app/main.py` | Register new dedup router | Low |
| `backend/schemas/transaction.py` | Add `duplicates_skipped` field | Low |

### New Files to Create

| File | Purpose | Lines (est.) |
|------|---------|--------------|
| `backend/services/deduplication_service.py` | Core deduplication logic | 250 |
| `backend/api/routes/deduplication.py` | Dedup management endpoints | 150 |
| `backend/schemas/deduplication.py` | Response schemas | 80 |
| `backend/alembic/versions/001_add_pdf_hash.py` | Migration: PDF hash | 60 |
| `backend/alembic/versions/002_add_transaction_dedup.py` | Migration: Transaction dedup | 80 |
| `backend/scripts/migrate_add_hashes.py` | Data migration script | 150 |
| `backend/tests/test_deduplication_service.py` | Unit tests | 200 |
| `backend/tests/test_deduplication_integration.py` | Integration tests | 150 |
| `docs/API_DEDUPLICATION.md` | API documentation | N/A |
| `docs/DEDUPLICATION_MIGRATION_GUIDE.md` | Deployment guide | N/A |

### Existing Patterns to Follow

1. **Service Singleton Pattern**: Export `deduplication_service = DeduplicationService()`
2. **Error Handling**: Service raises custom exceptions, routes convert to HTTPException
3. **Database Sessions**: Use `Depends(get_db)` dependency injection
4. **Response Structure**: `{"error": "type", "message": "msg", "details": "..."}`
5. **File Cleanup**: Delete files in except blocks when operations fail
6. **Logging**: Use `logging.getLogger(__name__)` pattern
7. **UUID Generation**: `str(uuid.uuid4())` for all IDs
8. **Model Serialization**: Implement `to_dict()` method on all models

---

## Technical Design

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Upload                         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              POST /api/upload/car (or /receipt)             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. Read file content                                  │   │
│  │ 2. Calculate SHA-256 hash                             │   │
│  │ 3. Check deduplication_service.check_duplicate_pdf()  │   │
│  │ 4. If duplicate: Return 409 with options             │   │
│  │ 5. If new: Save file + Create PDF record with hash   │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│            POST /api/extract/pdf/{pdf_id}                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 1. Extract transactions (existing service)            │   │
│  │ 2. For each transaction:                              │   │
│  │    a. Calculate fingerprint (date|amount|empid|type)  │   │
│  │    b. Check for duplicate transaction                │   │
│  │    c. Skip if duplicate, insert if new               │   │
│  │ 3. Return count + duplicates_skipped                 │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Database Layer                          │
│  ┌──────────────┐  ┌────────────────┐  ┌─────────────────┐  │
│  │ PDFs Table   │  │ Transactions   │  │ Dedup Service   │  │
│  │              │  │ Table          │  │                 │  │
│  │ + file_hash  │  │ + fingerprint  │  │ Hash functions  │  │
│  │ (unique)     │  │ + is_duplicate │  │ Duplicate check │  │
│  └──────────────┘  │ (unique constr)│  └─────────────────┘  │
│                    └────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

**Upload Flow**:
1. Client uploads PDF → `POST /api/upload/car`
2. Server reads file bytes → Calculate SHA-256
3. Query database for matching `file_hash`
4. **If duplicate found**:
   - Delete newly uploaded file
   - Return 409 with existing PDF info + action options
5. **If new**:
   - Save file to disk
   - Create PDF record with hash
   - Return 201 Created

**Extraction Flow**:
1. Client requests extraction → `POST /api/extract/pdf/{pdf_id}`
2. Extract transactions using existing service
3. For each transaction:
   - Calculate fingerprint: `SHA256(date|amount|employee_id|type)`
   - Query for existing transaction with same fingerprint
   - **If duplicate**: Skip insertion, increment `duplicates_skipped`
   - **If new**: Insert with fingerprint
4. Return transaction list + duplicate count

**Force Re-extract Flow**:
1. Client requests re-extraction → `POST /api/extract/force/{pdf_id}`
2. Check for matched transactions
3. **If matched found** and `delete_matched=false`: Return 400 error
4. **If safe to proceed**:
   - Delete existing unmatched transactions (cascade handled by DB)
   - Call normal extraction flow
   - Return new transaction list

### Database Schema Changes

**PDFs Table**:
```sql
ALTER TABLE pdfs ADD COLUMN file_hash VARCHAR(64);
CREATE UNIQUE INDEX idx_pdfs_file_hash ON pdfs(file_hash);
```

**Transactions Table**:
```sql
ALTER TABLE transactions ADD COLUMN content_fingerprint VARCHAR(64);
ALTER TABLE transactions ADD COLUMN is_duplicate BOOLEAN DEFAULT FALSE;
ALTER TABLE transactions ADD COLUMN duplicate_of_id VARCHAR(36);
ALTER TABLE transactions MODIFY COLUMN date DATE;  -- Change from DATETIME

CREATE INDEX idx_content_fingerprint ON transactions(content_fingerprint);
CREATE UNIQUE INDEX uq_transaction_content ON transactions(
    date, amount, employee_id, transaction_type
);

ALTER TABLE transactions ADD CONSTRAINT fk_duplicate_of
    FOREIGN KEY (duplicate_of_id) REFERENCES transactions(id);

-- Modify existing FK to add cascade delete
ALTER TABLE transactions MODIFY COLUMN pdf_id VARCHAR(36)
    REFERENCES pdfs(id) ON DELETE CASCADE;
```

---

## Dependencies and Libraries

**Existing** (already in requirements.txt):
- `sqlalchemy` - ORM and database operations
- `alembic` - Database migrations
- `pydantic` - Request/response schemas
- `fastapi` - Web framework
- `hashlib` (Python stdlib) - SHA-256 hashing

**New** (none required):
- All functionality uses existing dependencies

---

## Testing Strategy

### Unit Tests
**Location**: `backend/tests/test_deduplication_service.py`

**Coverage**:
- Hash calculation consistency
- Hash calculation from bytes vs file
- Transaction fingerprint generation
- Fingerprint changes with different values
- Duplicate PDF detection
- Duplicate transaction detection
- Find all duplicates query

### Integration Tests
**Location**: `backend/tests/test_deduplication_integration.py`

**Scenarios**:
- Upload duplicate PDF → Returns 409
- Extract with duplicate transactions → Skips duplicates
- Force re-extract → Deletes old, creates new
- Force re-extract with matched transactions → Returns error
- Check-file endpoint → Detects duplicates before save
- Extraction status endpoint → Shows correct counts

### Edge Cases to Cover
- Empty file content (hash of empty bytes)
- PDF with zero transactions
- Transaction with null values (date, amount, employee_id)
- Multiple transactions with identical values
- Concurrent uploads of same file
- Re-extraction while extraction is in progress
- Database constraint violation handling
- File system errors during hash calculation
- Orphaned transactions (PDF deleted but transactions remain) → Should be prevented by cascade delete

### Manual Testing Checklist
- [ ] Upload same PDF twice → 409 response
- [ ] Upload different PDFs with identical transactions → Duplicates detected
- [ ] Force re-extract removes old transactions
- [ ] Cannot force re-extract matched transactions
- [ ] Migration backfills hashes correctly
- [ ] Unique constraints enforced at database level
- [ ] Cascade delete removes transactions when PDF deleted
- [ ] Error messages are user-friendly
- [ ] API documentation accurate

---

## Success Criteria

### Functional Requirements
- [x] Duplicate PDF upload returns 409 Conflict
- [x] Error response includes actionable options
- [x] Duplicate transactions detected and skipped
- [x] Force re-extraction endpoint implemented
- [x] Matched transactions protected from deletion
- [x] Database constraints enforce uniqueness
- [x] Cascade deletes maintain referential integrity

### Non-Functional Requirements
- [ ] Hash calculation under 100ms for 10MB PDF
- [ ] Duplicate check query under 10ms
- [ ] No regression in extraction performance
- [ ] Migration completes in under 5 minutes for 10,000 records
- [ ] All tests pass (unit + integration)
- [ ] API documentation complete and accurate
- [ ] Code follows existing codebase patterns

### User Experience
- [ ] Clear error messages with guidance
- [ ] Users know when duplicates are detected
- [ ] Users have clear options to resolve duplicates
- [ ] Force re-extract requires explicit user action
- [ ] No data loss during migration

---

## Notes and Considerations

### Potential Challenges

1. **SQLite Limitations**:
   - Cannot modify foreign keys with ALTER
   - Solution: Table recreation script for development
   - Consider PostgreSQL for production

2. **DateTime to Date Migration**:
   - Existing data has time components
   - Migration must convert properly: `DATE(datetime_column)`
   - May affect existing queries expecting DateTime

3. **Concurrent Uploads**:
   - Race condition: Two simultaneous uploads of same file
   - Mitigation: Database unique constraint as final enforcement
   - Application check is best-effort for UX

4. **Large File Hashing**:
   - 300MB PDFs may take time to hash
   - Mitigation: Chunked reading (8KB chunks)
   - Consider async hashing for future optimization

5. **Existing Matched Transactions**:
   - Cannot delete without breaking matches
   - Solution: Provide clear error with guidance
   - Consider "unmatching" feature for future

### Future Enhancements

**Phase 2 (post-MVP)**:
- Soft delete for audit trail
- Batch duplicate resolution UI
- Duplicate merge functionality
- Fuzzy duplicate detection (similar but not identical)
- Duplicate analytics dashboard

**Performance Optimizations**:
- Cache file hashes in memory
- Async hash calculation
- Batch transaction fingerprint calculation
- Database query optimization with EXPLAIN ANALYZE

**User Experience**:
- Frontend duplicate warning before upload
- Progress indicator for large file hashing
- Duplicate resolution wizard
- Bulk operations for duplicate cleanup

### Rollback Plan

If deduplication causes critical issues:

1. **Remove unique constraints**:
```sql
ALTER TABLE pdfs DROP CONSTRAINT uq_pdf_file_hash;
ALTER TABLE transactions DROP CONSTRAINT uq_transaction_content;
```

2. **Revert code changes**:
```bash
git revert <dedup-commit-hash>
```

3. **Continue without deduplication**:
- System functions normally
- Manual duplicate cleanup required
- Plan remediation for next release

### Monitoring

**Metrics to Track**:
- Duplicate detection rate (% of uploads that are duplicates)
- Force re-extraction usage frequency
- Hash calculation time (p50, p95, p99)
- Database constraint violations
- User error reports related to duplicates

**Alerts**:
- High duplicate detection rate (may indicate user confusion)
- Hash calculation time > 500ms (performance issue)
- Frequent force re-extractions (may indicate workflow issue)

---

*This plan is ready for execution with `/execute-plan`*
