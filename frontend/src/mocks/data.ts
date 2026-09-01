/**
 * src/mocks/data.ts
 * ------------------
 * Seed data for MSW mocks — v1.1 contract-aligned.
 *
 * Three agents on the five-rung ladder, autonomy events showing the
 * drift + clawback arc, governance recommendations with opinions/dissent,
 * and a trust evaluation snapshot.
 */

import type {
  AgentSummary,
  AutonomyEvent,
  DecisionRecord,
  Recommendation,
  TrustEvaluation,
  AuditSample,
} from "@/types/api";

// ---------------------------------------------------------------------------
// Agents (five-rung ladder, v1.1 fields)
// ---------------------------------------------------------------------------

export const MOCK_AGENTS: AgentSummary[] = [
  {
    agent_id: "gemini-agent-001",
    name: "GeminiAgent (gemini-2.5-flash)",
    current_rung: 1,
    current_limit: 1000,
    state: "active",
    trust_score: 72.4,
    rolling_accuracy: 0.87,
    wilson_lower: 0.79,
    wilson_upper: 0.93,
    total_decisions: 320,
    pending_approvals: 4,
    direction: "HOLD",
    eligible_for_increase: false,
    drift_severity: "NONE",
    reason_codes: ["COOLDOWN_ACTIVE"],
    created_at: "2026-08-01T09:00:00Z",
    description: "Primary LLM agent powered by Gemini 2.5 Flash.",
  },
  {
    agent_id: "scripted-agent-001",
    name: "ScriptedAgent v1",
    current_rung: 3,
    current_limit: 5000,
    state: "active",
    trust_score: 88.1,
    rolling_accuracy: 0.92,
    wilson_lower: 0.85,
    wilson_upper: 0.96,
    total_decisions: 580,
    pending_approvals: 1,
    direction: "INCREASE",
    eligible_for_increase: true,
    drift_severity: "NONE",
    reason_codes: ["EVIDENCE_SUFFICIENT", "NO_DRIFT_DETECTED", "COOLDOWN_SATISFIED"],
    created_at: "2026-08-01T09:00:00Z",
    description: "Deterministic scripted agent — third-party governance demo.",
  },
  {
    agent_id: "gemini-agent-002",
    name: "GeminiAgent (recovery)",
    current_rung: 0,
    current_limit: 500,
    state: "restricted",
    trust_score: 48.2,
    rolling_accuracy: 0.91,
    wilson_lower: 0.83,
    wilson_upper: 0.96,
    total_decisions: 140,
    pending_approvals: 0,
    direction: "HOLD",
    eligible_for_increase: false,
    drift_severity: "WARNING",
    reason_codes: ["CLAWBACK_RECOVERY_PENDING", "DRIFT_ACTIVE"],
    created_at: "2026-08-15T09:00:00Z",
    description: "Recovery-phase agent after clawback event.",
  },
];

// ---------------------------------------------------------------------------
// Autonomy timeline  (the five-rung ladder arc)
// Shows:  ₹500 → ₹1000 (promotion) → degraded → clawback → ₹500 → recovery
// ---------------------------------------------------------------------------

function makeEvent(
  overrides: Partial<AutonomyEvent> & Pick<AutonomyEvent, "evaluated_at">
): AutonomyEvent {
  return {
    event_id: crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2),
    agent_id: "gemini-agent-001",
    current_rung: 0,
    current_limit: 500,
    rolling_accuracy: 0.9,
    wilson_lower: 0.84,
    wilson_upper: 0.95,
    sample_size: 20,
    direction: null,
    drift_severity: "NONE",
    is_clawback_event: false,
    is_promotion_event: false,
    state: "active",
    reason_codes: [],
    ...overrides,
  };
}

