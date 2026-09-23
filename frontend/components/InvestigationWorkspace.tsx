"use client";

import React, { useState, useEffect } from "react";
import {
  InvestigationResponse,
  EvidenceListResponse,
  GraphVisualizationResponse,
  SubmitEvidenceRequest,
} from "@/types/api";
import { api } from "@/lib/api";
import { RiskBadge, CaseStatusBadge, ActionBadge, ApprovalBadge } from "./StatusBadge";
import { InvestigationTimeline } from "./InvestigationTimeline";
import { FraudGraphVisualization } from "./FraudGraphVisualization";
import { AssessmentPanel } from "./AssessmentPanel";
import { HypothesisPanel } from "./HypothesisPanel";
import { EvidencePanel } from "./EvidencePanel";
import { NextBestActionPanel } from "./NextBestActionPanel";
import { SimilarCasesPanel } from "./SimilarCasesPanel";
import { PolicyGuidancePanel } from "./PolicyGuidancePanel";
import { AuditTrailPanel } from "./AuditTrailPanel";
import { useInvestigationSSE } from "@/hooks/useInvestigationSSE";
import {
  ShieldAlert,
  Brain,
  CheckCircle2,
  XCircle,
  FileText,
  Database,
  Network,
  Scale,
  Clock,
  ArrowRight,
  Send,
  Sparkles,
  Info,
  GitBranch,
  Radio,
  BookOpen,
  History,
  Terminal,
} from "lucide-react";

interface InvestigationWorkspaceProps {
  caseId: string;
  onCaseUpdated: (updated: InvestigationResponse) => void;
}

