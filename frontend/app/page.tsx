"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, CheckCircle, Clock, FileText, ArrowRight, ShieldAlert, Plus } from "lucide-react";
import { health, listCases } from "@/app/lib/api";
import { STATUS_CONFIG } from "@/app/lib/constants";
import Link from "next/link";


export default function Dashboard() {
  const router = useRouter();
  const [healthData, setHealth] = useState<any>(null);
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    Promise.all([health(), listCases().catch(() => [])])
      .then(([h, c]) => {
        if (!mounted) return;
        setHealth(h);
        setCases(Array.isArray(c) ? c : []);
        setLoading(false);
      })
      .catch((e) => {
        if (!mounted) return;
        setError(e.message);
        setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const stats = [
    { label: "Total Cases", value: cases.length, icon: FileText, color: "text-slate-600" },
    {
      label: "Matched",
      value: cases.filter((c) => c.status === "RECONCILED").length,
      icon: CheckCircle,
      color: "text-emerald-600",
    },
    {
      label: "Discrepancies",
      value: cases.filter((c) => c.status === "DISCREPANCIES_FOUND").length,
      icon: AlertCircle,
      color: "text-rose-600",
    },
    {
      label: "Needs Review",
      value: cases.filter((c) => c.status === "NEEDS_REVIEW").length,
      icon: Clock,
      color: "text-amber-600",
    },
  ];

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-2">
          <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          <p className="text-sm text-slate-500">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
        <h2 className="text-lg font-semibold text-slate-900">Unable to load dashboard</h2>
        <p className="text-slate-500 mt-1">{error}</p>
      </div>
    );
  }

  const recentCases = cases.slice(0, 8);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-slate-500">Overview of your reconciliation cases and system status.</p>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">{s.label}</p>
                <p className="text-2xl font-bold text-slate-900">{s.value}</p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center text-slate-500">
                <s.icon className="w-5 h-5" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recent cases */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-600" />
            <h2 className="text-sm font-semibold text-slate-900">Recent Cases</h2>
          </div>
          <Link href="/cases" className="text-sm text-blue-600 hover:text-blue-700 font-medium">
            View all →
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="px-6 py-3 text-xs font-semibold text-slate-500">Case Reference</th>
                <th className="px-6 py-3 text-xs font-semibold text-slate-500">Vendor</th>
                <th className="px-6 py-3 text-xs font-semibold text-slate-500">Status</th>
                <th className="px-6 py-3 text-xs font-semibold text-slate-500">Created</th>
                <th className="px-6 py-3 text-xs font-semibold text-slate-500 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {recentCases.length > 0 ? (
                recentCases.map((c) => {
                  const cfg = STATUS_CONFIG[c.status] || STATUS_CONFIG.CREATED;
                  return (
                    <tr
                      key={c.id}
                      onClick={() => router.push(`/cases/${c.id}`)}
                      className="border-b border-slate-100 hover:bg-slate-100 hover:shadow-sm transition-all duration-200 cursor-pointer group"
                    >
                      <td className="px-6 py-3 text-sm font-medium text-slate-900">
                        {c.case_reference}
                      </td>
                      <td className="px-6 py-3 text-sm text-slate-600">{c.vendor_name || "—"}</td>
                      <td className="px-6 py-3">
                        <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.color}`}>
                          {cfg.label}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-sm text-slate-600">
                        {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-6 py-3 text-right">
                        <Link
                          href={`/cases/${c.id}`}
                          className="text-xs font-medium text-blue-600 hover:text-blue-700 flex items-center gap-1"
                        >
                          Open <ArrowRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-500">
                    No cases yet. <Link href="/cases/new" className="text-blue-600 hover:text-blue-700 font-medium">Create your first case</Link>.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        {cases.length > 8 && (
          <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 text-center">
            <Link
              href="/cases"
              className="inline-flex items-center gap-1.5 px-4 py-2.5 border border-slate-200 text-slate-700 rounded-lg font-medium hover:bg-slate-100 hover:text-blue-700 transition-colors"
            >
              <ShieldAlert className="w-4 h-4" /> View All Cases ({cases.length})
            </Link>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Plus className="w-5 h-5 text-blue-600" />
            <h2 className="text-sm font-semibold text-slate-900">Quick Actions</h2>
          </div>
        </div>
        <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            href="/cases/new"
            className="flex flex-col items-center gap-3 px-6 py-4 border border-slate-200 rounded-xl bg-white hover:bg-blue-50 hover:border-blue-200 transition-colors group"
          >
            <Plus className="w-8 h-8 text-blue-600 group-hover:text-blue-700 transition-colors" />
            <span className="text-sm font-semibold text-slate-900">New Reconciliation</span>
            <span className="text-xs text-slate-500">Upload PO, Invoice & GRN</span>
          </Link>
          <Link
            href="/cases"
            className="flex flex-col items-center gap-3 px-6 py-4 border border-slate-200 rounded-xl bg-white hover:bg-blue-50 hover:border-blue-200 transition-colors group"
          >
            <ShieldAlert className="w-8 h-8 text-blue-600 group-hover:text-blue-700 transition-colors" />
            <span className="text-sm font-semibold text-slate-900">Browse Cases</span>
            <span className="text-xs text-slate-500">Manage all cases</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
