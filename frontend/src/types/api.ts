/**
 * src/types/api.ts
 * ----------------
 * TypeScript types mirroring shared/ v1.1 contracts.
 *
 * @generated — PLACEHOLDER
 * These types are hand-aligned to shared/contracts.py, shared/enums.py,
 * shared/constants.py, and shared/reason_codes.py (schema version 1.1).
 *
 * Once backend/openapi.json lands on main, DELETE this file and regenerate
 * via `npx openapi-typescript backend/openapi.json -o src/types/api.ts`.
 * Add `gen:api` script to package.json at that time.
 *
 * RULES:
 *  - snake_case throughout — matches Python contracts
 *  - Money fields are numbers (INR integer amounts, not strings)
 *  - All optional fields use `| null` not `undefined` (matches JSON null)
 *  - Never hand-edit once auto-generation is set up
 */

// ===========================================================================
// Enums — mirrors shared/enums.py
// ===========================================================================

/** What the agent did, or what ground truth says it should have done. */
export type Action = "APPROVE" | "REJECT" | "ESCALATE";

/**
 * Agent lifecycle state.
 * NOTE: lowercase values — pre-existing inconsistency preserved from Python.
 */
export type AgentState = "probation" | "active" | "restricted" | "suspended";

export type DriftSeverity = "NONE" | "WARNING" | "CONFIRMED" | "CRITICAL";

export type Direction = "INCREASE" | "HOLD" | "CLAWBACK";

export type RecommendationStatus = "PENDING" | "APPROVED" | "REJECTED" | "SUPERSEDED";

/** A single governance agent's stance on a recommendation. */
export type OpinionVerdict = "CONCUR" | "OBJECT" | "ABSTAIN";

/** A human reviewer's verdict on a sampled decision. */
export type ReviewVerdict = "AGREED" | "DISAGREED" | "INCONCLUSIVE";

// ===========================================================================
// Constants — mirrors shared/constants.py
// ===========================================================================

export const SCHEMA_VERSION = "1.1";
export const CURRENCY = "INR";

/** The five-rung autonomy ladder. Rungs are 0-indexed. */
export const AUTONOMY_LADDER: readonly number[] = [500, 1000, 2500, 5000, 10000] as const;
export const AUTONOMY_FLOOR = AUTONOMY_LADDER[0]; // 500
export const MAX_RUNG = AUTONOMY_LADDER.length - 1; // 4

export const TRUST_SCORE_MIN = 0.0;
export const TRUST_SCORE_MAX = 100.0;

/** Review-sampling rate per rung. Shrinks as trust increases — that's the ROI. */
export const SAMPLING_RATE_BY_RUNG: readonly number[] = [1.0, 0.50, 0.25, 0.10, 0.05] as const;
export const MIN_SAMPLES_FOR_ACCURACY_ESTIMATE = 20;

/** Which rung (0–4) does this rupee amount correspond to? */
export function rungOf(limit: number): number {
  let rung = 0;
  for (let i = 0; i < AUTONOMY_LADDER.length; i++) {
    if (limit >= AUTONOMY_LADDER[i]) rung = i;
  }
  return rung;
}

/** The rupee amount for a given rung, clamped to valid range. */
export function limitOf(rung: number): number {
  return AUTONOMY_LADDER[Math.max(0, Math.min(rung, MAX_RUNG))];
}

/** The review-sampling rate for a given rung, clamped to valid range. */
export function samplingRateOf(rung: number): number {
  return SAMPLING_RATE_BY_RUNG[Math.max(0, Math.min(rung, MAX_RUNG))];
}

// ===========================================================================
// Reason codes — mirrors shared/reason_codes.py
// ===========================================================================

// --- why an increase was blocked ---
export const INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE";
export const COOLDOWN_ACTIVE = "COOLDOWN_ACTIVE";
export const TRUST_BELOW_THRESHOLD = "TRUST_BELOW_THRESHOLD";
export const AT_MAX_RUNG = "AT_MAX_RUNG";
export const DRIFT_ACTIVE = "DRIFT_ACTIVE";
export const CLAWBACK_RECOVERY_PENDING = "CLAWBACK_RECOVERY_PENDING";

