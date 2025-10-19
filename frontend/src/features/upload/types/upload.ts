/**
 * Upload feature types.
 *
 * Pattern: Direct database values (no translation layers)
 * Reference: PRPs/ai_docs/API_NAMING_CONVENTIONS.md
 */

/** PDF type - matches backend literal */
export type PDFType = 'car' | 'receipt';

/** Upload status for UI state */
export type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

/** Response from PDF upload API */
export interface PDFUploadResponse {
  pdf_id: string;
  filename: string;
  pdf_type: PDFType;
  page_count: number;
  file_size_bytes: number;
  uploaded_at: string;  // ISO timestamp
  is_duplicate?: boolean;  // Whether this is a duplicate upload
  transaction_count?: number;  // Number of transactions already extracted
  matches_cleared?: number;  // Number of matches cleared for re-processing
}

/** API error response */
export interface PDFValidationError {
  error: string;
  message: string;
  details?: string;
}

/** Upload state for UI */
export interface UploadState {
  status: UploadStatus;
  progress: number;  // 0-100
  error: string | null;
  result: PDFUploadResponse | null;
}
