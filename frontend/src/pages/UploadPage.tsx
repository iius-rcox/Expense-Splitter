import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { UploadZone } from '@/features/upload/components/UploadZone';
import { useUploadCarPDF, useUploadReceiptPDF } from '@/features/upload/hooks/useUploadQueries';
import { PDFUploadResponse } from '@/features/upload/types/upload';
import { getErrorMessage } from '@/features/shared/api/apiClient';

export default function UploadPage() {
  const navigate = useNavigate();
  const [carUpload, setCarUpload] = useState<PDFUploadResponse | null>(null);
  const [receiptUpload, setReceiptUpload] = useState<PDFUploadResponse | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);

  const carMutation = useUploadCarPDF();
  const receiptMutation = useUploadReceiptPDF();

  const handleCarUpload = (file: File) => {
    carMutation.mutate(file, {
      onSuccess: (data) => {
        setCarUpload(data);

        // If duplicate upload and both PDFs ready, go directly to matching
        if (data.is_duplicate && receiptUpload) {
          // Both PDFs uploaded and at least one is duplicate
          navigate('/matching');
        }
      },
    });
  };

  const handleReceiptUpload = (file: File) => {
    receiptMutation.mutate(file, {
      onSuccess: (data) => {
        setReceiptUpload(data);

        // If duplicate upload and both PDFs ready, go directly to matching
        if (data.is_duplicate && carUpload) {
          // Both PDFs uploaded and at least one is duplicate
          navigate('/matching');
        }
      },
    });
  };

  const handleClearCar = () => {
    setCarUpload(null);
    carMutation.reset();
  };

  const handleClearReceipt = () => {
    setReceiptUpload(null);
    receiptMutation.reset();
  };

  const canProceed = carUpload && receiptUpload;

  const handleExtractTransactions = async () => {
    if (!carUpload || !receiptUpload) return;

    setExtracting(true);
    setExtractError(null);

    try {
      // Extract from CAR PDF
      await axios.post(`http://localhost:8000/api/extract/pdf/${carUpload.pdf_id}`);

      // Extract from receipt PDF
      await axios.post(`http://localhost:8000/api/extract/pdf/${receiptUpload.pdf_id}`);

      // Navigate to matching page
      navigate('/matching');
    } catch (err: any) {
      setExtractError(err.response?.data?.detail?.message || 'Error extracting transactions');
    } finally {
      setExtracting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold">PDF Transaction Matcher</h1>
          <p className="text-muted-foreground mt-2">
            Upload your CAR and receipt PDFs to begin matching transactions
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <UploadZone
            type="car"
            onUpload={handleCarUpload}
            isUploading={carMutation.isPending}
            uploadResult={carUpload}
            error={carMutation.isError ? getErrorMessage(carMutation.error) : null}
            onClear={handleClearCar}
          />

          <UploadZone
            type="receipt"
            onUpload={handleReceiptUpload}
            isUploading={receiptMutation.isPending}
            uploadResult={receiptUpload}
            error={receiptMutation.isError ? getErrorMessage(receiptMutation.error) : null}
            onClear={handleClearReceipt}
          />
        </div>

        {canProceed && (
          <div className="flex flex-col items-center gap-2">
            <button
              className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={handleExtractTransactions}
              disabled={extracting}
            >
              {extracting ? 'Extracting Transactions...' : 'Continue to Extract Transactions'}
            </button>
            {extractError && (
              <div className="text-sm text-destructive">{extractError}</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
