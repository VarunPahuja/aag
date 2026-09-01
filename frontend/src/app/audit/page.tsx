"use client";
/**
 * Page 4: /audit — Immutable Governance Record Table & Detail Drawer
 * v1.1 contracts: DecisionRecord, removed false "Verified" badge.
 *
 * The audit log IS hash-chained in the backend, but the hash/prev_hash fields
 * are not yet exposed via the API. Until they are, we show an honest
 * "awaiting backend fields" indicator rather than a false assurance.
 */

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { auditApi } from "@/lib/api-client";
import { IconShieldAlert } from "@/components/ui/Icons";
import type { DecisionRecord, Action } from "@/types/api";

const ACTION_BADGE: Record<Action, string> = {
  APPROVE:  "bg-green-100 text-[#5f8914] border-green-200",
  REJECT:   "bg-red-100 text-red-700 border-red-200",
  ESCALATE: "bg-amber-100 text-amber-900 border-amber-200",
};

export default function AuditPage() {
  const [page, setPage] = useState(1);
  const [selectedRecord, setSelectedRecord] = useState<DecisionRecord | null>(null);
  const PAGE_SIZE = 25;

  const { data, isLoading } = useQuery({
    queryKey: ["audit", page],
    queryFn: () => auditApi.list({ page, page_size: PAGE_SIZE }),
    refetchInterval: 10_000,
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1;

  return (
    <div>
      {/* Header */}
      <div className="editorial-header">
        <div className="flex items-center justify-between">
          <div>
            <span className="eyebrow-label">IMMUTABLE GOVERNANCE RECORD</span>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight mt-1">Audit Trail</h1>
            <p className="text-xs font-medium text-slate-600 max-w-xl mt-1">
              Every automated decision, human intervention, and autonomy change is recorded here.
            </p>
          </div>

          {/* Honest integrity indicator — NOT verified until backend exposes hash fields */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-[2px]">
            <IconShieldAlert className="w-4 h-4 text-amber-700" />
            <span className="text-xs font-bold text-amber-800">Hash verification: awaiting backend fields</span>
          </div>
        </div>
      </div>

      <div className="editorial-content">
        <div className="flex flex-col xl:flex-row gap-6">
          {/* Main Audit Data Table */}
          <div className="editorial-panel overflow-hidden flex-1">
            {isLoading ? (
              <div className="p-8 text-xs font-bold text-slate-400 uppercase tracking-widest animate-pulse">
                LOADING AUDIT RECORDS...
              </div>
            ) : (
              <table className="editorial-table">
                <thead>
                  <tr>
                    <th>Invoice ID</th>
                    <th>Agent ID</th>
                    <th>Action</th>
                    <th>Amount</th>
                    <th>Correct</th>
                    <th>Critical</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items.map(record => {
                    const isSelected = selectedRecord?.decision_id === record.decision_id;
                    return (
                      <tr
                        key={record.decision_id}
                        onClick={() => setSelectedRecord(record)}
                        className={`cursor-pointer transition-colors ${
                          isSelected ? "bg-slate-100 font-semibold" : "hover:bg-slate-50"
                        }`}
                      >
                        <td>
                          <span className="font-mono text-xs font-bold text-slate-900">
                            {record.invoice_id}
                          </span>
                        </td>
                        <td>
                          <span className="text-xs font-mono text-slate-500">{record.agent_id}</span>
                        </td>
                        <td>
                          <span className={`inline-block px-2 py-0.5 text-[10px] font-black uppercase rounded-[2px] border ${ACTION_BADGE[record.action]}`}>
                            {record.action}
                          </span>
                        </td>
                        <td>
                          <span className="text-xs font-bold text-slate-900">
                            ₹{record.amount.toLocaleString("en-IN")}
                          </span>
                        </td>
                        <td>
                          {record.is_correct == null ? (
                            <span className="text-xs text-slate-400">—</span>
                          ) : record.is_correct ? (
                            <span className="text-xs text-[#5f8914] font-bold">✓ Correct</span>
                          ) : (
                            <span className="text-xs text-red-700 font-bold">✗ Wrong</span>
                          )}
                        </td>
                        <td>
                          {record.is_critical_error ? (
                            <span className="text-[10px] font-extrabold text-red-700 bg-red-100 px-1.5 py-0.5 rounded border border-red-200">CRITICAL</span>
                          ) : (
                            <span className="text-xs text-slate-400">—</span>
                          )}
                        </td>
                        <td>
                          <span className="text-xs text-slate-500 font-medium">
                            {record.decided_at
                              ? new Date(record.decided_at).toLocaleString("en-IN", {
                                  month: "short", day: "numeric",
                                  hour: "2-digit", minute: "2-digit", hour12: false
                                })
                              : "—"}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}

            {/* Pagination Footer */}
            {totalPages > 1 && (
              <div className="p-4 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600 bg-slate-50">
                <span>
                  Page {page} of {totalPages} ({data?.total.toLocaleString()} total audit entries)
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="px-3 py-1 bg-white border border-slate-300 rounded-[2px] font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                  >
                    PREVIOUS
                  </button>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="px-3 py-1 bg-white border border-slate-300 rounded-[2px] font-bold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                  >
                    NEXT
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Right Contextual Inspection Panel */}
          {selectedRecord && (
            <div className="editorial-panel p-6 w-full xl:w-80 flex-shrink-0 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                <span className="eyebrow-label">RECORD INSPECTION</span>
                <button
                  onClick={() => setSelectedRecord(null)}
                  className="text-xs font-bold text-slate-400 hover:text-slate-900"
                >
                  ✕ CLOSE
                </button>
              </div>

              <div className="space-y-3 text-xs font-sans">
                <div>
                  <span className="eyebrow-label block text-[9px]">DECISION ID</span>
                  <span className="font-mono font-bold text-slate-900">{selectedRecord.decision_id}</span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">INVOICE ID</span>
                  <span className="font-mono font-bold text-slate-900">{selectedRecord.invoice_id}</span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">AGENT</span>
                  <span className="font-semibold text-slate-800">{selectedRecord.agent_id}</span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">AMOUNT</span>
                  <span className="font-bold text-slate-900">₹{selectedRecord.amount.toLocaleString("en-IN")}</span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">ACTION</span>
                  <span className={`inline-block px-2 py-0.5 text-[10px] font-black uppercase rounded-[2px] border ${ACTION_BADGE[selectedRecord.action]}`}>
                    {selectedRecord.action}
                  </span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">GROUND TRUTH</span>
                  <span className={`inline-block px-2 py-0.5 text-[10px] font-black uppercase rounded-[2px] border ${ACTION_BADGE[selectedRecord.ground_truth]}`}>
                    {selectedRecord.ground_truth}
                  </span>
                </div>
                {selectedRecord.is_escalated && (
                  <>
                    <div>
                      <span className="eyebrow-label block text-[9px]">RECOMMENDED ACTION</span>
                      <span className="font-bold text-slate-900">{selectedRecord.recommended_action ?? "—"}</span>
                    </div>
                    <div>
                      <span className="eyebrow-label block text-[9px]">HUMAN RULING</span>
                      <span className="font-bold text-slate-900">{selectedRecord.human_ruling ?? "—"}</span>
                    </div>
                  </>
                )}
                {selectedRecord.is_critical_error && (
                  <div className="bg-red-50 border border-red-200 p-2 rounded-[2px]">
                    <span className="text-[10px] font-extrabold text-red-700">
                      ⚠ CRITICAL ERROR — agent approved an invoice that should have been rejected
                    </span>
                  </div>
                )}
                <div>
                  <span className="eyebrow-label block text-[9px]">TIMESTAMP</span>
                  <span className="font-mono text-slate-500">{selectedRecord.decided_at}</span>
                </div>
                <div className="border-t border-slate-200 pt-3">
                  <span className="eyebrow-label block text-[9px]">HASH VERIFICATION</span>
                  <span className="text-[11px] text-amber-700 font-medium">Not yet available — awaiting backend hash fields</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
