"use client";

import React, { useEffect, useState } from "react";
import {
  ShieldAlert,
  Activity,
  PlusCircle,
  Database,
  Cpu,
  RefreshCw,
} from "lucide-react";

interface HeaderProps {
  onNewInvestigation: () => void;
  onRefreshCases: () => void;
  isRefreshing?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  onNewInvestigation,
  onRefreshCases,
  isRefreshing = false,
}) => {
  const [backendStatus, setBackendStatus] = useState<"connected" | "disconnected" | "checking">("checking");

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch("http://localhost:8000/health", { method: "GET" });
        if (res.ok) {
          setBackendStatus("connected");
        } else {
          setBackendStatus("disconnected");
        }
      } catch {
        setBackendStatus("disconnected");
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="sticky top-0 z-30 w-full border-b border-brand-700/60 bg-brand-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo & Name */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500/20 via-orange-500/10 to-transparent border border-orange-500/30 text-orange-400 shadow-glow-high">
            <ShieldAlert className="w-5 h-5 text-orange-400" />
            <span className="absolute -bottom-1 -right-1 flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-orange-500" />
            </span>
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-base font-extrabold tracking-tight text-white flex items-center gap-1.5">
                TIGER<span className="text-orange-400">GRAPH</span>
              </span>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider bg-orange-500/10 text-orange-400 border border-orange-500/20">
                Agentic Engine
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium">
              Autonomous Fraud Investigation & Precedent Memory Console
            </p>
          </div>
        </div>

        {/* Tech Stack Indicators & Actions */}
        <div className="flex items-center gap-4">
          {/* Stack Badges */}
          <div className="hidden md:flex items-center gap-3 pr-4 border-r border-slate-800 text-xs text-slate-400">
            <span className="flex items-center gap-1 font-mono">
              <Database className="w-3.5 h-3.5 text-orange-400" /> Savanna/GSQL
            </span>
            <span className="flex items-center gap-1 font-mono">
              <Cpu className="w-3.5 h-3.5 text-indigo-400" /> LangGraph + Groq
            </span>
          </div>

          {/* Backend Connection Pill */}
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-brand-900 border border-brand-700 text-xs">
            <Activity
              className={`w-3.5 h-3.5 ${
                backendStatus === "connected"
                  ? "text-emerald-400 animate-pulse"
                  : backendStatus === "checking"
                  ? "text-amber-400"
                  : "text-red-400"
              }`}
            />
            <span className="font-mono text-[11px] text-slate-300">
              {backendStatus === "connected"
                ? "API Active (8000)"
                : backendStatus === "checking"
                ? "Connecting..."
                : "API Offline"}
            </span>
          </div>

          {/* Refresh Cases Button */}
          <button
            onClick={onRefreshCases}
            disabled={isRefreshing}
            className="p-2 rounded-lg bg-brand-900 hover:bg-brand-800 border border-brand-700 text-slate-300 hover:text-white transition-all disabled:opacity-50"
            title="Refresh Cases"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-cyan-400" : ""}`} />
          </button>

          {/* Launch Investigation Action */}
          <button
            onClick={onNewInvestigation}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white font-semibold text-xs shadow-glow-high transition-all active:scale-95"
          >
            <PlusCircle className="w-4 h-4" />
            <span>New Investigation</span>
          </button>
        </div>
      </div>
    </header>
  );
};
