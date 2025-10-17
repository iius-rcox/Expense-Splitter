import { apiClient } from '@/features/shared/api/apiClient';
import { PDFUploadResponse, PDFType } from '../types/upload';

/**
 * Upload service for PDF files.
 *
 * Pattern Reference: PRPs/ai_docs/API_NAMING_CONVENTIONS.md - Service Object Pattern
 */

export const uploadService = {
  /**
   * Upload CAR PDF file.
   */
  async uploadCarPDF(file: File): Promise<PDFUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<PDFUploadResponse>(
      '/api/upload/car',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  /**
   * Upload receipt PDF file.
   */
  async uploadReceiptPDF(file: File): Promise<PDFUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post<PDFUploadResponse>(
      '/api/upload/receipt',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  },

  /**
   * Generic upload method (used by mutations).
   */
  async uploadPDF(file: File, type: PDFType): Promise<PDFUploadResponse> {
    if (type === 'car') {
      return this.uploadCarPDF(file);
    } else {
      return this.uploadReceiptPDF(file);
    }
  },
};
