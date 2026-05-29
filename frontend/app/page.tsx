"use client";
import { useRouter } from "next/navigation";
import DropZone from "@/components/upload/DropZone";

export default function Home() {
  const router = useRouter();

  const handleUploadComplete = (analysisId: string) => {
    router.push(`/dashboard/${analysisId}`);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-16">
      {/* Hero */}
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 bg-teal/10 text-teal px-4 py-1.5 rounded-full text-sm font-medium mb-4">
          <span className="w-2 h-2 bg-teal rounded-full animate-pulse" />
          AI-Powered · Industry Grade
        </div>
        <h1 className="text-4xl font-bold text-navy mb-3">
          Bank Statement Analyser
        </h1>
        <p className="text-gray-500 text-lg max-w-xl mx-auto">
          Upload any bank statement — digital PDF, scanned document, or passbook photos.
          Get a full financial intelligence report in seconds.
        </p>
      </div>

      {/* Upload card */}
      <DropZone onComplete={handleUploadComplete} />

      {/* Features grid */}
      <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
        {[
          { icon: "🏦", label: "All Indian Banks" },
          { icon: "🤖", label: "Claude + Gemini AI" },
          { icon: "📊", label: "FOIR & BSA Score" },
          { icon: "🔍", label: "AI QA Validator" },
        ].map((f) => (
          <div key={f.label} className="card py-4">
            <div className="text-2xl mb-1">{f.icon}</div>
            <div className="text-xs font-medium text-gray-600">{f.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
