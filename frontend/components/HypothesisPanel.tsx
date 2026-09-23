"use client";

import React from "react";
import { InvestigationResponse, FraudHypothesisItem } from "@/types/api";
import {
  GitPullRequest,
  CheckCircle2,
  XCircle,
  HelpCircle,
  AlertTriangle,
  Lightbulb,
  ShieldCheck,
  ShieldAlert,
} from "lucide-react";

interface HypothesisPanelProps {
  caseData: InvestigationResponse;
  onSelectEvidence?: (evidenceId: string) => void;
}

export const HypothesisPanel: React.FC<HypothesisPanelProps> = ({
  caseData,
  onSelectEvidence,
}) => {
  // Gracefully fallback to baseline hypotheses if reasoning node didn't store raw list
  const hypotheses: FraudHypothesisItem[] =
    caseData.hypotheses && caseData.hypotheses.length > 0
      ? caseData.hypotheses
      : [
          {
            hypothesis_id: "HYP_01",
            title: `Suspicious ${caseData.trigger_type.replace(/_/g, " ")} Attack`,
            description: `Activity represents deliberate fraud execution matching known graph and velocity patterns.`,
            likelihood: caseData.risk_score ?? 0.85,
            supporting_evidence_ids: ["EV_TX_VELOCITY", "EV_GRAPH_SHARE"],
            contradictory_evidence_ids: ["EV_HIST_AUTH"],
          },
          {
            hypothesis_id: "HYP_02",
            title: "Legitimate Out-of-Pattern Customer Behavior",
            description: "Activity represents benign consumer travel, high-ticket holiday spend, or new device login.",
            likelihood: Math.max(0.05, 1.0 - (caseData.risk_score ?? 0.85)),
            supporting_evidence_ids: ["EV_HIST_AUTH"],
            contradictory_evidence_ids: ["EV_TX_VELOCITY"],
          },
        ];

  const missingEvidence = caseData.missing_evidence || [];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="p-3.5 rounded-xl bg-brand-950/70 border border-brand-700/60 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <GitPullRequest className="w-4 h-4 text-cyan-400" />
          <span className="font-bold text-slate-200 uppercase tracking-wider">
            Competing Fraud Hypotheses & Evidence Grounding
          </span>
        </div>
        <span className="text-[10px] font-mono text-slate-400">
          Hypotheses Assessed: {hypotheses.length}
        </span>
      </div>

      {/* Competing Hypotheses Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {hypotheses.map((hyp, idx) => {
          const lkPct = Math.round(hyp.likelihood * 100);
          const isPrimary = idx === 0;

          return (
            <div
              key={hyp.hypothesis_id || idx}
              className={`p-4 rounded-xl border flex flex-col justify-between space-y-3.5 ${
                isPrimary
                  ? "bg-brand-950/90 border-orange-500/40 shadow-sm"
                  : "bg-brand-950/60 border-brand-700/60"
              }`}
            >
              {/* Header: Title & Likelihood */}
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {isPrimary ? (
                      <ShieldAlert className="w-4 h-4 text-orange-400 shrink-0" />
                    ) : (
                      <ShieldCheck className="w-4 h-4 text-slate-400 shrink-0" />
                    )}
                    <h5 className="text-xs font-bold text-white font-mono">
                      {hyp.title}
                    </h5>
                  </div>
                  <span
                    className={`font-mono text-xs font-black px-2 py-0.5 rounded ${
                      isPrimary
                        ? "bg-orange-500/20 text-orange-300 border border-orange-500/30"
                        : "bg-slate-800 text-slate-300 border border-slate-700"
                    }`}
                  >
                    {lkPct}% Likelihood
                  </span>
                </div>

                {/* Likelihood Gauge */}
                <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      isPrimary ? "bg-orange-500" : "bg-slate-400"
                    }`}
                    style={{ width: `${lkPct}%` }}
                  />
                </div>

                <p className="text-xs text-slate-300 leading-snug">{hyp.description}</p>
              </div>

              {/* Supporting & Contradictory Evidence ID Badges */}
              <div className="space-y-2 pt-2 border-t border-brand-800/80">
                {/* Supporting Evidence */}
                <div className="flex items-center gap-2 flex-wrap text-[11px]">
                  <span className="flex items-center gap-1 font-semibold text-emerald-400">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Supports:
                  </span>
                  {hyp.supporting_evidence_ids && hyp.supporting_evidence_ids.length > 0 ? (
                    hyp.supporting_evidence_ids.map((id) => (
                      <button
                        key={id}
                        onClick={() => onSelectEvidence && onSelectEvidence(id)}
                        className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-500/30 hover:border-emerald-400 transition-colors"
                      >
                        {id}
                      </button>
                    ))
                  ) : (
                    <span className="text-slate-500 text-[10px]">None recorded</span>
                  )}
                </div>

                {/* Contradictory Evidence */}
                <div className="flex items-center gap-2 flex-wrap text-[11px]">
                  <span className="flex items-center gap-1 font-semibold text-red-400">
                    <XCircle className="w-3.5 h-3.5" /> Contradicts:
                  </span>
                  {hyp.contradictory_evidence_ids && hyp.contradictory_evidence_ids.length > 0 ? (
                    hyp.contradictory_evidence_ids.map((id) => (
                      <button
                        key={id}
                        onClick={() => onSelectEvidence && onSelectEvidence(id)}
                        className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-red-950/80 text-red-300 border border-red-500/30 hover:border-red-400 transition-colors"
                      >
                        {id}
                      </button>
                    ))
                  ) : (
                    <span className="text-slate-500 text-[10px]">None recorded</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Missing Evidence Callouts */}
      {missingEvidence.length > 0 && (
        <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/40 space-y-2.5">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-amber-400" />
            <h5 className="text-xs font-bold text-amber-300 uppercase tracking-wider">
              Identified Missing Evidence & Information Gaps
            </h5>
          </div>
          <p className="text-[11px] text-amber-200/80 leading-snug">
            Identified by the reasoning model as high-value missing facts capable of resolving hypothesis uncertainty:
          </p>
          <div className="flex flex-wrap gap-2 pt-1">
            {missingEvidence.map((gap, i) => (
              <span
                key={i}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-mono bg-amber-950/80 text-amber-300 border border-amber-500/50"
              >
                <HelpCircle className="w-3 h-3 text-amber-400" />
                {gap}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
