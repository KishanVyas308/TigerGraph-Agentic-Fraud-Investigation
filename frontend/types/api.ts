/**
 * Frontend TypeScript Data Contracts matching backend FastAPI / Pydantic models.
 */

export type TriggerType =
  | "TRANSACTION_ALERT"
  | "DEVICE_ANOMALY"
  | "HIGH_RISK_MERCHANT"
  | "VELOCITY_BURST"
  | "MANUAL_ANALYST_TRIGGER";

export type RiskLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type CaseStatus =
  | "OPEN"
  | "IN_PROGRESS"
  | "AWAITING_EVIDENCE"
  | "AWAITING_APPROVAL"
  | "COMPLETED"
  | "RESOLVED"
  | "CLOSED";

export type ActionType =
  | "ALLOW_TRANSACTION"
  | "BLOCK_TRANSACTION"
  | "MONITOR_TRANSACTION"
  | "MONITOR_ACCOUNT"
  | "BLOCK_ACCOUNT"
  | "WARN_CUSTOMER"
  | "REQUEST_CUSTOMER_CONFIRMATION"
  | "REQUEST_STEP_UP_AUTH"
  | "REQUEST_ANALYST_EVIDENCE"
  | "ESCALATE_ANALYST"
  | "FILE_SAR"
  | "CLOSE_CASE"
  | "NO_ACTION";

export type ApprovalRole =
  | "FRAUD_ANALYST"
  | "SENIOR_FRAUD_ANALYST"
  | "FRAUD_SUPERVISOR"
  | "COMPLIANCE_OFFICER";

export type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "MODIFIED";

export type StopReason =
  | "SUFFICIENT_EVIDENCE_FOR_ACTION"
  | "NO_MATERIAL_FRAUD_EVIDENCE"
  | "POLICY_MANDATED_ESCALATION"
  | "AWAITING_HUMAN_REVIEW"
  | "LOW_VALUE_OF_ADDITIONAL_EVIDENCE"
  | "MAX_ITERATIONS_REACHED"
  | "INVESTIGATION_ERROR";

export type EvidenceCategory =
  | "TRANSACTION_BEHAVIOR"
  | "GRAPH_RELATIONSHIP"
  | "DEVICE"
  | "IDENTITY"
  | "MONEY_FLOW"
  | "HISTORICAL_CASE"
  | "POLICY"
  | "REGULATION"
  | "CUSTOMER_RESPONSE"
  | "AUTHENTICATION"
  | "ANALYST_INPUT"
  | "EXTERNAL_SIGNAL";

// Request Contracts
export interface TriggerInvestigationRequest {
  case_id?: string;
  trigger_type?: TriggerType;
  transaction_id?: string;
  customer_id?: string;
  account_ids?: string[];
  metadata?: Record<string, any>;
}

export interface SubmitEvidenceRequest {
  evidence_type?: string;
  category?: EvidenceCategory;
  fact: string;
  source_reference?: string;
  reliability?: number;
  metadata?: Record<string, any>;
}

export interface ApprovalActionRequest {
  reviewer_role?: ApprovalRole;
  reviewer_id?: string;
  comments?: string;
}

export interface ModifyActionRequest {
  action_type: ActionType;
  reviewer_role?: ApprovalRole;
  reviewer_id?: string;
  comments?: string;
  reasoning?: string;
}

export interface MockConfirmationRequest {
  customer_id: string;
  transaction_id: string;
  confirmed?: boolean;
}

export interface MockStepUpRequest {
  account_id: string;
  challenge_type?: string;
  passed?: boolean;
}

// Response Contracts
export interface EvidenceRequestItem {
  request_id: string;
  evidence_type: string;
  target_entity_id: string;
  reason: string;
  expected_uncertainty_reduction: number;
  status: string;
}

