import { useState, useCallback } from 'react';
import { Upload, File, X } from 'lucide-react';
import { PDFType, PDFUploadResponse } from '../types/upload';

interface UploadZoneProps {
  type: PDFType;
  onUpload: (file: File) => void;
  isUploading: boolean;
  uploadResult: PDFUploadResponse | null;
  error: string | null;
  onClear: () => void;
}

export function UploadZone({
  type,
  onUpload,
  isUploading,
  uploadResult,
  error,
  onClear,
}: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    const pdfFile = files.find(f => f.type === 'application/pdf');

    if (pdfFile) {
      onUpload(pdfFile);
    } else {
      // Could add error handling here
      console.error('No PDF file found in drop');
    }
  }, [onUpload]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onUpload(files[0]);
    }
  }, [onUpload]);

  const title = type === 'car' ? 'CAR PDF' : 'Receipt PDF';

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="w-full">
      <h3 className="text-lg font-semibold mb-2">{title}</h3>

      {!uploadResult ? (
        <div
          className={`
            border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
            transition-colors duration-200
            ${isDragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'}
            ${isUploading ? 'opacity-50 pointer-events-none' : ''}
          `}
          onDragEnter={handleDragEnter}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => document.getElementById(`file-input-${type}`)?.click()}
        >
          <input
            id={`file-input-${type}`}
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={handleFileSelect}
            disabled={isUploading}
          />

          {isUploading ? (
            <div className="flex flex-col items-center gap-3">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
              <p className="text-muted-foreground">Uploading...</p>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <Upload className="h-12 w-12 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium">Drop {title} here</p>
                <p className="text-xs text-muted-foreground mt-1">
                  or click to browse
                </p>
              </div>
              <p className="text-xs text-muted-foreground">
                Max 50MB, 500 pages
              </p>
            </div>
          )}

          {error && (
            <div className="mt-4 p-3 bg-destructive/10 border border-destructive rounded-md">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
        </div>
      ) : (
        <div className="border border-border rounded-lg p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <File className="h-8 w-8 text-primary mt-1" />
              <div>
                <p className="font-medium text-sm">{uploadResult.filename}</p>
                <div className="flex gap-4 mt-1 text-xs text-muted-foreground">
                  <span>{uploadResult.page_count} pages</span>
                  <span>{formatFileSize(uploadResult.file_size_bytes)}</span>
                </div>
              </div>
            </div>
            <button
              onClick={onClear}
              className="text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Clear upload"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
