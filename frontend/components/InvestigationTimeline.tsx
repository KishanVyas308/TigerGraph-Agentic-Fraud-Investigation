"use client";

import React, { useState, useEffect, useRef } from "react";
import { TimelineEventItem } from "@/types/api";
import { SSEConnectionStatus } from "@/hooks/useInvestigationSSE";
import {
  Activity,
  CheckCircle2,
  Clock,
  Database,
  FileText,
  Radio,
  RotateCw,
  Scale,
  ShieldAlert,
  Sparkles,
  XCircle,
  ChevronDown,
  ChevronRight,
  Zap,
} from "lucide-react";

interface InvestigationTimelineProps {
  events: TimelineEventItem[];
  connectionStatus: SSEConnectionStatus;
  onReconnect?: () => void;
  isLoading?: boolean;
}

export const InvestigationTimeline: React.FC<InvestigationTimelineProps> = ({
  events,
  connectionStatus,
  onReconnect,
  isLoading = false,
}) => {
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [expandedEvents, setExpandedEvents] = useState<Record<string, boolean>>({});
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new event
  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [events, autoScroll]);

  const toggleExpand = (id: string) => {
    setExpandedEvents((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const getEventIcon = (type: string) => {
    const t = type.toUpperCase();
    if (t.includes("ERROR")) {
      return <XCircle className="w-4 h-4 text-red-400" />;
    }
    if (t.includes("APPROVAL_REQUIRED") || t.includes("WAITING")) {
      return <Scale className="w-4 h-4 text-purple-400 animate-pulse" />;
    }
    if (t.includes("SAR") || t.includes("REPORT")) {
      return <FileText className="w-4 h-4 text-fuchsia-400" />;
    }
    if (t.includes("RISK") || t.includes("SUFFICIENCY")) {
      return <ShieldAlert className="w-4 h-4 text-orange-400" />;
    }
    if (t.includes("PERSIST") || t.includes("INDEX") || t.includes("DATABASE")) {
      return <Database className="w-4 h-4 text-emerald-400" />;
    }
    if (t.includes("ACTION")) {
      return <Sparkles className="w-4 h-4 text-cyan-400" />;
    }
    if (t.includes("GRAPH") || t.includes("EVIDENCE") || t.includes("FEATURE")) {
      return <Activity className="w-4 h-4 text-indigo-400" />;
    }
    if (t.includes("FINAL") || t.includes("COMPLETED")) {
      return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
    }
    return <Zap className="w-4 h-4 text-amber-400" />;
  };

  const getStatusBadge = () => {
    switch (connectionStatus) {
      case "OPEN":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-500/40">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span>Live SSE Active</span>
          </span>
        );
      case "CONNECTING":
      case "RECONNECTING":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-amber-950/80 text-amber-300 border border-amber-500/40">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            <span>Reconnecting...</span>
          </span>
        );
      case "CLOSED":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-900 text-slate-400 border border-slate-700">
            <span className="w-2 h-2 rounded-full bg-slate-500" />
            <span>Stream Complete</span>
          </span>
        );
      case "ERROR":
        return (
          <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-red-950/80 text-red-300 border border-red-500/40">
            <span className="w-2 h-2 rounded-full bg-red-400" />
            <span>Stream Interrupted</span>
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full bg-brand-950/70 border border-brand-700/60 rounded-xl overflow-hidden glass-panel">
      {/* Stream Control Bar */}
      <div className="p-3.5 border-b border-brand-700/60 flex items-center justify-between bg-brand-900/40">
        <div className="flex items-center gap-2.5">
          <Radio className="w-4 h-4 text-orange-400 animate-pulse" />
          <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
            Agent Workflow Progression Timeline
          </h4>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-brand-800 text-slate-400">
            {events.length} Events
          </span>
        </div>

        <div className="flex items-center gap-3">
          {getStatusBadge()}

          {/* Auto-scroll checkbox */}
          <label className="flex items-center gap-1.5 text-[11px] text-slate-400 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded bg-brand-950 border-brand-700 text-orange-500 focus:ring-0 w-3 h-3"
            />
            <span>Auto-scroll</span>
          </label>

          {/* Reconnect button */}
          {onReconnect && connectionStatus !== "OPEN" && (
            <button
              onClick={onReconnect}
              className="p-1 rounded bg-brand-800 hover:bg-brand-700 text-slate-300 transition-colors"
              title="Reconnect Stream"
            >
              <RotateCw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Events List Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
        {events.length === 0 ? (
          <div className="p-8 text-center text-slate-500 flex flex-col items-center justify-center">
            {isLoading ? (
              <>
                <div className="w-6 h-6 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mb-2" />
                <p className="text-xs font-mono text-slate-400">
                  Listening for agent workflow transitions...
                </p>
              </>
            ) : (
              <>
                <Clock className="w-8 h-8 text-slate-600 mb-2 stroke-[1.5]" />
                <p className="text-xs font-semibold text-slate-400">
                  No timeline events recorded yet.
                </p>
                <p className="text-[11px] text-slate-600 mt-0.5">
                  Workflow events stream automatically as nodes execute.
                </p>
              </>
            )}
          </div>
        ) : (
          <div className="relative border-l border-brand-700/60 ml-3.5 pl-5 space-y-4">
            {events.map((evt, idx) => {
              const isLast = idx === events.length - 1;
              const isExpanded = !!expandedEvents[evt.event_id];
              const hasDetails = evt.details && Object.keys(evt.details).length > 0;

              return (
                <div key={evt.event_id || idx} className="relative group">
                  {/* Timeline Node Bullet */}
                  <div
                    className={`absolute -left-[27px] top-1 flex items-center justify-center w-6 h-6 rounded-full border bg-brand-900 transition-all ${
                      isLast && connectionStatus === "OPEN"
                        ? "border-orange-500 shadow-glow-high"
                        : "border-brand-700 group-hover:border-slate-500"
                    }`}
                  >
                    {getEventIcon(evt.event_type)}
                  </div>

                  {/* Event Content Card */}
                  <div className="p-3 rounded-lg bg-brand-900/50 border border-brand-700/50 hover:border-brand-600/70 transition-all space-y-1.5">
                    {/* Header: Event Type & Timestamp */}
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-orange-400 text-[11px]">
                          {evt.event_type}
                        </span>
                        {evt.node_name && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-brand-800 text-slate-300 border border-brand-700">
                            node: {evt.node_name}
                          </span>
                        )}
                      </div>

                      <span className="font-mono text-[10px] text-slate-500">
                        {new Date(evt.timestamp).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </span>
                    </div>

                    {/* Message / Description */}
                    <p className="text-xs text-slate-200 leading-snug">{evt.description}</p>

                    {/* Expandable Details Accordion */}
                    {hasDetails && (
                      <div className="pt-1">
                        <button
                          onClick={() => toggleExpand(evt.event_id)}
                          className="flex items-center gap-1 text-[10px] font-mono text-cyan-400 hover:text-cyan-300 transition-colors"
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-3 h-3" />
                          ) : (
                            <ChevronRight className="w-3 h-3" />
                          )}
                          <span>{isExpanded ? "Hide Details" : "View Event Payload"}</span>
                        </button>

                        {isExpanded && (
                          <pre className="mt-2 p-2.5 rounded bg-brand-950 border border-brand-800 text-[10px] font-mono text-slate-300 overflow-x-auto max-h-48 scrollbar-thin">
                            {JSON.stringify(evt.details, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            <div ref={bottomRef} />
          </div>
        )}
      </div>
    </div>
  );
};
