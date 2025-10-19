from pathlib import Path
import pdfplumber
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ExtractedTransaction:
    """Data class for extracted transaction information."""
    transaction_type: str  # 'car' or 'receipt'
    date: Optional[datetime]
    amount: Optional[float]
    employee_id: Optional[str]
    employee_name: Optional[str]
    merchant: Optional[str]
    card_number: Optional[str]
    receipt_id: Optional[str]
    page_number: int
    raw_text: str
    extraction_confidence: float


class ExtractionError(Exception):
    """Custom exception for extraction errors."""
    pass


class ExtractionService:
    """Service for extracting transaction data from CAR and receipt PDFs."""

    # CAR PDF Patterns - Updated to match actual CAR format
    CAR_EMPLOYEE_ID_PATTERN = r'Employee\s+ID:\s*(?P<employee_id>\d{4,6})'
    CAR_CARD_NUMBER_PATTERN = r'Card\s+Number:\s*(?P<card_number>\d{6}X+\d{4})'
    CAR_CARDHOLDER_NAME_PATTERN = r'Cardholder\s+Name:\s*(?P<cardholder_name>[A-Z]+)'

    CAR_TOTALS_PATTERN = r'Transaction Totals:\s*\$([0-9,\.]+)'
    CAR_TRANSACTION_HEADER_PATTERN = r'Trans Date\s+Posted Date.*?Merchant Name'

    # CAR transaction line pattern
    CAR_DATE_PATTERN = r'(\d{2}/\d{2}/\d{4})'
    CAR_AMOUNT_PATTERN = r'\$([0-9,]+\.\d{2})'
    CAR_MERCHANT_PATTERN = r'^([A-Z0-9\s\-\.]+?)(?=\s+\d{2}/\d{2}/\d{4}|\$)'

    # Receipt PDF Patterns
    RECEIPT_DATE_PATTERN = r'(\d{1,2}/\d{1,2}/\d{2,4})'
    RECEIPT_AMOUNT_PATTERN = r'\$?\s*([0-9,]+\.\d{2})'
    RECEIPT_EMPLOYEE_PATTERN = r'(?:Employee|EE|ID)[\s:]*([A-Z\s,]+?)[\s,]+(\d{4,6})'
    RECEIPT_MERCHANT_PATTERN = r'^([A-Z][A-Z0-9\s\-\.&]+?)(?=\n|\s{2,})'

    def __init__(self):
        """Initialize extraction service."""
        pass

    def extract_car_transactions(self, pdf_path: Path) -> List[ExtractedTransaction]:
        """
        Extract transactions from CAR (Corporate American Express Report) PDF.

        Args:
            pdf_path: Path to CAR PDF file

        Returns:
            List of ExtractedTransaction objects

        Raises:
            ExtractionError: If extraction fails
        """
        transactions = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                current_employee_info = None

                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if not text:
                        continue

                    # Extract employee info from page header (now on separate lines)
                    employee_id_match = re.search(self.CAR_EMPLOYEE_ID_PATTERN, text)
                    card_number_match = re.search(self.CAR_CARD_NUMBER_PATTERN, text)
                    cardholder_name_match = re.search(self.CAR_CARDHOLDER_NAME_PATTERN, text)

                    if employee_id_match and card_number_match:
                        current_employee_info = {
                            'employee_id': employee_id_match.group('employee_id').strip(),
                            'employee_name': cardholder_name_match.group('cardholder_name').strip() if cardholder_name_match else None,
                            'card_number': card_number_match.group('card_number').strip()
                        }

                    # Find the transaction header line
                    header_match = re.search(self.CAR_TRANSACTION_HEADER_PATTERN, text)
                    if not header_match:
                        continue

                    # Extract transaction lines (lines that start with a date pattern)
                    lines = text.split('\n')
                    in_transaction_section = False

                    for line in lines:
                        line = line.strip()

                        # Start processing after we see the header
                        if 'Trans Date' in line and 'Posted Date' in line:
                            in_transaction_section = True
                            continue

                        # Stop at Transaction Totals
                        if 'Transaction Totals:' in line:
                            in_transaction_section = False
                            continue

                        if not in_transaction_section or len(line) < 10:
                            continue

                        # Try to extract transaction data from line
                        transaction = self._parse_car_line(
                            line,
                            page_num,
                            current_employee_info
                        )

                        if transaction:
                            transactions.append(transaction)

        except Exception as e:
            raise ExtractionError(f"Failed to extract CAR transactions: {str(e)}")

        return transactions

    def _parse_car_line(
        self,
        line: str,
        page_num: int,
        employee_info: Optional[Dict]
    ) -> Optional[ExtractedTransaction]:
        """
        Parse a single CAR transaction line.

        Format: Trans Date Posted Date Lvl Transaction# Merchant... City, State ... $Amount
        Example: 03/03/2025 03/04/2025 N 000425061 OVERHEAD DOOR COM KEMAH, TX ... $768.22
        """

        # Extract first date (Trans Date - this is the transaction date)
        date_matches = re.findall(self.CAR_DATE_PATTERN, line)
        if not date_matches or len(date_matches) < 1:
            return None

        date_str = date_matches[0]  # First date is Trans Date
        try:
            transaction_date = datetime.strptime(date_str, '%m/%d/%Y').date()
        except ValueError:
            transaction_date = None

        # Extract amount (last $amount in line - Net Cost)
        amount_matches = re.findall(self.CAR_AMOUNT_PATTERN, line)
        amount = None
        if amount_matches:
            # Take the LAST amount (Net Cost column)
            amount_str = amount_matches[-1].replace(',', '')
            try:
                amount = float(amount_str)
            except ValueError:
                pass

        # Extract merchant name
        # Format: Date Date Level TransNum MerchantName City, State ...
        # Split by dates and extract merchant portion
        merchant = None
        parts = re.split(r'\d{2}/\d{2}/\d{4}', line)
        if len(parts) >= 3:
            # Third part contains: Level TransNum Merchant...
            merchant_section = parts[2].strip()
            # Skip Level (1 char) and Trans# (space + number)
            merchant_match = re.search(r'[A-Z]\s+\d+\s+(.+?)(?:\s+[A-Z]{2}\s+|\s+\$)', merchant_section)
            if merchant_match:
                merchant = merchant_match.group(1).strip()
                merchant = re.sub(r'\s+', ' ', merchant)  # Normalize whitespace
                merchant = merchant[:255]  # Limit length

        # Calculate confidence based on extracted fields
        confidence = 0.0
        if transaction_date:
            confidence += 0.3
        if amount:
            confidence += 0.3
        if merchant:
            confidence += 0.2
        if employee_info:
            confidence += 0.2

        return ExtractedTransaction(
            transaction_type='car',
            date=transaction_date,
            amount=amount,
            employee_id=employee_info['employee_id'] if employee_info else None,
            employee_name=employee_info['employee_name'] if employee_info else None,
            merchant=merchant,
            card_number=employee_info['card_number'] if employee_info else None,
            receipt_id=None,
            page_number=page_num,
            raw_text=line,
            extraction_confidence=confidence
        )

    def extract_receipt_transactions(self, pdf_path: Path) -> List[ExtractedTransaction]:
        """
        Extract transactions from receipt collection PDF.

        Args:
            pdf_path: Path to receipt PDF file

        Returns:
            List of ExtractedTransaction objects

        Raises:
            ExtractionError: If extraction fails
        """
        transactions = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if not text:
                        continue

                    # Try to extract a transaction from this page
                    transaction = self._parse_receipt_page(text, page_num)
                    if transaction:
                        transactions.append(transaction)

        except Exception as e:
            raise ExtractionError(f"Failed to extract receipt transactions: {str(e)}")

        return transactions

    def _parse_receipt_page(self, text: str, page_num: int) -> Optional[ExtractedTransaction]:
        """Parse a single receipt page."""

        # Extract employee info
        employee_match = re.search(self.RECEIPT_EMPLOYEE_PATTERN, text, re.IGNORECASE)
        employee_name = None
        employee_id = None
        if employee_match:
            employee_name = employee_match.group(1).strip()
            employee_id = employee_match.group(2).strip()

        # Extract date
        date_match = re.search(self.RECEIPT_DATE_PATTERN, text)
        transaction_date = None
        if date_match:
            date_str = date_match.group(1)
            # Try multiple date formats
            for fmt in ['%m/%d/%Y', '%m/%d/%y', '%d/%m/%Y', '%d/%m/%y']:
                try:
                    transaction_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue

        # Extract amount (look for total)
        amount = None
        # Look for patterns like "Total: $123.45" or "TOTAL 123.45"
        total_patterns = [
            r'(?:Total|TOTAL|Amount|AMOUNT)[\s:]*\$?\s*([0-9,]+\.\d{2})',
            r'\$\s*([0-9,]+\.\d{2})\s*(?:Total|TOTAL)',
        ]

        for pattern in total_patterns:
            amount_match = re.search(pattern, text, re.IGNORECASE)
            if amount_match:
                amount_str = amount_match.group(1).replace(',', '')
                try:
                    amount = float(amount_str)
                    break
                except ValueError:
                    pass

        # Extract merchant (usually at top of receipt)
        merchant = None
        lines = text.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if len(line) > 3 and not line.isdigit():
                # Skip common header words
                if not any(word in line.upper() for word in ['RECEIPT', 'INVOICE', 'DATE', 'EMPLOYEE', 'TOTAL']):
                    merchant = line[:255]
                    break

        # Calculate confidence
        confidence = 0.0
        if transaction_date:
            confidence += 0.25
        if amount:
            confidence += 0.35
        if employee_id:
            confidence += 0.25
        if merchant:
            confidence += 0.15

        # Only return if we have at least some key info
        if not (transaction_date or amount):
            return None

        return ExtractedTransaction(
            transaction_type='receipt',
            date=transaction_date,
            amount=amount,
            employee_id=employee_id,
            employee_name=employee_name,
            merchant=merchant,
            card_number=None,
            receipt_id=None,  # Could extract if receipt has ID
            page_number=page_num,
            raw_text=text[:500],  # First 500 chars for debugging
            extraction_confidence=confidence
        )

    def extract_transactions(
        self,
        pdf_path: Path,
        pdf_type: str
    ) -> List[ExtractedTransaction]:
        """
        Extract transactions from PDF based on type.

        Args:
            pdf_path: Path to PDF file
            pdf_type: Type of PDF ('car' or 'receipt')

        Returns:
            List of ExtractedTransaction objects

        Raises:
            ExtractionError: If extraction fails
            ValueError: If pdf_type is invalid
        """
        if pdf_type == 'car':
            return self.extract_car_transactions(pdf_path)
        elif pdf_type == 'receipt':
            return self.extract_receipt_transactions(pdf_path)
        else:
            raise ValueError(f"Invalid pdf_type: {pdf_type}. Must be 'car' or 'receipt'.")


# Singleton instance
extraction_service = ExtractionService()
