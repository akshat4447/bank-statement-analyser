"use client";
import { useRouter } from "next/navigation";
import DropZone from "@/components/upload/DropZone";
import { Shield, TrendingUp, FileSearch, BarChart3, Zap, Lock, Building2, CheckCircle } from "lucide-react";

const FEATURES = [
  { icon: FileSearch, title: "Universal Extraction", desc: "Any bank, any format — digital PDFs, scanned docs, passbook images", color: "#00d4aa" },
  { icon: BarChart3, title: "60+ Financial Metrics", desc: "FOIR, BSA Score, AMB, income stability, EMI-to-income ratio and more", color: "#3b82f6" },
  { icon: Shield, title: "Risk Intelligence", desc: "Fraud signals, bounce detection, gambling merchants, P2P income flagging", color: "#f59e0b" },
  { icon: TrendingUp, title: "Underwriter Reports", desc: "Approve/Review/Reject verdicts with suggested loan amounts and EMI capacity", color: "#a855f7" },
  { icon: Zap, title: "Real-Time Analysis", desc: "Parallel processing with results in under 30 seconds for any statement", color: "#ec4899" },
  { icon: Lock, title: "Loan Simulator", desc: "Test EMI affordability with income stress scenarios at 10%, 20%, 30% drops", color: "#22c55e" },
];

const BANKS = ["SBI", "HDFC", "ICICI", "Axis", "Kotak", "PNB", "BoB", "Canara", "Yes", "IDFC", "IndusInd", "Federal"];

export default function Home() {
  const router = useRouter();

  return (
    <div className="min-h-screen" style={{ background: "linear-gradient(135deg, #0a0f1e 0%, #0d1a2e 60%, #080d1a 100%)" }}>
      {/* Ambient glow */}
      <div className="fixed top-0 left-1/3 w-96 h-96 rounded-full opacity-10 pointer-events-none"
        style={{ background: "radial-gradient(circle, #00d4aa 0%, transparent 70%)", filter: "blur(80px)" }} />
      <div className="fixed bottom-1/3 right-1/4 w-80 h-80 rounded-full opacity-8 pointer-events-none"
        style={{ background: "radial-gradient(circle, #3b82f6 0%, transparent 70%)", filter: "blur(80px)" }} />

      <div className="max-w-5xl mx-auto px-4 py-16 relative">
        {/* Hero */}
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold mb-6 border"
            style={{ background: "rgba(0,212,170,0.08)", borderColor: "rgba(0,212,170,0.2)", color: "#00d4aa" }}>
            <span className="w-1.5 h-1.5 rounded-full bg-[#00d4aa] animate-pulse" />
            Enterprise-Grade Financial Intelligence
          </div>

          <h1 className="text-5xl md:text-6xl font-black text-slate-100 mb-4 leading-tight">
            Bank Statement
            <span className="block text-gradient">Intelligence Platform</span>
          </h1>

          <p className="text-slate-400 text-lg max-w-2xl mx-auto leading-relaxed">
            Upload any bank statement. Get a complete underwriter-ready report with risk scoring,
            income verification, fraud detection, and loan affordability in seconds.
          </p>

          {/* Bank logos */}
          <div className="flex flex-wrap justify-center gap-2 mt-6">
            {BANKS.map(b => (
              <span key={b} className="text-xs px-2.5 py-1 rounded-lg text-slate-500 border border-[#1e2d45] bg-[#0d1424]">{b}</span>
            ))}
            <span className="text-xs px-2.5 py-1 rounded-lg text-slate-500 border border-[#1e2d45] bg-[#0d1424]">+ All Indian Banks</span>
          </div>
        </div>

        {/* Upload card */}
        <div className="max-w-2xl mx-auto mb-16">
          <DropZone onComplete={(id) => router.push(`/dashboard/${id}`)} />
        </div>

        {/* Features grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-16">
          {FEATURES.map((f) => (
            <div key={f.title} className="card hover:border-[#1e2d45] transition-all group"
              style={{ "--hover-color": f.color } as React.CSSProperties}>
              <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-3"
                style={{ background: `${f.color}15`, border: `1px solid ${f.color}30` }}>
                <f.icon className="w-5 h-5" style={{ color: f.color }} />
              </div>
              <h3 className="font-semibold text-slate-200 mb-1">{f.title}</h3>
              <p className="text-sm text-slate-500 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>

        {/* What you get */}
        <div className="card-glow p-8">
          <h2 className="text-xl font-bold text-slate-100 mb-6 text-center">Complete Analysis Output</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            {[
              { val: "60+", label: "Metrics Computed" },
              { val: "15+", label: "Risk Signals" },
              { val: "16", label: "Spend Categories" },
              { val: "3", label: "Export Formats" },
            ].map(s => (
              <div key={s.label}>
                <div className="text-3xl font-black text-gradient mb-1">{s.val}</div>
                <div className="text-xs text-slate-500">{s.label}</div>
              </div>
            ))}
          </div>
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            {["Transaction Extraction", "Income Verification", "EMI Detection", "Fraud Signals",
              "BSA Score", "FOIR Calculation", "Loan Simulator", "Underwriter Report",
              "Excel Export", "PDF Report", "QA Validation", "AI Chat"].map(f => (
              <span key={f} className="flex items-center gap-1 text-xs text-slate-400 bg-[#111827] px-3 py-1 rounded-full border border-[#1e2d45]">
                <CheckCircle className="w-3 h-3 text-[#00d4aa]" /> {f}
              </span>
            ))}
          </div>
        </div>

        <p className="text-center text-xs text-slate-600 mt-8">
          Supports PDF, JPG, PNG, TIFF up to 50MB · All transactions processed securely
        </p>
      </div>
    </div>
  );
}