export const InvestigationWorkspace: React.FC<InvestigationWorkspaceProps> = ({
  caseId,
  onCaseUpdated,
}) => {
  const [caseData, setCaseData] = useState<InvestigationResponse | null>(null);
  const [evidenceData, setEvidenceData] = useState<EvidenceListResponse | null>(null);
  const [graphData, setGraphData] = useState<GraphVisualizationResponse | null>(null);
  const [activeTab, setActiveTab] = useState<
    "overview" | "timeline" | "evidence" | "graph" | "precedents" | "policy" | "actions" | "audit"
  >("overview");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSubmittingEvidence, setIsSubmittingEvidence] = useState<boolean>(false);

  // Hook up real-time SSE stream
  const {
    events: sseEvents,
    connectionStatus,
    reconnect,
  } = useInvestigationSSE(caseId, {
    onEvent: (evt) => {
      if (
        [
          "APPROVAL_REQUIRED",
          "ACTION_EXECUTED",
          "SAR_REPORT_GENERATED",
          "CASE_FINALIZED",
          "CASE_MEMORY_PERSISTED",
          "INVESTIGATION_ERROR",
        ].includes(evt.event_type)
      ) {
        loadCaseDetails();
      }
    },
    onCaseFinished: () => {
      loadCaseDetails();
    },
  });

  // Fetch case details, evidence, and graph
  const loadCaseDetails = React.useCallback(async () => {
    setIsLoading(true);
    try {
      const [c, ev, gr] = await Promise.all([
        api.getInvestigation(caseId),
        api.getInvestigationEvidence(caseId).catch(() => null),
        api.getInvestigationGraph(caseId).catch(() => null),
      ]);
      setCaseData(c);
      setEvidenceData(ev);
      setGraphData(gr);
    } catch (err) {
      console.error("Error loading case details:", err);
    } finally {
      setIsLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    if (caseId) {
      loadCaseDetails();
    }
  }, [caseId, loadCaseDetails]);

  const handleEvidenceSubmit = async (req: SubmitEvidenceRequest) => {
    setIsSubmittingEvidence(true);
    try {
      const updated = await api.submitEvidence(caseId, req);
      setCaseData(updated);
      onCaseUpdated(updated);
      const ev = await api.getInvestigationEvidence(caseId);
      setEvidenceData(ev);
    } catch (err: any) {
      alert(`Failed to add evidence: ${err.message}`);
    } finally {
      setIsSubmittingEvidence(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-brand-950/40 rounded-xl border border-brand-700/60 p-12">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-9 w-9 border-2 border-orange-500 border-t-transparent mb-3" />
          <p className="text-sm font-semibold text-slate-300">Loading Case Intelligence Workspace...</p>
          <p className="text-xs text-slate-500 font-mono mt-1">{caseId}</p>
        </div>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="flex-1 flex items-center justify-center bg-brand-950/40 rounded-xl border border-brand-700/60 p-12 text-slate-400">
        <div className="text-center">
          <ShieldAlert className="w-10 h-10 text-slate-500 mx-auto mb-2" />
          <p className="text-sm font-semibold text-slate-300">Unable to load case data</p>
        </div>
      </div>
    );
  }

  const riskScorePct = caseData.risk_score != null ? Math.round(caseData.risk_score * 100) : null;
  const confPct = caseData.confidence != null ? Math.round(caseData.confidence * 100) : null;
  const compPct = caseData.evidence_completeness != null ? Math.round(caseData.evidence_completeness * 100) : null;

  return (
    <div className="flex-1 flex flex-col bg-brand-900/60 border border-brand-700/60 rounded-xl overflow-hidden glass-panel h-full">
      {/* Case Header Bar */}
      <div className="p-4 border-b border-brand-700/60 bg-brand-950/60 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-lg font-black tracking-tight text-white font-mono">
              {caseData.case_id}
            </span>
            <CaseStatusBadge status={caseData.case_status} />
          </div>

          <span className="text-slate-600">|</span>

          <span className="text-xs text-slate-400 font-medium">
            Trigger:{" "}
            <span className="text-slate-200 font-mono font-semibold">
              {caseData.trigger_type}
            </span>
          </span>
        </div>

        {/* Persisted & Memory Status Badges */}
        <div className="flex items-center gap-2 text-xs">
          {caseData.stop_reason && (
            <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-brand-800 text-slate-300 border border-brand-700">
              {caseData.stop_reason}
            </span>
          )}

          {caseData.sar_reference && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-fuchsia-950/80 text-fuchsia-300 border border-fuchsia-500/40">
              <FileText className="w-3 h-3" />
              SAR: {caseData.sar_reference}
            </span>
          )}

          {caseData.is_persisted && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-500/40">
              <Database className="w-3 h-3" /> Persisted
            </span>
          )}

          {caseData.is_indexed && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-indigo-950/80 text-indigo-300 border border-indigo-500/40">
              <Brain className="w-3 h-3" /> Memory Indexed
            </span>
          )}
        </div>
      </div>

      {/* Triad Score Cards (Risk, Confidence, Completeness) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4 bg-brand-950/30 border-b border-brand-700/60">
        {/* Risk Score */}
        <div className="p-3 rounded-lg bg-brand-950/80 border border-brand-700/60 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Assessed Risk
            </div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-xl font-black text-white font-mono">
                {riskScorePct !== null ? `${riskScorePct}%` : "N/A"}
              </span>
              <RiskBadge level={caseData.risk_level} size="sm" />
            </div>
          </div>
          <ShieldAlert className="w-7 h-7 text-orange-400/50" />
        </div>

        {/* Confidence */}
        <div className="p-3 rounded-lg bg-brand-950/80 border border-brand-700/60 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Investigation Confidence
            </div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-xl font-black text-cyan-400 font-mono">
                {confPct !== null ? `${confPct}%` : "N/A"}
              </span>
              <span className="text-xs text-slate-400">Certainty</span>
            </div>
          </div>
          <Sparkles className="w-7 h-7 text-cyan-400/50" />
        </div>

        {/* Evidence Completeness */}
        <div className="p-3 rounded-lg bg-brand-950/80 border border-brand-700/60 flex items-center justify-between">
          <div>
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Evidence Completeness
            </div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-xl font-black text-indigo-400 font-mono">
                {compPct !== null ? `${compPct}%` : "N/A"}
              </span>
              <span className="text-xs text-slate-400">Sufficiency Gate</span>
            </div>
          </div>
          <Scale className="w-7 h-7 text-indigo-400/50" />
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 px-4 pt-2 border-b border-brand-700/60 bg-brand-950/40 text-xs">
        <button
          onClick={() => setActiveTab("overview")}
          className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-medium transition-all ${
            activeTab === "overview"
              ? "border-orange-500 text-orange-400 font-bold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Info className="w-3.5 h-3.5" />
          <span>Reasoning & Actions</span>
        </button>

        <button
          onClick={() => setActiveTab("timeline")}
          className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-medium transition-all ${
            activeTab === "timeline"
              ? "border-orange-500 text-orange-400 font-bold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Radio
            className={`w-3.5 h-3.5 ${
              connectionStatus === "OPEN" ? "text-emerald-400 animate-pulse" : "text-slate-400"
            }`}
          />
          <span>Timeline ({sseEvents.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("evidence")}
          className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-medium transition-all ${
            activeTab === "evidence"
              ? "border-orange-500 text-orange-400 font-bold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Evidence Items ({evidenceData?.total_count ?? 0})</span>
        </button>

        <button
          onClick={() => setActiveTab("graph")}
          className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-medium transition-all ${
            activeTab === "graph"
              ? "border-orange-500 text-orange-400 font-bold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Network className="w-3.5 h-3.5" />
          <span>Graph Topology</span>
        </button>

        <button
          onClick={() => setActiveTab("precedents")}
          className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-medium transition-all ${
            activeTab === "precedents"
              ? "border-orange-500 text-orange-400 font-bold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <History className="w-3.5 h-3.5" />
          <span>Similar Precedents ({caseData.similar_cases?.length ?? 0})</span>
        </button>

        <button
          onClick={() => setActiveTab("policy")}
          className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-medium transition-all ${
            activeTab === "policy"
              ? "border-orange-500 text-orange-400 font-bold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <BookOpen className="w-3.5 h-3.5" />
          <span>Policy & Regulations ({caseData.policy_context?.length ?? 0})</span>
        </button>

        <button
          onClick={() => setActiveTab("actions")}
          className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-medium transition-all ${
            activeTab === "actions"
              ? "border-orange-500 text-orange-400 font-bold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          <span>Execution Log ({caseData.executed_actions?.length ?? 0})</span>
        </button>

        <button
          onClick={() => setActiveTab("audit")}
          className={`flex items-center gap-1.5 px-3 py-2 border-b-2 font-medium transition-all ${
            activeTab === "audit"
              ? "border-orange-500 text-orange-400 font-bold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>Audit & Traces</span>
        </button>
      </div>

      {/* Main Workspace Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* OVERVIEW TAB */}
        {activeTab === "overview" && (
          <div className="space-y-5">
            {/* Triad Assessment Panel (Risk, Confidence, Completeness) */}
            <AssessmentPanel caseData={caseData} />

            {/* Target Entities Involved */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="p-3 rounded-lg bg-brand-950/60 border border-brand-700/60">
                <span className="text-[10px] text-slate-500 uppercase font-mono">
                  Customer ID
                </span>
                <p className="text-xs font-mono font-bold text-slate-200 mt-0.5">
                  {caseData.customer_id || "Unspecified"}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-brand-950/60 border border-brand-700/60">
                <span className="text-[10px] text-slate-500 uppercase font-mono">
                  Trigger Transaction
                </span>
                <p className="text-xs font-mono font-bold text-slate-200 mt-0.5">
                  {caseData.transaction_id || "Unspecified"}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-brand-950/60 border border-brand-700/60">
                <span className="text-[10px] text-slate-500 uppercase font-mono">
                  Target Accounts
                </span>
                <p className="text-xs font-mono font-bold text-slate-200 mt-0.5 truncate">
                  {caseData.account_ids && caseData.account_ids.length > 0
                    ? caseData.account_ids.join(", ")
                    : "None specified"}
                </p>
              </div>
            </div>

            {/* Competing Hypotheses & Evidence Grounding */}
            <HypothesisPanel
              caseData={caseData}
              onSelectEvidence={() => setActiveTab("evidence")}
            />

            {/* Next-Best Actions & Human-in-the-Loop Governance */}
            <NextBestActionPanel
              caseData={caseData}
              onCaseUpdated={(updated) => {
                setCaseData(updated);
                onCaseUpdated(updated);
              }}
            />
          </div>
        )}

        {/* TIMELINE TAB */}
        {activeTab === "timeline" && (
          <div className="h-[560px]">
            <InvestigationTimeline
              events={sseEvents}
              connectionStatus={connectionStatus}
              onReconnect={reconnect}
              isLoading={isLoading}
            />
          </div>
        )}

        {/* EVIDENCE TAB */}
        {activeTab === "evidence" && (
          <EvidencePanel
            evidence={evidenceData?.evidence || []}
            onSubmitEvidence={handleEvidenceSubmit}
            isSubmitting={isSubmittingEvidence}
          />
        )}

        {/* GRAPH TAB */}
        {activeTab === "graph" && (
          <div className="h-[560px]">
            <FraudGraphVisualization
              graphData={graphData}
              evidenceData={evidenceData}
              caseId={caseId}
            />
          </div>
        )}

        {/* PRECEDENTS TAB */}
        {activeTab === "precedents" && (
          <SimilarCasesPanel
            caseData={caseData}
            evidenceList={evidenceData?.evidence}
          />
        )}

        {/* POLICY TAB */}
        {activeTab === "policy" && (
          <PolicyGuidancePanel
            caseData={caseData}
            evidenceList={evidenceData?.evidence}
          />
        )}

        {/* ACTIONS TAB */}
        {activeTab === "actions" && (
          <div className="space-y-4">
            <NextBestActionPanel
              caseData={caseData}
              onCaseUpdated={(updated) => {
                setCaseData(updated);
                onCaseUpdated(updated);
              }}
            />
          </div>
        )}

        {/* AUDIT & TRACES TAB */}
        {activeTab === "audit" && (
          <AuditTrailPanel
            caseId={caseId}
            caseData={caseData}
          />
        )}
      </div>
    </div>
  );
};
