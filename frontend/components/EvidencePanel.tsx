"use client";

import React, { useState } from "react";
import { EvidenceCard, EvidenceCategory, SubmitEvidenceRequest } from "@/types/api";
import {
  FileText,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  Database,
  Send,
  PlusCircle,
  Sparkles,
  ShieldCheck,
  Tag,
} from "lucide-react";

interface EvidencePanelProps {
  evidence: EvidenceCard[];
  onSubmitEvidence: (req: SubmitEvidenceRequest) => Promise<void>;
  isSubmitting?: boolean;
}

const CATEGORIES: Array<string> = [
  "ALL",
  "TRANSACTION_BEHAVIOR",
  "GRAPH_RELATIONSHIP",
  "DEVICE",
  "IDENTITY",
  "MONEY_FLOW",
  "POLICY",
  "REGULATION",
  "HISTORICAL_CASE",
  "CUSTOMER_RESPONSE",
  "ANALYST_INPUT",
];

export const EvidencePanel: React.FC<EvidencePanelProps> = ({
  evidence,
  onSubmitEvidence,
  isSubmitting = false,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [directionFilter, setDirectionFilter] = useState<"ALL" | "SUPPORTING" | "CONTRADICTORY">("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // New Evidence Form State
  const [showAddForm, setShowAddForm] = useState<boolean>(false);
  const [newCategory, setNewCategory] = useState<EvidenceCategory>("ANALYST_INPUT");
  const [newFact, setNewFact] = useState<string>("");
  const [newSourceRef, setNewSourceRef] = useState<string>("");

  // Filter evidence cards
  const filteredEvidence = evidence.filter((ev) => {
    // Category filter
    if (selectedCategory !== "ALL" && ev.category !== selectedCategory) {
      return false;
    }

    // Direction filter
    if (directionFilter === "SUPPORTING") {
      const hasSupport = ev.supports_hypotheses && ev.supports_hypotheses.length > 0;
      if (!hasSupport) return false;
    } else if (directionFilter === "CONTRADICTORY") {
      const hasContra = ev.contradicts_hypotheses && ev.contradicts_hypotheses.length > 0;
      if (!hasContra) return false;
    }

    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchFact = ev.fact.toLowerCase().includes(q);
      const matchId = ev.evidence_id.toLowerCase().includes(q);
      const matchSource = (ev.source || "").toLowerCase().includes(q);
      const matchRef = (ev.source_reference || "").toLowerCase().includes(q);
      return matchFact || matchId || matchSource || matchRef;
    }

    return true;
  });

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFact.trim()) return;

    await onSubmitEvidence({
      category: newCategory,
      fact: newFact.trim(),
      source_reference: newSourceRef.trim() || "Manual Analyst Note",
      reliability: 1.0,
    });

    setNewFact("");
    setNewSourceRef("");
    setShowAddForm(false);
  };

  const getSourceBadgeStyle = (source: string) => {
    const s = (source || "").toUpperCase();
    if (s.includes("TIGERGRAPH") || s.includes("GSQL")) {
      return "bg-orange-950/80 text-orange-300 border-orange-500/40";
    }
    if (s.includes("POLICY") || s.includes("GRAPHRAG")) {
      return "bg-indigo-950/80 text-indigo-300 border-indigo-500/40";
    }
    if (s.includes("CASE") || s.includes("MEMORY")) {
      return "bg-emerald-950/80 text-emerald-300 border-emerald-500/40";
    }
    if (s.includes("CUSTOMER")) {
      return "bg-cyan-950/80 text-cyan-300 border-cyan-500/40";
    }
    return "bg-slate-800 text-slate-300 border-slate-700";
  };

  return (
    <div className="space-y-4">
      {/* Top Filter and Actions Bar */}
      <div className="p-4 rounded-xl bg-brand-950/70 border border-brand-700/60 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-orange-400" />
            <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
              Normalized Evidence Matrix
            </h4>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-brand-800 text-slate-300 border border-brand-700">
              {filteredEvidence.length} of {evidence.length} Items
            </span>
          </div>

          <div className="flex items-center gap-2">
            {/* Direction Filter */}
            <div className="flex items-center gap-1 bg-brand-950 p-0.5 rounded-lg border border-brand-700 text-xs font-mono">
              {(["ALL", "SUPPORTING", "CONTRADICTORY"] as const).map((dir) => (
                <button
                  key={dir}
                  onClick={() => setDirectionFilter(dir)}
                  className={`px-2 py-0.5 rounded text-[11px] transition-colors ${
                    directionFilter === dir
                      ? dir === "CONTRADICTORY"
                        ? "bg-red-950/80 text-red-300 border border-red-500/40 font-bold"
                        : dir === "SUPPORTING"
                        ? "bg-emerald-950/80 text-emerald-300 border border-emerald-500/40 font-bold"
                        : "bg-orange-500/20 text-orange-400 border border-orange-500/40 font-bold"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {dir}
                </button>
              ))}
            </div>

            {/* Toggle Add Evidence Form */}
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-orange-600 hover:bg-orange-500 text-white font-semibold text-xs shadow-glow-high transition-all"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>{showAddForm ? "Close Form" : "Add Evidence"}</span>
            </button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search by fact content, evidence ID, source reference, or category..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-1.5 bg-brand-900 border border-brand-700 rounded-lg text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-orange-500"
          />
        </div>

        {/* Category Pills Bar */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-thin">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-2.5 py-1 rounded-full text-[10px] font-mono whitespace-nowrap transition-all border ${
                selectedCategory === cat
                  ? "bg-orange-500/20 text-orange-300 border-orange-500/50 font-bold"
                  : "bg-brand-900 text-slate-400 border-brand-700/60 hover:text-slate-200 hover:bg-brand-800"
              }`}
            >
              {cat.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>

      {/* Add Evidence Slide-Down Form */}
      {showAddForm && (
        <form
          onSubmit={handleFormSubmit}
          className="p-4 rounded-xl bg-brand-900/90 border border-orange-500/40 space-y-3 glass-card animate-fade-in"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
              <PlusCircle className="w-4 h-4 text-orange-400" />
              Submit Supplemental Evidence Fact
            </span>
            <span className="text-[10px] font-mono text-slate-400">
              Reliability: 1.0 (Analyst Attestation)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] font-medium text-slate-300 mb-1">
                Evidence Category
              </label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value as EvidenceCategory)}
                className="w-full px-3 py-1.5 bg-brand-950 border border-brand-700 rounded-lg text-xs text-slate-200 font-mono focus:outline-none focus:border-orange-500"
              >
                <option value="ANALYST_INPUT">ANALYST_INPUT</option>
                <option value="CUSTOMER_RESPONSE">CUSTOMER_RESPONSE</option>
                <option value="AUTHENTICATION">AUTHENTICATION</option>
                <option value="EXTERNAL_SIGNAL">EXTERNAL_SIGNAL</option>
                <option value="TRANSACTION_BEHAVIOR">TRANSACTION_BEHAVIOR</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-medium text-slate-300 mb-1">
                Source Reference
              </label>
              <input
                type="text"
                placeholder="e.g. Phone Interview, SMS response, Branch verification"
                value={newSourceRef}
                onChange={(e) => setNewSourceRef(e.target.value)}
                className="w-full px-3 py-1.5 bg-brand-950 border border-brand-700 rounded-lg text-xs text-slate-200 placeholder:text-slate-500 font-mono focus:outline-none focus:border-orange-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-[11px] font-medium text-slate-300 mb-1">
              Material Fact Statement
            </label>
            <textarea
              rows={2}
              placeholder="State verified factual finding with specific identifiers..."
              value={newFact}
              onChange={(e) => setNewFact(e.target.value)}
              className="w-full px-3 py-2 bg-brand-950 border border-brand-700 rounded-lg text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-orange-500"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="px-3 py-1.5 rounded-lg bg-brand-800 text-xs font-semibold text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !newFact.trim()}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-orange-600 hover:bg-orange-500 text-xs font-bold text-white shadow-glow-high transition-all disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{isSubmitting ? "Ingesting..." : "Ingest Fact"}</span>
            </button>
          </div>
        </form>
      )}

      {/* Evidence Cards List */}
      <div className="space-y-3">
        {filteredEvidence.length === 0 ? (
          <div className="p-8 text-center text-slate-500 bg-brand-950/40 rounded-xl border border-brand-800">
            <FileText className="w-8 h-8 text-slate-600 mx-auto mb-2 stroke-[1.5]" />
            <p className="text-xs font-semibold text-slate-400">
              No evidence items match the selected filter.
            </p>
            <p className="text-[11px] text-slate-600 mt-0.5">
              Reset search query or choose ALL categories.
            </p>
          </div>
        ) : (
          filteredEvidence.map((ev) => {
            const relPct = Math.round(ev.reliability * 100);
            const hasSupports = ev.supports_hypotheses && ev.supports_hypotheses.length > 0;
            const hasContra = ev.contradicts_hypotheses && ev.contradicts_hypotheses.length > 0;

            return (
              <div
                key={ev.evidence_id}
                className="p-4 rounded-xl bg-brand-950/70 border border-brand-700/60 hover:border-brand-600/80 transition-all space-y-2.5 shadow-sm"
              >
                {/* Header: ID, Category, Reliability */}
                <div className="flex items-center justify-between text-xs flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-orange-400 text-xs">
                      {ev.evidence_id}
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-brand-800 text-slate-300 border border-brand-700">
                      {ev.category}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono border ${getSourceBadgeStyle(
                        ev.source
                      )}`}
                    >
                      {ev.source}
                    </span>
                  </div>

                  {/* Reliability Meter */}
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-400">Reliability:</span>
                    <div className="w-16 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          relPct >= 80 ? "bg-emerald-400" : relPct >= 50 ? "bg-amber-400" : "bg-red-400"
                        }`}
                        style={{ width: `${relPct}%` }}
                      />
                    </div>
                    <span className="font-mono font-bold text-slate-300 text-[11px]">
                      {relPct}%
                    </span>
                  </div>
                </div>

                {/* Material Fact Text */}
                <p className="text-xs text-slate-200 leading-relaxed font-sans font-medium">
                  {ev.fact}
                </p>

                {/* Footer: Provenance reference and hypothesis linkages */}
                <div className="flex items-center justify-between pt-1 border-t border-brand-800/80 text-[11px] text-slate-400 flex-wrap gap-2">
                  <div className="font-mono text-[10px] text-slate-500">
                    {ev.source_reference ? `Ref: ${ev.source_reference}` : "Direct Grounded Observation"}
                  </div>

                  {/* Hypothesis Grounding Tags */}
                  <div className="flex items-center gap-2 flex-wrap">
                    {hasSupports && (
                      <div className="flex items-center gap-1 text-[10px] font-mono text-emerald-400">
                        <CheckCircle2 className="w-3 h-3" />
                        <span>Supports:</span>
                        {ev.supports_hypotheses!.map((h) => (
                          <span
                            key={h}
                            className="px-1.5 py-0.2 rounded bg-emerald-950/80 border border-emerald-500/40 text-emerald-300"
                          >
                            {h}
                          </span>
                        ))}
                      </div>
                    )}

                    {hasContra && (
                      <div className="flex items-center gap-1 text-[10px] font-mono text-red-400">
                        <XCircle className="w-3 h-3" />
                        <span>Contradicts:</span>
                        {ev.contradicts_hypotheses!.map((h) => (
                          <span
                            key={h}
                            className="px-1.5 py-0.2 rounded bg-red-950/80 border border-red-500/40 text-red-300"
                          >
                            {h}
                          </span>
                        ))}
                      </div>
                    )}

                    <span className="font-mono text-[10px] text-slate-600">
                      {new Date(ev.timestamp).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
