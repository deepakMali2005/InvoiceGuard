const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function apiRequest(path: string, init?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `API error ${res.status}`);
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  if (ct.includes("text/csv") || ct.includes("application/pdf")) return res.arrayBuffer();
  return res.text();
}

export async function listCases() {
  return apiRequest("/api/v1/cases/");
}

export async function createCase(caseReference: string, vendorName?: string) {
  const qs = new URLSearchParams({ case_reference: caseReference });
  if (vendorName) qs.set("vendor_name", vendorName);
  return apiRequest(`/api/v1/cases/?${qs.toString()}`, { method: "POST" });
}

export async function getCase(caseId: string) {
  return apiRequest(`/api/v1/cases/${caseId}`);
}

export async function uploadDocument(caseId: string, file: File, documentType: string) {
  const form = new FormData();
  form.append("file", file);
  form.append("document_type", documentType);
  const res = await fetch(`${API_BASE}/api/v1/cases/${caseId}/documents`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Upload failed ${res.status}`);
  }
  return res.json();
}

export async function listDocuments(caseId: string) {
  return apiRequest(`/api/v1/cases/${caseId}/documents`);
}

export async function extractDocument(documentId: string) {
  return apiRequest(`/api/v1/documents/${documentId}/extract`, { method: "POST" });
}

export async function getExtraction(documentId: string) {
  return apiRequest(`/api/v1/documents/${documentId}/extraction`);
}

export async function reconcileCase(caseId: string) {
  return apiRequest(`/api/v1/cases/${caseId}/reconcile`, { method: "POST" });
}

export async function getReconciliation(caseId: string) {
  return apiRequest(`/api/v1/cases/${caseId}/reconciliation`);
}

export async function getReport(caseId: string, format: "pdf" | "csv") {
  return apiRequest(`/api/v1/cases/${caseId}/report?format=${format}`, {});
}

export async function health() {
  return apiRequest("/health");
}

export async function deleteCase(caseId: string) {
  return apiRequest(`/api/v1/cases/${caseId}`, { method: "DELETE" });
}

export async function deleteDocument(documentId: string) {
  return apiRequest(`/api/v1/documents/${documentId}`, { method: "DELETE" });
}