// --- why an increase was allowed ---
export const EVIDENCE_SUFFICIENT = "EVIDENCE_SUFFICIENT";
export const NO_DRIFT_DETECTED = "NO_DRIFT_DETECTED";
export const NO_RECENT_CRITICAL_ERRORS = "NO_RECENT_CRITICAL_ERRORS";
export const COOLDOWN_SATISFIED = "COOLDOWN_SATISFIED";

// --- why autonomy was reduced ---
export const CLAWBACK_DRIFT = "CLAWBACK_DRIFT";
export const CLAWBACK_CRITICAL_ERROR = "CLAWBACK_CRITICAL_ERROR";

// --- evidence quality notes ---
export const NO_ACTED_DECISIONS = "NO_ACTED_DECISIONS";
export const AGREEMENT_EVIDENCE_INSUFFICIENT = "AGREEMENT_EVIDENCE_INSUFFICIENT";
export const WEIGHTS_RENORMALISED = "WEIGHTS_RENORMALISED";
export const SAMPLE_EVIDENCE_INSUFFICIENT = "SAMPLE_EVIDENCE_INSUFFICIENT";
export const RECOMMENDATION_CLAMPED = "RECOMMENDATION_CLAMPED";

// --- audit sample findings ---
export const SAMPLE_REVIEW_DISAGREEMENT = "SAMPLE_REVIEW_DISAGREEMENT";

/** Human-readable descriptions for all reason codes. */
export const HUMAN_READABLE: Record<string, string> = {
  [INSUFFICIENT_SAMPLE]: "Not enough acted decisions yet to support an increase.",
  [COOLDOWN_ACTIVE]: "Too few decisions since the last autonomy change.",
  [TRUST_BELOW_THRESHOLD]: "Trust score is below the threshold for the next rung.",
  [AT_MAX_RUNG]: "Already at the highest autonomy rung.",
  [DRIFT_ACTIVE]: "Recent performance has degraded against the historical baseline.",
  [CLAWBACK_RECOVERY_PENDING]: "Not enough clean decisions since the last clawback.",
  [EVIDENCE_SUFFICIENT]: "Sample size and confidence bound both clear the gate.",
  [NO_DRIFT_DETECTED]: "Recent performance matches the historical baseline.",
  [NO_RECENT_CRITICAL_ERRORS]: "No critical errors in the recent window.",
  [COOLDOWN_SATISFIED]: "Enough decisions have elapsed since the last change.",
  [CLAWBACK_DRIFT]: "Autonomy reduced one rung after confirmed performance drift.",
  [CLAWBACK_CRITICAL_ERROR]: "Autonomy reset to the floor after a critical error.",
  [NO_ACTED_DECISIONS]: "The agent has escalated everything and decided nothing.",
  [AGREEMENT_EVIDENCE_INSUFFICIENT]: "Too few human-ruled escalations to score agreement.",
  [WEIGHTS_RENORMALISED]: "Score computed over available components only.",
  [SAMPLE_EVIDENCE_INSUFFICIENT]: "Too few reviewed audit samples to support an accuracy estimate.",
  [RECOMMENDATION_CLAMPED]: "The proposed limit exceeded the hard ceiling and was reduced.",
  [SAMPLE_REVIEW_DISAGREEMENT]: "A sampled review found the agent's action did not match the reviewer's verdict.",
};

/** Turn a list of reason codes into a human-readable sentence. */
export function describeReasonCodes(codes: string[]): string {
  return codes
    .map((c) => HUMAN_READABLE[c] ?? `[${c}]`)
    .join(" ");
}

// ===========================================================================
// Data shapes — mirrors shared/contracts.py
// ===========================================================================

/** A count with its confidence bound attached. */
export interface ProportionResult {
  successes: number;
  trials: number;
  point: number | null;
  wilson_lower: number;
  wilson_upper: number;
}

