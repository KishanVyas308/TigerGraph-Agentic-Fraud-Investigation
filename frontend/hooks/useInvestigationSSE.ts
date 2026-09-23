"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { TimelineEventItem } from "@/types/api";
import { api } from "@/lib/api";

export type SSEConnectionStatus =
  | "DISCONNECTED"
  | "CONNECTING"
  | "OPEN"
  | "RECONNECTING"
  | "CLOSED"
  | "ERROR";

export const KNOWN_INVESTIGATION_EVENTS = [
  "CASE_CREATED",
  "VALIDATION_COMPLETED",
  "CASE_INTAKE_COMPLETED",
  "EVIDENCE_COLLECTION_STARTED",
  "TRANSACTION_ANALYSIS_COMPLETED",
  "GRAPH_ANALYSIS_COMPLETED",
  "POLICY_RETRIEVED",
  "SIMILAR_CASES_RETRIEVED",
  "EVIDENCE_NORMALIZED",
  "FEATURES_CALCULATED",
  "RISK_ASSESSED",
  "SUFFICIENCY_EVALUATED",
  "PRE_EVIDENCE_NBA_RECORDED",
  "EVIDENCE_REQUESTED",
  "EVIDENCE_INGESTED",
  "POST_EVIDENCE_NBA_DETERMINED",
  "POLICY_GATE_PASSED",
  "POLICY_GATE_BLOCKED",
  "APPROVAL_REQUIRED",
  "APPROVAL_DECISION_RECEIVED",
  "ACTION_EXECUTED",
  "SAR_REPORT_GENERATED",
  "CASE_FINALIZED",
  "CASE_MEMORY_PERSISTED",
  "CASE_SUMMARY_INDEXED",
  "INVESTIGATION_ERROR",
  "INVESTIGATION_STREAM_CLOSED",
  "ERROR",
];

interface UseInvestigationSSEOptions {
  enabled?: boolean;
  onEvent?: (event: TimelineEventItem) => void;
  onCaseFinished?: (data: { case_id: string; status: string }) => void;
  onError?: (error: any) => void;
}

export function useInvestigationSSE(
  caseId: string | null,
  options: UseInvestigationSSEOptions = {}
) {
  const { enabled = true, onEvent, onCaseFinished, onError } = options;

  const [events, setEvents] = useState<TimelineEventItem[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<SSEConnectionStatus>("DISCONNECTED");
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const seenEventIdsRef = useRef<Set<string>>(new Set());
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);

  // Stable callbacks using ref
  const onEventRef = useRef(onEvent);
  const onCaseFinishedRef = useRef(onCaseFinished);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onEventRef.current = onEvent;
    onCaseFinishedRef.current = onCaseFinished;
    onErrorRef.current = onError;
  }, [onEvent, onCaseFinished, onError]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!caseId || !enabled) return;

    disconnect();
    setConnectionStatus("CONNECTING");
    setError(null);

    const sseUrl = api.getEventsUrl(caseId);
    let es: EventSource;
    try {
      es = new EventSource(sseUrl);
      eventSourceRef.current = es;
    } catch (err: any) {
      setConnectionStatus("ERROR");
      setError(err?.message || "Failed to initialize EventSource");
      if (onErrorRef.current) onErrorRef.current(err);
      return;
    }

    es.onopen = () => {
      setConnectionStatus("OPEN");
      reconnectAttemptsRef.current = 0;
      setError(null);
    };

    es.onerror = () => {
      if (eventSourceRef.current !== es) return;

      // If connection closed or dropped unexpectedly
      if (es.readyState === EventSource.CLOSED) {
        setConnectionStatus("RECONNECTING");
        disconnect();

        // Exponential backoff reconnect if attempts < 5
        if (reconnectAttemptsRef.current < 5) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 8000);
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        } else {
          setConnectionStatus("CLOSED");
        }
      } else {
        setConnectionStatus("ERROR");
      }
    };

    // Generic message handler (for unnamed events)
    es.onmessage = (messageEvent) => {
      try {
        const parsed = JSON.parse(messageEvent.data);
        handleIncomingEvent(parsed);
      } catch (err) {
        console.error("Failed to parse SSE message:", err);
      }
    };

    const handleIncomingEvent = (payload: any) => {
      if (!payload || !payload.event_id) return;

      // Event deduplication check
      if (seenEventIdsRef.current.has(payload.event_id)) {
        return;
      }

      seenEventIdsRef.current.add(payload.event_id);

      const timelineItem: TimelineEventItem = {
        event_id: payload.event_id,
        event_type: payload.event_type || "UNKNOWN",
        node_name: payload.node_name,
        description: payload.description || "",
        timestamp: payload.timestamp || new Date().toISOString(),
        details: payload.details,
      };

      setEvents((prev) => [...prev, timelineItem]);
      if (onEventRef.current) {
        onEventRef.current(timelineItem);
      }
    };

    // Attach listeners for all known event types
    KNOWN_INVESTIGATION_EVENTS.forEach((eventType) => {
      es.addEventListener(eventType, (e: MessageEvent) => {
        try {
          const payload = JSON.parse(e.data);

          if (eventType === "INVESTIGATION_STREAM_CLOSED") {
            setConnectionStatus("CLOSED");
            disconnect();
            if (onCaseFinishedRef.current) {
              onCaseFinishedRef.current(payload);
            }
            return;
          }

          if (eventType === "ERROR") {
            setError(payload?.error || "Investigation streaming error");
            if (onErrorRef.current) onErrorRef.current(payload);
            return;
          }

          handleIncomingEvent(payload);
        } catch (err) {
          console.error(`Error processing SSE event [${eventType}]:`, err);
        }
      });
    });
  }, [caseId, enabled, disconnect]);

  // Connect on mount / when caseId changes
  useEffect(() => {
    // Reset state for new case
    setEvents([]);
    seenEventIdsRef.current.clear();
    reconnectAttemptsRef.current = 0;

    if (caseId && enabled) {
      connect();
    } else {
      setConnectionStatus("DISCONNECTED");
    }

    return () => {
      disconnect();
    };
  }, [caseId, enabled, connect, disconnect]);

  const clearEvents = useCallback(() => {
    setEvents([]);
    seenEventIdsRef.current.clear();
  }, []);

  return {
    events,
    connectionStatus,
    error,
    reconnect: connect,
    disconnect,
    clearEvents,
  };
}
