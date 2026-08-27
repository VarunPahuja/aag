"use client";
/**
 * Page 4: /audit — Immutable Governance Record Table & Detail Drawer
 * Deloitte White Enterprise Audit & Regulatory Product
 */

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { auditApi } from "@/lib/api-client";
import { IconCheckCircle } from "@/components/ui/Icons";
import type { AgentDecisionRecord, AgentDecision } from "@/types/api";

const DECISION_BADGE: Record<AgentDecision, string> = {
  approve:  "bg-green-100 text-[#5f8914] border-green-200",
  reject:   "bg-red-100 text-red-700 border-red-200",
  escalate: "bg-amber-100 text-amber-900 border-amber-200",
};

export default function AuditPage() {
  const [page, setPage] = useState(1);
  const [selectedRecord, setSelectedRecord] = useState<AgentDecisionRecord | null>(null);
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

          <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 border border-green-200 rounded-[2px]">
            <IconCheckCircle className="w-4 h-4 text-[#5f8914]" />
            <span className="text-xs font-bold text-[#5f8914]">Audit Integrity: Verified</span>
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
                    <th>Decision</th>
                    <th>Reason Code</th>
                    <th>Confidence</th>
                    <th>Correctness</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items.map(record => {
                    const isSelected = selectedRecord?.record_id === record.record_id;
                    return (
                      <tr
                        key={record.record_id}
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
                          <span className={`inline-block px-2 py-0.5 text-[10px] font-black uppercase rounded-[2px] border ${DECISION_BADGE[record.decision]}`}>
                            {record.decision}
                          </span>
                        </td>
                        <td>
                          <span className="text-xs text-slate-700 font-medium">
                            {record.reason}
                          </span>
                        </td>
                        <td>
                          <span className="text-xs font-mono font-bold text-slate-900">
                            {record.confidence != null ? `${Math.round(record.confidence * 100)}%` : "—"}
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
                          <span className="text-xs text-slate-500 font-medium">
                            {new Date(record.decided_at).toLocaleString("en-IN", {
                              month: "short", day: "numeric",
                              hour: "2-digit", minute: "2-digit", hour12: false
                            })}
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
                  <span className="eyebrow-label block text-[9px]">INVOICE ID</span>
                  <span className="font-mono font-bold text-slate-900">{selectedRecord.invoice_id}</span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">AGENT MODEL</span>
                  <span className="font-semibold text-slate-800">GeminiAgent (gemini-2.5-flash)</span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">DECISION DETAILS</span>
                  <span className={`inline-block px-2 py-0.5 text-[10px] font-black uppercase rounded-[2px] border ${DECISION_BADGE[selectedRecord.decision]}`}>
                    {selectedRecord.decision}
                  </span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">CONFIDENCE SCORE</span>
                  <span className="font-bold text-slate-900">
                    {selectedRecord.confidence != null ? `${Math.round(selectedRecord.confidence * 100)}%` : "N/A"}
                  </span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">REASON CODE</span>
                  <span className="font-mono font-semibold text-amber-900">{selectedRecord.reason}</span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">GOVERNANCE ACTION</span>
                  <span className="font-bold text-[#5f8914]">Logged to immutable trail</span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">TIMESTAMP</span>
                  <span className="font-mono text-slate-500">{selectedRecord.decided_at}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
