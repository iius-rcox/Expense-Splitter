# Upload Error Handling - Production-Ready Implementation

## Overview

The `upload.py` endpoint has been completely refactored with enterprise-grade error handling following industry best practices.

## Key Improvements

### 1. ✅ Consistent, Structured Error Responses

**Before:**
```json
{
  "detail": {
    "error": "validation_error",
    "message": "Error text",
    "details": null
  }
}
```

**After:**
```json
{
  "error": "pdf_validation_failed",
  "message": "Upload failed: PDF is password-protected",
  "status_code": 422,
  "timestamp": "2025-10-18T18:00:00.000Z",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "context": {
    "filename": "report.pdf"
  },
  "actions": [
    {
      "action": "verify_pdf",
      "description": "Ensure the PDF is not corrupted or password-protected"
    }
  ],
  "developer_detail": "Technical details for debugging"
}
```

**Benefits:**
- Clients can reliably parse and react to errors
- Consistent schema across all error types
- Machine-readable error types
- Timestamps for debugging

---

### 2. ✅ Differentiated Error Types

**HTTP Status Codes:**
- **422 Unprocessable Entity** - Validation failures (file type, format, corrupted PDF)
- **409 Conflict** - Duplicate PDF detected
- **503 Service Unavailable** - Database connectivity issues (retryable)
- **500 Internal Server Error** - Unexpected server errors

**Before:** Everything returned 400 or 500
**After:** Specific status codes for specific error types

---

### 3. ✅ Actionable Next Steps

Every error includes suggested actions for the client:

**Duplicate PDF (409):**
```json
{
  "actions": [
    {
      "action": "view_transactions",
      "description": "View existing transactions from this PDF",
      "endpoint": "/api/extract/transactions?pdf_id=abc123",
      "method": "GET"
    },
    {
      "action": "force_reextract",
      "description": "Delete existing data and re-extract transactions",
      "endpoint": "/api/extract/force/abc123",
      "method": "POST",
      "warning": "This will permanently delete existing unmatched transactions"
    }
  ]
}
```

**Validation Error (422):**
```json
{
  "actions": [
    {
      "action": "verify_pdf",
      "description": "Ensure the PDF is not corrupted or password-protected"
    },
    {
      "action": "check_requirements",
      "description": "Verify PDF meets requirements (max 300MB, 1-1500 pages, contains text)"
    }
  ]
}
```

---

### 4. ✅ Comprehensive Logging with Context

**Structured Logging:**
```python
log_context = {
    "error_type": "duplicate_pdf",
    "correlation_id": "a1b2c3d4-...",
    "timestamp": "2025-10-18T18:00:00.000Z",
    "filename": "report.pdf",
    "file_hash": "65373db6e8f4e113...",  # Truncated for privacy
    "pdf_type": "car",
    "exception_type": "IntegrityError",
    "exception_message": "..."
}
```

**Log Levels:**
- `INFO`: Successful operations
- `WARNING`: Duplicate detections, graceful degradations
- `ERROR`: Failures with full context

**Example:**
```
[a1b2c3d4-...] CAR upload started | filename=report.pdf
[a1b2c3d4-...] File validated | filename=report.pdf pages=45 size=2048576bytes hash=65373db6e8f4e113...
[a1b2c3d4-...] Duplicate PDF detected | original_id=5e19aad2-... original_filename=report_copy.pdf transactions=127
```

---

### 5. ✅ Request Correlation IDs

Every request gets a unique UUID for distributed tracing:

```python
correlation_id = str(uuid.uuid4())
# Include in all logs and error responses
```

**Benefits:**
- Track requests across logs
- Debug issues by correlation ID
- Support can reference specific requests

---

### 6. ✅ Early Validation (Before DB Operations)

**Validation Order:**
1. ✅ Check filename exists
2. ✅ Validate .pdf extension
3. ✅ Verify pdf_type is valid
4. ✅ Check content type (warning if unexpected)
5. Then proceed with file processing

