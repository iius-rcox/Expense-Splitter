from pathlib import Path
import pdfplumber
from PyPDF2 import PdfReader
from typing import Literal, Tuple
import shutil
import uuid


class PDFValidationError(Exception):
    """Custom exception for PDF validation errors."""
    pass


class PDFService:
    """Service for handling PDF uploads and validation."""

    # Constants
    MAX_FILE_SIZE_MB = 300
    MAX_PAGE_COUNT = 1500
    MIN_PAGE_COUNT = 1
    UPLOAD_DIR = Path("uploads")

    def __init__(self):
        """Initialize PDF service and ensure upload directory exists."""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def validate_pdf_format(self, file_path: Path) -> Tuple[int, bool]:
        """
        Validate PDF file format and structure.

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (page_count, is_valid)

        Raises:
            PDFValidationError: If PDF is invalid
        """
        try:
            # Try to open with PyPDF2 for basic validation
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)

                # Check if encrypted
                if reader.is_encrypted:
                    raise PDFValidationError(
                        "PDF is password-protected. Please upload an unencrypted PDF."
                    )

                page_count = len(reader.pages)

                # Validate page count
                if page_count < self.MIN_PAGE_COUNT:
                    raise PDFValidationError(
                        f"PDF must have at least {self.MIN_PAGE_COUNT} page."
                    )

                if page_count > self.MAX_PAGE_COUNT:
                    raise PDFValidationError(
                        f"PDF exceeds maximum {self.MAX_PAGE_COUNT} pages. "
                        f"Please split into smaller files."
                    )

                return page_count, True

        except PDFValidationError:
            raise  # Re-raise our custom errors
        except Exception as e:
            raise PDFValidationError(
                f"Unable to read PDF. Please ensure file is not corrupted. "
                f"Technical details: {str(e)}"
            )

    def validate_text_extractable(self, file_path: Path) -> bool:
        """
        Check if PDF contains extractable text (not just images).

        Args:
            file_path: Path to PDF file

        Returns:
            True if text is extractable

        Raises:
            PDFValidationError: If no text found
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                # Check first 3 pages for text
                pages_to_check = min(3, len(pdf.pages))
                total_text_length = 0

                for i in range(pages_to_check):
                    text = pdf.pages[i].extract_text()
                    if text:
                        total_text_length += len(text.strip())

                # Require at least 50 characters of text in first few pages
                if total_text_length < 50:
                    raise PDFValidationError(
                        "No parseable transactions found. "
                        "Please verify PDF contains text (not scanned images)."
                    )

                return True

        except PDFValidationError:
            raise
        except Exception as e:
            raise PDFValidationError(
                f"Error extracting text from PDF: {str(e)}"
            )

    def validate_file_size(self, file_path: Path) -> int:
        """
        Validate file size is within limits.

        Args:
            file_path: Path to file

        Returns:
            File size in bytes

        Raises:
            PDFValidationError: If file too large
        """
        file_size = file_path.stat().st_size
        max_size_bytes = self.MAX_FILE_SIZE_MB * 1024 * 1024

        if file_size > max_size_bytes:
            raise PDFValidationError(
                f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds "
                f"maximum {self.MAX_FILE_SIZE_MB} MB."
            )

        return file_size

    async def save_uploaded_file(
        self,
        file,  # FastAPI UploadFile
        pdf_type: Literal["car", "receipt"]
    ) -> Tuple[Path, str, int, int]:
        """
        Save uploaded file to disk with validation.

        Args:
            file: FastAPI UploadFile object
            pdf_type: Type of PDF ('car' or 'receipt')

        Returns:
            Tuple of (file_path, filename, page_count, file_size_bytes)

        Raises:
            PDFValidationError: If validation fails
        """
        # Generate unique filename
        file_id = str(uuid.uuid4())
        original_filename = file.filename
        file_extension = Path(original_filename).suffix

        # Ensure it's a PDF
        if file_extension.lower() != '.pdf':
            raise PDFValidationError("Only PDF files are accepted.")

        # Create type-specific subdirectory
        type_dir = self.UPLOAD_DIR / pdf_type
        type_dir.mkdir(parents=True, exist_ok=True)

        # Full path for saved file
        saved_filename = f"{file_id}{file_extension}"
        file_path = type_dir / saved_filename

        # Save file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise PDFValidationError(f"Failed to save file: {str(e)}")

        # Validate file size
        file_size = self.validate_file_size(file_path)

        # Validate PDF format
        page_count, _ = self.validate_pdf_format(file_path)

        # Validate text extractability
        self.validate_text_extractable(file_path)

        return file_path, original_filename, page_count, file_size

    def delete_file(self, file_path: Path):
        """Delete uploaded file (cleanup on error)."""
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass  # Ignore cleanup errors


# Singleton instance
pdf_service = PDFService()
