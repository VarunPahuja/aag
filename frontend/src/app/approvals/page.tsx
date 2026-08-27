"use client";
/**
 * Page 3: /approvals — Human-in-the-Loop Governance Queue
 * Deloitte White Enterprise Editorial Approvals Page
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { approvalsApi } from "@/lib/api-client";
import type { HumanApproval } from "@/types/api";

export default function ApprovalsPage() {
  const qc = useQueryClient();
  const [filter, setFilter] = useState<"pending" | "approved" | "rejected" | "all">("pending");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: approvals = [], isLoading } = useQuery({
    queryKey: ["approvals", filter],
    queryFn: () => approvalsApi.list(filter),
  });

  const handleResolve = async (approvalId: string, status: "approved" | "rejected") => {
    try {
      await approvalsApi.resolve(approvalId, { status });
      qc.invalidateQueries({ queryKey: ["approvals"] });
      qc.invalidateQueries({ queryKey: ["agents"] });
    } catch (err) {
      console.error(err);
    }
  };

  const pendingCount = approvals.filter(a => a.status === "pending").length;

  return (
    <div>
      {/* Header */}
      <div className="editorial-header">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <span className="eyebrow-label">HUMAN-IN-THE-LOOP GOVERNANCE</span>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight mt-1">Human Approvals</h1>
            <p className="text-xs font-medium text-slate-600 max-w-xl mt-1 leading-relaxed">
              Review decisions that exceed automated authority or require human judgment.
            </p>
          </div>

          {/* Large Prominent Counter */}
          <div className="bg-amber-50 border border-amber-200 px-5 py-2.5 rounded-[2px] text-right">
            <span className="eyebrow-label text-[9px] text-amber-900 block">PENDING REVIEW</span>
            <span className="text-3xl font-black text-amber-900">{pendingCount}</span>
          </div>
        </div>

        {/* Clean Filter Tabs */}
        <div className="flex border-b border-slate-200 mt-6 gap-6 text-xs font-semibold font-sans">
          {(["pending", "approved", "rejected", "all"] as const).map(f => (
            <button
              key={f}
              id={`filter-${f}`}
              onClick={() => setFilter(f)}
              className={`pb-3 uppercase tracking-wider text-[11px] font-bold transition-colors border-b-2 ${
                filter === f
                  ? "border-[#86BC25] text-slate-900"
                  : "border-transparent text-slate-400 hover:text-slate-900"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Main Review Queue Content */}
      <div className="editorial-content space-y-4">
        {isLoading && (
          <div className="text-xs font-bold text-slate-400 uppercase tracking-widest animate-pulse">
            LOADING APPROVAL QUEUE...
          </div>
        )}

        {!isLoading && approvals.length === 0 && (
          <div className="editorial-panel p-8 text-center text-xs text-slate-500 font-medium">
            No {filter} approvals requiring attention.
          </div>
        )}

        {!isLoading && approvals.map(appr => {
          const isExpanded = expandedId === appr.approval_id;
          const isPending = appr.status === "pending";

          return (
            <div key={appr.approval_id} className="editorial-panel p-5 space-y-3">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                {/* Main Row Information */}
                <div className="flex items-center gap-4 flex-1">
                  <span className="font-mono text-sm font-black text-slate-900">{appr.invoice_id}</span>
                  <span className="text-sm font-black text-slate-900">₹12,500</span>
                  <span className="text-xs font-semibold text-slate-600">GeminiAgent</span>
                  <span className="text-xs text-slate-500">Near autonomy boundary</span>
                </div>

                <div className="flex items-center gap-4">
                  <span className="text-xs text-slate-400 font-mono">15m ago</span>
                  <span className={`px-2 py-0.5 text-[10px] font-extrabold uppercase rounded-[2px] ${
                    appr.status === "pending" ? "bg-amber-100 text-amber-900" :
                    appr.status === "approved" ? "bg-green-100 text-[#5f8914]" :
                    "bg-red-100 text-red-700"
                  }`}>
                    {appr.status}
                  </span>

                  {isPending && (
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleResolve(appr.approval_id, "approved")}
                        className="px-3 py-1.5 rounded-[2px] bg-[#86BC25] hover:bg-[#72a31d] text-white text-xs font-bold transition-colors"
                      >
                        APPROVE
                      </button>
                      <button
                        onClick={() => handleResolve(appr.approval_id, "rejected")}
                        className="px-3 py-1.5 rounded-[2px] bg-red-600 hover:bg-red-700 text-white text-xs font-bold transition-colors"
                      >
                        REJECT
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Expandable Section: Why was this escalated? */}
              <div className="pt-2 border-t border-slate-200/60">
                <button
                  onClick={() => setExpandedId(isExpanded ? null : appr.approval_id)}
                  className="text-[11px] font-bold text-slate-600 hover:text-slate-900 flex items-center gap-1"
                >
                  <span>{isExpanded ? "▲ Hide escalation context" : "▼ Why was this escalated?"}</span>
                </button>

                {isExpanded && (
                  <div className="mt-3 grid grid-cols-3 gap-4 bg-slate-50 p-3 rounded-[2px] text-xs font-sans">
                    <div>
                      <span className="eyebrow-label block text-[9px]">CONFIDENCE</span>
                      <span className="font-bold text-slate-900">81%</span>
                    </div>
                    <div>
                      <span className="eyebrow-label block text-[9px]">AGENT AUTHORITY</span>
                      <span className="font-bold text-slate-900">LOW (₹3,000)</span>
                    </div>
                    <div>
                      <span className="eyebrow-label block text-[9px]">REASON CODE</span>
                      <span className="font-bold text-amber-800">escalate_boundary_amount</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