export interface NextBestActionItem {
  action_id: string;
  action_type: ActionType;
  target_entity_id?: string;
  target_entity_type?: string;
  reasoning: string;
  evidence_ids?: string[];
  policy_reference?: string;
  approval_required?: boolean;
  approval_role?: ApprovalRole;
  execution_mode?: string;
}

export interface ActionExecutionItem {
  execution_id: string;
  action_type: ActionType;
  execution_mode: string;
  success: boolean;
  result?: Record<string, any>;
  timestamp: string;
}

export interface FraudHypothesisItem {
  hypothesis_id: string;
  title: string;
  description: string;
  likelihood: number;
  supporting_evidence_ids: string[];
  contradictory_evidence_ids: string[];
}

export interface SimilarCaseItem {
  case_id: string;
  outcome: string;
  typology?: string;
  summary: string;
  similarity_score?: number;
  retrieval_method?: string;
  shared_entities?: string[];
  evidence_id?: string;
}

export interface PolicyContextItem {
  policy_id: string;
  title: string;
  document_type: string;
  text: string;
  relevance_score?: number;
  graph_references?: string[];
  evidence_id?: string;
}

export interface InvestigationResponse {
  case_id: string;
  case_status: CaseStatus;
  trigger_type: TriggerType;
  transaction_id?: string;
  customer_id?: string;
  account_ids: string[];
  risk_level?: RiskLevel;
  risk_score?: number;
  confidence?: number;
  evidence_completeness?: number;
  stop_reason?: StopReason;
  case_summary?: string;
  pre_evidence_action?: NextBestActionItem;
  requested_evidence?: EvidenceRequestItem[];
  post_evidence_action?: NextBestActionItem;
  approval_required: boolean;
  approval_status?: ApprovalStatus;
  executed_actions: ActionExecutionItem[];
  sar_reference?: string;
  is_persisted: boolean;
  is_indexed: boolean;
  hypotheses?: FraudHypothesisItem[];
  missing_evidence?: string[];
  historical_ml_score?: number;
  similar_cases?: SimilarCaseItem[];
  policy_context?: PolicyContextItem[];
  timeline_event_count: number;
  created_at: string;
}

export interface CaseQueueItem {
  case_id: string;
  trigger_type: string;
  risk_level?: RiskLevel;
  confidence?: number;
  status: string;
  created_at: string;
  stop_reason?: string;
  primary_action?: string;
}

export interface CaseQueueResponse {
  cases: CaseQueueItem[];
  total_count: number;
}

export interface CytoscapeElementData {
  id: string;
  label: string;
  type: string;
  source?: string;
  target?: string;
  properties?: Record<string, any>;
}

export interface CytoscapeElement {
  data: CytoscapeElementData;
  classes?: string;
}

export interface GraphVisualizationResponse {
  case_id: string;
  nodes: CytoscapeElement[];
  edges: CytoscapeElement[];
  summary: Record<string, number>;
}

export interface EvidenceCard {
  evidence_id: string;
  source: string;
  source_reference?: string;
  category: string;
  fact: string;
  reliability: number;
  timestamp: string;
  supports_hypotheses?: string[];
  contradicts_hypotheses?: string[];
}

export interface EvidenceListResponse {
  case_id: string;
  evidence: EvidenceCard[];
  total_count: number;
}

export interface TimelineEventItem {
  event_id: string;
  event_type: string;
  node_name?: string;
  description: string;
  timestamp: string;
  details?: Record<string, any>;
}

export interface TraceSpanItem {
  span_id: string;
  case_id: string;
  span_type: string;
  name: string;
  node_name?: string;
  start_time: string;
  end_time?: string;
  duration_ms?: number;
  status: string;
  inputs?: Record<string, any>;
  outputs?: Record<string, any>;
  metadata?: Record<string, any>;
  error?: string;
  tags?: string[];
}

export interface InvestigationTraceResponse {
  case_id: string;
  total_spans: number;
  total_duration_ms: number;
  spans: TraceSpanItem[];
  trace_file_path?: string;
}
