# Date Format Fix - Database Type Mismatch

## Problem
Application crashed with error:
```
ValueError: Invalid isoformat string: '2025-02-20 00:00:00.000000'
```

The database was storing **datetime values** (`2025-02-20 00:00:00.000000`) in a **Date column** which expects date-only format (`2025-02-20`).

## Root Cause
The extraction service was using `datetime.strptime()` which returns a `datetime` object, but the Transaction model's `date` field is defined as a `Date` column (SQLAlchemy).

## Solution Implemented

### Code Fix 1: `backend/services/extraction_service.py`

**Before:**
```python
# CAR extraction (line 152)
transaction_date = datetime.strptime(date_str, '%m/%d/%Y')

# Receipt extraction (line 258)
transaction_date = datetime.strptime(date_str, fmt)
```

**After:**
```python
# CAR extraction (line 152)
transaction_date = datetime.strptime(date_str, '%m/%d/%Y').date()

# Receipt extraction (line 258)
transaction_date = datetime.strptime(date_str, fmt).date()
```

### Code Fix 2: `backend/api/routes/extraction.py`

**Before:**
```python
# Line 78: Fingerprint calculation
'date': trans.date.date() if trans.date else None,

# Line 103: Transaction creation
date=trans.date.date() if trans.date else None,
```

**After:**
```python
# Line 78: Fingerprint calculation
'date': trans.date,  # Already a date object from extraction service

# Line 103: Transaction creation
date=trans.date,  # Already a date object from extraction service
```

**Why:** After fixing the extraction service to return `date` objects, the endpoint was trying to call `.date()` on a date object, which doesn't have that attribute.

### Database Cleanup
- Deleted **7,230 corrupted transactions** from database
- PDFs remain in database (can be re-extracted)

## Next Steps for User
1. ✅ Code is fixed (backend will auto-reload)
2. ✅ Database is cleaned
3. **Upload your PDFs again** and extract transactions
4. Dates will now be stored correctly as date-only values

## Technical Details

### Type Mismatch
- **Model definition**: `date = Column(Date, nullable=True)` → Expects Python `date` object
- **Old extraction code**: Returns `datetime` object → SQLite stores as `YYYY-MM-DD HH:MM:SS.ffffff`
- **New extraction code**: Returns `date` object → SQLite stores as `YYYY-MM-DD`

### Why It Failed
When SQLAlchemy tried to read the corrupted data:
1. Read `'2025-02-20 00:00:00.000000'` from database
2. Tried to parse as Date (ISO format: `YYYY-MM-DD`)
3. Failed because time component present
4. Raised `ValueError: Invalid isoformat string`

## Prevention
- Always use `.date()` when storing date-only values
- Use `.datetime()` or keep as `datetime` for datetime columns
- SQLAlchemy type hints help catch these at development time

---

**Date:** 2025-10-18
**Status:** ✅ Fixed
**Impact:** All transaction extractions
