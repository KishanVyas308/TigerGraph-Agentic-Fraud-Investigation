import React from "react";
import { RiskLevel, CaseStatus, ActionType, ApprovalStatus } from "@/types/api";

interface RiskBadgeProps {
  level?: RiskLevel | string;
  size?: "sm" | "md" | "lg";
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, size = "md" }) => {
  if (!level) return null;

  const normalized = level.toUpperCase();
  let badgeStyles = "bg-slate-800 text-slate-400 border-slate-700";
  let dotStyles = "bg-slate-400";

  switch (normalized) {
    case "CRITICAL":
      badgeStyles = "bg-red-950/70 text-red-400 border-red-500/40 shadow-glow-critical";
      dotStyles = "bg-red-500 animate-pulse";
      break;
    case "HIGH":
      badgeStyles = "bg-orange-950/70 text-orange-400 border-orange-500/40 shadow-glow-high";
      dotStyles = "bg-orange-500";
      break;
    case "MEDIUM":
      badgeStyles = "bg-amber-950/60 text-amber-300 border-amber-500/40 shadow-glow-medium";
      dotStyles = "bg-amber-400";
      break;
    case "LOW":
      badgeStyles = "bg-emerald-950/60 text-emerald-300 border-emerald-500/40 shadow-glow-low";
      dotStyles = "bg-emerald-400";
      break;
  }

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs font-semibold gap-1.5",
    md: "px-2.5 py-1 text-xs font-bold gap-2",
    lg: "px-3.5 py-1.5 text-sm font-black gap-2.5 tracking-wide",
  }[size];

  return (
    <span
      className={`inline-flex items-center rounded-full border transition-all ${badgeStyles} ${sizeClasses}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotStyles}`} />
      <span>{normalized}</span>
    </span>
  );
};

interface CaseStatusBadgeProps {
  status: CaseStatus | string;
}

export const CaseStatusBadge: React.FC<CaseStatusBadgeProps> = ({ status }) => {
  const normalized = (status || "OPEN").toUpperCase();

  let styles = "bg-slate-800/80 text-slate-300 border-slate-700";
  let pulse = false;

  switch (normalized) {
    case "OPEN":
      styles = "bg-blue-950/60 text-blue-300 border-blue-600/40";
      break;
    case "IN_PROGRESS":
      styles = "bg-cyan-950/60 text-cyan-300 border-cyan-500/40";
      pulse = true;
      break;
    case "AWAITING_APPROVAL":
      styles = "bg-purple-950/70 text-purple-300 border-purple-500/50 shadow-sm";
      pulse = true;
      break;
    case "AWAITING_EVIDENCE":
      styles = "bg-amber-950/60 text-amber-300 border-amber-500/40";
      break;
    case "COMPLETED":
    case "RESOLVED":
      styles = "bg-emerald-950/60 text-emerald-300 border-emerald-500/40";
      break;
    case "CLOSED":
      styles = "bg-slate-900 text-slate-400 border-slate-700/50";
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles}`}
    >
      {pulse && <span className="w-1.5 h-1.5 rounded-full bg-current animate-ping opacity-75" />}
      <span>{normalized.replace(/_/g, " ")}</span>
    </span>
  );
};

interface ActionBadgeProps {
  actionType: ActionType | string;
}

export const ActionBadge: React.FC<ActionBadgeProps> = ({ actionType }) => {
  const norm = (actionType || "").toUpperCase();

  let style = "bg-slate-800 text-slate-300 border-slate-700";

  if (norm.includes("BLOCK")) {
    style = "bg-red-950/80 text-red-300 border-red-500/40";
  } else if (norm.includes("ALLOW")) {
    style = "bg-emerald-950/80 text-emerald-300 border-emerald-500/40";
  } else if (norm.includes("MONITOR")) {
    style = "bg-sky-950/80 text-sky-300 border-sky-500/40";
  } else if (norm.includes("ESCALATE") || norm.includes("WARN")) {
    style = "bg-amber-950/80 text-amber-300 border-amber-500/40";
  } else if (norm.includes("SAR")) {
    style = "bg-fuchsia-950/80 text-fuchsia-300 border-fuchsia-500/40";
  } else if (norm.includes("REQUEST")) {
    style = "bg-indigo-950/80 text-indigo-300 border-indigo-500/40";
  }

  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-mono font-semibold border ${style}`}>
      {norm}
    </span>
  );
};

interface ApprovalBadgeProps {
  status?: ApprovalStatus | string;
}

export const ApprovalBadge: React.FC<ApprovalBadgeProps> = ({ status }) => {
  if (!status) return null;
  const norm = status.toUpperCase();

  let style = "bg-slate-800 text-slate-300 border-slate-700";
  switch (norm) {
    case "APPROVED":
      style = "bg-emerald-950 text-emerald-300 border-emerald-500";
      break;
    case "REJECTED":
      style = "bg-red-950 text-red-300 border-red-500";
      break;
    case "MODIFIED":
      style = "bg-amber-950 text-amber-300 border-amber-500";
      break;
    case "PENDING":
      style = "bg-purple-950 text-purple-300 border-purple-500 animate-pulse";
      break;
  }

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-bold border ${style}`}>
      {norm}
    </span>
  );
};
