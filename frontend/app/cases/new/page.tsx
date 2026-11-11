"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, AlertCircle, CheckCircle, Loader2, File, ArrowRight, Trash2 } from "lucide-react";
import { createCase, uploadDocument, extractDocument, listDocuments, reconcileCase } from "@/app/lib/api";
import { DOCUMENT_TYPES, STATUS_CONFIG } from "@/app/lib/constants";
import Link from "next/link";

type DocStatus = "idle" | "uploading" | "uploaded" | "extracting" | "extracted" | "error";

export default function NewCase() {
  const router = useRouter();
  const [step, setStep] = useState<"create" | "upload" | "extract" | "reconcile" | "done">("create");
  const [caseRef, setCaseRef] = useState("");
  const [vendorName, setVendorName] = useState("");
  const [caseId, setCaseId] = useState<string | null>(null);
  const [files, setFiles] = useState<Record<string, File | null>>({
    PURCHASE_ORDER: null,
    VENDOR_INVOICE: null,
    GOODS_RECEIPT_NOTE: null,
  });
  const [status, setStatus] = useState<Record<string, DocStatus>>({
    PURCHASE_ORDER: "idle",
    VENDOR_INVOICE: "idle",
    GOODS_RECEIPT_NOTE: "idle",
  });
  const [error, setError] = useState<string | null>(null);
  const [reconciliation, setReconciliation] = useState<any>(null);

  const allUploaded = Object.values(files).every((f) => f != null);
  const allExtracted = Object.values(status).every((s) => s === "extracted");
  const hasErrors = Object.values(status).some((s) => s === "error");

  const progress = (Object.values(status).filter((s) => s !== "idle").length / 6) * 100;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const created = await createCase(caseRef, vendorName || undefined);
      setCaseId(created.id);
      setStep("upload");
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleUpload = async (docType: string) => {
    const file = files[docType as keyof typeof files];
    if (!file || !caseId) return;
    setStatus((s) => ({ ...s, [docType]: "uploading" }));
    setError(null);
    try {
      await uploadDocument(caseId, file, docType);
      setStatus((s) => ({ ...s, [docType]: "uploaded" }));
    } catch (err: any) {
      setStatus((s) => ({ ...s, [docType]: "error" }));
      setError(err.message);
    }
  };

  const handleExtract = async (docType: string) => {
    setStatus((s) => ({ ...s, [docType]: "extracting" }));
    setError(null);
    try {
      const docs = await listDocuments(caseId!);
      const doc = docs.find((d: any) => d.document_type === docType);
      if (!doc) throw new Error("No document found");
      await extractDocument(doc.id);
      setStatus((s) => ({ ...s, [docType]: "extracted" }));
    } catch (err: any) {
      setStatus((s) => ({ ...s, [docType]: "error" }));
      setError(err.message);
    }
  };

  const handleReconcile = async () => {
    if (!caseId) return;
    setError(null);
    try {
      const result = await reconcileCase(caseId);
      setReconciliation(result);
      setStep("done");
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (step === "create") {
    return (
      <div className="max-w-2xl mx-auto py-8">
        <div className="flex items-center gap-3 mb-6">
          <Link href="/cases" className="text-sm text-slate-500 hover:text-slate-700">Back to cases</Link>
          <div className="w-px h-5 bg-slate-200 mx-2" />
          <h1 className="text-2xl font-bold text-slate-900">New Reconciliation</h1>
        </div>
        <p className="text-slate-500 mb-6">Create a case and upload your PO, vendor invoice, and GRN documents.</p>
        <form onSubmit={handleCreate} className="space-y-5">
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="block text-sm font-semibold text-slate-700">Case Reference <span className="text-rose-500">*</span></label>
                <input type="text" value={caseRef} onChange={(e) => setCaseRef(e.target.value)} placeholder="e.g. CASE-2026-001" required className="w-full px-4 py-2.5 border bg-white border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors" />
              </div>
              <div className="space-y-2">
                <label className="block text-sm font-semibold text-slate-700">Vendor Name</label>
                <input type="text" value={vendorName} onChange={(e) => setVendorName(e.target.value)} placeholder="e.g. Acme Industries" className="w-full px-4 py-2.5 border bg-white border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors" />
              </div>
            </div>
          </div>
          {error && (
            <div className="p-4 rounded-lg bg-rose-50 border border-rose-100 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-rose-600" />
              <p className="text-sm text-rose-700">{error}</p>
            </div>
          )}
          <button type="submit" disabled={!caseRef} className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg shadow-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium">Create Case</button>
        </form>
      </div>
    );
  }

  if (step === "done") {
    return (
      <div className="max-w-3xl mx-auto py-12 text-center">
        <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 mx-auto mb-6">
          <CheckCircle className="w-8 h-8" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Reconciliation Complete</h1>
        <p className="text-slate-500 mb-8">Your case has been reconciled successfully.</p>
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm mb-8">
          <h2 className="text-sm font-semibold text-slate-900 mb-4">Case Summary</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <span className="text-sm text-slate-600">Case Reference</span>
              <span className="text-sm font-medium text-slate-900">{caseRef}</span>
            </div>
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <span className="text-sm text-slate-600">Overall Status</span>
              <span className="text-sm font-medium">{reconciliation?.overall_status || "DISCREPANCIES_FOUND"}</span>
            </div>
            <div className="flex justify-between items-center border-b border-slate-100 pb-3">
              <span className="text-sm text-slate-600">Findings</span>
              <span className="text-sm font-medium text-slate-900">{reconciliation?.findings_count || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-slate-600">Review Required</span>
              <span className={`text-sm font-medium ${reconciliation?.review_required ? "text-rose-600" : "text-emerald-600"}`}>{String(reconciliation?.review_required)}</span>
            </div>
          </div>
        </div>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href={`/cases/${caseId}`} className="px-6 py-3 bg-blue-600 text-white rounded-lg shadow-sm hover:bg-blue-700 transition-colors font-medium">View Case Details</Link>
          <Link href="/cases/new" className="px-6 py-3 border border-slate-200 text-slate-700 rounded-lg shadow-sm hover:bg-slate-50 transition-colors font-medium">Create Another Case</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/cases" className="text-sm text-slate-500 hover:text-slate-700">Back to cases</Link>
        <div className="w-px h-5 bg-slate-200 mx-2" />
        <h1 className="text-2xl font-bold text-slate-900">New Reconciliation</h1>
      </div>
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm mb-6">
        <div className="flex items-center justify-between mb-4">
          <span className="text-sm font-semibold text-slate-700">Upload Progress</span>
          <span className="text-sm font-medium text-slate-900">{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
          <div className="h-full bg-blue-600 rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
        </div>
        <div className="flex justify-between mt-2 text-xs text-slate-500">
          <span>Step {step === "upload" ? 2 : step === "extract" ? 3 : step === "reconcile" ? 4 : 1} of 5</span>
          <span>{DOCUMENT_TYPES.length} documents to process</span>
        </div>
      </div>
      <div className="flex flex-col md:flex-row gap-4 mb-8">
        {[
          { key: "create", label: "Create Case" },
          { key: "upload", label: "Upload Documents" },
          { key: "extract", label: "Extract Data" },
          { key: "reconcile", label: "Reconcile" },
          { key: "done", label: "Complete" },
        ].map((s, i) => {
          const active = step === s.key;
          const completed =
            (s.key === "create" && step !== "create") ||
            (s.key === "upload" && ["extract", "reconcile", "done"].includes(step)) ||
            (s.key === "extract" && ["reconcile", "done"].includes(step)) ||
            (s.key === "reconcile" && step === "done");
          return (
            <div key={s.key} className={`flex-1 flex items-center gap-3 px-4 py-3 rounded-xl transition-colors ${active ? "bg-blue-50 border border-blue-200" : completed ? "bg-emerald-50 border border-emerald-200" : "bg-slate-50 border border-slate-200"}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${active ? "bg-blue-600 text-white" : completed ? "bg-emerald-600 text-white" : "bg-slate-200 text-slate-400"}`}>{active ? <Loader2 className="w-4 h-4 animate-spin" /> : completed ? <CheckCircle className="w-4 h-4" /> : i + 1}</div>
              <span className={`text-sm font-medium ${active ? "text-blue-700" : completed ? "text-emerald-700" : "text-slate-500"}`}>{s.label}</span>
            </div>
          );
        })}
      </div>
      {step === "upload" && (
        <div className="space-y-6">
          <h2 className="text-xl font-bold text-slate-900 mb-2">Upload Documents</h2>
          <p className="text-slate-500 mb-4">Upload your Purchase Order, Vendor Invoice, and Goods Receipt Note.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {DOCUMENT_TYPES.map((dt) => {
              const file = files[dt.value as keyof typeof files];
              const docStatus = status[dt.value as keyof typeof status];
              return (
                <div key={dt.value} className={`rounded-xl border p-5 transition-colors ${docStatus === "uploaded" ? "bg-emerald-50 border-emerald-200" : docStatus === "error" ? "bg-rose-50 border-rose-200" : "bg-white border-slate-200 hover:border-blue-300"}`}>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-slate-900">{dt.label}</h3>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${docStatus === "uploaded" ? "bg-emerald-100 text-emerald-700" : docStatus === "error" ? "bg-rose-100 text-rose-700" : "bg-slate-100 text-slate-500"}`}>{docStatus === "uploaded" ? "Uploaded" : docStatus === "error" ? "Error" : "Pending"}</span>
                  </div>
                  {file ? (
                    <div className="flex items-center gap-2 mb-3 text-sm text-slate-600"><File className="w-4 h-4 text-slate-400" /><span className="truncate">{file.name}</span></div>
                  ) : (
                    <div>
                      <button onClick={() => { const input = document.getElementById(`file-${dt.value}`) as HTMLInputElement; input?.click(); }} className="w-full py-3 border-2 border-dashed border-slate-300 rounded-lg text-sm text-slate-500 hover:border-blue-500 hover:text-blue-600 transition-colors flex flex-col items-center gap-2 group"><Upload className="w-5 h-5 text-slate-400 group-hover:text-blue-600" /><span>Choose PDF</span></button>
                      <input id={`file-${dt.value}`} type="file" accept=".pdf" className="hidden" onChange={(e) => { if (e.target.files?.[0]) { setFiles((f) => ({ ...f, [dt.value]: e.target.files![0] })); setStatus((s) => ({ ...s, [dt.value]: "idle" })); } }} />
                    </div>
                  )}
                  <button onClick={() => { setFiles((f) => ({ ...f, [dt.value]: null })); setStatus((s) => ({ ...s, [dt.value]: "idle" })); setError(null); }} disabled={!file} className={`w-full mt-2 py-1.5 rounded-lg text-xs font-medium transition-colors ${!file ? "bg-slate-100 text-slate-400 cursor-not-allowed" : "bg-rose-50 text-rose-600 border border-rose-200 hover:bg-rose-100"}`}>
                    <Trash2 className="w-3 h-3 mr-1.5" /> Remove
                  </button>
                  {docStatus === "uploading" && (<div className="flex items-center gap-2 text-sm text-blue-600"><Loader2 className="w-4 h-4 animate-spin" /><span>Uploading...</span></div>)}
                  {docStatus === "error" && (<div className="text-xs text-rose-600 mt-2">Upload failed</div>)}
                  <button onClick={() => handleUpload(dt.value)} disabled={!file || docStatus === "uploading" || docStatus === "uploaded"} className={`w-full mt-3 py-2 rounded-lg text-sm font-medium transition-colors ${!file || docStatus === "uploaded" ? "bg-slate-100 text-slate-400 cursor-not-allowed" : "bg-blue-600 text-white hover:bg-blue-700"}`}>{docStatus === "uploaded" ? "Uploaded" : "Upload"}</button>
                </div>
              );
            })}
          </div>
          {error && (
            <div className="p-4 rounded-lg bg-rose-50 border border-rose-100 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-rose-600" />
              <p className="text-sm text-rose-700">{error}</p>
            </div>
          )}
          {allUploaded && !hasErrors && (
            <div className="flex justify-end"><button onClick={() => setStep("extract")} className="px-6 py-3 bg-blue-600 text-white rounded-lg shadow-sm hover:bg-blue-700 transition-colors font-medium flex items-center gap-2">Next: Extract Data <ArrowRight className="w-4 h-4" /></button></div>
          )}
        </div>
      )}
      {step === "extract" && (
        <div className="space-y-6">
          <h2 className="text-xl font-bold text-slate-900 mb-2">Extract Document Data</h2>
          <p className="text-slate-500 mb-4">Run AI-powered extraction on each uploaded document.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {DOCUMENT_TYPES.map((dt) => {
              const docStatus = status[dt.value as keyof typeof status];
              return (
                <div key={dt.value} className={`rounded-xl border p-5 transition-colors ${docStatus === "extracted" ? "bg-emerald-50 border-emerald-200" : docStatus === "error" ? "bg-rose-50 border-rose-200" : "bg-white border-slate-200"}`}>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-slate-900">{dt.label}</h3>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${docStatus === "extracted" ? "bg-emerald-100 text-emerald-700" : docStatus === "error" ? "bg-rose-100 text-rose-700" : "bg-slate-100 text-slate-500"}`}>{docStatus === "extracted" ? "Extracted" : docStatus === "error" ? "Error" : "Pending"}</span>
                  </div>
                  <div className="h-2 bg-slate-200 rounded-full overflow-hidden mb-4"><div className={`h-full ${docStatus === "extracted" ? "bg-emerald-600" : docStatus === "error" ? "bg-rose-600" : "bg-blue-600"} transition-all duration-500`} style={{ width: docStatus === "extracted" || docStatus === "error" ? "100%" : "0%" }} /></div>
                  {docStatus === "extracting" && (<div className="flex items-center gap-2 text-sm text-blue-600 mb-4"><Loader2 className="w-4 h-4 animate-spin" /><span>Extracting...</span></div>)}
                  {docStatus === "error" && (<div className="text-xs text-rose-600 mb-4">Extraction failed</div>)}
                  <button onClick={() => handleExtract(dt.value)} disabled={docStatus === "extracting" || docStatus === "extracted"} className={`w-full py-2 rounded-lg text-sm font-medium transition-colors ${docStatus === "extracted" ? "bg-emerald-100 text-emerald-700 cursor-not-allowed" : "bg-blue-600 text-white hover:bg-blue-700"}`}>{docStatus === "extracted" ? "Extracted" : "Extract"}</button>
                </div>
              );
            })}
          </div>
          {error && (
            <div className="p-4 rounded-lg bg-rose-50 border border-rose-100 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-rose-600" />
              <p className="text-sm text-rose-700">{error}</p>
            </div>
          )}
          {allExtracted && !hasErrors && (
            <div className="flex justify-end"><button onClick={handleReconcile} className="px-6 py-3 bg-blue-600 text-white rounded-lg shadow-sm hover:bg-blue-700 transition-colors font-medium flex items-center gap-2">Run Reconciliation <ArrowRight className="w-4 h-4" /></button></div>
          )}
        </div>
      )}
      {step === "reconcile" && (
        <div className="text-center py-20"><Loader2 className="w-10 h-10 animate-spin text-blue-600 mb-4" /><h2 className="text-xl font-bold text-slate-900 mb-2">Running Reconciliation...</h2><p className="text-slate-500">Comparing PO, invoice, and GRN data.</p></div>
      )}
    </div>
  );
}