**Benefits:**
- Fail fast for obvious errors
- Reduce wasted DB queries
- More specific error messages

---

### 7. ✅ User-Friendly vs Developer Messages

**Separation of Concerns:**

```json
{
  "message": "Upload failed: Database is temporarily unavailable. Please try again in a moment.",
  "developer_detail": "OperationalError: (2002, \"Can't connect to MySQL server on 'localhost' (10061)\")"
}
```

- **User message**: Clear, actionable, non-technical
- **Developer detail**: Full technical context for debugging

---

### 8. ✅ Specific Exception Handling

**Database Errors:**
- `OperationalError` → 503 Service Unavailable (retryable)
- `IntegrityError` → 409 Conflict (duplicate race condition)
- `SQLAlchemyError` → 500 Internal Server Error (unexpected DB issue)

**Validation Errors:**
- `ServicePDFValidationError` → 422 Unprocessable Entity

**With automatic rollback and cleanup on failure.**

---

### 9. ✅ Graceful Degradation

**Example: Transaction Count Failure**
```python
try:
    transaction_count = db.query(Transaction).filter(...).count()
except SQLAlchemyError as count_error:
    logger.warning(f"Failed to count transactions: {count_error}")
    transaction_count = 0  # Graceful degradation
```

**Benefits:**
- Partial failures don't block the entire operation
- Still provide useful error information
- System remains operational

---

### 10. ✅ Robust Cleanup

**File Cleanup on Errors:**
```python
# Cleanup uploaded file if it exists
if file_path:
    try:
        pdf_service.delete_file(file_path)
    except Exception as cleanup_error:
        logger.error(f"[{correlation_id}] Cleanup failed: {cleanup_error}")
```

**Database Rollback:**
```python
except IntegrityError as integrity_error:
    db.rollback()  # Explicit rollback
    # ... cleanup and error response
```

---

## Error Response Examples

### 1. Invalid File Type (422)
```json
{
  "error": "invalid_file_type",
  "message": "Upload failed: 'document.docx' is not a PDF file. Only .pdf files are accepted.",
  "status_code": 422,
  "timestamp": "2025-10-18T18:00:00.000Z",
  "correlation_id": "a1b2c3d4-...",
  "context": {
    "filename": "document.docx",
    "expected_extension": ".pdf"
  },
  "actions": [
    {
      "action": "convert_to_pdf",
      "description": "Convert your file to PDF format and try again"
    }
  ]
}
```

### 2. Duplicate PDF (409)
```json
{
  "error": "duplicate_pdf",
  "message": "This PDF has already been uploaded as 'report_2024.pdf'.",
  "status_code": 409,
  "timestamp": "2025-10-18T18:00:00.000Z",
  "correlation_id": "b2c3d4e5-...",
  "context": {
    "duplicate_pdf": {
      "pdf_id": "5e19aad2-...",
      "filename": "report_2024.pdf",
      "uploaded_at": "2025-10-15T10:30:00.000Z",
      "transaction_count": 127,
      "pdf_type": "car"
    },
    "uploaded_filename": "report_duplicate.pdf"
  },
  "actions": [
    {
      "action": "view_transactions",
      "description": "View existing transactions from this PDF",
      "endpoint": "/api/extract/transactions?pdf_id=5e19aad2-...",
      "method": "GET"
    },
    {
      "action": "force_reextract",
      "description": "Delete existing data and re-extract transactions",
      "endpoint": "/api/extract/force/5e19aad2-...",
      "method": "POST",
      "warning": "This will permanently delete existing unmatched transactions"
    },
    {
      "action": "upload_different",
      "description": "Upload a different PDF instead"
    }
  ],
  "developer_detail": "SHA-256 hash match: 65373db6e8f4e1139198d888eabf9c872a41688a31566c91b893d776c5781f45"
}
```

