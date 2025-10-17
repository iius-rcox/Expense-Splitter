import { useState } from 'react';
import { UploadZone } from '@/features/upload/components/UploadZone';
import { useUploadCarPDF, useUploadReceiptPDF } from '@/features/upload/hooks/useUploadQueries';
import { PDFUploadResponse } from '@/features/upload/types/upload';
import { getErrorMessage } from '@/features/shared/api/apiClient';

export default function UploadPage() {
  const [carUpload, setCarUpload] = useState<PDFUploadResponse | null>(null);
  const [receiptUpload, setReceiptUpload] = useState<PDFUploadResponse | null>(null);

  const carMutation = useUploadCarPDF();
  const receiptMutation = useUploadReceiptPDF();

  const handleCarUpload = (file: File) => {
    carMutation.mutate(file, {
      onSuccess: (data) => {
        setCarUpload(data);
      },
    });
  };

  const handleReceiptUpload = (file: File) => {
    receiptMutation.mutate(file, {
      onSuccess: (data) => {
        setReceiptUpload(data);
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
          <div className="flex justify-center">
            <button
              className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors"
              onClick={() => {
                console.log('Ready to extract transactions', { carUpload, receiptUpload });
                // TODO: Navigate to extraction page (Phase 2)
              }}
            >
              Continue to Extract Transactions
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
