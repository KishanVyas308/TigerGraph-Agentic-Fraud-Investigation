"use client";

import React, { useMemo, useState } from "react";
import { EvidenceCard, InvestigationResponse, PolicyContextItem } from "@/types/api";
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  FileCheck,
  FileText,
  Filter,
  Layers,
  Link2,
  Lock,
  Network,
  Scale,
  Search,
  Shield,
  ShieldAlert,
  Sparkles,
  Tag,
} from "lucide-react";

interface PolicyGuidancePanelProps {
  caseData: InvestigationResponse;
  evidenceList?: EvidenceCard[];
}

export function PolicyGuidancePanel({
  caseData,
  evidenceList = [],
}: PolicyGuidancePanelProps) {
  const [pillarFilter, setPillarFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Extract policy items from caseData or fallback to evidenceList
  const policyItems: PolicyContextItem[] = useMemo(() => {
    if (caseData.policy_context && caseData.policy_context.length > 0) {
      return caseData.policy_context;
    }

    // Fallback extraction from normalized evidence items
    const fallbackItems: PolicyContextItem[] = [];
    const polEv = evidenceList.filter(
      (e) => e.category === "POLICY" || e.category === "REGULATION"
    );

    for (const ev of polEv) {
      const fact = ev.fact || "";
      let docType = ev.category === "REGULATION" ? "REGULATION" : "POLICY";
      if (fact.toUpperCase().includes("TYPOLOGY")) docType = "TYPOLOGY";

      // Attempt to extract source ID and title: e.g. [POL-01] Title: Text
      let title = "Institutional Governance Rule";
      let policyId = ev.source_reference?.replace("policy_index:", "") || ev.evidence_id;

      const titleMatch = fact.match(/^\[([^\]]+)\]\s*([^:]+):\s*(.*)$/);
      let text = fact;
      if (titleMatch) {
        policyId = titleMatch[1].trim();
        title = titleMatch[2].trim();
        text = titleMatch[3].trim();
      }

      fallbackItems.push({
        policy_id: policyId,
        title,
        document_type: docType,
        text,
        relevance_score: ev.reliability || 0.9,
        graph_references: [],
        evidence_id: ev.evidence_id,
      });
    }

    return fallbackItems;
  }, [caseData.policy_context, evidenceList]);

  // Pillar statistics
  const stats = useMemo(() => {
    let policyCount = 0;
    let typologyCount = 0;
    let regulationCount = 0;

    for (const item of policyItems) {
      const t = (item.document_type || "POLICY").toUpperCase();
      if (t.includes("REG")) regulationCount++;
      else if (t.includes("TYP")) typologyCount++;
      else policyCount++;
    }

    return {
      total: policyItems.length,
      policyCount,
      typologyCount,
      regulationCount,
    };
  }, [policyItems]);

  // Filtered policy items
  const filteredItems = useMemo(() => {
    return policyItems.filter((item) => {
      const t = (item.document_type || "POLICY").toUpperCase();

      if (pillarFilter === "POLICY" && !t.includes("POL")) return false;
      if (pillarFilter === "TYPOLOGY" && !t.includes("TYP")) return false;
      if (pillarFilter === "REGULATION" && !t.includes("REG")) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matches =
          item.policy_id.toLowerCase().includes(q) ||
          item.title.toLowerCase().includes(q) ||
          item.text.toLowerCase().includes(q) ||
          (item.graph_references || []).some((r) => r.toLowerCase().includes(q));
        if (!matches) return false;
      }

      return true;
    });
  }, [policyItems, pillarFilter, searchQuery]);

  const getDocTypeBadge = (docType: string) => {
    const t = docType.toUpperCase();
    if (t.includes("REG")) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-purple-950/80 border border-purple-500/50 text-purple-300">
          <Scale className="w-3 h-3 text-purple-400" />
          REGULATORY MANDATE
        </span>
      );
    }
    if (t.includes("TYP")) {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-950/80 border border-amber-500/50 text-amber-300">
          <Tag className="w-3 h-3 text-amber-400" />
          FRAUD TYPOLOGY
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-cyan-950/80 border border-cyan-500/50 text-cyan-300">
        <Shield className="w-3 h-3 text-cyan-400" />
        INSTITUTIONAL POLICY
      </span>
    );
  };

  return (
    <div className="space-y-5">
      {/* 1. Header & Governance Engine Banner */}
      <div className="p-4 rounded-xl bg-brand-950/90 border border-brand-700/80 flex items-start gap-3.5 shadow-lg">
        <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center shrink-0 mt-0.5">
          <BookOpen className="w-4 h-4 text-cyan-400" />
        </div>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h4 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
              TigerGraph GraphRAG Policy & Regulatory Context Engine
            </h4>
            <span className="text-[10px] font-mono px-2 py-0.2 rounded bg-cyan-950 border border-cyan-500/50 text-cyan-300 font-semibold">
              AGENTS.md §7 & §18
            </span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Every next-best action and investigative threshold is strictly governed by institutional
            fraud policies and statutory anti-money laundering regulations. The LLM recommends actions,
            but the deterministic policy engine authorizes execution based on these grounded rules.
          </p>
        </div>
      </div>

      {/* 2. Knowledge Pillar Breakdown Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-brand-950/70 border border-brand-700/60">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-slate-400 uppercase">
              Total Retrieved Rules
            </span>
            <FileText className="w-3.5 h-3.5 text-slate-400" />
          </div>
          <p className="text-xl font-bold font-mono text-slate-100 mt-1">
            {stats.total}
          </p>
          <span className="text-[10px] text-slate-500 font-mono">
            GraphRAG Clauses
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-brand-950/70 border border-cyan-800/40">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-cyan-300 uppercase">
              Bank Fraud Policies
            </span>
            <Shield className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <p className="text-xl font-bold font-mono text-cyan-200 mt-1">
            {stats.policyCount}
          </p>
          <span className="text-[10px] text-cyan-400/70 font-mono">
            Thresholds & Controls
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-brand-950/70 border border-amber-800/40">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-amber-300 uppercase">
              Fraud Typologies
            </span>
            <Tag className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <p className="text-xl font-bold font-mono text-amber-200 mt-1">
            {stats.typologyCount}
          </p>
          <span className="text-[10px] text-amber-400/70 font-mono">
            Modus Operandi Catalog
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-brand-950/70 border border-purple-800/40">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-purple-300 uppercase">
              Regulatory Mandates
            </span>
            <Scale className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <p className="text-xl font-bold font-mono text-purple-200 mt-1">
            {stats.regulationCount}
          </p>
          <span className="text-[10px] text-purple-400/70 font-mono">
            BSA / FinCEN / SAR Rules
          </span>
        </div>
      </div>

      {/* 3. Filter Pills and Keyword Search */}
      <div className="p-3 rounded-xl bg-brand-950/60 border border-brand-700/60 flex flex-wrap items-center justify-between gap-3">
        {/* Pillar Filter Pills */}
        <div className="flex items-center p-0.5 rounded-lg bg-brand-900 border border-brand-800 text-[11px] font-medium">
          <button
            onClick={() => setPillarFilter("ALL")}
            className={`px-2.5 py-1 rounded-md transition-all ${
              pillarFilter === "ALL"
                ? "bg-brand-700 text-white font-bold"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            All Pillars ({stats.total})
          </button>
          <button
            onClick={() => setPillarFilter("POLICY")}
            className={`px-2.5 py-1 rounded-md transition-all ${
              pillarFilter === "POLICY"
                ? "bg-cyan-950 text-cyan-300 font-bold border border-cyan-500/40"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Policies ({stats.policyCount})
          </button>
          <button
            onClick={() => setPillarFilter("TYPOLOGY")}
            className={`px-2.5 py-1 rounded-md transition-all ${
              pillarFilter === "TYPOLOGY"
                ? "bg-amber-950 text-amber-300 font-bold border border-amber-500/40"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Typologies ({stats.typologyCount})
          </button>
          <button
            onClick={() => setPillarFilter("REGULATION")}
            className={`px-2.5 py-1 rounded-md transition-all ${
              pillarFilter === "REGULATION"
                ? "bg-purple-950 text-purple-300 font-bold border border-purple-500/40"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Regulations ({stats.regulationCount})
          </button>
        </div>

        {/* Search Input */}
        <div className="relative min-w-[240px]">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search policies, citations, keywords..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-brand-900 border border-brand-800 rounded-lg text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>
      </div>

      {/* 4. Policy Clauses Cards Grid */}
      <div className="space-y-3">
        {filteredItems.length === 0 ? (
          <div className="p-8 text-center rounded-xl bg-brand-950/40 border border-brand-800 text-slate-500 space-y-2">
            <BookOpen className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-xs font-semibold text-slate-400">
              No matching policy or regulatory clauses found
            </p>
            <p className="text-[11px] text-slate-600">
              Try adjusting your pillar filters or search keyword.
            </p>
          </div>
        ) : (
          filteredItems.map((item, idx) => {
            const relevancePercent = Math.min(
              100,
              Math.max(0, Math.round((item.relevance_score || 0.9) * 100))
            );

            return (
              <div
                key={item.evidence_id || item.policy_id || idx}
                className="p-4 rounded-xl bg-brand-950/80 border border-brand-700/70 hover:border-brand-600 transition-all space-y-3 shadow-md"
              >
                {/* Policy Card Header */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-brand-800/80 pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-slate-200">
                      {item.policy_id}
                    </span>
                    {getDocTypeBadge(item.document_type)}
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-slate-400">
                      Relevance Match:
                    </span>
                    <div className="flex items-center gap-1.5">
                      <div className="w-16 h-2 rounded-full bg-brand-900 border border-brand-800 overflow-hidden">
                        <div
                          className="h-full bg-cyan-500 rounded-full"
                          style={{ width: `${relevancePercent}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono font-bold text-cyan-300">
                        {relevancePercent}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Section Title & Narrative Rule */}
                <div className="space-y-1.5">
                  <h5 className="text-xs font-bold text-slate-100 flex items-center gap-1.5">
                    <FileCheck className="w-3.5 h-3.5 text-cyan-400" />
                    {item.title}
                  </h5>
                  <p className="text-xs text-slate-300 leading-relaxed pl-5">
                    {item.text}
                  </p>
                </div>

                {/* Footer: Graph Entity References & Provenance */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-brand-900 text-[10px] font-mono text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <Network className="w-3 h-3 text-cyan-400" />
                    <span>TigerGraph References:</span>
                    {item.graph_references && item.graph_references.length > 0 ? (
                      item.graph_references.map((ref, rIdx) => (
                        <span
                          key={rIdx}
                          className="px-2 py-0.5 rounded bg-brand-900 text-cyan-300 border border-brand-800"
                        >
                          {ref}
                        </span>
                      ))
                    ) : (
                      <span className="text-slate-500 italic">Global Investigation Scope</span>
                    )}
                  </div>

                  <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-brand-900 text-slate-400 border border-brand-800">
                    Source: POLICY_GRAPHRAG
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
