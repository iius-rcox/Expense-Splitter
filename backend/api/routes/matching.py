from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from models.base import get_db
from models.transaction import Transaction, Match
from schemas.transaction import MatchListResponse, MatchWithTransactionsResponse, MatchUpdate
from services.matching_service import matching_service

router = APIRouter(prefix="/api/match", tags=["matching"])


@router.post("/run", response_model=MatchListResponse)
async def run_matching(
    min_confidence: Optional[float] = Query(0.70, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """
    Run matching algorithm on all unmatched transactions.

    Finds matches between CAR and receipt transactions using weighted scoring:
    - Date proximity (30%)
    - Exact amount (30%)
    - Employee ID match (25%)
    - Fuzzy merchant match (15%)

    Args:
        min_confidence: Minimum confidence threshold (default: 0.70)

    Returns:
        MatchListResponse with all created matches

    Raises:
        HTTPException: If insufficient transactions found (400) or error (500)
    """
    # Get unmatched transactions
    car_transactions = db.query(Transaction).filter(
        Transaction.transaction_type == 'car',
        Transaction.is_matched == False
    ).all()

    receipt_transactions = db.query(Transaction).filter(
        Transaction.transaction_type == 'receipt',
        Transaction.is_matched == False
    ).all()

    if not car_transactions or not receipt_transactions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "insufficient_data",
                "message": "Need both CAR and receipt transactions to perform matching",
                "car_count": len(car_transactions),
                "receipt_count": len(receipt_transactions)
            }
        )

    # Convert to dictionaries
    car_dicts = [t.to_dict() for t in car_transactions]
    receipt_dicts = [t.to_dict() for t in receipt_transactions]

    # Run matching algorithm
    try:
        matches = matching_service.find_best_matches(
            car_dicts,
            receipt_dicts,
            min_confidence
        )

        # Save matches to database
        match_records = []
        for match in matches:
            match_record = Match(
                car_transaction_id=match.car_transaction_id,
                receipt_transaction_id=match.receipt_transaction_id,
                confidence_score=match.confidence_score,
                date_score=match.date_score,
                amount_score=match.amount_score,
                employee_score=match.employee_score,
                merchant_score=match.merchant_score,
                status='pending'
            )
            db.add(match_record)
            match_records.append(match_record)

        # Mark transactions as matched
        matched_car_ids = [m.car_transaction_id for m in matches]
        matched_receipt_ids = [m.receipt_transaction_id for m in matches]

        db.query(Transaction).filter(
            Transaction.id.in_(matched_car_ids)
        ).update({Transaction.is_matched: True}, synchronize_session=False)

        db.query(Transaction).filter(
            Transaction.id.in_(matched_receipt_ids)
        ).update({Transaction.is_matched: True}, synchronize_session=False)

        db.commit()

        # Refresh to get IDs and relationships
        for match_record in match_records:
            db.refresh(match_record)

        # Get counts
        pending_count = len([m for m in match_records if m.status == 'pending'])
        approved_count = len([m for m in match_records if m.status == 'approved'])
        exported_count = len([m for m in match_records if m.exported])

        # Build response with full transaction details
        matches_with_transactions = []
        for match_record in match_records:
            matches_with_transactions.append({
                **match_record.to_dict(),
                'car_transaction': match_record.car_transaction.to_dict(),
                'receipt_transaction': match_record.receipt_transaction.to_dict()
            })

        return MatchListResponse(
            matches=[MatchWithTransactionsResponse.model_validate(m) for m in matches_with_transactions],
            total_count=len(match_records),
            pending_count=pending_count,
            approved_count=approved_count,
            exported_count=exported_count
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "matching_error",
                "message": "An error occurred during matching",
                "details": str(e)
            }
        )


@router.get("/matches", response_model=MatchListResponse)
async def get_all_matches(
    status_filter: Optional[str] = Query(None, regex="^(pending|approved|rejected|exported)$"),
    exported_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all matches with optional filtering.

    Args:
        status_filter: Filter by status (pending/approved/rejected/exported)
        exported_only: Only return exported matches

    Returns:
        MatchListResponse with filtered matches
    """
    query = db.query(Match)

    if status_filter:
        query = query.filter(Match.status == status_filter)

    if exported_only:
        query = query.filter(Match.exported == True)

    matches = query.order_by(Match.confidence_score.desc()).all()

    # Get counts
    pending_count = len([m for m in matches if m.status == 'pending'])
    approved_count = len([m for m in matches if m.status == 'approved'])
    exported_count = len([m for m in matches if m.exported])

    # Build response with full transaction details
    matches_with_transactions = []
    for match_record in matches:
        matches_with_transactions.append({
            **match_record.to_dict(),
            'car_transaction': match_record.car_transaction.to_dict(),
            'receipt_transaction': match_record.receipt_transaction.to_dict()
        })

    return MatchListResponse(
        matches=[MatchWithTransactionsResponse.model_validate(m) for m in matches_with_transactions],
        total_count=len(matches),
        pending_count=pending_count,
        approved_count=approved_count,
        exported_count=exported_count
    )


@router.get("/matches/{match_id}", response_model=MatchWithTransactionsResponse)
async def get_match(
    match_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific match by ID.

    Args:
        match_id: UUID of match

    Returns:
        MatchWithTransactionsResponse with full details

    Raises:
        HTTPException: If match not found (404)
    """
    match = db.query(Match).filter(Match.id == match_id).first()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match with id {match_id} not found"
        )

    match_data = {
        **match.to_dict(),
        'car_transaction': match.car_transaction.to_dict(),
        'receipt_transaction': match.receipt_transaction.to_dict()
    }

    return MatchWithTransactionsResponse.model_validate(match_data)


@router.patch("/matches/{match_id}", response_model=MatchWithTransactionsResponse)
async def update_match(
    match_id: str,
    update_data: MatchUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a match (approve, reject, add notes).

    Args:
        match_id: UUID of match
        update_data: Fields to update

    Returns:
        Updated MatchWithTransactionsResponse

    Raises:
        HTTPException: If match not found (404)
    """
    match = db.query(Match).filter(Match.id == match_id).first()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match with id {match_id} not found"
        )

    # Update fields if provided
    if update_data.status is not None:
        match.status = update_data.status

    if update_data.manually_reviewed is not None:
        match.manually_reviewed = update_data.manually_reviewed

    if update_data.review_notes is not None:
        match.review_notes = update_data.review_notes

    db.commit()
    db.refresh(match)

    match_data = {
        **match.to_dict(),
        'car_transaction': match.car_transaction.to_dict(),
        'receipt_transaction': match.receipt_transaction.to_dict()
    }

    return MatchWithTransactionsResponse.model_validate(match_data)


@router.delete("/matches/{match_id}")
async def delete_match(
    match_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a match and unmark the transactions as matched.

    Args:
        match_id: UUID of match to delete

    Returns:
        Success message

    Raises:
        HTTPException: If match not found (404) or already exported (400)
    """
    match = db.query(Match).filter(Match.id == match_id).first()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match with id {match_id} not found"
        )

    if match.exported:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete exported match"
        )

    # Unmark transactions
    car_trans = db.query(Transaction).filter(Transaction.id == match.car_transaction_id).first()
    receipt_trans = db.query(Transaction).filter(Transaction.id == match.receipt_transaction_id).first()

    if car_trans:
        car_trans.is_matched = False
    if receipt_trans:
        receipt_trans.is_matched = False

    # Delete match
    db.delete(match)
    db.commit()

    return {"message": "Match deleted successfully", "match_id": match_id}
