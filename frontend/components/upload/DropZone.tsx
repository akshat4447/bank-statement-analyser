"use client";
import { useState, useCallback } from "react";
import { Upload, FileText, Image, AlertCircle, Loader2, CheckCircle } from "lucide-react";
import { uploadStatement } from "@/lib/api";

interface Props { onComplete: (analysisId: string) => void; }

const ACCEPTED = [".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".webp"];

const STEPS = [
  "Converting pages to images...",
  "Extracting transactions with Vision AI...",
  "Classifying spending categories...",
  "Computing financial metrics...",
  "Generating risk assessment...",
];

export default function DropZone({ onComplete }: Props) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [step, setStep] = useState(0);

  const handleFile = useCallback(async (file: File) => {
    setError(null);
    setFileName(file.name);
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED.includes(ext)) {
      setError(`Unsupported file type. Accepted: ${ACCEPTED.join(", ")}`);
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setError("File too large. Max 50MB.");
      return;
    }
    setUploading(true);
    setStep(0);
    // Animate steps
    const interval = setInterval(() => setStep(s => Math.min(s + 1, STEPS.length - 1)), 4000);
    try {
      const { analysis_id } = await uploadStatement(file);
      clearInterval(interval);
      onComplete(analysis_id);
    } catch (e: unknown) {
      clearInterval(interval);
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

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => !uploading && document.getElementById("fs-file-input")?.click()}
      className={`relative rounded-2xl p-10 text-center transition-all duration-300 cursor-pointer border-2 border-dashed
        ${dragging
          ? "border-[#00d4aa] bg-[rgba(0,212,170,0.05)] scale-[1.01]"
          : uploading
            ? "border-[#1e2d45] bg-[#0d1424] cursor-default pointer-events-none"
            : "border-[#1e2d45] bg-[#0d1424] hover:border-[rgba(0,212,170,0.5)] hover:bg-[rgba(0,212,170,0.02)]"
        }`}
      style={dragging ? { boxShadow: "0 0 30px rgba(0,212,170,0.15)" } : {}}
    >
      <input id="fs-file-input" type="file" accept={ACCEPTED.join(",")}
        className="hidden" onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        disabled={uploading} />

      {uploading ? (
        <div className="flex flex-col items-center gap-4">
          <div className="relative">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center"
              style={{ background: "linear-gradient(135deg, rgba(0,212,170,0.15) 0%, rgba(59,130,246,0.15) 100%)" }}>
              <Loader2 className="w-8 h-8 text-[#00d4aa] animate-spin" />
            </div>
          </div>
          <div>
            <p className="font-bold text-slate-100 text-lg mb-1">Analysing {fileName}</p>
            <p className="text-sm text-[#00d4aa] font-medium">{STEPS[step]}</p>
          </div>
          <div className="w-full max-w-xs space-y-1.5 text-left">
            {STEPS.map((s, i) => (
              <div key={s} className={`flex items-center gap-2 text-xs transition-all ${i < step ? "text-[#00d4aa]" : i === step ? "text-slate-300" : "text-slate-600"}`}>
                {i < step
                  ? <CheckCircle className="w-3.5 h-3.5 text-[#00d4aa] flex-shrink-0" />
                  : i === step
                    ? <div className="w-3.5 h-3.5 rounded-full border-2 border-[#00d4aa] border-t-transparent animate-spin flex-shrink-0" />
                    : <div className="w-3.5 h-3.5 rounded-full border border-slate-700 flex-shrink-0" />
                }
                {s}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-5">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center transition-all"
            style={{ background: dragging ? "rgba(0,212,170,0.2)" : "rgba(0,212,170,0.08)", border: "1px solid rgba(0,212,170,0.2)" }}>
            <Upload className="w-7 h-7 text-[#00d4aa]" />
          </div>
          <div>
            <p className="font-bold text-slate-100 text-xl mb-1.5">
              {dragging ? "Release to analyse" : "Drop your bank statement"}
            </p>
            <p className="text-slate-500 text-sm">or click to browse files</p>
          </div>
          <div className="flex items-center gap-4 text-xs text-slate-600">
            <span className="flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-slate-500" /> PDF
            </span>
            <span className="flex items-center gap-1.5">
              <Image className="w-3.5 h-3.5 text-slate-500" /> JPG · PNG · TIFF
            </span>
            <span>Max 50MB</span>
          </div>

          {error && (
            <div className="flex items-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20 px-4 py-2.5 rounded-xl text-sm w-full">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
