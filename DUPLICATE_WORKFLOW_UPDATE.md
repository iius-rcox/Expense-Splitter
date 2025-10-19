# Duplicate Upload Workflow Update

## Summary
Implemented intelligent duplicate detection that clears previous matches and auto-navigates to the matching screen when users re-upload the same PDFs.

## Problem
When users uploaded the same PDF twice:
- ❌ Previously: Threw 409 Conflict error (bad UX)
- ❌ First fix: Returned existing record (incomplete solution)
- ✅ Final: Clear matches and navigate to matching screen

## Solution

### Backend Changes

#### 1. Enhanced Response Schema (`backend/schemas/pdf.py`)
Added three new fields to `PDFUploadResponse`:

```python
class PDFUploadResponse(BaseModel):
    pdf_id: str
    filename: str
    pdf_type: Literal["car", "receipt"]
    page_count: int
    file_size_bytes: int
    uploaded_at: datetime
    is_duplicate: bool = Field(default=False)
    transaction_count: int = Field(default=0)
    matches_cleared: int = Field(default=0)
```

#### 2. Match Clearing Logic (`backend/api/routes/upload.py`)
When duplicate PDF detected:

```python
# 1. Count existing transactions
transaction_count = db.query(Transaction).filter(
    Transaction.pdf_id == duplicate_pdf.id
).count()

# 2. Get all transaction IDs for this PDF
transaction_ids = db.query(Transaction.id).filter(
    Transaction.pdf_id == duplicate_pdf.id
).all()

# 3. Delete matches involving these transactions
matches_to_delete = db.query(Match).filter(
    (Match.car_transaction_id.in_(transaction_ids)) |
    (Match.receipt_transaction_id.in_(transaction_ids))
)
matches_cleared = matches_to_delete.count()
matches_to_delete.delete(synchronize_session=False)

# 4. Reset is_matched flags
db.query(Transaction).filter(
    Transaction.id.in_(transaction_ids)
).update({"is_matched": False}, synchronize_session=False)

# 5. Return response with duplicate metadata
return PDFUploadResponse(
    pdf_id=duplicate_pdf.id,
    filename=duplicate_pdf.filename,
    pdf_type=duplicate_pdf.pdf_type,
    page_count=duplicate_pdf.page_count,
    file_size_bytes=duplicate_pdf.file_size_bytes,
    uploaded_at=duplicate_pdf.uploaded_at,
    is_duplicate=True,
    transaction_count=transaction_count,
    matches_cleared=matches_cleared
)
```

### Frontend Changes

#### 1. TypeScript Interface (`frontend/src/features/upload/types/upload.ts`)
Added optional fields to match backend response:

```typescript
export interface PDFUploadResponse {
  pdf_id: string;
  filename: string;
  pdf_type: PDFType;
  page_count: number;
  file_size_bytes: number;
  uploaded_at: string;
  is_duplicate?: boolean;
  transaction_count?: number;
  matches_cleared?: number;
}
```

#### 2. Auto-Navigation Logic (`frontend/src/pages/UploadPage.tsx`)
Detects duplicates and navigates automatically:

```typescript
const handleCarUpload = (file: File) => {
  carMutation.mutate(file, {
    onSuccess: (data) => {
      setCarUpload(data);

      // If duplicate upload and both PDFs ready, go directly to matching
      if (data.is_duplicate && receiptUpload) {
        navigate('/matching');
      }
    },
  });
};

const handleReceiptUpload = (file: File) => {
  receiptMutation.mutate(file, {
    onSuccess: (data) => {
      setReceiptUpload(data);

      // If duplicate upload and both PDFs ready, go directly to matching
      if (data.is_duplicate && carUpload) {
        navigate('/matching');
      }
    },
  });
};
```

## Workflow

### Normal Upload Flow
1. User uploads CAR PDF → Returns `is_duplicate: false`
2. User uploads receipt PDF → Returns `is_duplicate: false`
3. User clicks "Extract Transactions" → Extracts data
4. Navigate to matching page

### Duplicate Upload Flow
1. User uploads CAR PDF (already uploaded) → Returns `is_duplicate: true`
   - Backend clears all matches involving this PDF's transactions
   - Backend resets `is_matched` flags to `false`
   - Returns count of transactions and matches cleared
2. If receipt PDF also uploaded → **Auto-navigate to matching page**
3. User can immediately run matching algorithm on fresh data

## Benefits

✅ **No More Errors**: Users never see 409 Conflict errors
✅ **Smart Detection**: SHA-256 hash-based duplicate detection
✅ **Automatic Cleanup**: Previous matches cleared automatically
✅ **Skip Extraction**: Duplicate PDFs already have extracted transactions
✅ **Seamless UX**: Auto-navigation to matching screen
✅ **Re-matching Enabled**: Reset flags allow running matching again

## Technical Details

### SHA-256 Deduplication
```python
# In PDFService
pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
duplicate_pdf = db.query(PDF).filter(
    PDF.pdf_hash == pdf_hash,
    PDF.pdf_type == pdf_type
).first()
```

### Match Cascade Deletion
Uses SQLAlchemy `OR` filter to find matches where either transaction is from duplicate PDF:

```python
db.query(Match).filter(
    (Match.car_transaction_id.in_(transaction_ids)) |
    (Match.receipt_transaction_id.in_(transaction_ids))
).delete()
```

### Transaction Flag Reset
Ensures transactions can be re-matched:

```python
db.query(Transaction).filter(
    Transaction.id.in_(transaction_ids)
).update({"is_matched": False})
```

## Files Modified

### Backend
- `backend/schemas/pdf.py` - Added response fields
- `backend/api/routes/upload.py` - Implemented match clearing logic (both endpoints)

### Frontend
- `frontend/src/features/upload/types/upload.ts` - Updated TypeScript interface
- `frontend/src/pages/UploadPage.tsx` - Added auto-navigation logic

## Example Response

### Duplicate Upload Response
```json
{
  "pdf_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "car_2025_10.pdf",
  "pdf_type": "car",
  "page_count": 15,
  "file_size_bytes": 1048576,
  "uploaded_at": "2025-10-16T10:30:00Z",
  "is_duplicate": true,
  "transaction_count": 240,
  "matches_cleared": 185
}
```

## Testing Scenarios

1. **Upload same CAR PDF twice**
   - ✅ Should return existing PDF with is_duplicate=true
   - ✅ Should clear matches involving CAR transactions
   - ✅ Should reset is_matched flags

2. **Upload CAR + receipt, then re-upload CAR**
   - ✅ Should clear all matches
   - ✅ Should auto-navigate to matching page
   - ✅ Both PDFs ready to re-match

3. **Upload receipt, then re-upload receipt, then upload CAR**
   - ✅ Auto-navigate when CAR uploaded (both ready)
   - ✅ All transactions available for matching

---

**Date:** 2025-10-18
**Status:** ✅ Complete
**Feature:** Intelligent Duplicate Upload Handling