export interface ScoreComponent {
  name: string;
  value: number | null;
  nominal_weight: number;
  effective_weight: number;
  available: boolean;
}

export interface DriftResult {
  severity: DriftSeverity;
  detected: boolean;
  recent_accuracy: number | null;
  baseline_accuracy: number | null;
  drop_pp: number | null;
  z_statistic: number | null;
  p_value: number | null;
  critical_errors_in_window: number;
  recent_n: number;
  baseline_n: number;
  underpowered: boolean;
}

// --- simulator -> trust engine ---

export interface DecisionRecord {
  decision_id: string;
  sequence: number;
  invoice_id: string;
  amount: number;
  action: Action;
  ground_truth: Action;
  agent_id: string;
  decided_at: string | null; // ISO datetime

  recommended_action: Action | null;
  human_ruling: Action | null;

  is_escalated: boolean;
  is_correct: boolean | null;
  is_critical_error: boolean;
}

// --- trust engine -> backend ---

export interface TrustEvaluation {
  agent_id: string;
  schema_version: string;

  total_decisions: number;
  acted_decisions: number;
  escalated_decisions: number;
  ruled_escalations: number;

  accuracy: ProportionResult | null;
  human_agreement: ProportionResult | null;
  utilization: ProportionResult | null;

  critical_errors: number;
  noncritical_errors: number;
  critical_error_rate: number;
  critical_errors_in_recent_window: number;

  trust_score: number;
  components: ScoreComponent[];
  weights_renormalised: boolean;

  drift: DriftResult;

  current_limit: number;
  recommended_limit: number;
  current_rung: number;
  recommended_rung: number;
  direction: Direction;
  state: AgentState;
  eligible_for_increase: boolean;
  decisions_since_last_change: number;

  reason_codes: string[];
  evaluated_at: string | null; // ISO datetime
  config_fingerprint: string;
}

// --- governance -> backend ---

export interface AgentOpinion {
  agent_name: string;
  verdict: OpinionVerdict;
  reasoning: string;
  concerns: string[];
  confidence: number;
}

export interface Recommendation {
  recommendation_id: string;
  agent_id: string;
  schema_version: string;

  direction: Direction;
  proposed_limit: number;
  proposed_rung: number;
  rationale: string;

  opinions: AgentOpinion[];
  has_dissent: boolean;
  confidence: number;

  governance_mode: string;
  status: RecommendationStatus;
  trust_evaluation_ref: string | null;
  generated_at: string | null; // ISO datetime

  clamped: boolean;
  clamped_from: number | null;
}

// --- human review -> trust engine ---

export interface AuditSample {
  sample_id: string;
  decision_id: string;
  agent_id: string;
  sampled_at: string | null;
  reviewed_at: string | null;
  reviewer: string | null;
  verdict: ReviewVerdict | null;
  reviewer_action: Action | null;
  is_reviewed: boolean;
  is_pending: boolean;
}

// ===========================================================================
// API-specific shapes (response envelopes, agent summary, autonomy events)
// ===========================================================================

/** Single data point in the autonomy timeline chart. */
export interface AutonomyEvent {
  event_id: string;
  agent_id: string;
  evaluated_at: string; // ISO datetime

  current_rung: number;
  current_limit: number;
  rolling_accuracy: number | null;
  wilson_lower: number;
  wilson_upper: number;
  sample_size: number;

  direction: Direction | null;
  drift_severity: DriftSeverity;
  is_clawback_event: boolean;
  is_promotion_event: boolean;
  state: AgentState;

  reason_codes: string[];
}

/** Agent summary for the /agents list. */
export interface AgentSummary {
  agent_id: string;
  name: string;
  current_rung: number;
  current_limit: number;
  state: AgentState;
  trust_score: number;
  rolling_accuracy: number | null;
  wilson_lower: number | null;
  wilson_upper: number | null;
  total_decisions: number;
  pending_approvals: number;
  direction: Direction;
  eligible_for_increase: boolean;
  drift_severity: DriftSeverity;
  reason_codes: string[];
  created_at: string;
  description: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
