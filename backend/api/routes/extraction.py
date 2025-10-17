from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pathlib import Path
from typing import List

from models.base import get_db
from models.pdf import PDF
from models.transaction import Transaction
from schemas.transaction import TransactionResponse, TransactionListResponse
from services.extraction_service import extraction_service, ExtractionError

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

        # Save to database
        transaction_records = []
        for trans in extracted:
            transaction = Transaction(
                pdf_id=pdf_id,
                transaction_type=trans.transaction_type,
                date=trans.date,
                amount=trans.amount,
                employee_id=trans.employee_id,
                employee_name=trans.employee_name,
                merchant=trans.merchant,
                card_number=trans.card_number,
                receipt_id=trans.receipt_id,
                page_number=trans.page_number,
                raw_text=trans.raw_text,
                extraction_confidence=trans.extraction_confidence
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
