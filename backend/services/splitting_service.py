from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
from typing import List, Tuple
from datetime import datetime
import uuid


class SplittingError(Exception):
    """Custom exception for PDF splitting errors."""
    pass


class SplittingService:
    """Service for splitting and combining PDFs based on matches."""

    EXPORT_DIR = Path("exports")

    def __init__(self):
        """Initialize splitting service and ensure export directory exists."""
        self.EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    def extract_pages(
        self,
        pdf_path: Path,
        page_numbers: List[int]
    ) -> PdfWriter:
        """
        Extract specific pages from a PDF.

        Args:
            pdf_path: Path to source PDF
            page_numbers: List of page numbers to extract (1-indexed)

        Returns:
            PdfWriter with extracted pages

        Raises:
            SplittingError: If extraction fails
        """
        try:
            reader = PdfReader(pdf_path)
            writer = PdfWriter()

            for page_num in page_numbers:
                # Convert from 1-indexed to 0-indexed
                page_index = page_num - 1

                if page_index < 0 or page_index >= len(reader.pages):
                    raise SplittingError(
                        f"Page {page_num} out of range for PDF with {len(reader.pages)} pages"
                    )

                writer.add_page(reader.pages[page_index])

            return writer

        except SplittingError:
            raise
        except Exception as e:
            raise SplittingError(f"Failed to extract pages: {str(e)}")

    def combine_pdfs(
        self,
        writers: List[PdfWriter],
        output_path: Path
    ) -> None:
        """
        Combine multiple PdfWriters into a single PDF file.

        Args:
            writers: List of PdfWriter objects to combine
            output_path: Path where combined PDF should be saved

        Raises:
            SplittingError: If combination fails
        """
        try:
            combined = PdfWriter()

            for writer in writers:
                # Add all pages from this writer
                for page in writer.pages:
                    combined.add_page(page)

            # Write to file
            with open(output_path, 'wb') as output_file:
                combined.write(output_file)

        except Exception as e:
            raise SplittingError(f"Failed to combine PDFs: {str(e)}")

    def create_match_pdf(
        self,
        car_pdf_path: Path,
        car_page_numbers: List[int],
        receipt_pdf_path: Path,
        receipt_page_numbers: List[int],
        match_id: str
    ) -> Tuple[Path, int]:
        """
        Create a combined PDF from matched CAR and receipt pages.

        The output PDF contains CAR pages first, then receipt pages.

        Args:
            car_pdf_path: Path to CAR PDF
            car_page_numbers: CAR page numbers to include
            receipt_pdf_path: Path to receipt PDF
            receipt_page_numbers: Receipt page numbers to include
            match_id: UUID of the match (for filename)

        Returns:
            Tuple of (output_path, total_pages)

        Raises:
            SplittingError: If PDF creation fails
        """
        try:
            # Extract pages from CAR PDF
            car_writer = self.extract_pages(car_pdf_path, car_page_numbers)

            # Extract pages from receipt PDF
            receipt_writer = self.extract_pages(receipt_pdf_path, receipt_page_numbers)

            # Generate output filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"match_{match_id}_{timestamp}.pdf"
            output_path = self.EXPORT_DIR / filename

            # Combine into single PDF
            self.combine_pdfs([car_writer, receipt_writer], output_path)

            # Count total pages
            total_pages = len(car_page_numbers) + len(receipt_page_numbers)

            return output_path, total_pages

        except SplittingError:
            raise
        except Exception as e:
            raise SplittingError(f"Failed to create match PDF: {str(e)}")

    def create_batch_pdfs(
        self,
        matches_data: List[dict]
    ) -> List[Tuple[str, Path, int]]:
        """
        Create PDFs for multiple matches at once.

        Args:
            matches_data: List of dicts with match info:
                {
                    'match_id': str,
                    'car_pdf_path': Path,
                    'car_pages': List[int],
                    'receipt_pdf_path': Path,
                    'receipt_pages': List[int]
                }

        Returns:
            List of tuples: (match_id, output_path, total_pages)

        Raises:
            SplittingError: If any PDF creation fails
        """
        results = []

        for match_data in matches_data:
            try:
                output_path, total_pages = self.create_match_pdf(
                    car_pdf_path=match_data['car_pdf_path'],
                    car_page_numbers=match_data['car_pages'],
                    receipt_pdf_path=match_data['receipt_pdf_path'],
                    receipt_page_numbers=match_data['receipt_pages'],
                    match_id=match_data['match_id']
                )

                results.append((match_data['match_id'], output_path, total_pages))

            except SplittingError as e:
                # Log error but continue with other matches
                print(f"Failed to create PDF for match {match_data['match_id']}: {e}")
                continue

        return results

    def delete_export(self, export_path: Path) -> bool:
        """
        Delete an exported PDF file.

        Args:
            export_path: Path to exported PDF

        Returns:
            True if deleted, False if file didn't exist
        """
        try:
            if export_path.exists():
                export_path.unlink()
                return True
            return False
        except Exception:
            return False

    def create_all_in_one_pdf(
        self,
        matches_data: List[dict],
        output_filename: str = None
    ) -> Tuple[Path, int]:
        """
        Create a single PDF containing all matches.

        Each match is added sequentially (CAR pages, then receipt pages).
        Useful for batch export.

        Args:
            matches_data: List of dicts with match info (same format as create_batch_pdfs)
            output_filename: Custom filename (optional)

        Returns:
            Tuple of (output_path, total_pages)

        Raises:
            SplittingError: If PDF creation fails
        """
        try:
            combined = PdfWriter()
            total_pages = 0

            for match_data in matches_data:
                # Extract CAR pages
                car_writer = self.extract_pages(
                    match_data['car_pdf_path'],
                    match_data['car_pages']
                )

                # Extract receipt pages
                receipt_writer = self.extract_pages(
                    match_data['receipt_pdf_path'],
                    match_data['receipt_pages']
                )

                # Add all pages to combined PDF
                for page in car_writer.pages:
                    combined.add_page(page)
                    total_pages += 1

                for page in receipt_writer.pages:
                    combined.add_page(page)
                    total_pages += 1

            # Generate output filename
            if not output_filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_filename = f"all_matches_{timestamp}.pdf"

            output_path = self.EXPORT_DIR / output_filename

            # Write combined PDF
            with open(output_path, 'wb') as output_file:
                combined.write(output_file)

            return output_path, total_pages

        except SplittingError:
            raise
        except Exception as e:
            raise SplittingError(f"Failed to create combined PDF: {str(e)}")


# Singleton instance
splitting_service = SplittingService()