// Timeline: 25 data points over ~2 weeks on the five-rung ladder
export const MOCK_AUTONOMY_EVENTS: AutonomyEvent[] = [
  // Days 1-5: good phase, stable high accuracy, at ₹500 (rung 0)
  makeEvent({ evaluated_at: "2026-08-01T10:00:00Z", rolling_accuracy: 0.88, wilson_lower: 0.76, wilson_upper: 0.95, current_limit: 500, current_rung: 0, state: "probation", reason_codes: ["INSUFFICIENT_SAMPLE"] }),
  makeEvent({ evaluated_at: "2026-08-01T18:00:00Z", rolling_accuracy: 0.90, wilson_lower: 0.79, wilson_upper: 0.96, current_limit: 500, current_rung: 0, state: "probation", reason_codes: ["INSUFFICIENT_SAMPLE"] }),
  makeEvent({ evaluated_at: "2026-08-02T10:00:00Z", rolling_accuracy: 0.91, wilson_lower: 0.82, wilson_upper: 0.96, current_limit: 500, current_rung: 0, state: "active" }),
  makeEvent({ evaluated_at: "2026-08-02T18:00:00Z", rolling_accuracy: 0.93, wilson_lower: 0.85, wilson_upper: 0.97, current_limit: 500, current_rung: 0, state: "active", reason_codes: ["COOLDOWN_ACTIVE"] }),
  makeEvent({ evaluated_at: "2026-08-03T10:00:00Z", rolling_accuracy: 0.94, wilson_lower: 0.87, wilson_upper: 0.98, current_limit: 500, current_rung: 0, state: "active", reason_codes: ["EVIDENCE_SUFFICIENT", "COOLDOWN_SATISFIED"] }),

  // Day 5 PM: PROMOTION — earned ₹1,000 (rung 1)
  makeEvent({ evaluated_at: "2026-08-03T18:00:00Z", rolling_accuracy: 0.95, wilson_lower: 0.88, wilson_upper: 0.98, current_limit: 1000, current_rung: 1, is_promotion_event: true, direction: "INCREASE", state: "active", reason_codes: ["EVIDENCE_SUFFICIENT", "NO_DRIFT_DETECTED"] }),
  makeEvent({ evaluated_at: "2026-08-04T10:00:00Z", rolling_accuracy: 0.94, wilson_lower: 0.87, wilson_upper: 0.97, current_limit: 1000, current_rung: 1, state: "active" }),
  makeEvent({ evaluated_at: "2026-08-04T18:00:00Z", rolling_accuracy: 0.93, wilson_lower: 0.86, wilson_upper: 0.97, current_limit: 1000, current_rung: 1, state: "active" }),
  makeEvent({ evaluated_at: "2026-08-05T10:00:00Z", rolling_accuracy: 0.92, wilson_lower: 0.85, wilson_upper: 0.96, current_limit: 1000, current_rung: 1, state: "active" }),

  // Days 6-8: DEGRADED PHASE — accuracy degrades, drift detected
  makeEvent({ evaluated_at: "2026-08-05T18:00:00Z", rolling_accuracy: 0.88, wilson_lower: 0.80, wilson_upper: 0.93, current_limit: 1000, current_rung: 1, drift_severity: "WARNING", state: "active", reason_codes: ["DRIFT_ACTIVE"] }),
  makeEvent({ evaluated_at: "2026-08-06T10:00:00Z", rolling_accuracy: 0.82, wilson_lower: 0.73, wilson_upper: 0.89, current_limit: 1000, current_rung: 1, drift_severity: "CONFIRMED", state: "restricted", reason_codes: ["DRIFT_ACTIVE"] }),
  makeEvent({ evaluated_at: "2026-08-06T18:00:00Z", rolling_accuracy: 0.77, wilson_lower: 0.67, wilson_upper: 0.85, current_limit: 1000, current_rung: 1, drift_severity: "CONFIRMED", state: "restricted", reason_codes: ["DRIFT_ACTIVE"] }),
  makeEvent({ evaluated_at: "2026-08-07T10:00:00Z", rolling_accuracy: 0.74, wilson_lower: 0.64, wilson_upper: 0.83, current_limit: 1000, current_rung: 1, drift_severity: "CRITICAL", state: "restricted", reason_codes: ["DRIFT_ACTIVE"] }),

  // Day 7 PM: CLAWBACK — slashed back to ₹500 (rung 0)
  makeEvent({ evaluated_at: "2026-08-07T18:00:00Z", rolling_accuracy: 0.71, wilson_lower: 0.60, wilson_upper: 0.80, current_limit: 500, current_rung: 0, is_clawback_event: true, direction: "CLAWBACK", drift_severity: "CRITICAL", state: "restricted", reason_codes: ["CLAWBACK_DRIFT"] }),
  makeEvent({ evaluated_at: "2026-08-08T10:00:00Z", rolling_accuracy: 0.70, wilson_lower: 0.59, wilson_upper: 0.79, current_limit: 500, current_rung: 0, drift_severity: "CONFIRMED", state: "restricted", reason_codes: ["CLAWBACK_RECOVERY_PENDING"] }),
  makeEvent({ evaluated_at: "2026-08-08T18:00:00Z", rolling_accuracy: 0.72, wilson_lower: 0.62, wilson_upper: 0.81, current_limit: 500, current_rung: 0, drift_severity: "WARNING", state: "restricted", reason_codes: ["CLAWBACK_RECOVERY_PENDING"] }),

  // Days 9-13: RECOVERY PHASE — accuracy climbing back
  makeEvent({ evaluated_at: "2026-08-09T10:00:00Z", rolling_accuracy: 0.76, wilson_lower: 0.66, wilson_upper: 0.84, current_limit: 500, current_rung: 0, drift_severity: "WARNING", state: "restricted", reason_codes: ["CLAWBACK_RECOVERY_PENDING"] }),
  makeEvent({ evaluated_at: "2026-08-09T18:00:00Z", rolling_accuracy: 0.80, wilson_lower: 0.71, wilson_upper: 0.87, current_limit: 500, current_rung: 0, drift_severity: "NONE", state: "active", reason_codes: ["CLAWBACK_RECOVERY_PENDING"] }),
  makeEvent({ evaluated_at: "2026-08-10T10:00:00Z", rolling_accuracy: 0.83, wilson_lower: 0.74, wilson_upper: 0.89, current_limit: 500, current_rung: 0, state: "active", reason_codes: ["CLAWBACK_RECOVERY_PENDING"] }),
  makeEvent({ evaluated_at: "2026-08-10T18:00:00Z", rolling_accuracy: 0.86, wilson_lower: 0.78, wilson_upper: 0.92, current_limit: 500, current_rung: 0, state: "active", reason_codes: ["COOLDOWN_ACTIVE"] }),
  makeEvent({ evaluated_at: "2026-08-11T10:00:00Z", rolling_accuracy: 0.88, wilson_lower: 0.80, wilson_upper: 0.93, current_limit: 500, current_rung: 0, state: "active", reason_codes: ["COOLDOWN_ACTIVE"] }),
  makeEvent({ evaluated_at: "2026-08-11T18:00:00Z", rolling_accuracy: 0.90, wilson_lower: 0.83, wilson_upper: 0.95, current_limit: 500, current_rung: 0, state: "active", reason_codes: ["COOLDOWN_ACTIVE"] }),
  makeEvent({ evaluated_at: "2026-08-12T10:00:00Z", rolling_accuracy: 0.91, wilson_lower: 0.84, wilson_upper: 0.96, current_limit: 500, current_rung: 0, state: "active", reason_codes: ["EVIDENCE_SUFFICIENT", "COOLDOWN_SATISFIED"] }),
  makeEvent({ evaluated_at: "2026-08-12T18:00:00Z", rolling_accuracy: 0.92, wilson_lower: 0.85, wilson_upper: 0.96, current_limit: 500, current_rung: 0, state: "active", reason_codes: ["EVIDENCE_SUFFICIENT", "COOLDOWN_SATISFIED", "NO_DRIFT_DETECTED"] }),
  makeEvent({ evaluated_at: "2026-08-13T10:00:00Z", rolling_accuracy: 0.93, wilson_lower: 0.87, wilson_upper: 0.97, current_limit: 500, current_rung: 0, state: "active", reason_codes: ["EVIDENCE_SUFFICIENT", "COOLDOWN_SATISFIED", "NO_DRIFT_DETECTED"] }),
];

