"use client";

import React from "react";
import { InvestigationResponse } from "@/types/api";
import { RiskBadge } from "./StatusBadge";
import {
  ShieldAlert,
  Sparkles,
  Scale,
  Brain,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Info,
} from "lucide-react";

interface AssessmentPanelProps {
  caseData: InvestigationResponse;
}

export const AssessmentPanel: React.FC<AssessmentPanelProps> = ({ caseData }) => {
  const riskScore = caseData.risk_score != null ? Math.round(caseData.risk_score * 100) : null;
  const confidence = caseData.confidence != null ? Math.round(caseData.confidence * 100) : null;
  const completeness =
    caseData.evidence_completeness != null
      ? Math.round(caseData.evidence_completeness * 100)
      : null;

  const isSufficient = (completeness ?? 0) >= 70;
  const mlScore =
    caseData.historical_ml_score != null
      ? Math.round(caseData.historical_ml_score * 100)
      : null;

  return (
    <div className="space-y-4">
      {/* Header Notification Banner */}
      <div className="p-3.5 rounded-xl bg-brand-950/70 border border-brand-700/60 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-orange-400" />
          <span className="font-bold text-slate-200 uppercase tracking-wider">
            Triad Multi-Dimensional Assessment Gate
          </span>
        </div>
        <span className="text-[10px] font-mono text-slate-500">
          Strict Separation Principle (AGENTS.md §13)
        </span>
      </div>

      {/* 3 Distinct Dimension Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
        {/* 1. Risk Dimension */}
        <div className="p-4 rounded-xl bg-brand-950/90 border border-brand-700/80 shadow-md flex flex-col justify-between space-y-3">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4 text-orange-400" />
                1. Assessed Risk
              </span>
              <RiskBadge level={caseData.risk_level} size="sm" />
            </div>

            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black text-white font-mono">
                {riskScore !== null ? `${riskScore}%` : "Evaluating..."}
              </span>
              <span className="text-xs text-slate-400 font-medium">Probability</span>
            </div>

            {/* Risk Gauge Bar */}
            <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  (riskScore ?? 0) >= 75
                    ? "bg-red-500"
                    : (riskScore ?? 0) >= 50
                    ? "bg-orange-500"
                    : (riskScore ?? 0) >= 25
                    ? "bg-amber-400"
                    : "bg-emerald-400"
                }`}
                style={{ width: `${riskScore ?? 0}%` }}
              />
            </div>
          </div>

          <p className="text-[11px] text-slate-400 leading-snug">
            Measures estimated harm and suspiciousness based on TigerGraph transaction and graph features.
          </p>
        </div>

        {/* 2. Confidence Dimension */}
        <div className="p-4 rounded-xl bg-brand-950/90 border border-brand-700/80 shadow-md flex flex-col justify-between space-y-3">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                2. Model Confidence
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950/80 text-cyan-300 border border-cyan-500/40">
                CERTAINTY
              </span>
            </div>

            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black text-cyan-400 font-mono">
                {confidence !== null ? `${confidence}%` : "Evaluating..."}
              </span>
              <span className="text-xs text-slate-400 font-medium">Certainty</span>
            </div>

            {/* Confidence Gauge Bar */}
            <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
              <div
                className="h-full bg-cyan-400 rounded-full transition-all duration-500"
                style={{ width: `${confidence ?? 0}%` }}
              />
            </div>
          </div>

          <p className="text-[11px] text-slate-400 leading-snug">
            Quantifies stability and lack of ambiguity across competing hypotheses and graph signals.
          </p>
        </div>

        {/* 3. Evidence Completeness Dimension */}
        <div className="p-4 rounded-xl bg-brand-950/90 border border-brand-700/80 shadow-md flex flex-col justify-between space-y-3">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Scale className="w-4 h-4 text-indigo-400" />
                3. Completeness
              </span>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-mono border ${
                  isSufficient
                    ? "bg-emerald-950/80 text-emerald-300 border-emerald-500/40"
                    : "bg-amber-950/80 text-amber-300 border-amber-500/40"
                }`}
              >
                {isSufficient ? "SUFFICIENT" : "GAPS DETECTED"}
              </span>
            </div>

            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-black text-indigo-400 font-mono">
                {completeness !== null ? `${completeness}%` : "Evaluating..."}
              </span>
              <span className="text-xs text-slate-400 font-medium">Sufficiency Gate</span>
            </div>

            {/* Completeness Gauge Bar */}
            <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isSufficient ? "bg-indigo-400" : "bg-amber-400"
                }`}
                style={{ width: `${completeness ?? 0}%` }}
              />
            </div>
          </div>

          <p className="text-[11px] text-slate-400 leading-snug">
            {isSufficient
              ? "Sufficient verified evidence gathered to justify deterministic policy action."
              : "Uncertainty exceeds threshold; additional step-up evidence required before blocking."}
          </p>
        </div>
      </div>

      {/* Optional Historical ML Signal (LightGBM) Callout */}
      {mlScore !== null && (
        <div className="p-3.5 rounded-xl bg-brand-950/60 border border-brand-700/60 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2.5">
            <Cpu className="w-4 h-4 text-indigo-400" />
            <div>
              <span className="font-bold text-slate-300">
                Supporting Statistical Precedent Signal (LightGBM):
              </span>{" "}
              <span className="font-mono font-bold text-indigo-300">{mlScore}%</span>
            </div>
          </div>
          <span className="text-[10px] font-mono text-slate-500">
            Historical signal only • Not ground truth (AGENTS.md §7)
          </span>
        </div>
      )}

      {/* Structured Case Summary / Narrative */}
      <div className="p-4 rounded-xl bg-brand-950/80 border border-brand-700/80 space-y-2">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-bold text-orange-400 uppercase tracking-wider flex items-center gap-2">
            <Brain className="w-4 h-4" /> Synthesized Case Assessment Narrative
          </h4>
          <span className="text-[10px] font-mono text-slate-500">
            Node: main_reasoning
          </span>
        </div>
        <p className="text-sm text-slate-300 leading-relaxed font-sans">
          {caseData.case_summary || "Reasoning synthesis in progress..."}
        </p>
      </div>
    </div>
  );
};
