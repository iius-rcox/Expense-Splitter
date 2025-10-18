from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Literal

from models.base import get_db
from models.pdf import PDF
from models.transaction import Transaction
from schemas.pdf import PDFUploadResponse, PDFValidationError
from services.pdf_service import pdf_service, PDFValidationError as ServicePDFValidationError
from services.deduplication_service import deduplication_service

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/car", response_model=PDFUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_car_pdf(
    file: UploadFile = File(..., description="CAR PDF file"),
    db: Session = Depends(get_db)
):
    """
    Upload Corporate American Express Report (CAR) PDF.

    Validates PDF format, size, and text extractability before saving.

    Returns:
        PDFUploadResponse with metadata about uploaded PDF

    Raises:
        HTTPException: If validation fails (400) or server error (500)
    """
    try:
        # Save and validate file (now includes hash)
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

        # Return response
        return PDFUploadResponse(
            pdf_id=pdf_record.id,
            filename=pdf_record.filename,
            pdf_type=pdf_record.pdf_type,
            page_count=pdf_record.page_count,
            file_size_bytes=pdf_record.file_size_bytes,
            uploaded_at=pdf_record.uploaded_at
        )

    except ServicePDFValidationError as e:
        # Validation error - return 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": str(e),
                "details": None
            }
        )
    except Exception as e:
        # Unexpected error - cleanup and return 500
        if 'file_path' in locals():
            pdf_service.delete_file(file_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "message": "An unexpected error occurred during upload.",
                "details": str(e)
            }
        )


@router.post("/receipt", response_model=PDFUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_receipt_pdf(
    file: UploadFile = File(..., description="Receipt PDF file"),
    db: Session = Depends(get_db)
):
    """
    Upload receipt collection PDF.

    Validates PDF format, size, and text extractability before saving.

    Returns:
        PDFUploadResponse with metadata about uploaded PDF

    Raises:
        HTTPException: If validation fails (400) or server error (500)
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Received receipt upload: {file.filename}")

        # Save and validate file (now includes hash)
        file_path, filename, page_count, file_size, file_hash = await pdf_service.save_uploaded_file(
            file, pdf_type="receipt"
        )

        logger.info(f"Receipt validation passed: {filename}, {page_count} pages, {file_size} bytes")

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
            pdf_type="receipt",
            page_count=page_count,
            file_size_bytes=file_size
        )

        db.add(pdf_record)
        db.commit()
        db.refresh(pdf_record)

        logger.info(f"Receipt PDF saved to database: {pdf_record.id}")

        # Return response
        return PDFUploadResponse(
            pdf_id=pdf_record.id,
            filename=pdf_record.filename,
            pdf_type=pdf_record.pdf_type,
            page_count=pdf_record.page_count,
            file_size_bytes=pdf_record.file_size_bytes,
            uploaded_at=pdf_record.uploaded_at
        )

    except ServicePDFValidationError as e:
        # Validation error - return 400
        logger.error(f"Receipt validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "validation_error",
                "message": str(e),
                "details": None
            }
        )
    except Exception as e:
        # Unexpected error - cleanup and return 500
        logger.error(f"Unexpected error during receipt upload: {str(e)}", exc_info=True)
        if 'file_path' in locals():
            pdf_service.delete_file(file_path)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "message": "An unexpected error occurred during upload.",
                "details": str(e)
            }
        )
