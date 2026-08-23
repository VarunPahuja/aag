/**
 * src/mocks/data.ts
 * ------------------
 * Seed data for MSW mocks — realistic, deterministic data derived from
 * the simulator fixture shapes.  Three agents, multiple autonomy events
 * showing the drift + clawback arc, and a pending approvals queue.
 */

import type {
  Agent,
  AgentDecisionRecord,
  AutonomyEvent,
  HumanApproval,
  SimulationRunResult,
} from "@/types/api";

// ---------------------------------------------------------------------------
// Agents
// ---------------------------------------------------------------------------

export const MOCK_AGENTS: Agent[] = [
  {
    agent_id: "gemini-agent-001",
    name: "GeminiAgent (gemini-2.5-flash)",
    tier: "low",
    current_limit: "3000",
    rolling_accuracy: 0.87,
    wilson_lower_bound: 0.79,
    total_decisions: 320,
    pending_approvals: 4,
    created_at: "2026-08-01T09:00:00Z",
    description: "Primary LLM agent powered by Gemini 2.5 Flash.",
  },
  {
    agent_id: "scripted-agent-001",
    name: "ScriptedAgent v1",
    tier: "medium",
    current_limit: "15000",
    rolling_accuracy: 0.92,
    wilson_lower_bound: 0.85,
    total_decisions: 580,
    pending_approvals: 1,
    created_at: "2026-08-01T09:00:00Z",
    description: "Deterministic scripted agent — third-party governance demo.",
  },
  {
    agent_id: "gemini-agent-002",
    name: "GeminiAgent (recovery)",
    tier: "low",
    current_limit: "3000",
    rolling_accuracy: 0.91,
    wilson_lower_bound: 0.83,
    total_decisions: 140,
    pending_approvals: 0,
    created_at: "2026-08-15T09:00:00Z",
    description: "Recovery-phase agent used for demo progression.",
  },
];

// ---------------------------------------------------------------------------
// Autonomy timeline  (the money-shot chart data)
// Shows:  good phase → degraded → clawback → recovery → promotion attempt
// ---------------------------------------------------------------------------

function makeEvent(
  overrides: Partial<AutonomyEvent> & Pick<AutonomyEvent, "evaluated_at">
): AutonomyEvent {
  return {
    event_id: crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2),
    agent_id: "gemini-agent-001",
    tier: "low",
    limit_amount: "3000",
    rolling_accuracy: 0.9,
    wilson_lower_bound: 0.84,
    sample_size: 20,
    drift_direction: null,
    is_clawback_event: false,
    is_promotion_event: false,
    phase: "good",
    ...overrides,
  };
}

