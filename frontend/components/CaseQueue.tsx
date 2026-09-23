"use client";

import React, { useState } from "react";
import { CaseQueueItem } from "@/types/api";
import { RiskBadge, CaseStatusBadge, ActionBadge } from "./StatusBadge";
import { Search, Filter, ShieldQuestion, ArrowRight } from "lucide-react";

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
    <div className="flex flex-col h-full bg-brand-900/60 border border-brand-700/60 rounded-xl overflow-hidden glass-panel">
      {/* Top Filter & Search Bar */}
      <div className="p-3.5 border-b border-brand-700/60 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-orange-400" />
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
              Investigation Queue
            </h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-brand-800 text-slate-400 border border-brand-700 font-mono">
              {filteredCases.length}
            </span>
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center gap-1 bg-brand-950/80 p-0.5 rounded-lg border border-brand-700/60 text-xs">
            {["ALL", "IN_PROGRESS", "AWAITING_APPROVAL", "COMPLETED"].map((tab) => (
              <button
                key={tab}
                onClick={() => setFilterTab(tab)}
                className={`px-2.5 py-1 rounded font-medium transition-all ${
                  filterTab === tab
                    ? "bg-orange-500/20 text-orange-400 border border-orange-500/40"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab.replace(/_/g, " ")}
              </button>
            ))}
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search by case ID, trigger, or risk level..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 bg-brand-950/90 border border-brand-700 rounded-lg text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-orange-500/60 transition-colors"
          />
        </div>
      </div>

      {/* Case List Body */}
      <div className="flex-1 overflow-y-auto divide-y divide-brand-700/40">
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
                className={`p-3.5 cursor-pointer transition-all flex flex-col gap-2 ${
                  isSelected
                    ? "bg-orange-500/10 border-l-4 border-l-orange-500 border-r-0 border-y-0"
                    : "hover:bg-brand-800/40 border-l-4 border-l-transparent"
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
