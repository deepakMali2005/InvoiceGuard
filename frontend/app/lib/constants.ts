export const DOCUMENT_TYPES = [
  { value: "PURCHASE_ORDER", label: "Purchase Order", icon: "FileText" },
  { value: "VENDOR_INVOICE", label: "Vendor Invoice", icon: "FileText" },
  { value: "GOODS_RECEIPT_NOTE", label: "Goods Receipt Note", icon: "FileText" },
] as const;

export const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  CREATED: { label: "Created", color: "text-slate-600", bg: "bg-slate-50" },
  PROCESSING: { label: "Processing", color: "text-blue-600", bg: "bg-blue-50" },
  READY_FOR_RECONCILIATION: { label: "Ready", color: "text-amber-600", bg: "bg-amber-50" },
  RECONCILED: { label: "Reconciled", color: "text-emerald-600", bg: "bg-emerald-50" },
  NEEDS_REVIEW: { label: "Needs Review", color: "text-orange-600", bg: "bg-orange-50" },
  DISCREPANCIES_FOUND: { label: "Discrepancies", color: "text-rose-600", bg: "bg-rose-50" },
  FAILED: { label: "Failed", color: "text-slate-600", bg: "bg-slate-50" },
};

export const DISCREPANCY_CONFIG: Record<string, { label: string; color: string }> = {
  PRICE_MISMATCH: { label: "Price Mismatch", color: "text-rose-600" },
  QUANTITY_MISMATCH: { label: "Quantity Mismatch", color: "text-rose-600" },
  UNORDERED_ITEM: { label: "Unordered Item", color: "text-rose-600" },
  UNBILLED_RECEIPT: { label: "Unbilled Receipt", color: "text-amber-600" },
  MISSING_LINE_ITEM: { label: "Missing Line Item", color: "text-amber-600" },
  REFERENCE_MISMATCH: { label: "Reference Mismatch", color: "text-rose-600" },
  ARITHMETIC_INCONSISTENCY: { label: "Arithmetic Error", color: "text-amber-600" },
};

export function formatCurrency(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return "—";
  }
}