### 3. Database Unavailable (503)
```json
{
  "error": "database_unavailable",
  "message": "Upload failed: Database is temporarily unavailable. Please try again in a moment.",
  "status_code": 503,
  "timestamp": "2025-10-18T18:00:00.000Z",
  "correlation_id": "c3d4e5f6-...",
  "actions": [
    {
      "action": "retry",
      "description": "Retry the upload in a few seconds"
    }
  ],
  "developer_detail": "OperationalError: (2002, \"Can't connect to MySQL server on 'localhost' (10061)\")"
}
```

### 4. Password-Protected PDF (422)
```json
{
  "error": "pdf_validation_failed",
  "message": "Upload failed: PDF is password-protected. Please upload an unencrypted PDF.",
  "status_code": 422,
  "timestamp": "2025-10-18T18:00:00.000Z",
  "correlation_id": "d4e5f6g7-...",
  "context": {
    "filename": "encrypted_report.pdf"
  },
  "actions": [
    {
      "action": "verify_pdf",
      "description": "Ensure the PDF is not corrupted or password-protected"
    },
    {
      "action": "check_requirements",
      "description": "Verify PDF meets requirements (max 300MB, 1-1500 pages, contains text)"
    }
  ],
  "developer_detail": "PDF is password-protected. Please upload an unencrypted PDF."
}
```

---

## Monitoring & Observability

### Log Format
All errors are logged with structured context:
```
ERROR:api.routes.upload:PDF validation failed | Context: {
  'error_type': 'pdf_validation_failed',
  'correlation_id': 'a1b2c3d4-...',
  'timestamp': '2025-10-18T18:00:00.000Z',
  'filename': 'report.pdf',
  'pdf_type': 'car',
  'exception_type': 'PDFValidationError',
  'exception_message': 'PDF is password-protected...'
}
```

### Correlation ID Tracking
```
[a1b2c3d4-...] CAR upload started | filename=report.pdf
[a1b2c3d4-...] File validated | filename=report.pdf pages=45 size=2048576bytes
[a1b2c3d4-...] CAR PDF saved successfully | pdf_id=5e19aad2-... filename=report.pdf
```

---

## Production Readiness Checklist

- ✅ Consistent error response schema
- ✅ Differentiated HTTP status codes (422, 409, 503, 500)
- ✅ Actionable error messages with next steps
- ✅ Correlation IDs for distributed tracing
- ✅ Structured logging with context
- ✅ Early validation before DB operations
- ✅ User-friendly vs developer messages
- ✅ Specific exception handling (DB, validation, etc.)
- ✅ Graceful degradation on partial failures
- ✅ Robust cleanup (files and DB transactions)
- ✅ Request-level tracing
- ✅ Privacy-aware logging (truncated hashes)
- ✅ Retry guidance for transient errors

---

## Future Enhancements

### 1. Circuit Breaker Pattern
Prevent cascading failures when DB is down:
```python
if db_failure_count > threshold:
    return 503 immediately without attempting DB call
```

### 2. Retry Logic
Implement automatic retries for transient errors:
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential())
async def upload_with_retry():
    ...
```

### 3. Rate Limiting
Prevent abuse with upload rate limits:
```python
@limiter.limit("10/minute")
async def upload_car_pdf():
    ...
```

### 4. Structured JSON Logs
For better log parsing in production:
```python
logger.info(json.dumps({
    "event": "upload_started",
    "correlation_id": correlation_id,
    "filename": filename,
    "timestamp": datetime.utcnow().isoformat()
}))
```

### 5. Metrics & Alerting
Track error rates and alert on anomalies:
```python
metrics.increment('upload.error', tags=['error_type:duplicate_pdf'])
metrics.increment('upload.success')
```

---

## Summary

The new error handling implementation provides:

1. **Better UX**: Clear, actionable error messages
2. **Better DX**: Detailed developer context for debugging
3. **Better Ops**: Structured logs with correlation IDs
4. **Better Reliability**: Graceful degradation and cleanup
5. **Better Scalability**: Specific error types for automated handling

All uploads now follow a consistent, production-ready error handling pattern that makes the API more reliable, debuggable, and user-friendly.
