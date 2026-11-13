"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  Search,
  Plus,
  AlertCircle,
  Trash2,
  ShieldAlert,
} from "lucide-react";
import { listCases, deleteCase } from "@/app/lib/api";
import { STATUS_CONFIG } from "@/app/lib/constants";

export default function CasesList() {
  const router = useRouter();
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<{ id: string; ref: string } | null>(null);

  useEffect(() => {
    loadCases();
  }, []);

  async function loadCases() {
    try {
      const data = await listCases();
      setCases(Array.isArray(data) ? data : []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  const filtered = cases.filter((c) => {
    const matchesSearch =
      c.case_reference?.toLowerCase().includes(search.toLowerCase()) ||
      (c.vendor_name || "").toLowerCase().includes(search.toLowerCase());
    const matchesStatus = !statusFilter || c.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statusOptions = Object.entries(STATUS_CONFIG) as [string, { label: string; color: string; bg: string }][];

  const handleDelete = async (id: string, ref: string) => {
    setDeleting(id);
    try {
      await deleteCase(id);
      setCases((prev) => prev.filter((c) => c.id !== id));
      setConfirmDelete(null);
    } catch (err: any) {
      setError(err.message || "Failed to delete case");
    } finally {
      setDeleting(null);
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin" />
          <p className="text-sm text-slate-500">Loading cases...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white">
              <FileText className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900">Cases</h1>
          </div>
          <p className="text-slate-500 mt-1">Manage and review your reconciliation cases.</p>
        </div>
        <Link
          href="/cases/new"
          className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg shadow-sm hover:bg-blue-700 transition-colors font-medium"
        >
          <Plus className="w-4 h-4" />
          New Case
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <div className="flex flex-col md:flex-row gap-4 items-end">
          <div className="relative flex-1 md:flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search by case reference or vendor..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors"
            />
          </div>
          <div className="relative flex-1 md:flex-1">
            <ShieldAlert className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-slate-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors appearance-none cursor-pointer"
            >
              <option value="">All Statuses</option>
              {statusOptions.map(([key, cfg]) => (
                <option key={key} value={key}>
                  {cfg.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute right-3 top-3 text-slate-400">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>
            </div>
          </div>
          <button
            onClick={() => router.push("/cases/new")}
            className="px-4 py-3 border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Create Case
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Case Reference</th>
                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Vendor</th>
                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Documents</th>
                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Created</th>
                <th className="px-6 py-4 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length > 0 ? (
                filtered.map((c) => {
                  const cfg = STATUS_CONFIG[c.status] || STATUS_CONFIG.CREATED;
                  const isDeleting = deleting === c.id;
                  return (
                    <tr
                      key={c.id}
                      onClick={() => router.push(`/cases/${c.id}`)}
                      className="border-b border-slate-50 hover:bg-slate-100 hover:shadow-sm transition-all duration-200 cursor-pointer group"
                    >
                      <td className="px-6 py-4 text-sm font-medium text-slate-900">
                        {c.case_reference}
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">{c.vendor_name || "—"}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.color}`}>
                          {cfg.label}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">3/3</td>
                      <td className="px-6 py-4 text-sm text-slate-600">
                        {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            href={`/cases/${c.id}`}
                            className="text-xs font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1"
                          >
                            View Details
                            <ShieldAlert className="w-3 h-3" />
                          </Link>
                          {confirmDelete?.id === c.id ? (
                            <button
                              onClick={() => handleDelete(c.id, c.case_reference)}
                              disabled={isDeleting}
                              className="px-2 py-1.5 bg-rose-600 text-white rounded-lg hover:bg-rose-700 transition-colors flex items-center justify-center"
                            >
                              {isDeleting ? (
                                <svg className="w-3 h-3 animate-spin text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                              ) : (
                                <Trash2 className="w-3 h-3" />
                              )}
                            </button>
                          ) : (
                            <button
                              onClick={() => setConfirmDelete({ id: c.id, ref: c.case_reference })}
                              disabled={isDeleting}
                              className="text-xs font-medium text-rose-600 hover:text-rose-800 hover:bg-rose-50 rounded-lg px-2 py-1.5 transition-colors flex items-center gap-1"
                            >
                              <Trash2 className="w-3 h-3" />
                              Delete
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={6} className="px-6 py-16 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mx-auto">
                        <FileText className="w-8 h-8" />
                      </div>
                      <p className="text-sm font-medium text-slate-900">No cases found</p>
                      <p className="text-xs text-slate-500 max-w-xs mx-auto">
                        Try adjusting your search or filter criteria, or create your first case.
                      </p>
                      <Link
                        href="/cases/new"
                        className="mt-4 inline-flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium shadow-sm hover:bg-blue-700 transition-colors"
                      >
                        <Plus className="w-4 h-4" />
                        Create New Case
                      </Link>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Delete confirmation dialog */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm transition-opacity" onClick={() => setConfirmDelete(null)} />
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 relative animate-in fade-in zoom-in duration-200">
            <button
              onClick={() => setConfirmDelete(null)}
              className="absolute right-4 top-4 text-slate-400 hover:text-slate-600 transition-colors"
            >
              <svg className="w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
            <div className="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center text-rose-600 mx-auto mb-4">
              <Trash2 className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-slate-900 mb-2 text-center">Delete Case</h2>
            <p className="text-slate-600 mb-6 text-center">
              Are you sure you want to delete case <strong className="text-slate-900">{confirmDelete.ref}</strong>? This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmDelete(null)}
                className="flex-1 px-4 py-3 border border-slate-200 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(confirmDelete.id, confirmDelete.ref)}
                disabled={deleting === confirmDelete.id}
                className="flex-1 px-4 py-3 bg-rose-600 text-white rounded-lg shadow-sm hover:bg-rose-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {deleting === confirmDelete.id ? "Deleting..." : "Delete Case"}
              </button>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-rose-50 border border-rose-100">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-rose-600" />
            <p className="text-sm text-rose-700">{error}</p>
          </div>
        </div>
      )}
    </div>
  );
}
