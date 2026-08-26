import { Outlet } from "react-router-dom";

import Navigation from "./Navigation";

export default function AppLayout() {
  return (
    <div className="min-h-full">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <div>
            <p className="text-lg font-semibold text-slate-900">
              Resume Tailor
            </p>
            <p className="text-xs text-slate-500">
              Truth-constrained resume tailoring
            </p>
          </div>
          <Navigation />
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
