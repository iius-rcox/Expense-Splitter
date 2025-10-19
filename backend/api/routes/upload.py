"""
Upload endpoint handlers with robust error handling.

Features:
- Consistent structured error responses
- Request correlation IDs for tracing
- Differentiated error types (422, 409, 400, 500)
- Actionable error messages
- Comprehensive logging with context
- Early validation before DB operations
"""

from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from typing import Literal, Dict, Any, Optional, List
import logging
import traceback
import uuid
from datetime import datetime

from models.base import get_db
from models.pdf import PDF
from models.transaction import Transaction
from schemas.pdf import PDFUploadResponse, PDFValidationError
from services.pdf_service import pdf_service, PDFValidationError as ServicePDFValidationError
from services.deduplication_service import deduplication_service

router = APIRouter(prefix="/api/upload", tags=["upload"])
logger = logging.getLogger(__name__)


# ============================================================================
# Error Response Helpers
# ============================================================================

def create_error_response(
    error_type: str,
    user_message: str,
    status_code: int,
    context: Optional[Dict[str, Any]] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    developer_detail: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a consistent, structured error response.

    Args:
        error_type: Machine-readable error type (e.g., 'duplicate_pdf', 'validation_error')
        user_message: Human-friendly message for end users
        status_code: HTTP status code
        context: Additional context about the error (e.g., duplicate PDF details)
        actions: List of actionable next steps for the client
        developer_detail: Technical details for debugging (not shown to end users)
        correlation_id: Request correlation ID for tracing

    Returns:
        Structured error response dictionary
    """
    response = {
        "error": error_type,
        "message": user_message,
        "status_code": status_code,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if correlation_id:
        response["correlation_id"] = correlation_id

    if context:
        response["context"] = context

    if actions:
        response["actions"] = actions

    # Only include developer details in development/debug mode
    if developer_detail:
        response["developer_detail"] = developer_detail

    return response


def log_error_with_context(
    logger: logging.Logger,
    error_type: str,
    message: str,
    correlation_id: str,
    filename: Optional[str] = None,
    file_hash: Optional[str] = None,
    pdf_type: Optional[str] = None,
    exception: Optional[Exception] = None,
    include_traceback: bool = False
):
    """
    Log error with structured context for observability.

    Args:
        logger: Logger instance
        error_type: Error type identifier
        message: Error message
        correlation_id: Request correlation ID
        filename: Upload filename
        file_hash: File SHA-256 hash
        pdf_type: PDF type (car/receipt)
        exception: Exception object if available
        include_traceback: Whether to include full traceback
    """
    log_context = {
        "error_type": error_type,
        "correlation_id": correlation_id,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if filename:
        log_context["filename"] = filename
    if file_hash:
        log_context["file_hash"] = file_hash[:16]  # Truncate for privacy
    if pdf_type:
        log_context["pdf_type"] = pdf_type
    if exception:
        log_context["exception_type"] = type(exception).__name__
        log_context["exception_message"] = str(exception)

    logger.error(f"{message} | Context: {log_context}")

    if include_traceback and exception:
        logger.error(f"Traceback: {traceback.format_exc()}")


# ============================================================================
# Early Validation Helpers
# ============================================================================

def validate_upload_file(file: UploadFile, pdf_type: str) -> Optional[Dict[str, Any]]:
    """
    Perform early validation before processing the file.

    Returns:
        Error response dict if validation fails, None if validation passes
    """
    # Check filename exists
    if not file.filename:
        return create_error_response(
            error_type="missing_filename",
            user_message="Upload failed: filename is required.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            developer_detail="UploadFile.filename is None or empty"
        )

    # Check file extension
    if not file.filename.lower().endswith('.pdf'):
        return create_error_response(
            error_type="invalid_file_type",
            user_message=f"Upload failed: '{file.filename}' is not a PDF file. Only .pdf files are accepted.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            context={"filename": file.filename, "expected_extension": ".pdf"},
            actions=[
                {
                    "action": "convert_to_pdf",
                    "description": "Convert your file to PDF format and try again"
                }
            ]
        )

    # Validate PDF type
    if pdf_type not in ["car", "receipt"]:
        return create_error_response(
            error_type="invalid_pdf_type",
            user_message=f"Upload failed: '{pdf_type}' is not a valid PDF type.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            context={"provided_type": pdf_type, "valid_types": ["car", "receipt"]},
            developer_detail="pdf_type must be 'car' or 'receipt'"
        )

    # Check content type if provided
    if file.content_type and not file.content_type.startswith('application/pdf'):
        logger.warning(f"Unexpected content type: {file.content_type} for file {file.filename}")

    return None  # Validation passed


# ============================================================================
# Upload Handlers
# ============================================================================

@router.post("/car", response_model=PDFUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_car_pdf(
    request: Request,
    file: UploadFile = File(..., description="CAR PDF file"),
    db: Session = Depends(get_db)
):
    """
    Upload Corporate American Express Report (CAR) PDF.

    Features:
    - Early validation of file type and format
    - Duplicate detection via SHA-256 hash (idempotent - returns existing PDF)
    - Structured error responses with actionable next steps
    - Request correlation for distributed tracing
    - Comprehensive logging with context

    Returns:
        PDFUploadResponse: Metadata about uploaded PDF (new or existing)

    Raises:
        HTTPException 422: Validation failed (invalid file type, format)
        HTTPException 400: Bad request (corrupted file, unreadable)
        HTTPException 500: Server error (DB failure, unexpected error)
    """
    # Generate correlation ID for request tracing
    correlation_id = str(uuid.uuid4())

    # Initialize variables for cleanup
    file_path = None
    filename = None
    file_hash = None

    try:
        # ====================
        # 1. EARLY VALIDATION (before any processing)
        # ====================
        validation_error = validate_upload_file(file, pdf_type="car")
        if validation_error:
            validation_error["correlation_id"] = correlation_id
            raise HTTPException(
                status_code=validation_error["status_code"],
                detail=validation_error
            )

        logger.info(
            f"[{correlation_id}] CAR upload started | filename={file.filename}"
        )

        # ====================
        # 2. SAVE & VALIDATE FILE (with hash calculation)
        # ====================
        try:
            file_path, filename, page_count, file_size, file_hash = await pdf_service.save_uploaded_file(
                file, pdf_type="car"
            )

            logger.info(
                f"[{correlation_id}] File validated | "
                f"filename={filename} pages={page_count} size={file_size}bytes hash={file_hash[:16]}..."
            )

        except ServicePDFValidationError as e:
            # Validation error - return 422 Unprocessable Entity
            log_error_with_context(
                logger,
                error_type="pdf_validation_failed",
                message="PDF validation failed",
                correlation_id=correlation_id,
                filename=file.filename,
                pdf_type="car",
                exception=e
            )

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=create_error_response(
                    error_type="pdf_validation_failed",
                    user_message=f"Upload failed: {str(e)}",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    context={"filename": file.filename},
                    actions=[
                        {
                            "action": "verify_pdf",
                            "description": "Ensure the PDF is not corrupted or password-protected"
                        },
                        {
                            "action": "check_requirements",
                            "description": "Verify PDF meets requirements (max 300MB, 1-1500 pages, contains text)"
                        }
                    ],
                    correlation_id=correlation_id,
                    developer_detail=str(e)
                )
            )

        # ====================
        # 3. DUPLICATE DETECTION
        # ====================
        try:
            duplicate_pdf = deduplication_service.check_duplicate_pdf(file_hash, db)

            if duplicate_pdf:
                # Delete newly saved file (it's a duplicate)
                pdf_service.delete_file(file_path)

                # Count existing transactions
                try:
                    transaction_count = db.query(Transaction).filter(
                        Transaction.pdf_id == duplicate_pdf.id
                    ).count()
                except SQLAlchemyError as count_error:
                    logger.warning(
                        f"[{correlation_id}] Failed to count transactions for duplicate: {count_error}"
                    )
                    transaction_count = 0  # Graceful degradation

                # Clear any existing matches for this PDF's transactions
                matches_cleared = 0
                try:
                    from models.transaction import Match

                    # Get all transaction IDs for this PDF
                    transaction_ids = db.query(Transaction.id).filter(
                        Transaction.pdf_id == duplicate_pdf.id
                    ).all()
                    transaction_ids = [t[0] for t in transaction_ids]

                    # Delete matches where either CAR or receipt is from this PDF
                    if transaction_ids:
                        matches_to_delete = db.query(Match).filter(
                            (Match.car_transaction_id.in_(transaction_ids)) |
                            (Match.receipt_transaction_id.in_(transaction_ids))
                        )
                        matches_cleared = matches_to_delete.count()
                        matches_to_delete.delete(synchronize_session=False)

                        # Reset is_matched flag for all transactions
                        db.query(Transaction).filter(
                            Transaction.id.in_(transaction_ids)
                        ).update({"is_matched": False}, synchronize_session=False)

                        db.commit()

                        logger.info(
                            f"[{correlation_id}] Cleared {matches_cleared} matches for duplicate PDF"
                        )
                except Exception as match_error:
                    logger.warning(
                        f"[{correlation_id}] Failed to clear matches: {match_error}"
                    )
                    db.rollback()
                    matches_cleared = 0

                logger.info(
                    f"[{correlation_id}] Duplicate PDF detected, returning existing record | "
                    f"original_id={duplicate_pdf.id} original_filename={duplicate_pdf.filename} "
                    f"transactions={transaction_count} matches_cleared={matches_cleared}"
                )

                # Return existing PDF record with duplicate flag
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

        except OperationalError as db_error:
            # Database connectivity issue during duplicate check
            log_error_with_context(
                logger,
                error_type="database_connection_error",
                message="Database connectivity issue during duplicate check",
                correlation_id=correlation_id,
                filename=filename,
                file_hash=file_hash,
                exception=db_error,
                include_traceback=True
            )

            # Cleanup uploaded file
            if file_path:
                pdf_service.delete_file(file_path)

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=create_error_response(
                    error_type="database_unavailable",
                    user_message="Upload failed: Database is temporarily unavailable. Please try again in a moment.",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    actions=[
                        {
                            "action": "retry",
                            "description": "Retry the upload in a few seconds"
                        }
                    ],
                    correlation_id=correlation_id,
                    developer_detail=f"OperationalError: {str(db_error)}"
                )
            )

        # ====================
        # 4. CREATE DATABASE RECORD
        # ====================
        try:
            pdf_record = PDF(
                filename=filename,
                file_path=str(file_path.absolute()),
                file_hash=file_hash,
                pdf_type="car",
                page_count=page_count,
                file_size_bytes=file_size
            )

            db.add(pdf_record)
            db.commit()
            db.refresh(pdf_record)

            logger.info(
                f"[{correlation_id}] CAR PDF saved successfully | "
                f"pdf_id={pdf_record.id} filename={filename}"
            )

            # Return success response
            return PDFUploadResponse(
                pdf_id=pdf_record.id,
                filename=pdf_record.filename,
                pdf_type=pdf_record.pdf_type,
                page_count=pdf_record.page_count,
                file_size_bytes=pdf_record.file_size_bytes,
                uploaded_at=pdf_record.uploaded_at
            )

        except IntegrityError as integrity_error:
            # Race condition: duplicate was inserted between check and insert
            db.rollback()

            log_error_with_context(
                logger,
                error_type="integrity_error",
                message="Database integrity error (possible race condition)",
                correlation_id=correlation_id,
                filename=filename,
                file_hash=file_hash,
                exception=integrity_error
            )

            # Cleanup uploaded file
            if file_path:
                pdf_service.delete_file(file_path)

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=create_error_response(
                    error_type="duplicate_detected",
                    user_message="This PDF has already been uploaded (detected during save).",
                    status_code=status.HTTP_409_CONFLICT,
                    actions=[
                        {
                            "action": "refresh_list",
                            "description": "Refresh your PDF list to see the existing upload"
                        }
                    ],
                    correlation_id=correlation_id,
                    developer_detail=f"IntegrityError: {str(integrity_error)}"
                )
            )

        except SQLAlchemyError as db_error:
            # Database error during commit
            db.rollback()

            log_error_with_context(
                logger,
                error_type="database_error",
                message="Database error during PDF record creation",
                correlation_id=correlation_id,
                filename=filename,
                file_hash=file_hash,
                exception=db_error,
                include_traceback=True
            )

            # Cleanup uploaded file
            if file_path:
                pdf_service.delete_file(file_path)

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=create_error_response(
                    error_type="database_error",
                    user_message="Upload failed: Unable to save PDF metadata to database.",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    actions=[
                        {
                            "action": "retry",
                            "description": "Try uploading again"
                        },
                        {
                            "action": "contact_support",
                            "description": f"If problem persists, contact support with correlation ID: {correlation_id}"
                        }
                    ],
                    correlation_id=correlation_id,
                    developer_detail=f"SQLAlchemyError: {str(db_error)}"
                )
            )

    except HTTPException:
        # Re-raise HTTP exceptions (already handled)
        raise

    except Exception as e:
        # Unexpected error - catch-all handler
        log_error_with_context(
            logger,
            error_type="unexpected_error",
            message="Unexpected error during CAR upload",
            correlation_id=correlation_id,
            filename=filename,
            file_hash=file_hash,
            pdf_type="car",
            exception=e,
            include_traceback=True
        )

        # Cleanup uploaded file if it exists
        if file_path:
            try:
                pdf_service.delete_file(file_path)
            except Exception as cleanup_error:
                logger.error(f"[{correlation_id}] Cleanup failed: {cleanup_error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                error_type="unexpected_error",
                user_message="An unexpected error occurred during upload. The file was not saved.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                actions=[
                    {
                        "action": "retry",
                        "description": "Try uploading again"
                    },
                    {
                        "action": "contact_support",
                        "description": f"If problem persists, contact support with correlation ID: {correlation_id}"
                    }
                ],
                correlation_id=correlation_id,
                developer_detail=f"{type(e).__name__}: {str(e)}"
            )
        )


@router.post("/receipt", response_model=PDFUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_receipt_pdf(
    request: Request,
    file: UploadFile = File(..., description="Receipt PDF file"),
    db: Session = Depends(get_db)
):
    """
    Upload receipt collection PDF.

    Features:
    - Early validation of file type and format
    - Duplicate detection via SHA-256 hash (idempotent - returns existing PDF)
    - Structured error responses with actionable next steps
    - Request correlation for distributed tracing
    - Comprehensive logging with context

    Returns:
        PDFUploadResponse: Metadata about uploaded PDF (new or existing)

    Raises:
        HTTPException 422: Validation failed (invalid file type, format)
        HTTPException 400: Bad request (corrupted file, unreadable)
        HTTPException 500: Server error (DB failure, unexpected error)
    """
    # Generate correlation ID for request tracing
    correlation_id = str(uuid.uuid4())

    # Initialize variables for cleanup
    file_path = None
    filename = None
    file_hash = None

    try:
        # ====================
        # 1. EARLY VALIDATION (before any processing)
        # ====================
        validation_error = validate_upload_file(file, pdf_type="receipt")
        if validation_error:
            validation_error["correlation_id"] = correlation_id
            raise HTTPException(
                status_code=validation_error["status_code"],
                detail=validation_error
            )

        logger.info(
            f"[{correlation_id}] Receipt upload started | filename={file.filename}"
        )

        # ====================
        # 2. SAVE & VALIDATE FILE (with hash calculation)
        # ====================
        try:
            file_path, filename, page_count, file_size, file_hash = await pdf_service.save_uploaded_file(
                file, pdf_type="receipt"
            )

            logger.info(
                f"[{correlation_id}] File validated | "
                f"filename={filename} pages={page_count} size={file_size}bytes hash={file_hash[:16]}..."
            )

        except ServicePDFValidationError as e:
            # Validation error - return 422 Unprocessable Entity
            log_error_with_context(
                logger,
                error_type="pdf_validation_failed",
                message="PDF validation failed",
                correlation_id=correlation_id,
                filename=file.filename,
                pdf_type="receipt",
                exception=e
            )

            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=create_error_response(
                    error_type="pdf_validation_failed",
                    user_message=f"Upload failed: {str(e)}",
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    context={"filename": file.filename},
                    actions=[
                        {
                            "action": "verify_pdf",
                            "description": "Ensure the PDF is not corrupted or password-protected"
                        },
                        {
                            "action": "check_requirements",
                            "description": "Verify PDF meets requirements (max 300MB, 1-1500 pages, contains text)"
                        }
                    ],
                    correlation_id=correlation_id,
                    developer_detail=str(e)
                )
            )

        # ====================
        # 3. DUPLICATE DETECTION
        # ====================
        try:
            duplicate_pdf = deduplication_service.check_duplicate_pdf(file_hash, db)

            if duplicate_pdf:
                # Delete newly saved file (it's a duplicate)
                pdf_service.delete_file(file_path)

                # Count existing transactions
                try:
                    transaction_count = db.query(Transaction).filter(
                        Transaction.pdf_id == duplicate_pdf.id
                    ).count()
                except SQLAlchemyError as count_error:
                    logger.warning(
                        f"[{correlation_id}] Failed to count transactions for duplicate: {count_error}"
                    )
                    transaction_count = 0  # Graceful degradation

                # Clear any existing matches for this PDF's transactions
                matches_cleared = 0
                try:
                    from models.transaction import Match

                    # Get all transaction IDs for this PDF
                    transaction_ids = db.query(Transaction.id).filter(
                        Transaction.pdf_id == duplicate_pdf.id
                    ).all()
                    transaction_ids = [t[0] for t in transaction_ids]

                    # Delete matches where either CAR or receipt is from this PDF
                    if transaction_ids:
                        matches_to_delete = db.query(Match).filter(
                            (Match.car_transaction_id.in_(transaction_ids)) |
                            (Match.receipt_transaction_id.in_(transaction_ids))
                        )
                        matches_cleared = matches_to_delete.count()
                        matches_to_delete.delete(synchronize_session=False)

                        # Reset is_matched flag for all transactions
                        db.query(Transaction).filter(
                            Transaction.id.in_(transaction_ids)
                        ).update({"is_matched": False}, synchronize_session=False)

                        db.commit()

                        logger.info(
                            f"[{correlation_id}] Cleared {matches_cleared} matches for duplicate PDF"
                        )
                except Exception as match_error:
                    logger.warning(
                        f"[{correlation_id}] Failed to clear matches: {match_error}"
                    )
                    db.rollback()
                    matches_cleared = 0

                logger.info(
                    f"[{correlation_id}] Duplicate PDF detected, returning existing record | "
                    f"original_id={duplicate_pdf.id} original_filename={duplicate_pdf.filename} "
                    f"transactions={transaction_count} matches_cleared={matches_cleared}"
                )

                # Return existing PDF record with duplicate flag
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

        except OperationalError as db_error:
            # Database connectivity issue during duplicate check
            log_error_with_context(
                logger,
                error_type="database_connection_error",
                message="Database connectivity issue during duplicate check",
                correlation_id=correlation_id,
                filename=filename,
                file_hash=file_hash,
                exception=db_error,
                include_traceback=True
            )

            # Cleanup uploaded file
            if file_path:
                pdf_service.delete_file(file_path)

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=create_error_response(
                    error_type="database_unavailable",
                    user_message="Upload failed: Database is temporarily unavailable. Please try again in a moment.",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    actions=[
                        {
                            "action": "retry",
                            "description": "Retry the upload in a few seconds"
                        }
                    ],
                    correlation_id=correlation_id,
                    developer_detail=f"OperationalError: {str(db_error)}"
                )
            )

        # ====================
        # 4. CREATE DATABASE RECORD
        # ====================
        try:
            pdf_record = PDF(
                filename=filename,
                file_path=str(file_path.absolute()),
                file_hash=file_hash,
                pdf_type="receipt",
                page_count=page_count,
                file_size_bytes=file_size
            )

            db.add(pdf_record)
            db.commit()
            db.refresh(pdf_record)

            logger.info(
                f"[{correlation_id}] Receipt PDF saved successfully | "
                f"pdf_id={pdf_record.id} filename={filename}"
            )

            # Return success response
            return PDFUploadResponse(
                pdf_id=pdf_record.id,
                filename=pdf_record.filename,
                pdf_type=pdf_record.pdf_type,
                page_count=pdf_record.page_count,
                file_size_bytes=pdf_record.file_size_bytes,
                uploaded_at=pdf_record.uploaded_at
            )

        except IntegrityError as integrity_error:
            # Race condition: duplicate was inserted between check and insert
            db.rollback()

            log_error_with_context(
                logger,
                error_type="integrity_error",
                message="Database integrity error (possible race condition)",
                correlation_id=correlation_id,
                filename=filename,
                file_hash=file_hash,
                exception=integrity_error
            )

            # Cleanup uploaded file
            if file_path:
                pdf_service.delete_file(file_path)

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=create_error_response(
                    error_type="duplicate_detected",
                    user_message="This PDF has already been uploaded (detected during save).",
                    status_code=status.HTTP_409_CONFLICT,
                    actions=[
                        {
                            "action": "refresh_list",
                            "description": "Refresh your PDF list to see the existing upload"
                        }
                    ],
                    correlation_id=correlation_id,
                    developer_detail=f"IntegrityError: {str(integrity_error)}"
                )
            )

        except SQLAlchemyError as db_error:
            # Database error during commit
            db.rollback()

            log_error_with_context(
                logger,
                error_type="database_error",
                message="Database error during PDF record creation",
                correlation_id=correlation_id,
                filename=filename,
                file_hash=file_hash,
                exception=db_error,
                include_traceback=True
            )

            # Cleanup uploaded file
            if file_path:
                pdf_service.delete_file(file_path)

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=create_error_response(
                    error_type="database_error",
                    user_message="Upload failed: Unable to save PDF metadata to database.",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    actions=[
                        {
                            "action": "retry",
                            "description": "Try uploading again"
                        },
                        {
                            "action": "contact_support",
                            "description": f"If problem persists, contact support with correlation ID: {correlation_id}"
                        }
                    ],
                    correlation_id=correlation_id,
                    developer_detail=f"SQLAlchemyError: {str(db_error)}"
                )
            )

    except HTTPException:
        # Re-raise HTTP exceptions (already handled)
        raise

    except Exception as e:
        # Unexpected error - catch-all handler
        log_error_with_context(
            logger,
            error_type="unexpected_error",
            message="Unexpected error during receipt upload",
            correlation_id=correlation_id,
            filename=filename,
            file_hash=file_hash,
            pdf_type="receipt",
            exception=e,
            include_traceback=True
        )

        # Cleanup uploaded file if it exists
        if file_path:
            try:
                pdf_service.delete_file(file_path)
            except Exception as cleanup_error:
                logger.error(f"[{correlation_id}] Cleanup failed: {cleanup_error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(
                error_type="unexpected_error",
                user_message="An unexpected error occurred during upload. The file was not saved.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                actions=[
                    {
                        "action": "retry",
                        "description": "Try uploading again"
                    },
                    {
                        "action": "contact_support",
                        "description": f"If problem persists, contact support with correlation ID: {correlation_id}"
                    }
                ],
                correlation_id=correlation_id,
                developer_detail=f"{type(e).__name__}: {str(e)}"
            )
        )
