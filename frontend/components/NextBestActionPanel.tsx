"use client";

import React, { useState } from "react";
import {
  ActionType,
  ApprovalActionRequest,
  ApprovalRole,
  InvestigationResponse,
  ModifyActionRequest,
  NextBestActionItem,
} from "@/types/api";
import { api } from "@/lib/api";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Edit3,
  FileText,
  GitBranch,
  Lock,
  RefreshCw,
  Scale,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Sparkles,
  UserCheck,
  XCircle,
} from "lucide-react";

interface NextBestActionPanelProps {
  caseData: InvestigationResponse;
  onCaseUpdated: (updated: InvestigationResponse) => void;
}

const MODIFIABLE_ACTIONS: { type: ActionType; label: string; desc: string }[] = [
  {
    type: "ALLOW_TRANSACTION",
    label: "Allow Transaction",
    desc: "Permit transaction processing without friction",
  },
  {
    type: "BLOCK_TRANSACTION",
    label: "Block Transaction",
    desc: "Decline transaction immediately due to elevated fraud risk",
  },
  {
    type: "MONITOR_TRANSACTION",
    label: "Monitor Transaction",
    desc: "Flag transaction for ongoing post-settlement surveillance",
  },
  {
    type: "MONITOR_ACCOUNT",
    label: "Monitor Account",
    desc: "Place account under heightened AML/fraud monitoring",
  },
  {
    type: "BLOCK_ACCOUNT",
    label: "Block Account",
    desc: "Freeze account activities pending comprehensive KYC review",
  },
  {
    type: "WARN_CUSTOMER",
    label: "Warn Customer",
    desc: "Issue security alert to cardholder regarding suspicious activity",
  },
  {
    type: "REQUEST_CUSTOMER_CONFIRMATION",
    label: "Request Customer Confirmation",
    desc: "Send 2-way SMS or in-app push to verify transaction validity",
  },
  {
    type: "REQUEST_STEP_UP_AUTH",
    label: "Request Step-Up Auth",
    desc: "Trigger 3D Secure / biometric challenge before authorization",
  },
  {
    type: "REQUEST_ANALYST_EVIDENCE",
    label: "Request Analyst Evidence",
    desc: "Route case to Tier 2 specialist for deep forensic inquiry",
  },
  {
    type: "ESCALATE_ANALYST",
    label: "Escalate to Analyst",
    desc: "Escalate to senior fraud manager or compliance team",
  },
  {
    type: "FILE_SAR",
    label: "File SAR",
    desc: "Generate and submit Suspicious Activity Report",
  },
  {
    type: "CLOSE_CASE",
    label: "Close Case",
    desc: "Close case with resolution findings",
  },
  {
    type: "NO_ACTION",
    label: "No Action",
    desc: "No intervention warranted; activity cleared as benign",
  },
];

