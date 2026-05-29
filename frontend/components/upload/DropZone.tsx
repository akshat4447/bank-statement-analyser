"use client";
import { useState, useCallback } from "react";
import { Upload, FileText, Image, AlertCircle, Loader2 } from "lucide-react";
import { uploadStatement } from "@/lib/api";

interface Props {
  onComplete: (analysisId: string) => void;
}

const ACCEPTED = [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".webp"];

export default function DropZone({ onComplete }: Props) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleFile = useCallback(async (file: File) => {
    setError(null);
    setFileName(file.name);
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED.includes(ext)) {
      setError(`Unsupported file type. Please upload: ${ACCEPTED.join(", ")}`);
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setError("File too large. Max 50MB.");
      return;
    }

    setUploading(true);
    try {
      const { analysis_id } = await uploadStatement(file);
      onComplete(analysis_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed. Please try again.");
      setUploading(false);
    }
  }, [onComplete]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={`relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-200 cursor-pointer
        ${dragging ? "border-teal bg-teal/5 scale-[1.01]" : "border-gray-200 bg-white hover:border-teal/50 hover:bg-gray-50"}
        ${uploading ? "pointer-events-none" : ""}`}
      onClick={() => !uploading && document.getElementById("file-input")?.click()}
    >
      <input
        id="file-input"
        type="file"
        accept={ACCEPTED.join(",")}
        className="hidden"
        onChange={onInputChange}
        disabled={uploading}
      />

      {uploading ? (
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-12 h-12 text-teal animate-spin" />
          <p className="font-semibold text-navy text-lg">Uploading & analysing...</p>
          <p className="text-sm text-gray-400">{fileName}</p>
          <p className="text-xs text-gray-400 mt-1">
            Extracting transactions → Running AI analysis → Validating...
          </p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 bg-teal/10 rounded-2xl flex items-center justify-center">
            <Upload className="w-8 h-8 text-teal" />
          </div>
          <div>
            <p className="font-semibold text-navy text-xl mb-1">
              Drop your bank statement here
            </p>
            <p className="text-gray-400 text-sm">or click to browse</p>
          </div>

          <div className="flex items-center gap-3 text-xs text-gray-400">
            <span className="flex items-center gap-1">
              <FileText className="w-3.5 h-3.5" /> PDF
            </span>
            <span className="flex items-center gap-1">
              <Image className="w-3.5 h-3.5" /> JPG / PNG
            </span>
            <span>• Max 50MB • All Indian Banks</span>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-600 bg-red-50 px-4 py-2 rounded-lg text-sm mt-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
