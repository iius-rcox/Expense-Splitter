# Deduplication Feature Tests

## Quick Start

Run all deduplication tests:
```bash
cd backend
python -m pytest tests/test_deduplication_service.py tests/test_deduplication_constraints.py -v
```

## Test Files

### test_deduplication_service.py
Core service logic tests - hash calculation, fingerprinting, duplicate detection

**Run command:**
```bash
python -m pytest tests/test_deduplication_service.py -v
```

**Test classes:**
- `TestFileHashing` - SHA-256 hash calculation for files
- `TestTransactionFingerprinting` - Business key fingerprint calculation
- `TestDatabaseDuplicateChecks` - Duplicate detection queries

### test_deduplication_constraints.py
Database constraint and edge case tests

**Run command:**
```bash
python -m pytest tests/test_deduplication_constraints.py -v
```

**Test classes:**
- `TestDatabaseConstraints` - Unique constraints validation
- `TestCascadeDelete` - FK cascade behavior (PostgreSQL-specific)
- `TestEdgeCases` - Null values, special chars, edge amounts
- `TestDuplicateRelationships` - duplicate_of FK relationships

### test_deduplication_routes.py
API route integration tests (requires full app environment)

**Run command:**
```bash
python -m pytest tests/test_deduplication_routes.py -v
```

**Test classes:**
- `TestUploadDuplicateDetection` - 409 responses on duplicate uploads
- `TestTransactionDuplicateDetection` - Duplicate skipping during extraction
- `TestForceReExtraction` - Force re-extract endpoint safety
- `TestDeduplicationManagement` - Admin dedup endpoints
- `TestExtractionStatusEndpoint` - Status endpoint info

## Useful Test Commands

### Run specific test class
```bash
python -m pytest tests/test_deduplication_service.py::TestFileHashing -v
```

### Run specific test method
```bash
python -m pytest tests/test_deduplication_service.py::TestFileHashing::test_calculate_file_hash_from_bytes -v
```

### Run with coverage
```bash
python -m pytest tests/test_deduplication_service.py --cov=services.deduplication_service --cov-report=html
```

### Run with output
```bash
python -m pytest tests/test_deduplication_service.py -v -s
```

### Run failing tests only
```bash
python -m pytest tests/test_deduplication_service.py --lf
```

### Skip specific tests
```bash
python -m pytest tests/ -k "not cascade" -v
```

## Test Coverage

### What's Tested
- ✅ File hash calculation (SHA-256)
- ✅ Transaction fingerprint calculation
- ✅ Duplicate PDF detection
- ✅ Duplicate transaction detection
- ✅ Database unique constraints
- ✅ Edge cases (null, empty, special chars)
- ✅ Duplicate marking
- ✅ Foreign key relationships

### What's NOT Tested (Future Work)
- ⚠️ End-to-end API tests with real PDFs
- ⚠️ Concurrent upload scenarios
- ⚠️ Performance tests for large files
- ⚠️ Migration from existing data

## Expected Results

All tests should pass except:
- `test_deleting_pdf_deletes_transactions` - SQLite in-memory limitation (works in PostgreSQL)

**Total:** 33 passing tests

## Troubleshooting

### Import errors
Ensure you're in the backend directory and the virtual environment is activated:
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### Module not found
Install dependencies:
```bash
pip install -r requirements.txt
```

### Database errors
Tests use in-memory SQLite - no external database needed.

## CI/CD Integration

Add to your CI pipeline:
```yaml
- name: Run deduplication tests
  run: |
    cd backend
    python -m pytest tests/test_deduplication_service.py tests/test_deduplication_constraints.py -v --tb=short
```