// Timeline: 30 data points over ~2 weeks
export const MOCK_AUTONOMY_EVENTS: AutonomyEvent[] = [
  // Days 1-5: good phase, stable high accuracy
  makeEvent({ evaluated_at: "2026-08-01T10:00:00Z", rolling_accuracy: 0.91, wilson_lower_bound: 0.80, limit_amount: "3000", phase: "good" }),
  makeEvent({ evaluated_at: "2026-08-01T18:00:00Z", rolling_accuracy: 0.92, wilson_lower_bound: 0.81, limit_amount: "3000", phase: "good" }),
  makeEvent({ evaluated_at: "2026-08-02T10:00:00Z", rolling_accuracy: 0.90, wilson_lower_bound: 0.79, limit_amount: "3000", phase: "good" }),
  makeEvent({ evaluated_at: "2026-08-02T18:00:00Z", rolling_accuracy: 0.93, wilson_lower_bound: 0.83, limit_amount: "3000", phase: "good" }),
  makeEvent({ evaluated_at: "2026-08-03T10:00:00Z", rolling_accuracy: 0.94, wilson_lower_bound: 0.85, limit_amount: "3000", phase: "good" }),
  // Day 5: promotion event — tier upgrade earned
  makeEvent({ evaluated_at: "2026-08-03T18:00:00Z", rolling_accuracy: 0.95, wilson_lower_bound: 0.87, limit_amount: "15000", tier: "medium", phase: "good", is_promotion_event: true, drift_direction: "recovering" }),
  makeEvent({ evaluated_at: "2026-08-04T10:00:00Z", rolling_accuracy: 0.94, wilson_lower_bound: 0.86, limit_amount: "15000", tier: "medium", phase: "good" }),
  makeEvent({ evaluated_at: "2026-08-04T18:00:00Z", rolling_accuracy: 0.93, wilson_lower_bound: 0.85, limit_amount: "15000", tier: "medium", phase: "good" }),
  makeEvent({ evaluated_at: "2026-08-05T10:00:00Z", rolling_accuracy: 0.92, wilson_lower_bound: 0.83, limit_amount: "15000", tier: "medium", phase: "good" }),
  // Days 6-8: DEGRADED PHASE starts — accuracy degrades
  makeEvent({ evaluated_at: "2026-08-05T18:00:00Z", rolling_accuracy: 0.88, wilson_lower_bound: 0.78, limit_amount: "15000", tier: "medium", phase: "degraded", drift_direction: "degrading" }),
  makeEvent({ evaluated_at: "2026-08-06T10:00:00Z", rolling_accuracy: 0.82, wilson_lower_bound: 0.71, limit_amount: "15000", tier: "medium", phase: "degraded", drift_direction: "degrading" }),
  makeEvent({ evaluated_at: "2026-08-06T18:00:00Z", rolling_accuracy: 0.77, wilson_lower_bound: 0.66, limit_amount: "15000", tier: "medium", phase: "degraded", drift_direction: "degrading" }),
  makeEvent({ evaluated_at: "2026-08-07T10:00:00Z", rolling_accuracy: 0.74, wilson_lower_bound: 0.62, limit_amount: "15000", tier: "medium", phase: "degraded", drift_direction: "degrading" }),
  // Day 7 PM: CLAWBACK — Wilson LB drops below threshold, limit slashed back
  makeEvent({ evaluated_at: "2026-08-07T18:00:00Z", rolling_accuracy: 0.71, wilson_lower_bound: 0.59, limit_amount: "3000", tier: "low", phase: "degraded", is_clawback_event: true, drift_direction: "degrading" }),
  makeEvent({ evaluated_at: "2026-08-08T10:00:00Z", rolling_accuracy: 0.70, wilson_lower_bound: 0.58, limit_amount: "3000", tier: "low", phase: "degraded", drift_direction: "degrading" }),
  makeEvent({ evaluated_at: "2026-08-08T18:00:00Z", rolling_accuracy: 0.72, wilson_lower_bound: 0.60, limit_amount: "3000", tier: "low", phase: "degraded" }),
  // Days 9-11: RECOVERY PHASE — accuracy climbing back
  makeEvent({ evaluated_at: "2026-08-09T10:00:00Z", rolling_accuracy: 0.76, wilson_lower_bound: 0.64, limit_amount: "3000", tier: "low", phase: "recovery", drift_direction: "recovering" }),
  makeEvent({ evaluated_at: "2026-08-09T18:00:00Z", rolling_accuracy: 0.80, wilson_lower_bound: 0.69, limit_amount: "3000", tier: "low", phase: "recovery", drift_direction: "recovering" }),
  makeEvent({ evaluated_at: "2026-08-10T10:00:00Z", rolling_accuracy: 0.83, wilson_lower_bound: 0.72, limit_amount: "3000", tier: "low", phase: "recovery", drift_direction: "recovering" }),
  makeEvent({ evaluated_at: "2026-08-10T18:00:00Z", rolling_accuracy: 0.86, wilson_lower_bound: 0.76, limit_amount: "3000", tier: "low", phase: "recovery", drift_direction: "recovering" }),
  makeEvent({ evaluated_at: "2026-08-11T10:00:00Z", rolling_accuracy: 0.88, wilson_lower_bound: 0.79, limit_amount: "3000", tier: "low", phase: "recovery", drift_direction: "recovering" }),
  makeEvent({ evaluated_at: "2026-08-11T18:00:00Z", rolling_accuracy: 0.90, wilson_lower_bound: 0.81, limit_amount: "3000", tier: "low", phase: "recovery", drift_direction: "recovering" }),
  makeEvent({ evaluated_at: "2026-08-12T10:00:00Z", rolling_accuracy: 0.91, wilson_lower_bound: 0.82, limit_amount: "3000", tier: "low", phase: "recovery" }),
  makeEvent({ evaluated_at: "2026-08-12T18:00:00Z", rolling_accuracy: 0.92, wilson_lower_bound: 0.84, limit_amount: "3000", tier: "low", phase: "recovery" }),
  makeEvent({ evaluated_at: "2026-08-13T10:00:00Z", rolling_accuracy: 0.93, wilson_lower_bound: 0.85, limit_amount: "3000", tier: "low", phase: "recovery" }),
];

