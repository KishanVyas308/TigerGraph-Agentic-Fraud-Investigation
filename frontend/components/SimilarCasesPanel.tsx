"use client";

import React, { useMemo, useState } from "react";
import { EvidenceCard, InvestigationResponse, SimilarCaseItem } from "@/types/api";
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  ExternalLink,
  Filter,
  GitBranch,
  History,
  Layers,
  Network,
  Scale,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Tag,
  XCircle,
} from "lucide-react";

interface SimilarCasesPanelProps {
  caseData: InvestigationResponse;
  evidenceList?: EvidenceCard[];
}

export function SimilarCasesPanel({
  caseData,
  evidenceList = [],
}: SimilarCasesPanelProps) {
  const [outcomeFilter, setOutcomeFilter] = useState<string>("ALL");
  const [methodFilter, setMethodFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Extract similar cases from caseData or fallback to evidenceList
  const cases: SimilarCaseItem[] = useMemo(() => {
    if (caseData.similar_cases && caseData.similar_cases.length > 0) {
      return caseData.similar_cases;
    }

    // Fallback extraction from normalized evidence items
    const fallbackItems: SimilarCaseItem[] = [];
    const histEv = evidenceList.filter((e) => e.category === "HISTORICAL_CASE");

    for (const ev of histEv) {
      const fact = ev.fact || "";
      let outcome = "UNKNOWN";
      if (fact.toUpperCase().includes("OUTCOME: FRAUD")) outcome = "FRAUD_CONFIRMED";
      else if (fact.toUpperCase().includes("OUTCOME: CLEARED")) outcome = "CLEARED_BENIGN";
      else if (fact.toUpperCase().includes("FRAUD")) outcome = "FRAUD_CONFIRMED";
      else if (fact.toUpperCase().includes("CLEARED")) outcome = "CLEARED_BENIGN";

      let typology = "GENERAL_FRAUD";
      const typMatch = fact.match(/Typology:\s*([^,\)]+)/i);
      if (typMatch && typMatch[1]) typology = typMatch[1].trim();

      let score = 0.85;
      const scoreMatch = fact.match(/Match:\s*([A-Za-z]+)\s*([0-9\.]+)/i);
      let method = "HYBRID";
      if (scoreMatch) {
        method = scoreMatch[1].toUpperCase();
        score = parseFloat(scoreMatch[2]) || 0.85;
      }

      fallbackItems.push({
        case_id: ev.source_reference?.replace("case_memory:", "") || ev.evidence_id,
        outcome,
        typology,
        summary: fact,
        similarity_score: score,
        retrieval_method: method,
        shared_entities: [],
        evidence_id: ev.evidence_id,
      });
    }

    return fallbackItems;
  }, [caseData.similar_cases, evidenceList]);

  // Retrieval method stats
  const stats = useMemo(() => {
    let graphCount = 0;
    let vectorCount = 0;
    let fraudCount = 0;
    let clearedCount = 0;

    for (const c of cases) {
      const m = (c.retrieval_method || "VECTOR").toUpperCase();
      if (m.includes("GRAPH")) graphCount++;
      else vectorCount++;

      const out = (c.outcome || "").toUpperCase();
      if (out.includes("FRAUD")) fraudCount++;
      else if (out.includes("CLEAR") || out.includes("BENIGN")) clearedCount++;
    }

    return {
      total: cases.length,
      graphCount,
      vectorCount,
      fraudCount,
      clearedCount,
    };
  }, [cases]);

  // Filtered cases
  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      // Outcome filter
      if (outcomeFilter !== "ALL") {
        const out = (c.outcome || "").toUpperCase();
        if (outcomeFilter === "FRAUD" && !out.includes("FRAUD")) return false;
        if (
          outcomeFilter === "CLEARED" &&
          !out.includes("CLEAR") &&
          !out.includes("BENIGN")
        )
          return false;
      }

      // Method filter
      if (methodFilter !== "ALL") {
        const m = (c.retrieval_method || "").toUpperCase();
        if (methodFilter === "GRAPH" && !m.includes("GRAPH")) return false;
        if (methodFilter === "VECTOR" && !m.includes("VECTOR") && !m.includes("HYBRID"))
          return false;
      }

      // Keyword query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesText =
          c.case_id.toLowerCase().includes(q) ||
          (c.typology || "").toLowerCase().includes(q) ||
          c.summary.toLowerCase().includes(q) ||
          (c.shared_entities || []).some((e) => e.toLowerCase().includes(q));
        if (!matchesText) return false;
      }

      return true;
    });
  }, [cases, outcomeFilter, methodFilter, searchQuery]);

  const getOutcomeBadge = (outcome: string) => {
    const upper = outcome.toUpperCase();
    if (upper.includes("FRAUD")) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-red-950/80 border border-red-500/50 text-red-300">
          <ShieldAlert className="w-3 h-3 text-red-400" />
          FRAUD CONFIRMED
        </span>
      );
    }
    if (upper.includes("CLEAR") || upper.includes("BENIGN")) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-950/80 border border-emerald-500/50 text-emerald-300">
          <ShieldCheck className="w-3 h-3 text-emerald-400" />
          CLEARED BENIGN
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-950/80 border border-amber-500/50 text-amber-300">
        <AlertTriangle className="w-3 h-3 text-amber-400" />
        {outcome}
      </span>
    );
  };

  const getMethodBadge = (method?: string) => {
    const m = (method || "VECTOR").toUpperCase();
    if (m.includes("GRAPH")) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950 border border-cyan-500/50 text-cyan-300">
          <Network className="w-3 h-3 text-cyan-400" />
          GRAPH MATCH
        </span>
      );
    }
    if (m.includes("HYBRID")) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-purple-950 border border-purple-500/50 text-purple-300">
          <Sparkles className="w-3 h-3 text-purple-400" />
          HYBRID MATCH
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-blue-950 border border-blue-500/50 text-blue-300">
        <Database className="w-3 h-3 text-blue-400" />
        VECTOR MATCH
      </span>
    );
  };

  return (
    <div className="space-y-5">
      {/* 1. Precedent Compliance Disclaimer Banner */}
      <div className="p-4 rounded-xl bg-brand-950/90 border border-brand-700/80 flex items-start gap-3.5 shadow-lg">
        <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center shrink-0 mt-0.5">
          <Scale className="w-4 h-4 text-amber-400" />
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h4 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
              TigerGraph Case Memory & Precedent Precedent Engine
            </h4>
            <span className="text-[10px] font-mono px-2 py-0.2 rounded bg-amber-950 border border-amber-500/50 text-amber-300 font-semibold">
              AGENTS.md §6.4 & §14
            </span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            <strong className="text-amber-300">Precedent is not proof:</strong> Historical cases
            are retrieved via TigerGraph graph traversal and semantic embeddings to identify
            shared attack networks and historical analyst precedents. They provide contextual
            guidance for hypothesis exploration and institutional policy consistency, but do not
            substitute for grounded evidence on the active case.
          </p>
        </div>
      </div>

      {/* 2. Comparative Retrieval Metrics Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-brand-950/70 border border-brand-700/60">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-slate-400 uppercase">
              Retrieved Precedents
            </span>
            <History className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <p className="text-xl font-bold font-mono text-slate-100 mt-1">
            {stats.total}
          </p>
          <span className="text-[10px] text-slate-500 font-mono">
            Bounded Case Memory
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-brand-950/70 border border-cyan-800/40">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-cyan-300 uppercase">
              Graph Entity Links
            </span>
            <Network className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <p className="text-xl font-bold font-mono text-cyan-200 mt-1">
            {stats.graphCount}
          </p>
          <span className="text-[10px] text-cyan-400/70 font-mono">
            Shared Device/IP/Cluster
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-brand-950/70 border border-purple-800/40">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-purple-300 uppercase">
              Vector Semantic Matches
            </span>
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <p className="text-xl font-bold font-mono text-purple-200 mt-1">
            {stats.vectorCount}
          </p>
          <span className="text-[10px] text-purple-400/70 font-mono">
            Typology Embedding Match
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-brand-950/70 border border-brand-700/60">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-slate-400 uppercase">
              Outcome Breakdown
            </span>
            <Scale className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs font-mono font-bold text-red-400">
              {stats.fraudCount} Fraud
            </span>
            <span className="text-xs text-slate-600">/</span>
            <span className="text-xs font-mono font-bold text-emerald-400">
              {stats.clearedCount} Cleared
            </span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono">
            Precedent Split
          </span>
        </div>
      </div>

      {/* 3. Search & Filter Bar */}
      <div className="p-3 rounded-xl bg-brand-950/60 border border-brand-700/60 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          {/* Outcome Filter Pills */}
          <div className="flex items-center p-0.5 rounded-lg bg-brand-900 border border-brand-800 text-[11px] font-medium">
            <button
              onClick={() => setOutcomeFilter("ALL")}
              className={`px-2.5 py-1 rounded-md transition-all ${
                outcomeFilter === "ALL"
                  ? "bg-brand-700 text-white font-bold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              All Outcomes
            </button>
            <button
              onClick={() => setOutcomeFilter("FRAUD")}
              className={`px-2.5 py-1 rounded-md transition-all ${
                outcomeFilter === "FRAUD"
                  ? "bg-red-950 text-red-300 font-bold border border-red-500/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Fraud Confirmed ({stats.fraudCount})
            </button>
            <button
              onClick={() => setOutcomeFilter("CLEARED")}
              className={`px-2.5 py-1 rounded-md transition-all ${
                outcomeFilter === "CLEARED"
                  ? "bg-emerald-950 text-emerald-300 font-bold border border-emerald-500/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Cleared Benign ({stats.clearedCount})
            </button>
          </div>

          {/* Retrieval Method Pills */}
          <div className="flex items-center p-0.5 rounded-lg bg-brand-900 border border-brand-800 text-[11px] font-medium">
            <button
              onClick={() => setMethodFilter("ALL")}
              className={`px-2.5 py-1 rounded-md transition-all ${
                methodFilter === "ALL"
                  ? "bg-brand-700 text-white font-bold"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              All Methods
            </button>
            <button
              onClick={() => setMethodFilter("GRAPH")}
              className={`px-2.5 py-1 rounded-md transition-all ${
                methodFilter === "GRAPH"
                  ? "bg-cyan-950 text-cyan-300 font-bold border border-cyan-500/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Graph ({stats.graphCount})
            </button>
            <button
              onClick={() => setMethodFilter("VECTOR")}
              className={`px-2.5 py-1 rounded-md transition-all ${
                methodFilter === "VECTOR"
                  ? "bg-purple-950 text-purple-300 font-bold border border-purple-500/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Vector ({stats.vectorCount})
            </button>
          </div>
        </div>

        {/* Real-time Keyword Search */}
        <div className="relative min-w-[220px]">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search precedents, typologies..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-brand-900 border border-brand-800 rounded-lg text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>
      </div>

      {/* 4. Precedent Case Cards List */}
      <div className="space-y-3">
        {filteredCases.length === 0 ? (
          <div className="p-8 text-center rounded-xl bg-brand-950/40 border border-brand-800 text-slate-500 space-y-2">
            <History className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-xs font-semibold text-slate-400">
              No matching historical case precedents found
            </p>
            <p className="text-[11px] text-slate-600">
              Try adjusting your outcome or retrieval method filters.
            </p>
          </div>
        ) : (
          filteredCases.map((caseItem, idx) => {
            const similarityPercent = Math.min(
              100,
              Math.max(0, Math.round((caseItem.similarity_score || 0.85) * 100))
            );

            return (
              <div
                key={caseItem.case_id || idx}
                className="p-4 rounded-xl bg-brand-950/80 border border-brand-700/70 hover:border-brand-600 transition-all space-y-3 shadow-md"
              >
                {/* Precedent Header */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-brand-800/80 pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-slate-200">
                      {caseItem.case_id}
                    </span>
                    {getOutcomeBadge(caseItem.outcome)}
                    {getMethodBadge(caseItem.retrieval_method)}
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-slate-400">
                      Match Confidence:
                    </span>
                    <div className="flex items-center gap-1.5">
                      <div className="w-16 h-2 rounded-full bg-brand-900 border border-brand-800 overflow-hidden">
                        <div
                          className="h-full bg-cyan-500 rounded-full"
                          style={{ width: `${similarityPercent}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono font-bold text-cyan-300">
                        {similarityPercent}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Typology and Narrative Summary */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Tag className="w-3 h-3 text-amber-400" />
                    <span className="text-[11px] font-mono font-semibold text-amber-300 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800/50">
                      Typology: {caseItem.typology || "UNSPECIFIED"}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">
                    {caseItem.summary}
                  </p>
                </div>

                {/* Shared Graph Entities (if any) */}
                {caseItem.shared_entities && caseItem.shared_entities.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-brand-900 text-[10px] font-mono text-slate-400">
                    <Network className="w-3 h-3 text-cyan-400 mr-1" />
                    <span>Shared Graph Entities:</span>
                    {caseItem.shared_entities.map((ent, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded bg-brand-900 text-cyan-300 border border-brand-800"
                      >
                        {ent}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
