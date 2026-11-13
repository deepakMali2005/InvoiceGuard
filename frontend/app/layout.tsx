import Link from "next/link";

import "./globals.css";

export const metadata = { title: "InvoiceGuard" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-slate-900 antialiased">
        <div className="flex h-screen flex-col overflow-hidden">
          <header className="flex-none h-16 border-b border-slate-200 bg-white px-6 flex items-center justify-between">
            <div className="flex items-center gap-3 cursor-pointer">
              <Link href="/" className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-blue-500/20">
                  IG
                </div>
                <span className="font-bold text-lg tracking-tight text-slate-900">InvoiceGuard</span>
              </Link>
            </div>
            <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-600">
              <Link
                href="/"
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg transition-colors hover:bg-slate-100 hover:text-slate-900"
              >
                Dashboard
              </Link>
              <Link
                href="/cases"
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg transition-colors hover:bg-slate-100 hover:text-slate-900"
              >
                Cases
              </Link>
              <Link
                href="/cases/new"
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg transition-colors hover:bg-slate-100 hover:text-slate-900"
              >
                New Reconciliation
              </Link>
            </nav>
          </header>
          <div className="flex-1 overflow-y-auto p-6">
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
