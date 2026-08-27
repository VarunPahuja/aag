"use client";
/**
 * src/components/domain/InvoiceCard.tsx
 * ----------------------------------------
 * Enterprise structured row for invoice decisions.
 */

import type { AgentDecisionRecord, AgentDecision } from "@/types/api";

const DECISION_STYLES: Record<AgentDecision, { text: string; bg: string; border: string }> = {
  approve:  { text: "text-[#5f8914]", bg: "bg-[#86BC25]/10", border: "border-[#86BC25]/30" },
  reject:   { text: "text-red-700",   bg: "bg-red-50",        border: "border-red-200"        },
  escalate: { text: "text-amber-800", bg: "bg-amber-50",      border: "border-amber-200"      },
};

const REASON_LABELS: Record<string, string> = {
  approve_within_limit:    "Within limit",
  approve_known_vendor:    "Known vendor",
  approve_low_risk:        "Low risk",
  reject_blocked_vendor:   "Blocked vendor",
  reject_exceeds_limit:    "Exceeds limit",
  reject_invalid_category: "Invalid category",
  reject_negative_amount:  "Invalid amount",
  reject_future_date:      "Future date",
  escalate_missing_fields: "Missing fields",
  escalate_boundary_amount:"Near boundary",
  escalate_ambiguous_vendor:"Unknown vendor",
  escalate_exceeds_tier:   "Exceeds tier",
  escalate_policy_conflict:"Policy conflict",
};

interface Props {
  record: AgentDecisionRecord;
  showCorrectness?: boolean;
}

export function InvoiceCard({ record, showCorrectness = true }: Props) {
  const style = DECISION_STYLES[record.decision] ?? DECISION_STYLES.escalate;
  const reasonLabel = REASON_LABELS[record.reason] ?? record.reason;
  const time = new Date(record.decided_at).toLocaleString("en-IN", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false,
  });

  return (
    <div className="bg-white border border-slate-200 rounded-[4px] p-3 flex items-center justify-between gap-3 text-xs hover:bg-slate-50 transition-colors">
      <div className="flex items-center gap-3 min-w-0">
        <span className={`px-2 py-0.5 font-bold uppercase rounded-[3px] border ${style.bg} ${style.text} ${style.border}`}>
          {record.decision}
        </span>
        <div className="min-w-0">
          <span className="font-mono font-medium text-slate-900 mr-2">{record.invoice_id}</span>
          <span className="text-slate-500">{reasonLabel}</span>
        </div>
      </div>
      <div className="flex items-center gap-4 text-slate-500 flex-shrink-0">
        {record.confidence != null && (
          <span className="font-semibold text-slate-700">{Math.round(record.confidence * 100)}% conf</span>
        )}
        {showCorrectness && record.is_correct != null && (
          <span className={`font-bold ${record.is_correct ? "text-[#5f8914]" : "text-red-700"}`}>
            {record.is_correct ? "✓ Correct" : "✗ Wrong"}
          </span>
        )}
        {record.from_cache && (
          <span className="bg-slate-100 text-slate-600 text-[10px] font-semibold px-1.5 py-0.5 rounded border border-slate-200">
            Cached
          </span>
        )}
        <span>{time}</span>
      </div>
    </div>
  );
}