// ---------------------------------------------------------------------------
// Trust evaluation (full snapshot for gemini-agent-001)
// ---------------------------------------------------------------------------

export const MOCK_TRUST_EVALUATION: TrustEvaluation = {
  agent_id: "gemini-agent-001",
  schema_version: "1.1",
  total_decisions: 320,
  acted_decisions: 248,
  escalated_decisions: 72,
  ruled_escalations: 52,
  accuracy: { successes: 216, trials: 248, point: 0.87, wilson_lower: 0.82, wilson_upper: 0.91 },
  human_agreement: { successes: 44, trials: 52, point: 0.846, wilson_lower: 0.72, wilson_upper: 0.93 },
  utilization: { successes: 248, trials: 320, point: 0.775, wilson_lower: 0.73, wilson_upper: 0.82 },
  critical_errors: 3,
  noncritical_errors: 29,
  critical_error_rate: 0.012,
  critical_errors_in_recent_window: 0,
  trust_score: 72.4,
  components: [
    { name: "accuracy", value: 0.87, nominal_weight: 0.40, effective_weight: 0.40, available: true },
    { name: "human_agreement", value: 0.846, nominal_weight: 0.20, effective_weight: 0.20, available: true },
    { name: "critical_errors", value: 0.95, nominal_weight: 0.25, effective_weight: 0.25, available: true },
    { name: "utilization", value: 0.775, nominal_weight: 0.15, effective_weight: 0.15, available: true },
  ],
  weights_renormalised: false,
  drift: {
    severity: "NONE",
    detected: false,
    recent_accuracy: 0.90,
    baseline_accuracy: 0.87,
    drop_pp: null,
    z_statistic: null,
    p_value: null,
    critical_errors_in_window: 0,
    recent_n: 50,
    baseline_n: 248,
    underpowered: false,
  },
  current_limit: 1000,
  recommended_limit: 1000,
  current_rung: 1,
  recommended_rung: 1,
  direction: "HOLD",
  state: "active",
  eligible_for_increase: false,
  decisions_since_last_change: 42,
  reason_codes: ["COOLDOWN_ACTIVE"],
  evaluated_at: "2026-08-13T10:00:00Z",
  config_fingerprint: "sha256:abc123",
};

