"use client";
/**
 * src/components/domain/InvoiceCard.tsx
 * ----------------------------------------
 * Enterprise structured row for invoice decisions — v1.1 contracts.
 * Uses reason codes from shared/reason_codes.py instead of hand-written labels.
 */

import type { DecisionRecord, Action } from "@/types/api";

const ACTION_STYLES: Record<Action, { text: string; bg: string; border: string }> = {
  APPROVE:  { text: "text-[#5f8914]", bg: "bg-[#86BC25]/10", border: "border-[#86BC25]/30" },
  REJECT:   { text: "text-red-700",   bg: "bg-red-50",        border: "border-red-200"     },
  ESCALATE: { text: "text-amber-800", bg: "bg-amber-50",      border: "border-amber-200"   },
};

interface Props {
  record: DecisionRecord;
  showCorrectness?: boolean;
}

function fmtAmount(amount: number): string {
  return `₹${amount.toLocaleString("en-IN")}`;
}

export function InvoiceCard({ record, showCorrectness = true }: Props) {
  const style = ACTION_STYLES[record.action] ?? ACTION_STYLES.ESCALATE;
  const time = record.decided_at
    ? new Date(record.decided_at).toLocaleString("en-IN", {
        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false,
      })
    : "—";

  return (
    <div className="bg-white border border-slate-200 rounded-[4px] p-3 flex items-center justify-between gap-3 text-xs hover:bg-slate-50 transition-colors">
      <div className="flex items-center gap-3 min-w-0">
        <span className={`px-2 py-0.5 font-bold uppercase rounded-[3px] border ${style.bg} ${style.text} ${style.border}`}>
          {record.action}
        </span>
        <div className="min-w-0">
          <span className="font-mono font-medium text-slate-900 mr-2">{record.invoice_id}</span>
          <span className="font-bold text-slate-700 mr-2">{fmtAmount(record.amount)}</span>
          {record.is_escalated && record.recommended_action && (
            <span className="text-slate-500">
              Recommended: {record.recommended_action}
              {record.human_ruling ? ` → Ruled: ${record.human_ruling}` : ""}
            </span>
          )}
        </div>
      </div>
      <div className="flex items-center gap-4 text-slate-500 flex-shrink-0">
        {showCorrectness && record.is_correct != null && (
          <span className={`font-bold ${record.is_correct ? "text-[#5f8914]" : "text-red-700"}`}>
            {record.is_correct ? "✓ Correct" : "✗ Wrong"}
          </span>
        )}
        {record.is_critical_error && (
          <span className="bg-red-100 text-red-800 text-[10px] font-extrabold px-1.5 py-0.5 rounded border border-red-200">
            CRITICAL
          </span>
        )}
        <span>{time}</span>
      </div>
    </div>
  );
}
