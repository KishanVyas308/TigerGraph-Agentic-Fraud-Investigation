"use client";

import React, { useState } from "react";
import { CaseQueueItem } from "@/types/api";
import { RiskBadge, CaseStatusBadge, ActionBadge } from "./StatusBadge";
import { Search, ShieldQuestion, ArrowRight, ListFilter } from "lucide-react";

interface CaseQueueProps {
  cases: CaseQueueItem[];
  selectedCaseId: string | null;
  onSelectCase: (caseId: string) => void;
  isLoading: boolean;
}

export const CaseQueue: React.FC<CaseQueueProps> = ({
  cases,
  selectedCaseId,
  onSelectCase,
  isLoading,
}) => {
  const [filterTab, setFilterTab] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const filteredCases = cases.filter((c) => {
    // Tab filter
    if (filterTab === "IN_PROGRESS" && c.status !== "IN_PROGRESS") return false;
    if (filterTab === "AWAITING_APPROVAL" && c.status !== "AWAITING_APPROVAL") return false;
    if (filterTab === "COMPLETED" && c.status !== "COMPLETED" && c.status !== "RESOLVED") return false;

    // Search query filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = c.case_id.toLowerCase().includes(q);
      const matchTrigger = (c.trigger_type || "").toLowerCase().includes(q);
      const matchRisk = (c.risk_level || "").toLowerCase().includes(q);
      return matchId || matchTrigger || matchRisk;
    }

    return true;
  });

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-2xl border border-white/[0.07] bg-[#0b1019]/90 shadow-2xl shadow-black/20 backdrop-blur-xl">
      {/* Top Filter & Search Bar */}
      <div className="flex flex-col gap-3 border-b border-white/[0.07] p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <ListFilter className="h-4 w-4 text-orange-400" />
            <h3 className="text-xs font-bold uppercase tracking-[0.14em] text-slate-200">
              Case queue
            </h3>
            <span className="rounded-full border border-white/[0.07] bg-white/[0.04] px-2 py-0.5 font-mono text-[10px] text-slate-400">
              {filteredCases.length}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1 overflow-x-auto rounded-xl border border-white/[0.06] bg-black/20 p-1 text-xs">
            {["ALL", "IN_PROGRESS", "AWAITING_APPROVAL", "COMPLETED"].map((tab) => (
              <button
                key={tab}
                onClick={() => setFilterTab(tab)}
                className={`whitespace-nowrap rounded-lg px-2.5 py-1.5 text-[9px] font-semibold transition-all ${
                  filterTab === tab
                    ? "border border-orange-500/30 bg-orange-500/15 text-orange-300"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab.replace(/_/g, " ")}
              </button>
            ))}
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search by case ID, trigger, or risk level..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-xl border border-white/[0.07] bg-black/20 py-2 pl-9 pr-4 text-xs text-slate-200 placeholder:text-slate-600 focus:border-orange-500/50 focus:outline-none"
          />
        </div>
      </div>

      {/* Case List Body */}
      <div className="flex-1 divide-y divide-white/[0.055] overflow-y-auto">
        {isLoading && cases.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-2 border-orange-500 border-t-transparent mb-3" />
            <p className="text-xs font-mono">Loading investigation cases from TigerGraph...</p>
          </div>
        ) : filteredCases.length === 0 ? (
          <div className="p-8 text-center text-slate-500 flex flex-col items-center justify-center">
            <ShieldQuestion className="w-10 h-10 text-slate-600 mb-2 stroke-[1.5]" />
            <p className="text-sm font-semibold text-slate-300">No matching cases found</p>
            <p className="text-xs text-slate-500 mt-1">
              Trigger a new investigation or change filter parameters.
            </p>
          </div>
        ) : (
          filteredCases.map((c) => {
            const isSelected = selectedCaseId === c.case_id;

            return (
              <div
                key={c.case_id}
                onClick={() => onSelectCase(c.case_id)}
                className={`relative flex cursor-pointer flex-col gap-2.5 px-4 py-4 transition-all ${
                  isSelected
                    ? "bg-gradient-to-r from-orange-500/[0.13] to-transparent before:absolute before:inset-y-3 before:left-0 before:w-0.5 before:rounded-full before:bg-orange-400"
                    : "hover:bg-white/[0.035]"
                }`}
              >
                {/* Header row: ID & Status */}
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs font-bold text-slate-200 truncate">
                    {c.case_id}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <CaseStatusBadge status={c.status} />
                    {isSelected && (
                      <ArrowRight className="w-3.5 h-3.5 text-orange-400 animate-pulse" />
                    )}
                  </div>
                </div>

                {/* Sub row: Trigger & Risk */}
                <div className="flex items-center justify-between gap-2 text-xs">
                  <span className="text-[11px] text-slate-400 font-medium truncate">
                    {c.trigger_type.replace(/_/g, " ")}
                  </span>
                  <RiskBadge level={c.risk_level} size="sm" />
                </div>

                {/* Footer row: Action / Created */}
                <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-brand-800/60">
                  {c.primary_action ? (
                    <ActionBadge actionType={c.primary_action} />
                  ) : (
                    <span className="italic text-slate-500">Evaluating...</span>
                  )}
                  <span className="font-mono">
                    {new Date(c.created_at).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
