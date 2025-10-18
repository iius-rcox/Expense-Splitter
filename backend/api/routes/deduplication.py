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
