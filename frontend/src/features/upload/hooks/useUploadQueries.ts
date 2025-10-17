import { useMutation } from '@tanstack/react-query';
import { uploadService } from '../services/uploadService';
import { PDFType } from '../types/upload';
import { getErrorMessage } from '@/features/shared/api/apiClient';

/**
 * Upload query hooks and key factory.
 *
 * Pattern Reference: PRPs/ai_docs/DATA_FETCHING_ARCHITECTURE.md - Feature Implementation Patterns
 */

/** Query key factory for upload operations */
export const uploadKeys = {
  all: ['uploads'] as const,
  car: () => [...uploadKeys.all, 'car'] as const,
  receipt: () => [...uploadKeys.all, 'receipt'] as const,
};

/**
 * Mutation hook for uploading PDFs.
 *
 * Usage:
 * ```tsx
 * const uploadMutation = useUploadPDF();
 * uploadMutation.mutate({ file, type: 'car' });
 * ```
 */
export function useUploadPDF() {
  return useMutation({
    mutationFn: ({ file, type }: { file: File; type: PDFType }) => {
      return uploadService.uploadPDF(file, type);
    },
    onError: (error) => {
      console.error('Upload failed:', getErrorMessage(error));
    },
  });
}

/**
 * Separate mutation hooks for explicit CAR/receipt uploads.
 */

export function useUploadCarPDF() {
  return useMutation({
    mutationFn: (file: File) => uploadService.uploadCarPDF(file),
    onError: (error) => {
      console.error('CAR upload failed:', getErrorMessage(error));
    },
  });
}

export function useUploadReceiptPDF() {
  return useMutation({
    mutationFn: (file: File) => uploadService.uploadReceiptPDF(file),
    onError: (error) => {
      console.error('Receipt upload failed:', getErrorMessage(error));
    },
  });
}
