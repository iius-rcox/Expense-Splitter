export interface Transaction {
  transaction_id: string;
  pdf_id: string;
  transaction_type: 'car' | 'receipt';
  date: string | null;
  amount: number | null;
  employee_id: string | null;
  employee_name: string | null;
  merchant: string | null;
  card_number: string | null;
  receipt_id: string | null;
  page_number: number;
  raw_text: string | null;
  extraction_confidence: number | null;
  is_matched: boolean;
  extracted_at: string;
  created_at: string;
  updated_at: string | null;
}

export interface TransactionListResponse {
  transactions: Transaction[];
  total_count: number;
  car_count: number;
  receipt_count: number;
  unmatched_count: number;
}

export interface Match {
  match_id: string;
  car_transaction_id: string;
  receipt_transaction_id: string;
  confidence_score: number;
  date_score: number | null;
  amount_score: number | null;
  employee_score: number | null;
  merchant_score: number | null;
  status: 'pending' | 'approved' | 'rejected' | 'exported';
  manually_reviewed: boolean;
  review_notes: string | null;
  exported: boolean;
  export_path: string | null;
  exported_at: string | null;
  matched_at: string;
  updated_at: string | null;
  car_transaction: Transaction;
  receipt_transaction: Transaction;
}

export interface MatchListResponse {
  matches: Match[];
  total_count: number;
  pending_count: number;
  approved_count: number;
  exported_count: number;
}
