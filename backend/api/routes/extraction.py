from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pathlib import Path
from typing import List
import logging

from models.base import get_db
from models.pdf import PDF
from models.transaction import Transaction
from schemas.transaction import TransactionResponse, TransactionListResponse
from services.extraction_service import extraction_service, ExtractionError
from services.deduplication_service import deduplication_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/extract", tags=["extraction"])


@router.post("/pdf/{pdf_id}", response_model=TransactionListResponse)
async def extract_pdf_transactions(
    pdf_id: str,
    db: Session = Depends(get_db)
):
    """
    Extract transactions from an uploaded PDF.

    Automatically detects PDF type (CAR or receipt) and applies appropriate
    extraction logic with regex patterns.

    Args:
        pdf_id: UUID of uploaded PDF

    Returns:
        TransactionListResponse with all extracted transactions

    Raises:
        HTTPException: If PDF not found (404) or extraction fails (500)
    """
    # Get PDF record
    pdf_record = db.query(PDF).filter(PDF.id == pdf_id).first()
    if not pdf_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF with id {pdf_id} not found"
        )

    # Check if already extracted
    existing_count = db.query(Transaction).filter(Transaction.pdf_id == pdf_id).count()
    if existing_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transactions already extracted for this PDF. Found {existing_count} existing transactions."
        )

    # Extract transactions
    try:
        pdf_path = Path(pdf_record.file_path)
        if not pdf_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="PDF file not found on disk"
            )

        extracted = extraction_service.extract_transactions(
            pdf_path,
            pdf_record.pdf_type
        )

        # Save to database with deduplication
        transaction_records = []
        duplicate_count = 0
        duplicates_info = []

        for trans in extracted:
            # Calculate fingerprint
            trans_data = {
                'date': trans.date,  # Already a date object from extraction service
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
                logger.info(f"Skipping duplicate transaction: {fingerprint[:16]}...")
                continue  # Skip inserting duplicate

            # Create transaction with fingerprint
            transaction = Transaction(
                pdf_id=pdf_id,
                transaction_type=trans.transaction_type,
                date=trans.date,  # Already a date object from extraction service
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

        # Refresh to get IDs and timestamps
        for transaction in transaction_records:
            db.refresh(transaction)

        # Get counts
        car_count = sum(1 for t in transaction_records if t.transaction_type == 'car')
        receipt_count = sum(1 for t in transaction_records if t.transaction_type == 'receipt')

        # Log duplicate info
        if duplicate_count > 0:
            logger.warning(
                f"Extracted {len(transaction_records)} transactions, "
                f"skipped {duplicate_count} duplicates from PDF {pdf_id}"
            )

        return TransactionListResponse(
            transactions=[TransactionResponse.model_validate(t) for t in transaction_records],
            total_count=len(transaction_records),
            car_count=car_count,
            receipt_count=receipt_count,
            unmatched_count=len(transaction_records)  # All unmatched initially
        )

    except ExtractionError as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Extraction error for PDF {pdf_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "extraction_error",
                "message": str(e),
                "details": None
            }
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error during extraction for PDF {pdf_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "message": "An unexpected error occurred during extraction.",
                "details": str(e)
            }
        )


@router.get("/transactions", response_model=TransactionListResponse)
async def get_all_transactions(
    pdf_id: str = None,
    transaction_type: str = None,
    unmatched_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all extracted transactions with optional filtering.

    Args:
        pdf_id: Filter by PDF ID (optional)
        transaction_type: Filter by type 'car' or 'receipt' (optional)
        unmatched_only: Only return unmatched transactions (optional)

    Returns:
        TransactionListResponse with filtered transactions
    """
    query = db.query(Transaction)

    if pdf_id:
        query = query.filter(Transaction.pdf_id == pdf_id)

    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)

    if unmatched_only:
        query = query.filter(Transaction.is_matched == False)

    transactions = query.order_by(Transaction.date, Transaction.created_at).all()

    # Calculate counts
    car_count = sum(1 for t in transactions if t.transaction_type == 'car')
    receipt_count = sum(1 for t in transactions if t.transaction_type == 'receipt')
    unmatched_count = sum(1 for t in transactions if not t.is_matched)

    return TransactionListResponse(
        transactions=[TransactionResponse.model_validate(t) for t in transactions],
        total_count=len(transactions),
        car_count=car_count,
        receipt_count=receipt_count,
        unmatched_count=unmatched_count
    )


@router.delete("/transactions/{transaction_id}")
async def delete_transaction(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a transaction.

    Args:
        transaction_id: UUID of transaction to delete

    Returns:
        Success message

    Raises:
        HTTPException: If transaction not found (404) or already matched (400)
    """
    transaction = db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with id {transaction_id} not found"
        )

    if transaction.is_matched:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete matched transaction. Delete the match first."
        )

    db.delete(transaction)
    db.commit()

    return {"message": "Transaction deleted successfully", "transaction_id": transaction_id}


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
