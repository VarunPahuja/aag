"use client";
/**
 * src/components/domain/ApprovalRow.tsx
 * ----------------------------------------
 * Enterprise Approval Row component for human authorization queue.
 */

import { useState } from "react";
import type { HumanApproval } from "@/types/api";
import { approvalsApi } from "@/lib/api-client";

interface Props {
  approval: HumanApproval;
  onResolved: (updated: HumanApproval) => void;
}

export function ApprovalRow({ approval, onResolved }: Props) {
  const [loading, setLoading] = useState<"approve" | "reject" | null>(null);
  const [optimistic, setOptimistic] = useState<HumanApproval>(approval);

  const resolve = async (action: "approved" | "rejected") => {
    const key = action === "approved" ? "approve" : "reject";
    setLoading(key);
    const updated: HumanApproval = {
      ...optimistic,
      status: action,
      resolved_at: new Date().toISOString(),
    };
    setOptimistic(updated);
    try {
      const result = await approvalsApi.resolve(approval.approval_id, { status: action });
      onResolved(result);
    } catch {
      setOptimistic(approval);
    } finally {
      setLoading(null);
    }
  };

  const isPending = optimistic.status === "pending";

  const timeAgo = (iso: string) => {
    const diff = Date.now() - new Date(iso).getTime();
    const h = Math.floor(diff / 3_600_000);
    const m = Math.floor((diff % 3_600_000) / 60_000);
    if (h > 0) return `${h}h ago`;
    return `${m}m ago`;
  };

  return (
    <tr className="hover:bg-slate-50 transition-colors">
      <td className="font-mono text-xs font-bold text-slate-900">{optimistic.invoice_id}</td>
      <td className="text-xs font-semibold text-slate-700">GeminiAgent</td>
      <td className="text-xs font-bold text-slate-900">₹12,500</td>
      <td className="text-xs text-slate-600">Near autonomy boundary</td>
      <td className="text-xs text-slate-500">{timeAgo(optimistic.requested_at)}</td>
      <td>
        <span
          className={`inline-block px-2 py-0.5 text-[11px] font-bold uppercase rounded-[3px] ${
            optimistic.status === "pending"
              ? "bg-amber-50 text-amber-800 border border-amber-200"
              : optimistic.status === "approved"
              ? "bg-green-50 text-[#5f8914] border border-green-200"
              : "bg-red-50 text-red-700 border border-red-200"
          }`}
        >
          {optimistic.status}
        </span>
      </td>
      <td className="text-xs text-slate-500">
        {optimistic.resolved_by ?? "—"}
      </td>
      <td>
        {isPending ? (
          <div className="flex gap-1.5">
            <button
              id={`approve-btn-${approval.approval_id}`}
              onClick={() => resolve("approved")}
              disabled={loading !== null}
              className="px-2.5 py-1 text-xs font-bold rounded-[4px] bg-[#86BC25] hover:bg-[#72a31d] text-white transition-colors disabled:opacity-50"
            >
              {loading === "approve" ? "..." : "Approve"}
            </button>
            <button
              id={`reject-btn-${approval.approval_id}`}
              onClick={() => resolve("rejected")}
              disabled={loading !== null}
              className="px-2.5 py-1 text-xs font-bold rounded-[4px] bg-red-600 hover:bg-red-700 text-white transition-colors disabled:opacity-50"
            >
              {loading === "reject" ? "..." : "Reject"}
            </button>
          </div>
        ) : (
          <span className="text-xs text-slate-400">Resolved</span>
        )}
      </td>
    </tr>
  );
}
