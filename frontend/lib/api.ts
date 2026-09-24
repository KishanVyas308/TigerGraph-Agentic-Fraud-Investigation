import type {
  ApprovalActionRequest,
  CaseQueueResponse,
  EvidenceListResponse,
  GraphVisualizationResponse,
  InvestigationResponse,
  InvestigationTraceResponse,
  ModifyActionRequest,
  SubmitEvidenceRequest,
  TriggerInvestigationRequest,
} from "@/types/api";

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;

    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (Array.isArray(payload.detail)) {
        detail = payload.detail
          .map((issue) => {
            if (!issue || typeof issue !== "object") return String(issue);
            const validationIssue = issue as {
              loc?: unknown[];
              msg?: string;
            };
            const location = validationIssue.loc?.slice(1).join(".");
            return `${location ? `${location}: ` : ""}${validationIssue.msg ?? "Invalid value"}`;
          })
          .join("; ");
      }
    } catch {
      // Keep the HTTP status when the response is not JSON.
    }

    throw new Error(detail);
  }

  return (await response.json()) as T;
}

function casePath(caseId: string): string {
  return `/api/investigations/${encodeURIComponent(caseId)}`;
}

export const api = {
  listCases(): Promise<CaseQueueResponse> {
    return request<CaseQueueResponse>("/api/cases");
  },

  triggerInvestigation(
    payload: TriggerInvestigationRequest
  ): Promise<InvestigationResponse> {
    return request<InvestigationResponse>("/api/investigations", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getInvestigation(caseId: string): Promise<InvestigationResponse> {
    return request<InvestigationResponse>(casePath(caseId));
  },

  getInvestigationEvidence(caseId: string): Promise<EvidenceListResponse> {
    return request<EvidenceListResponse>(`${casePath(caseId)}/evidence`);
  },

  getInvestigationGraph(caseId: string): Promise<GraphVisualizationResponse> {
    return request<GraphVisualizationResponse>(`${casePath(caseId)}/graph`);
  },

  getInvestigationTrace(caseId: string): Promise<InvestigationTraceResponse> {
    return request<InvestigationTraceResponse>(`${casePath(caseId)}/trace`);
  },

  submitEvidence(
    caseId: string,
    payload: SubmitEvidenceRequest
  ): Promise<InvestigationResponse> {
    return request<InvestigationResponse>(`${casePath(caseId)}/evidence`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  approveAction(
    caseId: string,
    payload: ApprovalActionRequest
  ): Promise<InvestigationResponse> {
    return request<InvestigationResponse>(`${casePath(caseId)}/approve`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  rejectAction(
    caseId: string,
    payload: ApprovalActionRequest
  ): Promise<InvestigationResponse> {
    return request<InvestigationResponse>(`${casePath(caseId)}/reject`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  modifyAction(
    caseId: string,
    payload: ModifyActionRequest
  ): Promise<InvestigationResponse> {
    return request<InvestigationResponse>(`${casePath(caseId)}/modify-action`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getEventsUrl(caseId: string): string {
    return `${API_BASE_URL}${casePath(caseId)}/events`;
  },
};
