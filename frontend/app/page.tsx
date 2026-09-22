import React from "react";
import { ShieldAlert, Activity, CheckCircle2 } from "lucide-react";

export default function HomePage() {
  return (
    <main className="min-h-screen p-8 max-w-6xl mx-auto flex flex-col gap-8">
      <header className="flex items-center justify-between border-b border-slate-800 pb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-indigo-600/20 border border-indigo-500/40 text-indigo-400">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              TigerGraph Agentic Fraud Investigation
            </h1>
            <p className="text-sm text-slate-400">
              Analyst Investigation & Decision Console
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-950/60 border border-emerald-500/30 text-emerald-400 text-xs">
          <CheckCircle2 className="w-4 h-4" />
          <span>Layer 0 Bootstrap Active</span>
        </div>
      </header>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-xl bg-slate-900/50 border border-slate-800">
          <div className="flex items-center gap-2 text-indigo-400 font-semibold mb-2">
            <Activity className="w-5 h-5" />
            <span>Graph Analytics Engine</span>
          </div>
          <p className="text-sm text-slate-400">
            TigerGraph Savanna & GSQL deterministic pattern detection for accounts, devices, and transactions.
          </p>
        </div>

        <div className="p-6 rounded-xl bg-slate-900/50 border border-slate-800">
          <div className="flex items-center gap-2 text-emerald-400 font-semibold mb-2">
            <Activity className="w-5 h-5" />
            <span>GraphRAG Knowledge</span>
          </div>
          <p className="text-sm text-slate-400">
            Fraud policy retrieval, typologies, regulatory context, and historical case precedents.
          </p>
        </div>

        <div className="p-6 rounded-xl bg-slate-900/50 border border-slate-800">
          <div className="flex items-center gap-2 text-amber-400 font-semibold mb-2">
            <Activity className="w-5 h-5" />
            <span>LangGraph Decision Control</span>
          </div>
          <p className="text-sm text-slate-400">
            Structured reasoning with uncertainty gate, value-of-information evidence planner, and policy authorization.
          </p>
        </div>
      </section>

      <section className="p-6 rounded-xl bg-slate-900/40 border border-slate-800/80">
        <h2 className="text-lg font-semibold text-white mb-2">System Status</h2>
        <div className="text-sm text-slate-400 flex flex-col gap-1">
          <p>• Backend: FastAPI on port 8000 (Health Check: <code className="text-indigo-300">/health</code>)</p>
          <p>• Frontend: Next.js with React 18, TypeScript, Tailwind CSS</p>
          <p>• Active Layer: Layer 0 (Repository Bootstrap & Local Config)</p>
        </div>
      </section>
    </main>
  );
}
