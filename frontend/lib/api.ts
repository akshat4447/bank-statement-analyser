import { AnalysisResponse, AnalysisStatus } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function uploadStatement(file: File): Promise<{ analysis_id: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE_URL}/api/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getAnalysis(id: string): Promise<AnalysisResponse> {
  const res = await fetch(`${BASE_URL}/api/analysis/${id}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getStatus(id: string): Promise<{ status: AnalysisStatus; error?: string }> {
  const res = await fetch(`${BASE_URL}/api/analysis/${id}/status`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function sendChatMessage(
  analysisId: string,
  message: string,
  history: { role: string; content: string }[]
): Promise<{ reply: string; suggested_chips: string[] }> {
  const res = await fetch(`${BASE_URL}/api/chat/${analysisId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function loanSimulator(
  analysisId: string,
  proposedEmi: number
): Promise<import("./types").LoanAffordability> {
  const res = await fetch(`${BASE_URL}/api/analysis/${analysisId}/loan-simulator`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ proposed_emi: proposedEmi }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function getPdfUrl(id: string) {
  return `${BASE_URL}/api/report/${id}/pdf`;
}
export function getExcelUrl(id: string) {
  return `${BASE_URL}/api/report/${id}/excel`;
}
