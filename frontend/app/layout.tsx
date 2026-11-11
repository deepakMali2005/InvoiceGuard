import Link from "next/link";

import "./globals.css";

export const metadata = { title: "InvoiceGuard" };

const NAV_ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/cases", label: "Cases" },
  { href: "/cases/new", label: "New Reconciliation" },
  { href: "/evaluation", label: "Evaluation" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 antialiased">
        <div className="flex h-screen overflow-hidden">
          <aside className="hidden lg:flex flex-col w-64 bg-slate-900 text-slate-300 border-r border-slate-800">
            <div className="flex items-center gap-3 px-6 py-6">
              <div className="w-8 h-8 rounded bg-blue-600 flex items-center justify-center text-white font-bold">
                IG
              </div>
              <span className="font-bold text-lg tracking-tight text-white">InvoiceGuard</span>
            </div>
            <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
              {NAV_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
                >
                  {item.label}
                </Link>
              ))}
              <div className="px-3 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                System
              </div>
              <Link
                href="/evaluation"
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors text-white bg-slate-800"
              >
                Evaluation
              </Link>
            </nav>
            <div className="p-4 border-t border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-blue-600 flex items-center justify-center text-white text-sm font-medium">
                  AD
                </div>
                <div>
                  <div className="text-sm font-medium text-white">Admin User</div>
                  <div className="text-xs text-slate-500">invoiceguard.local</div>
                </div>
              </div>
            </div>
          </aside>
          <div className="flex-1 flex flex-col overflow-hidden">
            <header className="flex-none h-16 border-b border-slate-200 bg-white px-6 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <h1 className="text-lg font-semibold text-slate-900">InvoiceGuard</h1>
              </div>
              <div className="flex items-center gap-3">
                <Link href="/" className="text-sm font-medium text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg hover:bg-slate-100">
                  Dashboard
                </Link>
              </div>
            </header>
            <main className="flex-1 overflow-y-auto p-6">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