export function NextBestActionPanel({
  caseData,
  onCaseUpdated,
}: NextBestActionPanelProps) {
  const [isActing, setIsActing] = useState(false);
  const [actionComments, setActionComments] = useState("");
  const [feedbackMessage, setFeedbackMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  // Modify Modal State
  const [modifyModalOpen, setModifyModalOpen] = useState(false);
  const [selectedModifyAction, setSelectedModifyAction] = useState<ActionType>(
    caseData.post_evidence_action?.action_type ||
      caseData.pre_evidence_action?.action_type ||
      "MONITOR_TRANSACTION"
  );
  const [modifyReasoning, setModifyReasoning] = useState("");
  const [reviewerRole, setReviewerRole] = useState<ApprovalRole>(
    caseData.post_evidence_action?.approval_role || "FRAUD_ANALYST"
  );

  const preAction = caseData.pre_evidence_action;
  const postAction = caseData.post_evidence_action;
  const requestedEvidence = caseData.requested_evidence || [];
  const executedActions = caseData.executed_actions || [];

  // Determine if recommendation changed after evidence loop
  const hasRecommendationShift =
    preAction && postAction && preAction.action_type !== postAction.action_type;

  const handleApprove = async () => {
    setIsActing(true);
    setFeedbackMessage(null);
    try {
      const req: ApprovalActionRequest = {
        reviewer_role: reviewerRole,
        reviewer_id: "ANALYST_01",
        comments: actionComments.trim() || "Approved by fraud investigator",
      };
      const updated = await api.approveAction(caseData.case_id, req);
      onCaseUpdated(updated);
      setActionComments("");
      setFeedbackMessage({
        type: "success",
        text: "Action successfully authorized and executed in simulation mode.",
      });
    } catch (err: any) {
      setFeedbackMessage({
        type: "error",
        text: `Approval failed: ${err.message}`,
      });
    } finally {
      setIsActing(false);
    }
  };

  const handleReject = async () => {
    setIsActing(true);
    setFeedbackMessage(null);
    try {
      const req: ApprovalActionRequest = {
        reviewer_role: reviewerRole,
        reviewer_id: "ANALYST_01",
        comments: actionComments.trim() || "Action rejected after manual verification",
      };
      const updated = await api.rejectAction(caseData.case_id, req);
      onCaseUpdated(updated);
      setActionComments("");
      setFeedbackMessage({
        type: "success",
        text: "Action rejected. Case routed to alternative policy state.",
      });
    } catch (err: any) {
      setFeedbackMessage({
        type: "error",
        text: `Rejection failed: ${err.message}`,
      });
    } finally {
      setIsActing(false);
    }
  };

  const handleModify = async () => {
    setIsActing(true);
    setFeedbackMessage(null);
    try {
      const req: ModifyActionRequest = {
        action_type: selectedModifyAction,
        reviewer_role: reviewerRole,
        reviewer_id: "ANALYST_01",
        comments: actionComments.trim() || "Action modified based on analyst discretion",
        reasoning:
          modifyReasoning.trim() ||
          "Action modified by analyst to align with customer profile and evidence nuance",
      };
      const updated = await api.modifyAction(caseData.case_id, req);
      onCaseUpdated(updated);
      setModifyModalOpen(false);
      setActionComments("");
      setModifyReasoning("");
      setFeedbackMessage({
        type: "success",
        text: `Action successfully modified to ${selectedModifyAction} and re-evaluated through policy engine.`,
      });
    } catch (err: any) {
      setFeedbackMessage({
        type: "error",
        text: `Action modification failed: ${err.message}`,
      });
    } finally {
      setIsActing(false);
    }
  };

  const getActionBadgeClass = (actionType?: string) => {
    if (!actionType) return "bg-slate-800 text-slate-400 border-slate-700";
    if (actionType.includes("BLOCK")) {
      return "bg-red-500/10 text-red-400 border-red-500/40";
    }
    if (actionType.includes("ALLOW") || actionType.includes("CLOSE")) {
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/40";
    }
    if (actionType.includes("MONITOR")) {
      return "bg-cyan-500/10 text-cyan-400 border-cyan-500/40";
    }
    if (actionType.includes("WARN") || actionType.includes("REQUEST")) {
      return "bg-amber-500/10 text-amber-400 border-amber-500/40";
    }
    if (actionType.includes("SAR") || actionType.includes("ESCALATE")) {
      return "bg-purple-500/10 text-purple-400 border-purple-500/40";
    }
    return "bg-brand-800 text-slate-300 border-brand-700";
  };

  const getApprovalBadgeClass = (status?: string) => {
    switch (status) {
      case "APPROVED":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/40";
      case "REJECTED":
        return "bg-red-500/10 text-red-400 border-red-500/40";
      case "MODIFIED":
        return "bg-cyan-500/10 text-cyan-400 border-cyan-500/40";
      case "PENDING":
        return "bg-amber-500/10 text-amber-400 border-amber-500/40 animate-pulse";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  return (
    <div className="rounded-xl bg-brand-950/80 border border-brand-700/80 p-5 space-y-5">
      {/* Header & Governance Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-brand-700/60 pb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center">
            <GitBranch className="w-4 h-4 text-cyan-400" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-100 uppercase tracking-wider">
              Next-Best Action & Policy Resolution Engine
            </h4>
            <p className="text-[11px] text-slate-400">
              Grounded policy validation, progression tracking, and human-in-the-loop governance
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Simulated Mode Badge */}
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-cyan-950/70 border border-cyan-500/50 text-cyan-300">
            <Shield className="w-3 h-3 text-cyan-400" />
            SIMULATED EXECUTION
          </span>

          {/* Approval State Badge */}
          <span
            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold border ${getApprovalBadgeClass(
              caseData.approval_status
            )}`}
          >
            {caseData.approval_status === "PENDING" && <Clock className="w-3 h-3" />}
            {caseData.approval_status === "APPROVED" && <CheckCircle2 className="w-3 h-3" />}
            {caseData.approval_status === "REJECTED" && <XCircle className="w-3 h-3" />}
            {caseData.approval_status === "MODIFIED" && <Edit3 className="w-3 h-3" />}
            APPROVAL: {caseData.approval_status || "NOT_REQUIRED"}
          </span>
        </div>
      </div>

      {/* Feedback Alert if any */}
      {feedbackMessage && (
        <div
          className={`p-3 rounded-lg text-xs flex items-center justify-between border ${
            feedbackMessage.type === "success"
              ? "bg-emerald-950/50 border-emerald-500/40 text-emerald-300"
              : "bg-red-950/50 border-red-500/40 text-red-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {feedbackMessage.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
            )}
            <span>{feedbackMessage.text}</span>
          </div>
          <button
            onClick={() => setFeedbackMessage(null)}
            className="text-[10px] text-slate-400 hover:text-white underline ml-3"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Evolution Warning Banner if Recommendation Shifted */}
      {hasRecommendationShift && (
        <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-500/40 flex items-start gap-2.5">
          <Sparkles className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-0.5">
            <span className="text-xs font-bold text-amber-300">
              Adaptive Policy Shift Detected
            </span>
            <p className="text-[11px] text-slate-300">
              Additional evidence collection evolved the recommendation from{" "}
              <strong className="text-amber-200">{preAction?.action_type}</strong> to{" "}
              <strong className="text-orange-200">{postAction?.action_type}</strong>. Per{" "}
              <span className="font-mono text-[10px] text-amber-400/90">AGENTS.md §16</span>, both
              recommendations are preserved for compliance auditability.
            </p>
          </div>
        </div>
      )}

      {/* Recommendation Progression Pipeline (Stage 1 -> Intermediary -> Stage 2) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Stage 1: Pre-Evidence Baseline Recommendation */}
        <div className="rounded-xl bg-brand-900/50 border border-brand-700/60 p-4 flex flex-col justify-between space-y-3">
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-semibold tracking-wider text-slate-400 uppercase flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-slate-400"></span>
                1. Initial Baseline Action
              </span>
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                PRE-EVIDENCE
              </span>
            </div>

            {preAction ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2.5 py-1 rounded-md text-xs font-mono font-bold border ${getActionBadgeClass(
                      preAction.action_type
                    )}`}
                  >
                    {preAction.action_type}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">
                  {preAction.reasoning}
                </p>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic py-4">
                No initial baseline recommendation recorded.
              </p>
            )}
          </div>

          {/* Pre-Evidence Footer Metadata */}
          {preAction && (
            <div className="pt-3 border-t border-brand-800/80 space-y-1.5 text-[10px] font-mono text-slate-400">
              <div className="flex items-center justify-between">
                <span>Policy Citation:</span>
                <span className="text-slate-300 font-semibold truncate max-w-[180px]">
                  {preAction.policy_reference || "Standard Baseline Policy"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Governed Role:</span>
                <span className="text-slate-300">
                  {preAction.approval_role || "FRAUD_ANALYST"}
                </span>
              </div>
              {preAction.evidence_ids && preAction.evidence_ids.length > 0 && (
                <div className="flex items-center justify-between">
                  <span>Evidence Grounding:</span>
                  <span className="text-cyan-400">
                    {preAction.evidence_ids.length} facts linked
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Intermediary: Requested Evidence Items (Evidence Planner Loop) */}
        <div className="rounded-xl bg-purple-950/20 border border-purple-800/40 p-4 flex flex-col justify-between space-y-3">
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-semibold tracking-wider text-purple-400 uppercase flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse"></span>
                2. Intermediary Evidence
              </span>
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800/60">
                VOI OPTIMIZED
              </span>
            </div>

            {requestedEvidence.length > 0 ? (
              <div className="space-y-2.5 max-h-48 overflow-y-auto pr-1">
                {requestedEvidence.map((req, idx) => (
                  <div
                    key={req.request_id || idx}
                    className="p-2.5 rounded-lg bg-brand-950/80 border border-purple-900/60 space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-mono font-bold text-purple-300">
                        {req.evidence_type}
                      </span>
                      <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-purple-950/80 text-purple-400 border border-purple-800/50">
                        {req.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-300 leading-tight">
                      {req.reason}
                    </p>
                    <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 font-mono">
                      <span>Target: {req.target_entity_id}</span>
                      <span className="text-emerald-400">
                        ΔU: {(req.expected_uncertainty_reduction * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-6 text-center space-y-1">
                <CheckCircle2 className="w-5 h-5 text-purple-400/60 mx-auto" />
                <p className="text-xs text-purple-300/80">
                  Initial evidence sufficient.
                </p>
                <p className="text-[10px] text-slate-500">
                  Zero secondary evidence loops required for adjudication.
                </p>
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-purple-900/40 text-[10px] font-mono text-purple-300/70 flex items-center justify-between">
            <span>Evidence Loop Status:</span>
            <span className="font-semibold text-purple-300">
              {requestedEvidence.length > 0 ? "Resolved" : "Bypassed"}
            </span>
          </div>
        </div>

        {/* Stage 3: Post-Evidence / Final Active Action */}
        <div className="rounded-xl bg-orange-950/20 border border-orange-500/50 p-4 flex flex-col justify-between space-y-3 shadow-lg shadow-orange-950/20">
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-mono font-bold tracking-wider text-orange-400 uppercase flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-orange-400" />
                3. Active Decision
              </span>
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-orange-950 text-orange-300 border border-orange-700/60 font-bold">
                POLICY AUTHORIZED
              </span>
            </div>

            {postAction ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2.5 py-1 rounded-md text-xs font-mono font-bold border ${getActionBadgeClass(
                      postAction.action_type
                    )}`}
                  >
                    {postAction.action_type}
                  </span>
                  {postAction.approval_required && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-950 border border-purple-500/50 text-purple-300 flex items-center gap-1">
                      <Lock className="w-2.5 h-2.5" />
                      Approval Req
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-200 font-medium leading-relaxed">
                  {postAction.reasoning}
                </p>
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic py-4">
                Evaluating active action through sufficiency gate...
              </p>
            )}
          </div>

          {/* Post-Evidence Footer Metadata */}
          {postAction && (
            <div className="pt-3 border-t border-orange-900/40 space-y-1.5 text-[10px] font-mono text-slate-400">
              <div className="flex items-center justify-between">
                <span>Enforced Policy:</span>
                <span className="text-orange-300 font-semibold truncate max-w-[180px]">
                  {postAction.policy_reference || "Standard Hackathon Policy"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Required Authority:</span>
                <span className="text-orange-300">
                  {postAction.approval_role || "FRAUD_ANALYST"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Execution Mode:</span>
                <span className="text-cyan-400 font-semibold">
                  {postAction.execution_mode || "SIMULATED"}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Human Approval Interactive Console (when approval_required is true and status is PENDING) */}
      {caseData.approval_required && caseData.approval_status === "PENDING" && (
        <div className="p-4 rounded-xl bg-purple-950/40 border border-purple-500/60 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-purple-800/40 pb-2.5">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-purple-500/20 border border-purple-500/40 flex items-center justify-center">
                <Scale className="w-3.5 h-3.5 text-purple-300" />
              </div>
              <span className="text-xs font-bold text-purple-200">
                Mandatory Human Authorization Gate
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-[11px] text-slate-400">Reviewer Role:</span>
              <select
                value={reviewerRole}
                onChange={(e) => setReviewerRole(e.target.value as ApprovalRole)}
                className="px-2 py-1 rounded bg-brand-950 border border-purple-500/50 text-purple-300 text-xs font-mono focus:outline-none focus:border-purple-400"
              >
                <option value="FRAUD_ANALYST">FRAUD_ANALYST</option>
                <option value="SENIOR_FRAUD_ANALYST">SENIOR_FRAUD_ANALYST</option>
                <option value="FRAUD_SUPERVISOR">FRAUD_SUPERVISOR</option>
                <option value="COMPLIANCE_OFFICER">COMPLIANCE_OFFICER</option>
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-[11px] font-semibold text-slate-300 flex items-center justify-between">
              <span>Analyst Adjudication Notes & Compliance Justification</span>
              <span className="text-[10px] text-slate-500 font-normal">
                Persisted to TigerGraph case audit trail
              </span>
            </label>
            <textarea
              rows={2}
              value={actionComments}
              onChange={(e) => setActionComments(e.target.value)}
              placeholder="Enter structured analyst justification, customer contact history, or override rationale..."
              className="w-full px-3 py-2 bg-brand-950 border border-brand-700/80 rounded-lg text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-purple-400"
            />
          </div>

          {/* Action Decision Buttons */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <span className="text-[11px] text-slate-400">
              Selected action will be executed in{" "}
              <strong className="text-cyan-300 font-mono">SIMULATED</strong> mode.
            </span>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setModifyModalOpen(true)}
                disabled={isActing}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-950/80 hover:bg-amber-900 border border-amber-600/50 text-amber-300 text-xs font-semibold transition-all disabled:opacity-50"
              >
                <Sliders className="w-3.5 h-3.5" />
                Modify Action...
              </button>

              <button
                type="button"
                onClick={handleReject}
                disabled={isActing}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-red-950/80 hover:bg-red-900 border border-red-600/50 text-red-300 text-xs font-bold transition-all disabled:opacity-50"
              >
                <XCircle className="w-3.5 h-3.5" />
                Reject Action
              </button>

              <button
                type="button"
                onClick={handleApprove}
                disabled={isActing}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-950 transition-all disabled:opacity-50"
              >
                {isActing ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                )}
                Approve & Execute Action
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Executed Actions Audit Log Section */}
      {executedActions.length > 0 && (
        <div className="space-y-3 pt-2 border-t border-brand-800/80">
          <div className="flex items-center justify-between">
            <h5 className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              Action Execution History ({executedActions.length})
            </h5>
            <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/60">
              ALL EXECUTIONS SIMULATED
            </span>
          </div>

          <div className="space-y-2">
            {executedActions.map((action, idx) => (
              <div
                key={action.execution_id || idx}
                className="p-3 rounded-lg bg-brand-900/40 border border-brand-700/60 flex flex-wrap items-center justify-between gap-2"
              >
                <div className="flex items-center gap-2.5">
                  <div
                    className={`w-6 h-6 rounded flex items-center justify-center ${
                      action.success
                        ? "bg-emerald-500/20 text-emerald-400"
                        : "bg-red-500/20 text-red-400"
                    }`}
                  >
                    {action.success ? (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-slate-200">
                        {action.action_type}
                      </span>
                      <span className="text-[9px] font-mono text-cyan-400 bg-cyan-950 px-1.5 py-0.2 rounded border border-cyan-800/40">
                        {action.execution_mode}
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-400 font-mono">
                      ID: {action.execution_id} • {new Date(action.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>

                {action.result && Object.keys(action.result).length > 0 && (
                  <span className="text-[10px] font-mono text-slate-400 bg-brand-950 px-2 py-1 rounded border border-brand-800 max-w-xs truncate">
                    Result: {JSON.stringify(action.result)}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SAR Notification Bar if Generated */}
      {caseData.sar_reference && (
        <div className="p-3 rounded-lg bg-purple-950/40 border border-purple-500/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-purple-400" />
            <div>
              <span className="text-xs font-bold text-purple-300">
                Suspicious Activity Report (SAR) Generated
              </span>
              <p className="text-[11px] text-slate-300">
                Regulatory filing artifact prepared per policy threshold. Case Ref:{" "}
                <span className="font-mono text-purple-200">{caseData.sar_reference}</span>
              </p>
            </div>
          </div>
          <span className="text-[10px] font-mono text-purple-300 bg-purple-900/60 px-2.5 py-1 rounded border border-purple-700/60">
            SAR VERIFIED
          </span>
        </div>
      )}

      {/* MODIFY ACTION MODAL */}
      {modifyModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-brand-900 border border-brand-700 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-brand-700 pb-3">
              <div className="flex items-center gap-2">
                <Sliders className="w-5 h-5 text-amber-400" />
                <h3 className="text-sm font-bold text-slate-100">
                  Modify Next-Best Action
                </h3>
              </div>
              <button
                onClick={() => setModifyModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  Select Alternative Action
                </label>
                <div className="grid grid-cols-1 gap-2 max-h-56 overflow-y-auto pr-1">
                  {MODIFIABLE_ACTIONS.map((item) => (
                    <button
                      key={item.type}
                      type="button"
                      onClick={() => setSelectedModifyAction(item.type)}
                      className={`p-2.5 rounded-lg text-left border transition-all ${
                        selectedModifyAction === item.type
                          ? "bg-amber-950/60 border-amber-500/80 text-amber-200"
                          : "bg-brand-950/60 border-brand-800 text-slate-300 hover:border-brand-700"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold font-mono">
                          {item.label}
                        </span>
                        <span className="text-[10px] font-mono text-slate-400">
                          {item.type}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {item.desc}
                      </p>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  Modification Rationale (Audit Obligation)
                </label>
                <textarea
                  rows={2}
                  value={modifyReasoning}
                  onChange={(e) => setModifyReasoning(e.target.value)}
                  placeholder="Explain why the automated recommendation is being modified..."
                  className="w-full px-3 py-2 bg-brand-950 border border-brand-700 rounded-lg text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-amber-400"
                />
              </div>

              <div className="p-3 rounded-lg bg-brand-950 border border-brand-800 text-[11px] text-slate-400 space-y-1">
                <div className="flex items-center gap-1.5 text-amber-300 font-semibold">
                  <ShieldAlert className="w-3.5 h-3.5" /> Policy Engine Re-Validation
                </div>
                <p>
                  Per AGENTS.md §19, the modified action will be re-validated against{" "}
                  <code className="text-cyan-300">policy.yaml</code> before execution.
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-brand-800">
              <button
                type="button"
                onClick={() => setModifyModalOpen(false)}
                className="px-4 py-2 rounded-lg bg-brand-800 hover:bg-brand-700 text-slate-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleModify}
                disabled={isActing}
                className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold shadow-lg shadow-amber-950 transition-all disabled:opacity-50"
              >
                {isActing ? "Validating..." : "Confirm & Re-evaluate"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
