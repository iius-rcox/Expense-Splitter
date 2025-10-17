from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from rapidfuzz import fuzz


@dataclass
class MatchScore:
    """Data class for match scoring details."""
    car_transaction_id: str
    receipt_transaction_id: str
    confidence_score: float
    date_score: float
    amount_score: float
    employee_score: float
    merchant_score: float


class MatchingService:
    """Service for matching CAR transactions with receipt transactions."""

    # Matching weights (must sum to 1.0)
    DATE_WEIGHT = 0.30
    AMOUNT_WEIGHT = 0.30
    EMPLOYEE_WEIGHT = 0.25
    MERCHANT_WEIGHT = 0.15

    # Matching thresholds
    CONFIDENCE_THRESHOLD = 0.70  # Minimum confidence for valid match
    DATE_TOLERANCE_DAYS = 1  # Allow 1 day difference
    AMOUNT_TOLERANCE = 0.01  # $0.01 tolerance for floating point comparison
    FUZZY_MATCH_THRESHOLD = 80  # Minimum fuzzy match score for merchant names

    def __init__(self):
        """Initialize matching service."""
        pass

    def calculate_date_score(
        self,
        car_date: Optional[datetime],
        receipt_date: Optional[datetime]
    ) -> float:
        """
        Calculate date proximity score.

        Args:
            car_date: Transaction date from CAR
            receipt_date: Transaction date from receipt

        Returns:
            Score from 0.0 to 1.0
        """
        if not car_date or not receipt_date:
            return 0.0

        # Calculate day difference
        day_diff = abs((car_date - receipt_date).days)

        if day_diff == 0:
            return 1.0  # Exact match
        elif day_diff <= self.DATE_TOLERANCE_DAYS:
            # Linear decay within tolerance
            return 1.0 - (day_diff / self.DATE_TOLERANCE_DAYS) * 0.5
        else:
            return 0.0  # Outside tolerance

    def calculate_amount_score(
        self,
        car_amount: Optional[float],
        receipt_amount: Optional[float]
    ) -> float:
        """
        Calculate amount match score.

        Args:
            car_amount: Amount from CAR
            receipt_amount: Amount from receipt

        Returns:
            Score from 0.0 to 1.0 (binary: exact match or no match)
        """
        if not car_amount or not receipt_amount:
            return 0.0

        # Check if amounts match within tolerance
        if abs(car_amount - receipt_amount) <= self.AMOUNT_TOLERANCE:
            return 1.0
        else:
            return 0.0

    def calculate_employee_score(
        self,
        car_employee_id: Optional[str],
        receipt_employee_id: Optional[str]
    ) -> float:
        """
        Calculate employee ID match score.

        Args:
            car_employee_id: Employee ID from CAR
            receipt_employee_id: Employee ID from receipt

        Returns:
            Score from 0.0 to 1.0 (binary: exact match or no match)
        """
        if not car_employee_id or not receipt_employee_id:
            return 0.0

        # Normalize and compare
        car_id = car_employee_id.strip().upper()
        receipt_id = receipt_employee_id.strip().upper()

        if car_id == receipt_id:
            return 1.0
        else:
            return 0.0

    def calculate_merchant_score(
        self,
        car_merchant: Optional[str],
        receipt_merchant: Optional[str]
    ) -> float:
        """
        Calculate merchant name fuzzy match score.

        Args:
            car_merchant: Merchant name from CAR
            receipt_merchant: Merchant name from receipt

        Returns:
            Score from 0.0 to 1.0 based on fuzzy string matching
        """
        if not car_merchant or not receipt_merchant:
            return 0.0

        # Normalize merchant names
        car_norm = car_merchant.strip().upper()
        receipt_norm = receipt_merchant.strip().upper()

        # Use rapidfuzz for fuzzy string matching
        # Try multiple matching algorithms and take the best score
        ratio_score = fuzz.ratio(car_norm, receipt_norm)
        partial_score = fuzz.partial_ratio(car_norm, receipt_norm)
        token_sort_score = fuzz.token_sort_ratio(car_norm, receipt_norm)

        # Take the maximum score
        fuzzy_score = max(ratio_score, partial_score, token_sort_score)

        # Convert 0-100 score to 0.0-1.0
        normalized_score = fuzzy_score / 100.0

        # Apply threshold
        if fuzzy_score < self.FUZZY_MATCH_THRESHOLD:
            return 0.0

        return normalized_score

    def calculate_match_score(
        self,
        car_transaction: Dict,
        receipt_transaction: Dict
    ) -> MatchScore:
        """
        Calculate overall match score between CAR and receipt transactions.

        Args:
            car_transaction: Dictionary with CAR transaction data
            receipt_transaction: Dictionary with receipt transaction data

        Returns:
            MatchScore with component scores and overall confidence
        """
        # Calculate component scores
        date_score = self.calculate_date_score(
            car_transaction.get('date'),
            receipt_transaction.get('date')
        )

        amount_score = self.calculate_amount_score(
            car_transaction.get('amount'),
            receipt_transaction.get('amount')
        )

        employee_score = self.calculate_employee_score(
            car_transaction.get('employee_id'),
            receipt_transaction.get('employee_id')
        )

        merchant_score = self.calculate_merchant_score(
            car_transaction.get('merchant'),
            receipt_transaction.get('merchant')
        )

        # Calculate weighted overall confidence
        confidence = (
            date_score * self.DATE_WEIGHT +
            amount_score * self.AMOUNT_WEIGHT +
            employee_score * self.EMPLOYEE_WEIGHT +
            merchant_score * self.MERCHANT_WEIGHT
        )

        return MatchScore(
            car_transaction_id=car_transaction.get('transaction_id'),
            receipt_transaction_id=receipt_transaction.get('transaction_id'),
            confidence_score=confidence,
            date_score=date_score,
            amount_score=amount_score,
            employee_score=employee_score,
            merchant_score=merchant_score
        )

    def find_matches(
        self,
        car_transactions: List[Dict],
        receipt_transactions: List[Dict],
        min_confidence: Optional[float] = None
    ) -> List[MatchScore]:
        """
        Find all matches between CAR and receipt transactions.

        Uses weighted scoring algorithm to match transactions. Only returns
        matches above the confidence threshold.

        Args:
            car_transactions: List of CAR transaction dictionaries
            receipt_transactions: List of receipt transaction dictionaries
            min_confidence: Minimum confidence threshold (default: 0.70)

        Returns:
            List of MatchScore objects sorted by confidence (highest first)
        """
        if min_confidence is None:
            min_confidence = self.CONFIDENCE_THRESHOLD

        matches = []

        # Compare each CAR transaction with each receipt transaction
        for car_trans in car_transactions:
            for receipt_trans in receipt_transactions:
                # Calculate match score
                match_score = self.calculate_match_score(car_trans, receipt_trans)

                # Only keep matches above threshold
                if match_score.confidence_score >= min_confidence:
                    matches.append(match_score)

        # Sort by confidence score (highest first)
        matches.sort(key=lambda x: x.confidence_score, reverse=True)

        return matches

    def find_best_matches(
        self,
        car_transactions: List[Dict],
        receipt_transactions: List[Dict],
        min_confidence: Optional[float] = None
    ) -> List[MatchScore]:
        """
        Find best 1:1 matches between CAR and receipt transactions.

        Ensures each transaction is matched at most once by using a greedy
        algorithm (highest confidence matches first).

        Args:
            car_transactions: List of CAR transaction dictionaries
            receipt_transactions: List of receipt transaction dictionaries
            min_confidence: Minimum confidence threshold (default: 0.70)

        Returns:
            List of MatchScore objects (each transaction matched once max)
        """
        # Get all potential matches
        all_matches = self.find_matches(
            car_transactions,
            receipt_transactions,
            min_confidence
        )

        # Track which transactions have been matched
        matched_car_ids = set()
        matched_receipt_ids = set()
        best_matches = []

        # Greedy matching: process highest confidence first
        for match in all_matches:
            # Skip if either transaction already matched
            if (match.car_transaction_id in matched_car_ids or
                match.receipt_transaction_id in matched_receipt_ids):
                continue

            # Add match and mark transactions as matched
            best_matches.append(match)
            matched_car_ids.add(match.car_transaction_id)
            matched_receipt_ids.add(match.receipt_transaction_id)

        return best_matches


# Singleton instance
matching_service = MatchingService()
