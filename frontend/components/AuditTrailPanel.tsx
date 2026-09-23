"use client";

import React, { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { InvestigationResponse, InvestigationTraceResponse, TraceSpanItem } from "@/types/api";
import {
  Activity,
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Code,
  Copy,
  Cpu,
  Database,
  Download,
  ExternalLink,
  Eye,
  FileCode2,
  Filter,
  Layers,
  RefreshCw,
  Search,
  Shield,
  Sparkles,
  Terminal,
  Zap,
} from "lucide-react";

interface AuditTrailPanelProps {
  caseId: string;
  caseData?: InvestigationResponse;
}

export function AuditTrailPanel({ caseId, caseData }: AuditTrailPanelProps) {
  const [traceData, setTraceData] = useState<InvestigationTraceResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSpanType, setSelectedSpanType] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedSpan, setSelectedSpan] = useState<TraceSpanItem | null>(null);
  const [copiedPath, setCopiedPath] = useState<boolean>(false);
  const [copiedJson, setCopiedJson] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  // Load trace data from backend
  const fetchTrace = React.useCallback(async () => {
    setIsRefreshing(true);
    setError(null);
    try {
      const data = await api.getInvestigationTrace(caseId);
      setTraceData(data);
    } catch (err: any) {
      console.error("Failed to load trace data:", err);
      setError(err?.message || "Failed to load trace data.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [caseId]);

  useEffect(() => {
    if (caseId) {
      fetchTrace();
    }
  }, [caseId, fetchTrace]);

  // Aggregate metrics
  const metrics = useMemo(() => {
    if (!traceData || !traceData.spans) {
      return {
        totalDurationMs: 0,
        gsqlDurationMs: 0,
        graphRagDurationMs: 0,
        llmDurationMs: 0,
        nodeDurationMs: 0,
        policyDurationMs: 0,
        actionDurationMs: 0,
        errorCount: 0,
        spanCount: 0,
        maxSpanDurationMs: 1,
      };
    }

    let gsql = 0;
    let graphRag = 0;
    let llm = 0;
    let node = 0;
    let policy = 0;
    let action = 0;
    let errors = 0;
    let maxDuration = 1;

    for (const span of traceData.spans) {
      const d = span.duration_ms || 0;
      if (d > maxDuration) maxDuration = d;
      if (span.status === "ERROR") errors++;

      switch (span.span_type) {
        case "GSQL_QUERY":
          gsql += d;
          break;
        case "GRAPHRAG":
          graphRag += d;
          break;
        case "LLM_INVOCATION":
          llm += d;
          break;
        case "NODE":
          node += d;
          break;
        case "POLICY_CHECK":
          policy += d;
          break;
        case "ACTION_SIMULATION":
          action += d;
          break;
      }
    }

    return {
      totalDurationMs: traceData.total_duration_ms || 0,
      gsqlDurationMs: gsql,
      graphRagDurationMs: graphRag,
      llmDurationMs: llm,
      nodeDurationMs: node,
      policyDurationMs: policy,
      actionDurationMs: action,
      errorCount: errors,
      spanCount: traceData.spans.length,
      maxSpanDurationMs: maxDuration,
    };
  }, [traceData]);

  // Filtered Spans
  const filteredSpans = useMemo(() => {
    if (!traceData?.spans) return [];

    return traceData.spans.filter((span) => {
      // Type filter
      if (selectedSpanType !== "ALL") {
        if (selectedSpanType === "ERROR") {
          if (span.status !== "ERROR") return false;
        } else if (span.span_type !== selectedSpanType) {
          return false;
        }
      }

      // Search query filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = span.name.toLowerCase().includes(q);
        const matchType = span.span_type.toLowerCase().includes(q);
        const matchNode = span.node_name?.toLowerCase().includes(q) || false;
        const matchTags = span.tags ? span.tags.some((t: string) => t.toLowerCase().includes(q)) : false;
        return matchName || matchType || matchNode || matchTags;
      }

      return true;
    });
  }, [traceData, selectedSpanType, searchQuery]);

  const copyTracePath = () => {
    if (traceData?.trace_file_path) {
      navigator.clipboard.writeText(traceData.trace_file_path);
      setCopiedPath(true);
      setTimeout(() => setCopiedPath(false), 2000);
    }
  };

  const copyRawJson = () => {
    if (selectedSpan) {
      navigator.clipboard.writeText(JSON.stringify(selectedSpan, null, 2));
      setCopiedJson(true);
      setTimeout(() => setCopiedJson(false), 2000);
    }
  };

  const downloadFullTraceJson = () => {
    if (!traceData) return;
    const blob = new Blob([JSON.stringify(traceData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `trace_${caseId}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Helper badge styles for span types
  const getSpanTypeBadge = (spanType: string) => {
    switch (spanType) {
      case "NODE":
        return {
          label: "Workflow Node",
          bg: "bg-blue-500/10 border-blue-500/30 text-blue-400",
          icon: Layers,
        };
      case "GSQL_QUERY":
        return {
          label: "TigerGraph GSQL",
          bg: "bg-orange-500/10 border-orange-500/30 text-orange-400",
          icon: Database,
        };
      case "GRAPHRAG":
        return {
          label: "GraphRAG Retrieval",
          bg: "bg-purple-500/10 border-purple-500/30 text-purple-400",
          icon: Sparkles,
        };
      case "LLM_INVOCATION":
        return {
          label: "LLM Reasoning",
          bg: "bg-cyan-500/10 border-cyan-500/30 text-cyan-400",
          icon: Cpu,
        };
      case "POLICY_CHECK":
        return {
          label: "Policy Engine",
          bg: "bg-amber-500/10 border-amber-500/30 text-amber-400",
          icon: Shield,
        };
      case "ACTION_SIMULATION":
        return {
          label: "Action Sim",
          bg: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
          icon: Zap,
        };
      case "HUMAN_APPROVAL":
        return {
          label: "Analyst Approval",
          bg: "bg-pink-500/10 border-pink-500/30 text-pink-400",
          icon: CheckCircle2,
        };
      default:
        return {
          label: spanType,
          bg: "bg-slate-500/10 border-slate-500/30 text-slate-400",
          icon: Activity,
        };
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 bg-brand-950/40 border border-brand-700/60 rounded-xl text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-2 border-orange-500 border-t-transparent mb-3" />
        <p className="text-sm font-semibold text-slate-300">Loading Execution Audit Trail...</p>
        <p className="text-xs text-slate-500 font-mono mt-1">Reading trace logs for {caseId}</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Top Header & Audit Trace Path Callout */}
      <div className="bg-brand-950/60 border border-brand-700/60 rounded-xl p-4">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 pb-3 border-b border-brand-800">
          <div>
            <div className="flex items-center gap-2">
              <Terminal className="w-5 h-5 text-orange-400" />
              <h3 className="text-base font-bold text-white tracking-wide">
                Investigation Audit Trail & Execution Observability
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Deterministic, sanitized span telemetry recorded during LangGraph orchestration.
              Every node transition, GSQL query, GraphRAG retrieval, and policy check is logged.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchTrace}
              disabled={isRefreshing}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-900 border border-brand-700 text-xs font-medium text-slate-200 hover:bg-brand-850 hover:text-white transition disabled:opacity-50"
              title="Refresh trace"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-orange-400" : ""}`} />
              <span>Refresh</span>
            </button>
            <button
              onClick={downloadFullTraceJson}
              disabled={!traceData?.spans?.length}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-orange-600/20 border border-orange-500/40 text-xs font-semibold text-orange-300 hover:bg-orange-600/30 transition disabled:opacity-50"
              title="Download JSON trace"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Trace</span>
            </button>
          </div>
        </div>

        {/* Trace File Storage & Sanitization Guarantee */}
        <div className="mt-3 flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2 text-slate-300 font-mono truncate">
            <FileCode2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span className="text-slate-400 font-sans text-xs">Trace Log:</span>
            <span className="text-emerald-300 truncate bg-slate-900/80 px-2 py-0.5 rounded border border-emerald-900/50">
              {traceData?.trace_file_path || `outputs/traces/${caseId}.jsonl`}
            </span>
            <button
              onClick={copyTracePath}
              className="text-slate-400 hover:text-slate-200 transition p-1"
              title="Copy trace path"
            >
              <Copy className="w-3.5 h-3.5" />
            </button>
            {copiedPath && <span className="text-[10px] text-emerald-400 font-sans">Copied!</span>}
          </div>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[11px] font-medium">
              <Shield className="w-3 h-3" />
              AGENTS.md §32 Secrets Sanitized
            </span>
          </div>
        </div>
      </div>

      {/* Latency & Telemetry Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {/* Total Duration */}
        <div className="p-3 rounded-lg bg-brand-950/70 border border-brand-700/60">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px] font-medium">
            <Clock className="w-3.5 h-3.5 text-orange-400" />
            <span>Total Duration</span>
          </div>
          <div className="text-lg font-bold font-mono text-white mt-1">
            {metrics.totalDurationMs >= 1000
              ? `${(metrics.totalDurationMs / 1000).toFixed(2)}s`
              : `${Math.round(metrics.totalDurationMs)}ms`}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5 font-mono">{metrics.spanCount} spans</div>
        </div>

        {/* TigerGraph GSQL Latency */}
        <div className="p-3 rounded-lg bg-brand-950/70 border border-brand-700/60">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px] font-medium">
            <Database className="w-3.5 h-3.5 text-orange-400" />
            <span>GSQL Queries</span>
          </div>
          <div className="text-lg font-bold font-mono text-orange-400 mt-1">
            {Math.round(metrics.gsqlDurationMs)}ms
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5 font-mono">TigerGraph Savanna</div>
        </div>

        {/* GraphRAG Retrieval */}
        <div className="p-3 rounded-lg bg-brand-950/70 border border-brand-700/60">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px] font-medium">
            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
            <span>GraphRAG Latency</span>
          </div>
          <div className="text-lg font-bold font-mono text-purple-400 mt-1">
            {Math.round(metrics.graphRagDurationMs)}ms
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5 font-mono">Hybrid Retrieval</div>
        </div>

        {/* LLM Reasoning */}
        <div className="p-3 rounded-lg bg-brand-950/70 border border-brand-700/60">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px] font-medium">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span>LLM Latency</span>
          </div>
          <div className="text-lg font-bold font-mono text-cyan-400 mt-1">
            {Math.round(metrics.llmDurationMs)}ms
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5 font-mono">Groq / Gemini</div>
        </div>

        {/* Policy Checks */}
        <div className="p-3 rounded-lg bg-brand-950/70 border border-brand-700/60">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px] font-medium">
            <Shield className="w-3.5 h-3.5 text-amber-400" />
            <span>Policy Engine</span>
          </div>
          <div className="text-lg font-bold font-mono text-amber-400 mt-1">
            {Math.round(metrics.policyDurationMs)}ms
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5 font-mono">Deterministic Rules</div>
        </div>

        {/* Error Count */}
        <div className="p-3 rounded-lg bg-brand-950/70 border border-brand-700/60">
          <div className="flex items-center gap-1.5 text-slate-400 text-[11px] font-medium">
            <AlertCircle
              className={`w-3.5 h-3.5 ${metrics.errorCount > 0 ? "text-red-400" : "text-emerald-400"}`}
            />
            <span>Trace Health</span>
          </div>
          <div
            className={`text-lg font-bold font-mono mt-1 ${
              metrics.errorCount > 0 ? "text-red-400" : "text-emerald-400"
            }`}
          >
            {metrics.errorCount === 0 ? "100% OK" : `${metrics.errorCount} Errors`}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5 font-mono">Execution Status</div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Span Type Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 text-xs">
          {[
            { id: "ALL", label: "All Spans" },
            { id: "NODE", label: "Workflow Nodes" },
            { id: "GSQL_QUERY", label: "GSQL Queries" },
            { id: "GRAPHRAG", label: "GraphRAG" },
            { id: "LLM_INVOCATION", label: "LLM Invocations" },
            { id: "POLICY_CHECK", label: "Policy Checks" },
            { id: "ACTION_SIMULATION", label: "Actions" },
            { id: "ERROR", label: `Errors (${metrics.errorCount})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedSpanType(tab.id)}
              className={`px-2.5 py-1 rounded-md font-medium text-xs transition ${
                selectedSpanType === tab.id
                  ? "bg-orange-500 text-white shadow-sm shadow-orange-500/20"
                  : "bg-brand-900/60 text-slate-400 hover:text-slate-200 border border-brand-700/50"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search input */}
        <div className="relative min-w-[200px]">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search spans, nodes, tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-brand-950/80 border border-brand-700/60 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-orange-500 transition"
          />
        </div>
      </div>

      {/* Main Execution Waterfall Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Waterfall List (Left column or full if no selection) */}
        <div className={`space-y-2 ${selectedSpan ? "lg:col-span-7" : "lg:col-span-12"}`}>
          {filteredSpans.length === 0 ? (
            <div className="p-8 text-center bg-brand-950/30 border border-brand-700/40 rounded-xl text-slate-400 text-xs">
              <Activity className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="font-semibold text-slate-300">No telemetry spans found matching criteria.</p>
              <p className="text-slate-500 mt-1">
                Trigger an investigation run or adjust search and filter options.
              </p>
            </div>
          ) : (
            filteredSpans.map((span, idx) => {
              const badge = getSpanTypeBadge(span.span_type);
              const Icon = badge.icon;
              const isSelected = selectedSpan?.span_id === span.span_id;
              const duration = span.duration_ms || 0;
              // Bar width relative to max span duration
              const barWidthPct = Math.max(3, Math.min(100, (duration / metrics.maxSpanDurationMs) * 100));

              return (
                <div
                  key={span.span_id || idx}
                  onClick={() => setSelectedSpan(isSelected ? null : span)}
                  className={`p-3 rounded-lg border transition cursor-pointer select-none ${
                    isSelected
                      ? "bg-brand-900/90 border-orange-500 ring-1 ring-orange-500/50"
                      : span.status === "ERROR"
                      ? "bg-red-950/20 border-red-500/40 hover:border-red-500/60"
                      : "bg-brand-950/60 border-brand-700/60 hover:border-brand-600 hover:bg-brand-900/40"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5 min-w-0">
                      <div
                        className={`p-1.5 rounded-md border mt-0.5 shrink-0 ${badge.bg}`}
                        title={badge.label}
                      >
                        <Icon className="w-3.5 h-3.5" />
                      </div>

                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-xs text-white truncate font-mono">
                            {span.name}
                          </span>
                          {span.node_name && (
                            <span className="text-[10px] text-slate-400 px-1.5 py-0.2 rounded bg-brand-900 border border-brand-700 font-mono">
                              {span.node_name}
                            </span>
                          )}
                          {span.status === "ERROR" && (
                            <span className="text-[10px] font-bold text-red-400 px-1.5 py-0.2 rounded bg-red-500/20 border border-red-500/40">
                              ERROR
                            </span>
                          )}
                        </div>

                        {/* Tags & Start timestamp */}
                        <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-400">
                          <span>{span.start_time ? new Date(span.start_time).toLocaleTimeString() : "--:--:--"}</span>
                          {span.tags && span.tags.length > 0 && (
                            <>
                              <span>•</span>
                              <div className="flex items-center gap-1 truncate">
                                {span.tags.map((t: string, ti: number) => (
                                  <span key={ti} className="text-slate-500 font-mono">
                                    #{t}
                                  </span>
                                ))}
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Latency and Duration Meter */}
                    <div className="flex flex-col items-end shrink-0 min-w-[90px]">
                      <div className="flex items-center gap-1 font-mono text-xs font-semibold text-slate-200">
                        <Clock className="w-3 h-3 text-slate-400" />
                        <span>{duration < 1 ? "<1ms" : `${Math.round(duration)}ms`}</span>
                      </div>

                      {/* Waterfall mini-meter bar */}
                      <div className="w-20 bg-slate-800 h-1.5 rounded-full overflow-hidden mt-1.5">
                        <div
                          className={`h-full rounded-full ${
                            span.status === "ERROR"
                              ? "bg-red-500"
                              : span.span_type === "GSQL_QUERY"
                              ? "bg-orange-500"
                              : span.span_type === "GRAPHRAG"
                              ? "bg-purple-500"
                              : span.span_type === "LLM_INVOCATION"
                              ? "bg-cyan-500"
                              : "bg-blue-500"
                          }`}
                          style={{ width: `${barWidthPct}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Selected Span Detailed Inspector Drawer */}
        {selectedSpan && (
          <div className="lg:col-span-5 bg-brand-950/80 border border-brand-700/80 rounded-xl p-4 space-y-4 self-start sticky top-4">
            <div className="flex items-center justify-between border-b border-brand-800 pb-3">
              <div className="flex items-center gap-2">
                <Code className="w-4 h-4 text-orange-400" />
                <h4 className="text-xs font-bold text-white uppercase tracking-wider">
                  Span Telemetry Inspector
                </h4>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={copyRawJson}
                  className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200 bg-brand-900 border border-brand-700 px-2 py-1 rounded transition"
                  title="Copy Span JSON"
                >
                  <Copy className="w-3 h-3" />
                  <span>{copiedJson ? "Copied!" : "Copy JSON"}</span>
                </button>
                <button
                  onClick={() => setSelectedSpan(null)}
                  className="text-slate-400 hover:text-white text-xs p-1"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Span summary info */}
            <div className="space-y-2 text-xs">
              <div>
                <span className="text-slate-500 text-[10px] uppercase font-mono">Span Identifier</span>
                <p className="font-mono font-bold text-slate-200 break-all">{selectedSpan.span_id}</p>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-mono">Span Type</span>
                  <p className="font-mono text-slate-300 font-semibold">{selectedSpan.span_type}</p>
                </div>
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-mono">Duration</span>
                  <p className="font-mono text-orange-400 font-bold">
                    {selectedSpan.duration_ms ? `${selectedSpan.duration_ms.toFixed(1)} ms` : "In Progress"}
                  </p>
                </div>
              </div>

              {selectedSpan.node_name && (
                <div>
                  <span className="text-slate-500 text-[10px] uppercase font-mono">LangGraph Node</span>
                  <p className="font-mono text-slate-300">{selectedSpan.node_name}</p>
                </div>
              )}

              {selectedSpan.error && (
                <div className="p-2.5 rounded bg-red-950/40 border border-red-500/40 text-red-300">
                  <div className="text-[10px] font-bold uppercase font-mono text-red-400">Captured Exception</div>
                  <div className="text-xs font-mono mt-1 whitespace-pre-wrap">{selectedSpan.error}</div>
                </div>
              )}
            </div>

            {/* Formatted Inputs */}
            {selectedSpan.inputs && Object.keys(selectedSpan.inputs).length > 0 && (
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-400 font-bold">
                  Inputs (Sanitized)
                </span>
                <pre className="mt-1 p-2.5 rounded-lg bg-slate-950/90 border border-brand-800 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-44">
                  {JSON.stringify(selectedSpan.inputs, null, 2)}
                </pre>
              </div>
            )}

            {/* Formatted Outputs */}
            {selectedSpan.outputs && Object.keys(selectedSpan.outputs).length > 0 && (
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-400 font-bold">
                  Outputs / Results
                </span>
                <pre className="mt-1 p-2.5 rounded-lg bg-slate-950/90 border border-brand-800 text-[11px] font-mono text-slate-300 overflow-x-auto max-h-56">
                  {JSON.stringify(selectedSpan.outputs, null, 2)}
                </pre>
              </div>
            )}

            {/* Metadata & Tags */}
            {selectedSpan.metadata && Object.keys(selectedSpan.metadata).length > 0 && (
              <div>
                <span className="text-[10px] uppercase font-mono text-slate-400 font-bold">
                  Metadata & Config
                </span>
                <pre className="mt-1 p-2.5 rounded-lg bg-slate-950/90 border border-brand-800 text-[11px] font-mono text-slate-400 overflow-x-auto max-h-36">
                  {JSON.stringify(selectedSpan.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
