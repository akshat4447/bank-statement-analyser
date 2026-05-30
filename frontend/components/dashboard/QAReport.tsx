import { QAValidationResult, StatementQuality } from "@/lib/types";
import { CheckCircle, XCircle, AlertCircle, FileSearch } from "lucide-react";

const GRADE_STYLES: Record<string, string> = {
  A: "text-[#00d4aa] border-[rgba(0,212,170,0.3)] bg-[rgba(0,212,170,0.08)]",
  B: "text-blue-400 border-blue-500/30 bg-blue-500/05",
  C: "text-amber-400 border-amber-500/30 bg-amber-500/05",
  D: "text-orange-400 border-orange-500/30 bg-orange-500/05",
  F: "text-red-400 border-red-500/30 bg-red-500/05",
};

interface Props { qa: QAValidationResult; quality?: StatementQuality | null }

export default function QAReport({ qa, quality }: Props) {
  return (
    <div className="space-y-5">
      {/* Statement quality */}
      {quality && (
        <div className="card">
          <h3 className="section-title"><FileSearch className="w-4 h-4 text-[#00d4aa]" /> Statement Quality Analysis</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {[
              { label: "Rows Extracted", value: quality.total_rows_extracted, good: true },
              { label: "Uncertain Rows", value: quality.missing_uncertain_rows, good: quality.missing_uncertain_rows === 0 },
              { label: "OCR Confidence", value: `${quality.ocr_confidence.toFixed(1)}%`, good: quality.ocr_confidence >= 85 },
              { label: "Balance Continuity", value: `${quality.balance_continuity_pass_rate.toFixed(1)}%`, good: quality.balance_continuity_pass_rate >= 80 },
              { label: "Duplicate Rows", value: quality.duplicate_rows_detected, good: quality.duplicate_rows_detected === 0 },
              { label: "Quality Score", value: `${quality.overall_quality_score.toFixed(0)}%`, good: quality.overall_quality_score >= 80 },
            ].map(m => (
              <div key={m.label} className="bg-[#111827] rounded-xl p-4 border border-[#1e2d45]">
                <p className="stat-label mb-1">{m.label}</p>
                <p className={`text-xl font-black ${m.good ? "text-slate-100" : "text-amber-400"}`}>{m.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Accuracy scores */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Overall Confidence", value: qa.overall_confidence, icon: "🎯" },
          { label: "Extraction Accuracy", value: qa.extraction_accuracy, icon: "📤" },
          { label: "Calculation Accuracy", value: qa.calculation_accuracy, icon: "🔢" },
          { label: "Categorization", value: qa.categorization_accuracy, icon: "🏷️" },
        ].map(m => (
          <div key={m.label} className="card text-center">
            <div className="text-2xl mb-1">{m.icon}</div>
            <div className={`text-2xl font-black ${m.value >= 90 ? "text-[#00d4aa]" : m.value >= 75 ? "text-amber-400" : "text-red-400"}`}>
              {m.value.toFixed(1)}%
            </div>
            <div className="text-xs text-slate-500 mt-0.5">{m.label}</div>
          </div>
        ))}
      </div>

      {/* Grade */}
      <div className="card flex items-center gap-5">
        <div className={`text-5xl font-black border-2 rounded-2xl w-20 h-20 flex items-center justify-center flex-shrink-0 ${GRADE_STYLES[qa.data_quality_grade] || ""}`}>
          {qa.data_quality_grade}
        </div>
        <div>
          <p className="font-bold text-slate-100 text-xl">Data Quality Grade</p>
          <p className="text-sm text-slate-500">
            Validated {new Date(qa.validated_at).toLocaleString("en-IN")}
          </p>
          {qa.manual_review_required && (
            <div className="mt-1 flex items-center gap-1.5 text-amber-400 text-xs font-semibold">
              <AlertCircle className="w-3.5 h-3.5" /> Manual review recommended
            </div>
          )}
          {qa.issues_found.length > 0 && (
            <p className="text-amber-400 text-xs mt-1">{qa.issues_found.length} issue(s) found</p>
          )}
        </div>
      </div>

      {/* Checks */}
      <div className="card">
        <h3 className="section-title">Validation Checks ({qa.checks.length})</h3>
        <div className="space-y-2">
          {qa.checks.map((check, i) => (
            <div key={i} className={`flex items-start gap-3 p-3 rounded-xl border text-sm ${check.passed ? "bg-[#00d4aa]/5 border-[#00d4aa]/15" : "bg-red-500/5 border-red-500/15"}`}>
              {check.passed
                ? <CheckCircle className="w-4 h-4 text-[#00d4aa] mt-0.5 flex-shrink-0" />
                : <XCircle className="w-4 h-4 text-red-400 mt-0.5 flex-shrink-0" />
              }
              <div className="flex-1 min-w-0">
                <div className="font-medium text-slate-200">{check.check_name}</div>
                {check.note && <div className="text-xs text-slate-500 mt-0.5">{check.note}</div>}
                {(check.expected || check.actual) && (
                  <div className="text-xs text-slate-600 mt-0.5">
                    {check.expected && <span>Expected: {check.expected} </span>}
                    {check.actual && <span>Got: {check.actual}</span>}
                  </div>
                )}
              </div>
              <div className={`text-xs font-bold ml-auto flex-shrink-0 ${check.confidence >= 90 ? "text-[#00d4aa]" : check.confidence >= 70 ? "text-amber-400" : "text-red-400"}`}>
                {check.confidence.toFixed(0)}%
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Issues */}
      {qa.issues_found.length > 0 && (
        <div className="card">
          <h3 className="section-title text-amber-400"><AlertCircle className="w-4 h-4 text-amber-400" /> Issues Detected</h3>
          <ul className="space-y-2">
            {qa.issues_found.map((issue, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-amber-300 bg-amber-500/5 border border-amber-500/15 px-3 py-2 rounded-xl">
                <span className="font-bold text-amber-500">{i + 1}.</span> {issue}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
