import { QAValidationResult } from "@/lib/types";
import { CheckCircle, XCircle, AlertCircle } from "lucide-react";

const GRADE_STYLES: Record<string, string> = {
  A: "bg-green-100 text-green-700 border-green-200",
  B: "bg-blue-100 text-blue-700 border-blue-200",
  C: "bg-amber-100 text-amber-700 border-amber-200",
  D: "bg-orange-100 text-orange-700 border-orange-200",
  F: "bg-red-100 text-red-700 border-red-200",
};

interface Props { qa: QAValidationResult }

export default function QAReport({ qa }: Props) {
  return (
    <div className="space-y-5">
      {/* Summary scores */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Overall Confidence", value: qa.overall_confidence, icon: "🎯" },
          { label: "Extraction Accuracy", value: qa.extraction_accuracy, icon: "📤" },
          { label: "Calculation Accuracy", value: qa.calculation_accuracy, icon: "🔢" },
          { label: "Categorization", value: qa.categorization_accuracy, icon: "🏷️" },
        ].map((m) => (
          <div key={m.label} className="card text-center">
            <div className="text-2xl mb-1">{m.icon}</div>
            <div
              className={`text-2xl font-bold ${
                m.value >= 90 ? "text-green-600" : m.value >= 75 ? "text-amber-500" : "text-red-500"
              }`}
            >
              {m.value.toFixed(1)}%
            </div>
            <div className="text-xs text-gray-400 mt-0.5">{m.label}</div>
          </div>
        ))}
      </div>

      {/* Grade badge */}
      <div className="card flex items-center gap-4">
        <div className={`text-5xl font-black border-2 rounded-2xl w-20 h-20 flex items-center justify-center ${GRADE_STYLES[qa.data_quality_grade] || ""}`}>
          {qa.data_quality_grade}
        </div>
        <div>
          <p className="font-semibold text-navy text-lg">Data Quality Grade</p>
          <p className="text-sm text-gray-400">
            Validated at {new Date(qa.validated_at).toLocaleString("en-IN")}
          </p>
          {qa.issues_found.length > 0 && (
            <p className="text-amber-600 text-sm mt-1">
              {qa.issues_found.length} issue(s) detected
            </p>
          )}
        </div>
      </div>

      {/* Individual checks */}
      <div className="card">
        <h3 className="font-semibold text-navy mb-4">Validation Checks</h3>
        <div className="space-y-2">
          {qa.checks.map((check, i) => (
            <div
              key={i}
              className={`flex items-start gap-3 p-3 rounded-xl text-sm ${
                check.passed ? "bg-green-50 border border-green-100" : "bg-red-50 border border-red-100"
              }`}
            >
              {check.passed
                ? <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                : <XCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
              }
              <div className="flex-1 min-w-0">
                <div className="font-medium text-navy">{check.check_name}</div>
                {check.note && <div className="text-xs text-gray-500 mt-0.5">{check.note}</div>}
                {(check.expected || check.actual) && (
                  <div className="text-xs text-gray-400 mt-0.5">
                    {check.expected && <span>Expected: {check.expected} </span>}
                    {check.actual && <span>Got: {check.actual}</span>}
                  </div>
                )}
              </div>
              <div className={`text-xs font-bold ml-auto flex-shrink-0 ${
                check.confidence >= 90 ? "text-green-600" : check.confidence >= 70 ? "text-amber-500" : "text-red-500"
              }`}>
                {check.confidence.toFixed(0)}%
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Issues */}
      {qa.issues_found.length > 0 && (
        <div className="card">
          <h3 className="font-semibold text-navy mb-3 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-500" /> Issues Detected
          </h3>
          <ul className="space-y-2">
            {qa.issues_found.map((issue, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-amber-700 bg-amber-50 px-3 py-2 rounded-lg">
                <span className="font-bold">{i + 1}.</span> {issue}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