// ---------------------------------------------------------------------------
// Recommendations (with governance opinions and dissent)
// ---------------------------------------------------------------------------

export const MOCK_RECOMMENDATIONS: Recommendation[] = [
  {
    recommendation_id: "rec-001",
    agent_id: "scripted-agent-001",
    schema_version: "1.1",
    direction: "INCREASE",
    proposed_limit: 10000,
    proposed_rung: 4,
    rationale: "Agent has sustained accuracy above threshold for sufficient sample size with no recent drift.",
    opinions: [
      { agent_name: "performance", verdict: "CONCUR", reasoning: "Accuracy 92% (Wilson LB 85%) over 580 decisions exceeds the threshold. No drift detected.", concerns: [], confidence: 0.91 },
      { agent_name: "risk", verdict: "OBJECT", reasoning: "3 critical errors in the lifetime. While none are recent, the lifetime rate of 0.5% warrants caution at the highest rung.", concerns: ["Lifetime critical error count is non-zero", "Maximum rung carries highest financial exposure"], confidence: 0.68 },
      { agent_name: "compliance", verdict: "CONCUR", reasoning: "All regulatory sampling requirements met. Post-hoc review rate at current rung is 10%, within guidelines.", concerns: [], confidence: 0.85 },
      { agent_name: "audit", verdict: "ABSTAIN", reasoning: "Insufficient reviewed audit samples at this rung to form an independent opinion.", concerns: ["Only 12 of 29 samples reviewed"], confidence: 0.40 },
    ],
    has_dissent: true,
    confidence: 0.72,
    governance_mode: "langgraph",
    status: "PENDING",
    trust_evaluation_ref: "eval-scripted-001",
    generated_at: "2026-08-13T09:30:00Z",
    clamped: false,
    clamped_from: null,
  },
  {
    recommendation_id: "rec-002",
    agent_id: "gemini-agent-001",
    schema_version: "1.1",
    direction: "INCREASE",
    proposed_limit: 2500,
    proposed_rung: 2,
    rationale: "Performance has recovered post-clawback. Wilson lower bound now above threshold.",
    opinions: [
      { agent_name: "performance", verdict: "CONCUR", reasoning: "Rolling accuracy at 93% with Wilson LB 87%. Recovery trajectory is strong.", concerns: [], confidence: 0.88 },
      { agent_name: "risk", verdict: "CONCUR", reasoning: "No critical errors since clawback. Recent window is clean.", concerns: [], confidence: 0.82 },
      { agent_name: "compliance", verdict: "CONCUR", reasoning: "Post-clawback recovery period requirements met. Sample review rate appropriate.", concerns: [], confidence: 0.86 },
      { agent_name: "audit", verdict: "CONCUR", reasoning: "Recent audit samples show consistent agreement. 18 of 20 agreed.", concerns: [], confidence: 0.79 },
    ],
    has_dissent: false,
    confidence: 0.84,
    governance_mode: "langgraph",
    status: "PENDING",
    trust_evaluation_ref: "eval-gemini-001",
    generated_at: "2026-08-13T10:15:00Z",
    clamped: true,
    clamped_from: 5000,
  },
  {
    recommendation_id: "rec-003",
    agent_id: "gemini-agent-002",
    schema_version: "1.1",
    direction: "HOLD",
    proposed_limit: 500,
    proposed_rung: 0,
    rationale: "Agent is in recovery from clawback. Insufficient clean decisions to warrant increase.",
    opinions: [
      { agent_name: "performance", verdict: "CONCUR", reasoning: "Accuracy recovering but Wilson LB still at 83%, marginally below threshold.", concerns: ["Lower bound still within noise range"], confidence: 0.65 },
      { agent_name: "risk", verdict: "CONCUR", reasoning: "Hold is appropriate during recovery phase.", concerns: [], confidence: 0.90 },
      { agent_name: "compliance", verdict: "CONCUR", reasoning: "Recovery period policy requires minimum 50 clean decisions.", concerns: [], confidence: 0.88 },
      { agent_name: "audit", verdict: "CONCUR", reasoning: "All recent samples reviewed and agreed.", concerns: [], confidence: 0.82 },
    ],
    has_dissent: false,
    confidence: 0.81,
    governance_mode: "langgraph",
    status: "APPROVED",
    trust_evaluation_ref: "eval-gemini-002",
    generated_at: "2026-08-12T14:00:00Z",
    clamped: false,
    clamped_from: null,
  },
];

