/**
 * src/types/api.ts
 * ----------------
 * TypeScript types mirroring shared/contracts.py Pydantic models.
 *
 * RULES (from spec):
 *  - snake_case throughout — no camelCase conversion needed
 *  - Money fields are STRINGS — never number
 *  - All optional fields use `| null` not `undefined` (matches JSON null)
 */

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export type InvoiceCategory =
  | "travel"
  | "supplies"
  | "software"
  | "consulting"
  | "logistics";

export type SimulationPhase = "good" | "degraded" | "recovery";

export type AgentDecision = "approve" | "reject" | "escalate";

export type AutonomyTier = "low" | "medium" | "high";

export type ApprovalStatus = "pending" | "approved" | "rejected";

export type DriftDirection = "degrading" | "recovering";

// ---------------------------------------------------------------------------
// Core models
// ---------------------------------------------------------------------------

export interface Invoice {
  invoice_id: string;
  submitted_by: string;
  vendor_name: string;
  invoice_date: string; // ISO date string "YYYY-MM-DD"
  created_at: string;   // ISO datetime

  category: InvoiceCategory;
  amount: string;        // INR as string — NEVER parse to float
  description: string | null;

  department: string | null;
  cost_centre: string | null;
  purchase_order: string | null;

  phase: SimulationPhase;
  is_boundary_case: boolean;
  is_ambiguous_vendor: boolean;
  has_missing_fields: boolean;
  missing_field_names: string[];

  ground_truth_decision: AgentDecision;
  ground_truth_reason: string;
  ground_truth_confidence: number;
}

export interface AgentDecisionRecord {
  record_id: string;
  invoice_id: string;
  agent_id: string;
  decided_at: string;

  decision: AgentDecision;
  reason: string;
  confidence: number | null;
  is_correct: boolean | null;

  from_cache: boolean;
  cache_key: string | null;
}

export interface HumanApproval {
  approval_id: string;
  invoice_id: string;
  agent_decision_record_id: string;
  requested_at: string;
  resolved_at: string | null;

  status: ApprovalStatus;
  resolved_by: string | null;
  resolution_note: string | null;
}

/** Single data point in the autonomy timeline chart */
export interface AutonomyEvent {
  event_id: string;
  agent_id: string;
  evaluated_at: string;

  tier: AutonomyTier;
  limit_amount: string;       // INR as string
  rolling_accuracy: number;
  wilson_lower_bound: number;
  sample_size: number;

  drift_direction: DriftDirection | null;
  is_clawback_event: boolean;
  is_promotion_event: boolean;

  phase: SimulationPhase | null;
}

// ---------------------------------------------------------------------------
// Agents
// ---------------------------------------------------------------------------

export interface Agent {
  agent_id: string;
  name: string;
  tier: AutonomyTier;
  current_limit: string;      // INR as string
  rolling_accuracy: number | null;
  wilson_lower_bound: number | null;
  total_decisions: number;
  pending_approvals: number;
  created_at: string;
  description: string | null;
}

// ---------------------------------------------------------------------------
// Simulation
// ---------------------------------------------------------------------------

export interface SimulationRunConfig {
  phase: SimulationPhase;
  invoice_count: number;
  seed: number;
  agent_type: string;
  agent_id: string;
  api_base_url: string;
}

export interface SimulationRunResult {
  run_id: string;
  config: SimulationRunConfig;
  started_at: string;
  completed_at: string | null;

  total_invoices: number;
  approved_count: number;
  rejected_count: number;
  escalated_count: number;

  correct_decisions: number;
  accuracy: number | null;
  wilson_lower_bound: number | null;

  cache_hits: number;
  llm_calls: number;
  errors: string[];
}

// ---------------------------------------------------------------------------
// API response envelopes
// ---------------------------------------------------------------------------

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface SubmitInvoiceResponse {
  invoice_id: string;
  accepted: boolean;
  policy_decision: AgentDecision;
  approval_id: string | null;
  message: string;
}