// Extract drift and clawback events for reference lines on the chart
export const DRIFT_EVENT = MOCK_AUTONOMY_EVENTS.find(e => e.drift_direction === "degrading");
export const CLAWBACK_EVENT = MOCK_AUTONOMY_EVENTS.find(e => e.is_clawback_event);
export const PROMOTION_EVENT = MOCK_AUTONOMY_EVENTS.find(e => e.is_promotion_event);

// ---------------------------------------------------------------------------
// Recent decisions (for audit trail + agent detail)
// ---------------------------------------------------------------------------

export const MOCK_DECISIONS: AgentDecisionRecord[] = [
  { record_id: "r1", invoice_id: "inv-001", agent_id: "gemini-agent-001", decided_at: "2026-08-13T09:00:00Z", decision: "approve", reason: "approve_within_limit", confidence: 0.95, is_correct: true, from_cache: false, cache_key: null },
  { record_id: "r2", invoice_id: "inv-002", agent_id: "gemini-agent-001", decided_at: "2026-08-13T09:05:00Z", decision: "escalate", reason: "escalate_boundary_amount", confidence: 0.72, is_correct: true, from_cache: true, cache_key: "abc123" },
  { record_id: "r3", invoice_id: "inv-003", agent_id: "gemini-agent-001", decided_at: "2026-08-13T09:10:00Z", decision: "approve", reason: "approve_low_risk", confidence: 0.98, is_correct: true, from_cache: false, cache_key: null },
  { record_id: "r4", invoice_id: "inv-004", agent_id: "gemini-agent-001", decided_at: "2026-08-13T09:15:00Z", decision: "approve", reason: "approve_within_limit", confidence: 0.88, is_correct: false, from_cache: false, cache_key: null },
  { record_id: "r5", invoice_id: "inv-005", agent_id: "gemini-agent-001", decided_at: "2026-08-13T09:20:00Z", decision: "reject", reason: "reject_blocked_vendor", confidence: 0.99, is_correct: true, from_cache: true, cache_key: "def456" },
];

// ---------------------------------------------------------------------------
// Pending approvals
// ---------------------------------------------------------------------------

export const MOCK_APPROVALS: HumanApproval[] = [
  { approval_id: "appr-001", invoice_id: "inv-002", agent_decision_record_id: "r2", requested_at: "2026-08-13T09:05:00Z", resolved_at: null, status: "pending", resolved_by: null, resolution_note: null },
  { approval_id: "appr-002", invoice_id: "inv-006", agent_decision_record_id: "r6", requested_at: "2026-08-13T08:00:00Z", resolved_at: null, status: "pending", resolved_by: null, resolution_note: null },
  { approval_id: "appr-003", invoice_id: "inv-007", agent_decision_record_id: "r7", requested_at: "2026-08-12T16:00:00Z", resolved_at: "2026-08-12T17:00:00Z", status: "approved", resolved_by: "reviewer@company.com", resolution_note: "Verified with vendor." },
  { approval_id: "appr-004", invoice_id: "inv-008", agent_decision_record_id: "r8", requested_at: "2026-08-12T14:00:00Z", resolved_at: "2026-08-12T15:30:00Z", status: "rejected", resolved_by: "reviewer@company.com", resolution_note: "Duplicate submission." },
];

// ---------------------------------------------------------------------------
// Simulation runs
// ---------------------------------------------------------------------------

export const MOCK_SIMULATION_RUNS: SimulationRunResult[] = [
  {
    run_id: "run-001",
    config: { phase: "good", invoice_count: 200, seed: 42, agent_type: "llm", agent_id: "gemini-agent-001", api_base_url: "http://localhost:8000" },
    started_at: "2026-08-13T08:00:00Z",
    completed_at: "2026-08-13T08:12:00Z",
    total_invoices: 200, approved_count: 106, rejected_count: 2, escalated_count: 92,
    correct_decisions: 178, accuracy: 0.89, wilson_lower_bound: 0.84,
    cache_hits: 120, llm_calls: 80, errors: [],
  },
  {
    run_id: "run-002",
    config: { phase: "degraded", invoice_count: 200, seed: 42, agent_type: "llm", agent_id: "gemini-agent-001", api_base_url: "http://localhost:8000" },
    started_at: "2026-08-13T09:00:00Z",
    completed_at: "2026-08-13T09:14:00Z",
    total_invoices: 200, approved_count: 40, rejected_count: 22, escalated_count: 138,
    correct_decisions: 144, accuracy: 0.72, wilson_lower_bound: 0.66,
    cache_hits: 80, llm_calls: 120, errors: [],
  },
];