// ---------------------------------------------------------------------------
// Recent decisions (v1.1 DecisionRecord shape)
// ---------------------------------------------------------------------------

export const MOCK_DECISIONS: DecisionRecord[] = [
  { decision_id: "d1", sequence: 316, invoice_id: "inv-001", amount: 450, agent_id: "gemini-agent-001", action: "APPROVE", ground_truth: "APPROVE", decided_at: "2026-08-13T09:00:00Z", recommended_action: null, human_ruling: null, is_escalated: false, is_correct: true, is_critical_error: false },
  { decision_id: "d2", sequence: 317, invoice_id: "inv-002", amount: 1200, agent_id: "gemini-agent-001", action: "ESCALATE", ground_truth: "APPROVE", decided_at: "2026-08-13T09:05:00Z", recommended_action: "APPROVE", human_ruling: "APPROVE", is_escalated: true, is_correct: null, is_critical_error: false },
  { decision_id: "d3", sequence: 318, invoice_id: "inv-003", amount: 380, agent_id: "gemini-agent-001", action: "APPROVE", ground_truth: "APPROVE", decided_at: "2026-08-13T09:10:00Z", recommended_action: null, human_ruling: null, is_escalated: false, is_correct: true, is_critical_error: false },
  { decision_id: "d4", sequence: 319, invoice_id: "inv-004", amount: 950, agent_id: "gemini-agent-001", action: "APPROVE", ground_truth: "REJECT", decided_at: "2026-08-13T09:15:00Z", recommended_action: null, human_ruling: null, is_escalated: false, is_correct: false, is_critical_error: true },
  { decision_id: "d5", sequence: 320, invoice_id: "inv-005", amount: 2100, agent_id: "gemini-agent-001", action: "REJECT", ground_truth: "REJECT", decided_at: "2026-08-13T09:20:00Z", recommended_action: null, human_ruling: null, is_escalated: false, is_correct: true, is_critical_error: false },
];

// ---------------------------------------------------------------------------
// Audit samples
// ---------------------------------------------------------------------------

export const MOCK_AUDIT_SAMPLES: AuditSample[] = [
  { sample_id: "smp-001", decision_id: "d1", agent_id: "gemini-agent-001", sampled_at: "2026-08-13T09:01:00Z", reviewed_at: "2026-08-13T10:00:00Z", reviewer: "reviewer@company.com", verdict: "AGREED", reviewer_action: "APPROVE", is_reviewed: true, is_pending: false },
  { sample_id: "smp-002", decision_id: "d3", agent_id: "gemini-agent-001", sampled_at: "2026-08-13T09:11:00Z", reviewed_at: null, reviewer: null, verdict: null, reviewer_action: null, is_reviewed: false, is_pending: true },
  { sample_id: "smp-003", decision_id: "d5", agent_id: "gemini-agent-001", sampled_at: "2026-08-13T09:21:00Z", reviewed_at: null, reviewer: null, verdict: null, reviewer_action: null, is_reviewed: false, is_pending: true },
];
