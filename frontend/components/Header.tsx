"use client";

import React, { useEffect, useState } from "react";
import { Activity, Plus, RefreshCw, Search, ShieldCheck } from "lucide-react";

interface HeaderProps {
  onNewInvestigation: () => void;
  onRefreshCases: () => void;
  isRefreshing?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ onNewInvestigation, onRefreshCases, isRefreshing = false }) => {
  const [backendStatus, setBackendStatus] = useState<"connected" | "disconnected" | "checking">("checking");

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch("http://localhost:8000/health");
        setBackendStatus(response.ok ? "connected" : "disconnected");
      } catch {
        setBackendStatus("disconnected");
      }
    };
    checkHealth();
    const interval = window.setInterval(checkHealth, 15000);
    return () => window.clearInterval(interval);
  }, []);

  return (
    <header className="sticky top-0 z-30 border-b border-white/[0.07] bg-[#090d15]/90 backdrop-blur-xl">
      <div className="flex h-[70px] items-center gap-3 px-3 sm:px-5 lg:px-6">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-orange-500 text-white lg:hidden">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold tracking-tight text-white sm:text-base">Fraud Investigation Center</p>
            <p className="hidden text-[11px] text-slate-500 sm:block">Graph-grounded case intelligence and policy control</p>
          </div>
        </div>

        <div className="hidden h-9 w-full max-w-xs items-center gap-2 rounded-xl border border-white/[0.07] bg-white/[0.035] px-3 text-slate-500 xl:flex">
          <Search className="h-4 w-4" />
          <span className="text-xs">Search entities, cases, evidence</span>
          <span className="ml-auto rounded border border-white/10 px-1.5 py-0.5 font-mono text-[9px]">⌘K</span>
        </div>

        <div className="hidden items-center gap-2 rounded-full border border-white/[0.07] bg-white/[0.035] px-3 py-1.5 sm:flex">
          <Activity className={`h-3.5 w-3.5 ${backendStatus === "connected" ? "text-emerald-400" : backendStatus === "checking" ? "text-amber-400" : "text-red-400"}`} />
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
            {backendStatus === "connected" ? "Systems online" : backendStatus === "checking" ? "Checking" : "API offline"}
          </span>
        </div>

        <button onClick={onRefreshCases} disabled={isRefreshing} title="Refresh cases" className="grid h-9 w-9 place-items-center rounded-xl border border-white/[0.08] bg-white/[0.035] text-slate-400 transition hover:bg-white/[0.07] hover:text-white disabled:opacity-50">
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
        </button>
        <button onClick={onNewInvestigation} className="flex h-9 items-center gap-2 rounded-xl bg-orange-500 px-3 text-xs font-bold text-white shadow-[0_8px_24px_rgba(249,115,22,0.22)] transition hover:bg-orange-400 sm:px-4">
          <Plus className="h-4 w-4" />
          <span className="hidden sm:inline">New investigation</span>
        </button>
      </div>
    </header>
  );
};
