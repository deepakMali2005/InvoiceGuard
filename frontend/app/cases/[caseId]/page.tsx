"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  AlertCircle,
  CheckCircle,
  Loader2,
  Trash2,
  DownloadIcon,
  FileText,
  ArrowLeftIcon,
  ExternalLink,
  ShieldAlert,
  Table,
} from "lucide-react";
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
  { value: "PURCHASE_ORDER", label: "Purchase Order", color: "text-blue-600" },
  { value: "VENDOR_INVOICE", label: "Vendor Invoice", color: "text-indigo-600" },
  { value: "GOODS_RECEIPT_NOTE", label: "Goods Receipt Note", color: "text-emerald-600" },
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

  // Build a unified line-item comparison table
  const allItems: Array<{
    description: string;
    code: string;
    poQty: string;
    poPrice: string;
    poTotal: string;
    invQty: string;
    invPrice: string;
    invTotal: string;
    grnQty: string;
    grnPrice: string;
    grnTotal: string;
  }> = [];

  const poItems = poExt?.line_items || [];
  const invItems = invoiceExt?.line_items || [];
  const grnItems = grnExt?.line_items || [];

  // Simple match by product code
  const codes = new Set([
    ...poItems.map((i: any) => i.product_code),
    ...invItems.map((i: any) => i.product_code),
    ...grnItems.map((i: any) => i.product_code),
  ]);

  codes.forEach((code) => {
    const p = poItems.find((i: any) => i.product_code === code);
    const i = invItems.find((it: any) => it.product_code === code);
    const g = grnItems.find((it: any) => it.product_code === code);
    allItems.push({
      description: (p?.description || i?.description || g?.description || "Unknown"),
      code: code || "—",
      poQty: p?.quantity || "—",
      poPrice: p?.unit_price || "—",
      poTotal: p?.line_total || "—",
      invQty: i?.quantity || "—",
      invPrice: i?.unit_price || "—",
      invTotal: i?.line_total || "—",
      grnQty: g?.quantity || "—",
      grnPrice: g?.unit_price || "—",
      grnTotal: g?.line_total || "—",
    });
  });

  return (
    <div className="space-y-6">
      {/* Header */}
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
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 text-xs font-semibold border border-amber-200">
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
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg shadow-sm hover:bg-blue-700 transition-colors font-medium border-0"
          >
            <DownloadIcon className="w-4 h-4" /> Download PDF Report
          </button>
          <button
            onClick={() => handleDownload("csv")}
            className="flex items-center gap-2 px-4 py-2.5 border border-slate-200 text-slate-700 rounded-lg shadow-sm hover:bg-slate-50 transition-colors font-medium"
          >
            <DownloadIcon className="w-4 h-4" /> Download CSV
          </button>
        </div>
      </div>

      {/* Document status row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {DOCUMENT_TYPES_ORDER.map((dt) => {
          const doc = documents.find((d: any) => d.document_type === dt.value);
          const ext = extractions[dt.value];
          const isExtracting = extracting === dt.value;
          return (
            <div
              key={dt.value}
              className={`bg-white rounded-2xl p-5 shadow-sm border ${
                doc ? "border-blue-100" : "border-slate-200"
              } ${doc ? "bg-blue-50/30" : "bg-slate-50"}`}
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${dt.color}10 text-${dt.color.split('-')[0]}-600`}>
                    <FileText className="w-4 h-4" />
                  </div>
                  <h3 className="text-sm font-semibold text-slate-900">{dt.label}</h3>
                </div>
                <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${
                  doc ? "bg-emerald-100 text-emerald-700 border-emerald-200" : "bg-slate-100 text-slate-500 border-slate-200"
                }`}>
                  {doc ? "Uploaded" : "Missing"}
                </span>
              </div>
              {doc ? (
                <>
                  <div className="mb-4 space-y-1">
                    <p className="text-xs text-slate-500 truncate">{doc.original_filename}</p>
                    <p className="text-xs text-slate-400">{formatDate(doc.created_at)}</p>
                  </div>
                  {ext ? (
                    <div className="space-y-2 mb-4">
                      <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Extracted</p>
                      <div className="space-y-1">
                        <p className="text-xs text-slate-600">
                          <span className="font-medium text-slate-400">Doc #:</span> {ext.document_number || "—"}
                        </p>
                        <p className="text-xs text-slate-600">
                          <span className="font-medium text-slate-400">Currency:</span> {ext.currency || "—"}
                        </p>
                        <p className="text-xs text-slate-600">
                          <span className="font-medium text-slate-400">Line Items:</span> {ext.line_items?.length || 0}
                        </p>
                        <p className="text-xs text-slate-600">
                          <span className="font-medium text-slate-400">Grand Total:</span> {formatCurrency(ext.grand_total)}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-rose-500 mb-4">Not extracted</p>
                  )}
                  <div className="flex items-center justify-between gap-2">
                    <button
                      onClick={() => handleExtract(dt.value)}
                      disabled={!!ext || isExtracting}
                      className={`flex-1 py-2.5 rounded-lg text-xs font-medium transition-colors flex items-center justify-center gap-1.5 border-0 ${
                        !!ext ? "bg-slate-100 text-slate-400 cursor-not-allowed" : isExtracting ? "bg-blue-50 text-blue-600" : "bg-blue-600 text-white hover:bg-blue-700"
                      }`}
                    >
                      {isExtracting ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : null}
                      {!!ext ? "Extracted" : "Extract"}
                    </button>
                    <button
                      onClick={() => handleDeleteDocument(doc.id, dt.label)}
                      className="p-2 rounded-lg text-rose-500 hover:bg-rose-50 hover:text-rose-700 transition-colors border-0"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </>
              ) : (
                <div className="pt-8 text-center">
                  <p className="text-xs text-slate-400">Not uploaded</p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Line Item Comparison */}
      {(poExt || invoiceExt || grnExt) && allItems.length > 0 && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Table className="w-5 h-5 text-blue-600" />
              <h2 className="text-sm font-semibold text-slate-900">Line Item Comparison</h2>
            </div>
            <span className="text-xs font-semibold text-slate-500">PO vs Invoice vs GRN</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Description</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Code</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">PO Qty</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">PO Price</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">Inv Qty</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">Inv Price</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">GRN Qty</th>
                  <th className="px-6 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">GRN Price</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {allItems.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-25/50 transition-colors group">
                    <td className="px-6 py-3 text-sm font-medium text-slate-900">{item.description}</td>
                    <td className="px-6 py-3 text-sm text-slate-600 font-mono">{item.code}</td>
                    <td className="px-6 py-3 text-sm text-slate-600 text-right">{item.poQty}</td>
                    <td className="px-6 py-3 text-sm text-slate-600 text-right">{item.poPrice}</td>
                    <td className="px-6 py-3 text-sm text-slate-600 text-right">{item.invQty}</td>
                    <td className="px-6 py-3 text-sm text-slate-600 text-right">{item.invPrice}</td>
                    <td className="px-6 py-3 text-sm text-slate-600 text-right">{item.grnQty}</td>
                    <td className="px-6 py-3 text-sm text-slate-600 text-right">{item.grnPrice}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Reconciliation Findings */}
      {reconciliation && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-rose-600" />
              <h2 className="text-sm font-semibold text-slate-900">Reconciliation Findings</h2>
            </div>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${
              reconciliation.overall_status === "DISCREPANCIES_FOUND" ? "bg-rose-50 text-rose-600 border-rose-100" :
              reconciliation.overall_status === "MATCHED" ? "bg-emerald-50 text-emerald-600 border-emerald-100" :
              "bg-amber-50 text-amber-600 border-amber-100"
            }`}>
              {reconciliation.findings_count} Findings
            </span>
          </div>
          <div className="divide-y divide-slate-100">
            {reconciliation.discrepancies?.length > 0 ? (
              reconciliation.discrepancies.map((d: any, i: number) => {
                const dc = DISCREPANCY_CONFIG[d.discrepancy_type] || { label: d.discrepancy_type, color: "text-slate-600" };
                const severityConfig = {
                  HIGH: { bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-100" },
                  MEDIUM: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-100" },
                  LOW: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-100" },
                };
                const sev = severityConfig[d.severity as keyof typeof severityConfig] || severityConfig.LOW;
                return (
                  <div key={i} className="p-5 last:border-0 group hover:bg-slate-25/50 transition-colors border-b border-slate-50">
                    <div className="flex items-start justify-between gap-3 mb-3">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-bold px-2 py-1 rounded-full ${dc.color}`}>
                          {dc.label}
                        </span>
                        <span className={`text-xs font-bold px-2 py-1 rounded-full ${sev.bg} ${sev.text} border ${sev.border}`}>
                          {d.severity}
                        </span>
                        {d.requires_review && (
                          <span className="text-xs font-bold px-2 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-100">
                            Review Required
                          </span>
                        )}
                      </div>
                    </div>
                    <p className="text-sm text-slate-700 mb-4">{d.description}</p>

                    {/* Plain Language Explanation - Prominent */}
                    {d.plain_language_explanation && (
                      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 mb-4 shadow-sm">
                        <div className="flex items-center gap-2 mb-2">
                          <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span className="text-xs font-bold text-emerald-700 uppercase tracking-wider">
                            What this means
                          </span>
                        </div>
                        <p className="text-sm text-emerald-800">{d.plain_language_explanation}</p>
                      </div>
                    )}

                    {/* Comparison Values */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
                      {(() => {
                        const isQty = d.discrepancy_type === "QUANTITY_MISMATCH";
                        const isPrice = d.discrepancy_type === "PRICE_MISMATCH";
                        const isArithmetic = d.discrepancy_type === "ARITHMETIC_INCONSISTENCY";
                        const isPoVsInv = isQty && d.description?.includes("ordered");
                        return (
                          <>
                            <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                                {isPoVsInv ? "Ordered Qty" : isQty ? "Invoiced Qty" : isPrice ? "PO Unit Price" : isArithmetic ? "Expected Total" : "Expected Value"}
                              </p>
                              <p className="text-sm font-bold text-slate-900">{d.expected_value || "—"}</p>
                            </div>
                            <div className="bg-rose-50 rounded-lg p-3 border border-rose-100">
                              <p className="text-xs font-bold text-rose-500 uppercase tracking-wider">
                                {isPoVsInv ? "Invoiced Qty" : isQty ? "Received Qty" : isPrice ? "Invoice Unit Price" : isArithmetic ? "Recorded Total" : "Actual Value"}
                              </p>
                              <p className="text-sm font-bold text-rose-700">{d.actual_value || "—"}</p>
                            </div>
                            <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Difference</p>
                              <p className="text-sm font-bold text-rose-600">{d.difference || "—"}</p>
                            </div>
                            <div className="bg-slate-100 rounded-lg p-3 border border-slate-200">
                              <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Severity</p>
                              <p className="text-sm font-bold text-slate-700 capitalize">{d.severity}</p>
                            </div>
                          </>
                        );
                      })()}
                    </div>

                    {d.calculation_details && (
                      <div className="bg-blue-50 rounded-lg p-3 mb-4 border border-blue-100">
                        <div className="flex items-center gap-2 mb-1">
                          <ShieldAlert className="w-3 h-3 text-blue-600" />
                          <p className="text-xs font-bold text-blue-700 uppercase tracking-wider">Calculation</p>
                        </div>
                        <p className="text-xs text-blue-900 font-mono">{d.calculation_details}</p>
                      </div>
                    )}

                    {d.evidence_references && (
                      <div className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                        <div className="flex items-center gap-2 mb-1">
                          <FileText className="w-3 h-3 text-slate-400" />
                          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Evidence</p>
                        </div>
                        <p className="text-xs text-slate-700 font-mono">{d.evidence_references}</p>
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="p-12 text-center">
                <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 mx-auto mb-4">
                  <CheckCircle className="w-8 h-8" />
                </div>
                <h3 className="text-emerald-700 font-bold text-lg mb-2">No discrepancies found</h3>
                <p className="text-slate-500 text-sm">All documents match within configured tolerances.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Extracted Data Detail */}
      {(poExt || invoiceExt || grnExt) && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-600" />
              <h2 className="text-sm font-semibold text-slate-900">Extracted Data</h2>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm divide-y divide-slate-50">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Document</th>
                  <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Field</th>
                  <th className="px-6 py-3 text-xs font-bold text-slate-500 uppercase tracking-wider">Value</th>
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
                    <tr key={`${dt.value}-${i}`} className="last:border-0">
                      <td className="px-6 py-3 text-sm text-slate-600">{dt.label}</td>
                      <td className="px-6 py-3 text-sm text-slate-600">{r.label}</td>
                      <td className="px-6 py-3 text-sm font-medium text-slate-900">{r.value}</td>
                    </tr>
                  ));
                })}
                {Object.values(extractions).every((e) => !e) && (
                  <tr>
                    <td colSpan={3} className="px-6 py-12 text-center text-slate-500">
                      No extracted data available.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
