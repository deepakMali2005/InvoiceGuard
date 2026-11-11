"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AlertCircle, CheckCircle, Loader2, Trash2, DownloadIcon, FileText, ArrowLeftIcon } from "lucide-react";
import {
  getCase,
  listDocuments,
  getExtraction,
  getReconciliation,
  getReport,
  extractDocument as extractDoc,
  deleteDocument,
} from "@/app/lib/api";
import { STATUS_CONFIG, DISCREPANCY_CONFIG, formatCurrency, formatDate } from "@/app/lib/constants";

const DOCUMENT_TYPES_ORDER = [
  { value: "PURCHASE_ORDER", label: "Purchase Order" },
  { value: "VENDOR_INVOICE", label: "Vendor Invoice" },
  { value: "GOODS_RECEIPT_NOTE", label: "Goods Receipt Note" },
];

export default function CaseDetail({ params }: { params: { caseId: string } }) {
  const router = useRouter();
  const [caseData, setCaseData] = useState<any>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [extractions, setExtractions] = useState<Record<string, any>>({});
  const [reconciliation, setReconciliation] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [extracting, setExtracting] = useState<string | null>(null);

  useEffect(() => {
    load();
  }, [params.caseId]);

  async function load() {
    setLoading(true);
    try {
      const [c, docs] = await Promise.all([getCase(params.caseId), listDocuments(params.caseId)]);
      setCaseData(c);
      setDocuments(docs);

      const extPromises = docs.map(async (d: any) => {
        try {
          const ext = await getExtraction(d.id);
          return { documentId: d.id, documentType: d.document_type, data: ext };
        } catch {
          return { documentId: d.id, documentType: d.document_type, data: null };
        }
      });
      const extResults = await Promise.all(extPromises);
      const extMap: Record<string, any> = {};
      extResults.forEach((r) => {
        extMap[r.documentType] = r.data;
      });
      setExtractions(extMap);

      try {
        const rec = await getReconciliation(params.caseId);
        setReconciliation(rec);
      } catch {
        setReconciliation(null);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="p-6 flex flex-col items-center justify-center h-full">
        <div className="w-8 h-8 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin mb-3" />
        <p className="text-sm text-slate-500">Loading case...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
        <h2 className="text-lg font-semibold text-slate-900">Unable to load case</h2>
        <p className="text-slate-500 mt-1">{error}</p>
        <button
          onClick={() => router.push("/cases")}
          className="mt-4 text-sm font-medium text-blue-600 hover:text-blue-700"
        >
          Back to cases
        </button>
      </div>
    );
  }

  if (!caseData) {
    return <div className="p-6 text-center">Case not found.</div>;
  }

  const cfg = STATUS_CONFIG[caseData.status] || STATUS_CONFIG.CREATED;
  const invoiceExt = extractions.VENDOR_INVOICE;
  const poExt = extractions.PURCHASE_ORDER;
  const grnExt = extractions.GOODS_RECEIPT_NOTE;

  const handleExtract = async (docType: string) => {
    const doc = documents.find((d: any) => d.document_type === docType);
    if (!doc) return;
    setExtracting(docType);
    try {
      await extractDoc(doc.id);
      const ext = await getExtraction(doc.id);
      setExtractions((prev) => ({ ...prev, [docType]: ext }));
      setExtracting(null);
    } catch (err: any) {
      setExtracting(null);
      setError(err.message);
    }
  };

  const handleDownload = async (format: "pdf" | "csv") => {
    try {
      const ab = await getReport(params.caseId, format);
      const blob = new Blob([ab], {
        type: format === "pdf" ? "application/pdf" : "text/csv",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `reconciliation_${caseData.case_reference}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDeleteDocument = async (documentId: string, docType: string) => {
    if (!window.confirm(`Remove this ${docType} document?`)) return;
    try {
      await deleteDocument(documentId);
      setDocuments((prev) => prev.filter((d) => d.id !== documentId));
      setExtractions((prev) => {
        const next = { ...prev };
        delete next[docType];
        return next;
      });
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to remove document");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <Link
            href="/cases"
            className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 mb-2"
          >
            <ArrowLeftIcon className="w-4 h-4" /> Back to cases
          </Link>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.color}`}>
              {cfg.label}
            </span>
            {reconciliation?.review_required && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 text-xs font-semibold">
                <AlertCircle className="w-3 h-3" /> Review Required
              </span>
            )}
          </div>
          <h1 className="text-2xl font-bold text-slate-900">{caseData.case_reference}</h1>
          <p className="text-slate-500">
            Vendor: {caseData.vendor_name || "—"} · Created: {formatDate(caseData.created_at)}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => handleDownload("pdf")}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg shadow-sm hover:bg-blue-700 transition-colors font-medium"
          >
            <DownloadIcon className="w-4 h-4" /> Download PDF
          </button>
          <button
            onClick={() => handleDownload("csv")}
            className="flex items-center gap-2 px-4 py-2.5 border border-slate-200 text-slate-700 rounded-lg shadow-sm hover:bg-slate-50 transition-colors font-medium"
          >
            <DownloadIcon className="w-4 h-4" /> Download CSV
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {DOCUMENT_TYPES_ORDER.map((dt) => {
          const doc = documents.find((d: any) => d.document_type === dt.value);
          const ext = extractions[dt.value];
          const isExtracting = extracting === dt.value;
          return (
            <div key={dt.value} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-900">{dt.label}</h3>
                <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${doc ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                  {doc ? "Uploaded" : "Missing"}
                </span>
              </div>
              {doc ? (
                <>
                  <div className="mb-3">
                    <p className="text-xs text-slate-500 truncate">{doc.original_filename}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{formatDate(doc.created_at)}</p>
                  </div>
                  {ext ? (
                    <div className="space-y-2">
                      <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Extraction</p>
                      <p className="text-xs text-slate-600">
                        <span className="font-medium">Doc #:</span> {ext.document_number || "—"}
                      </p>
                      <p className="text-xs text-slate-600">
                        <span className="font-medium">Currency:</span> {ext.currency || "—"}
                      </p>
                      <p className="text-xs text-slate-600">
                        <span className="font-medium">Line Items:</span> {ext.line_items?.length || 0}
                      </p>
                      <p className="text-xs text-slate-600">
                        <span className="font-medium">Grand Total:</span> {formatCurrency(ext.grand_total)}
                      </p>
                    </div>
                  ) : (
                    <p className="text-xs text-rose-500">Not extracted</p>
                  )}
                  <div className="mt-4 flex items-center justify-between gap-2">
                    <button
                      onClick={() => handleExtract(dt.value)}
                      disabled={!!ext || isExtracting}
                      className={`flex-1 py-2 rounded-lg text-xs font-medium transition-colors flex items-center justify-center gap-1.5 ${!!ext ? "bg-slate-100 text-slate-400 cursor-not-allowed" : isExtracting ? "bg-blue-50 text-blue-600" : "bg-blue-50 text-blue-600 hover:bg-blue-100"}`}
                    >
                      {isExtracting ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : null}
                      {!!ext ? "Extracted" : "Extract"}
                    </button>
                    <button
                      onClick={() => handleDeleteDocument(doc.id, dt.label)}
                      className="px-2 py-2 rounded-lg text-rose-500 hover:bg-rose-50 hover:text-rose-700 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </>
              ) : (
                <div className="pt-4 text-center text-xs text-slate-400">Not uploaded</div>
              )}
            </div>
          );
        })}
      </div>

      {reconciliation && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-600" />
              Reconciliation Findings
            </h2>
            <span className={`text-xs font-semibold px-2 py-1 rounded-full ${reconciliation.overall_status === "DISCREPANCIES_FOUND" ? "bg-rose-50 text-rose-600 border border-rose-100" : reconciliation.overall_status === "MATCHED" ? "bg-emerald-50 text-emerald-600 border border-emerald-100" : "bg-amber-50 text-amber-600 border border-amber-100"}`}>
              {reconciliation.findings_count} Findings
            </span>
          </div>
          <div className="divide-y divide-slate-100">
            {reconciliation.discrepancies?.length > 0 ? (
              reconciliation.discrepancies.map((d: any, i: number) => {
                const dc = DISCREPANCY_CONFIG[d.discrepancy_type] || { label: d.discrepancy_type, color: "text-slate-600" };
                const severityColor =
                  d.severity === "HIGH" ? "bg-rose-100 text-rose-700" :
                  d.severity === "MEDIUM" ? "bg-amber-100 text-amber-700" :
                  "bg-emerald-100 text-emerald-700";
                return (
                  <div key={i} className="p-5 last:border-0 group hover:bg-slate-50 transition-colors">
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-semibold px-2 py-1 rounded-full ${dc.color}`}>
                          {dc.label}
                        </span>
                        <span className={`text-xs font-semibold px-2 py-1 rounded-full ${severityColor}`}>
                          {d.severity}
                        </span>
                      </div>
                      {d.requires_review && (
                        <span className="text-xs font-semibold px-2 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-100">
                          Review Required
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-600 mb-4">{d.description}</p>

                    {/* Plain language explanation */}
                    {d.plain_language_explanation && (
                      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 mb-4 shadow-sm">
                        <div className="flex items-center gap-2 mb-2">
                          <svg className="w-5 h-5 text-emerald-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                          <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider">What this means</span>
                        </div>
                        <p className="text-sm text-emerald-800 italic">{d.plain_language_explanation}</p>
                      </div>
                    )}

                    {/* Values row */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                      {(() => {
                        const isQty = d.discrepancy_type === "QUANTITY_MISMATCH";
                        const isPrice = d.discrepancy_type === "PRICE_MISMATCH";
                        const isArithmetic = d.discrepancy_type === "ARITHMETIC_INCONSISTENCY";
                        const isPoVsInv = isQty && d.description?.includes("ordered");
                        return (
                          <>
                            <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                {isPoVsInv ? "Ordered Qty" : isQty ? "Invoiced Qty" : isPrice ? "PO Unit Price" : isArithmetic ? "Expected Total" : "Expected Value"}
                              </p>
                              <p className="text-sm font-medium text-slate-900">{d.expected_value || "—"}</p>
                            </div>
                            <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                {isPoVsInv ? "Invoiced Qty" : isQty ? "Received Qty" : isPrice ? "Invoice Unit Price" : isArithmetic ? "Recorded Total" : "Actual Value"}
                              </p>
                              <p className="text-sm font-medium text-slate-900">{d.actual_value || "—"}</p>
                            </div>
                            <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Difference</p>
                              <p className="text-sm font-medium text-rose-600">{d.difference || "—"}</p>
                            </div>
                          </>
                        );
                      })()}
                    </div>

                    {d.calculation_details && (
                      <div className="bg-blue-50 rounded-lg p-3 mb-4 border border-blue-100">
                        <p className="text-xs font-semibold text-blue-700 uppercase tracking-wider mb-1">Calculation</p>
                        <p className="text-blue-900 font-mono text-xs">{d.calculation_details}</p>
                      </div>
                    )}

                    {d.evidence_references && (
                      <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Evidence</p>
                        <p className="text-slate-700 font-mono text-xs">{d.evidence_references}</p>
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="p-8 text-center">
                <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 mx-auto mb-4">
                  <CheckCircle className="w-6 h-6" />
                </div>
                <p className="text-emerald-600 font-medium">No discrepancies found</p>
                <p className="text-xs text-slate-500 mt-1">All documents match within configured tolerances.</p>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-900">Extracted Data</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="px-6 py-3 text-xs font-semibold text-slate-500">Document</th>
                <th className="px-6 py-3 text-xs font-semibold text-slate-500">Field</th>
                <th className="px-6 py-3 text-xs font-semibold text-slate-500">Value</th>
              </tr>
            </thead>
            <tbody>
              {[...DOCUMENT_TYPES_ORDER].flatMap((dt) => {
                const ext = extractions[dt.value];
                if (!ext) return [];
                const rows: Array<{ label: string; value: string }> = [];
                if (ext.document_number) rows.push({ label: "Document Number", value: ext.document_number });
                if (ext.document_date) rows.push({ label: "Document Date", value: ext.document_date });
                if (ext.vendor_name) rows.push({ label: "Vendor", value: ext.vendor_name });
                if (ext.purchase_order_reference) rows.push({ label: "PO Reference", value: ext.purchase_order_reference });
                if (ext.currency) rows.push({ label: "Currency", value: ext.currency });
                if (ext.subtotal) rows.push({ label: "Subtotal", value: formatCurrency(ext.subtotal) });
                if (ext.tax_amount) rows.push({ label: "Tax", value: formatCurrency(ext.tax_amount) });
                if (ext.grand_total) rows.push({ label: "Grand Total", value: formatCurrency(ext.grand_total) });
                return rows.map((r, i) => (
                  <tr key={`${dt.value}-${i}`} className="border-b border-slate-50 last:border-0">
                    <td className="px-6 py-3 text-sm text-slate-600">{dt.label}</td>
                    <td className="px-6 py-3 text-sm text-slate-600">{r.label}</td>
                    <td className="px-6 py-3 text-sm font-medium text-slate-900">{r.value}</td>
                  </tr>
                ));
              })}
              {Object.values(extractions).every((e) => !e) && (
                <tr>
                  <td colSpan={3} className="px-6 py-8 text-center text-slate-500">
                    No extracted data available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
