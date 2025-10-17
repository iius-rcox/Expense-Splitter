from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime
from typing import List

from models.base import get_db
from models.transaction import Match
from models.pdf import PDF
from services.splitting_service import splitting_service, SplittingError

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/match/{match_id}")
async def export_match(
    match_id: str,
    db: Session = Depends(get_db)
):
    """
    Export a single match as a combined PDF.

    Creates a PDF with CAR pages followed by receipt pages for the matched pair.

    Args:
        match_id: UUID of match to export

    Returns:
        Export metadata with file path

    Raises:
        HTTPException: If match not found (404) or export fails (500)
    """
    # Get match with relationships
    match = db.query(Match).filter(Match.id == match_id).first()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match with id {match_id} not found"
        )

    # Get PDF records
    car_trans = match.car_transaction
    receipt_trans = match.receipt_transaction

    car_pdf = db.query(PDF).filter(PDF.id == car_trans.pdf_id).first()
    receipt_pdf = db.query(PDF).filter(PDF.id == receipt_trans.pdf_id).first()

    if not car_pdf or not receipt_pdf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source PDF files not found in database"
        )

    # Verify files exist on disk
    car_path = Path(car_pdf.file_path)
    receipt_path = Path(receipt_pdf.file_path)

    if not car_path.exists() or not receipt_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source PDF files not found on disk"
        )

    # Create the split PDF
    try:
        output_path, total_pages = splitting_service.create_match_pdf(
            car_pdf_path=car_path,
            car_page_numbers=[car_trans.page_number],
            receipt_pdf_path=receipt_path,
            receipt_page_numbers=[receipt_trans.page_number],
            match_id=match_id
        )

        # Update match record
        match.exported = True
        match.export_path = str(output_path.absolute())
        match.exported_at = datetime.now()
        match.status = 'exported'

        db.commit()
        db.refresh(match)

        return {
            "message": "Match exported successfully",
            "match_id": match_id,
            "export_path": str(output_path),
            "total_pages": total_pages,
            "exported_at": match.exported_at.isoformat()
        }

    except SplittingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "export_error",
                "message": str(e)
            }
        )


@router.post("/matches/batch")
async def export_batch_matches(
    match_ids: List[str],
    db: Session = Depends(get_db)
):
    """
    Export multiple matches at once.

    Creates separate PDFs for each match.

    Args:
        match_ids: List of match UUIDs to export

    Returns:
        Export results for each match

    Raises:
        HTTPException: If no valid matches found (404) or export fails (500)
    """
    # Get matches
    matches = db.query(Match).filter(Match.id.in_(match_ids)).all()

    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matches found with provided IDs"
        )

    # Prepare data for batch export
    matches_data = []
    for match in matches:
        car_pdf = db.query(PDF).filter(PDF.id == match.car_transaction.pdf_id).first()
        receipt_pdf = db.query(PDF).filter(PDF.id == match.receipt_transaction.pdf_id).first()

        if not car_pdf or not receipt_pdf:
            continue

        matches_data.append({
            'match_id': match.id,
            'car_pdf_path': Path(car_pdf.file_path),
            'car_pages': [match.car_transaction.page_number],
            'receipt_pdf_path': Path(receipt_pdf.file_path),
            'receipt_pages': [match.receipt_transaction.page_number]
        })

    if not matches_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No valid match data found"
        )

    # Create batch PDFs
    try:
        results = splitting_service.create_batch_pdfs(matches_data)

        # Update match records
        for match_id, output_path, total_pages in results:
            match = db.query(Match).filter(Match.id == match_id).first()
            if match:
                match.exported = True
                match.export_path = str(output_path.absolute())
                match.exported_at = datetime.now()
                match.status = 'exported'

        db.commit()

        return {
            "message": f"Exported {len(results)} matches successfully",
            "exported_count": len(results),
            "failed_count": len(matches_data) - len(results),
            "results": [
                {
                    "match_id": match_id,
                    "export_path": str(output_path),
                    "total_pages": total_pages
                }
                for match_id, output_path, total_pages in results
            ]
        }

    except SplittingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "export_error",
                "message": str(e)
            }
        )


@router.post("/matches/all-in-one")
async def export_all_in_one(
    match_ids: List[str] = None,
    db: Session = Depends(get_db)
):
    """
    Export all matches (or specified matches) into a single combined PDF.

    Args:
        match_ids: List of match UUIDs (optional, defaults to all approved matches)

    Returns:
        Export metadata for combined PDF

    Raises:
        HTTPException: If no matches found (404) or export fails (500)
    """
    # Get matches
    if match_ids:
        matches = db.query(Match).filter(Match.id.in_(match_ids)).all()
    else:
        # Default to all approved matches
        matches = db.query(Match).filter(Match.status == 'approved').all()

    if not matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matches found"
        )

    # Prepare data
    matches_data = []
    for match in matches:
        car_pdf = db.query(PDF).filter(PDF.id == match.car_transaction.pdf_id).first()
        receipt_pdf = db.query(PDF).filter(PDF.id == match.receipt_transaction.pdf_id).first()

        if not car_pdf or not receipt_pdf:
            continue

        matches_data.append({
            'match_id': match.id,
            'car_pdf_path': Path(car_pdf.file_path),
            'car_pages': [match.car_transaction.page_number],
            'receipt_pdf_path': Path(receipt_pdf.file_path),
            'receipt_pages': [match.receipt_transaction.page_number]
        })

    if not matches_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No valid match data found"
        )

    # Create combined PDF
    try:
        output_path, total_pages = splitting_service.create_all_in_one_pdf(matches_data)

        # Update all match records
        for match in matches:
            match.exported = True
            match.exported_at = datetime.now()
            match.status = 'exported'

        db.commit()

        return {
            "message": f"Exported {len(matches)} matches into single PDF",
            "match_count": len(matches),
            "export_path": str(output_path),
            "total_pages": total_pages
        }

    except SplittingError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "export_error",
                "message": str(e)
            }
        )


@router.get("/download/{match_id}")
async def download_match(
    match_id: str,
    db: Session = Depends(get_db)
):
    """
    Download the exported PDF for a match.

    Args:
        match_id: UUID of match

    Returns:
        PDF file download

    Raises:
        HTTPException: If match not found (404) or not exported (400)
    """
    match = db.query(Match).filter(Match.id == match_id).first()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Match with id {match_id} not found"
        )

    if not match.exported or not match.export_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Match has not been exported yet"
        )

    export_path = Path(match.export_path)

    if not export_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export file not found on disk"
        )

    return FileResponse(
        path=export_path,
        media_type='application/pdf',
        filename=export_path.name
    )
