"use client";
/**
 * Page 4: /audit — Immutable Governance Record Table & Detail Drawer
 * v1.1 contracts: AuditLogEntry with hash chain verification.
 *
 * The audit log IS hash-chained — each row stores
 * sha256(prev_hash + canonical_json(payload)). The UI verifies the chain
 * and reports the result dynamically.
 */

import { useQuery } from "@tanstack/react-query";
import { useState, useMemo } from "react";
import { auditLogApi } from "@/lib/api-client";
import { IconShieldAlert, IconCheckCircle } from "@/components/ui/Icons";
import type { AuditLogEntry } from "@/types/api";

const EVENT_TYPE_BADGE: Record<string, string> = {
  agent_registered:       "bg-blue-100 text-blue-700 border-blue-200",
  decision_recorded:      "bg-green-100 text-[#5f8914] border-green-200",
  trust_evaluated:        "bg-slate-100 text-slate-700 border-slate-200",
  autonomy_changed:       "bg-amber-100 text-amber-900 border-amber-200",
  drift_detected:         "bg-red-100 text-red-700 border-red-200",
  recommendation_created: "bg-purple-100 text-purple-700 border-purple-200",
  sample_reviewed:        "bg-cyan-100 text-cyan-800 border-cyan-200",
};

function fmtEventType(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

/** Verify the hash chain: each entry's prev_hash must match the prior entry's hash. */
function verifyChain(entries: AuditLogEntry[]): {
  valid: boolean;
  checkedCount: number;
  brokenAt: number | null;
} {
  if (entries.length === 0) return { valid: true, checkedCount: 0, brokenAt: null };

  for (let i = 1; i < entries.length; i++) {
    if (entries[i].prev_hash !== entries[i - 1].hash) {
      return { valid: false, checkedCount: i, brokenAt: i };
    }
  }
  return { valid: true, checkedCount: entries.length, brokenAt: null };
}

export default function AuditPage() {
  const [page, setPage] = useState(1);
  const [selectedEntry, setSelectedEntry] = useState<AuditLogEntry | null>(null);
  const PAGE_SIZE = 25;

  const { data, isLoading } = useQuery({
    queryKey: ["audit-log", page],
    queryFn: () => auditLogApi.list({ page, page_size: PAGE_SIZE }),
    refetchInterval: 10_000,
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1;

  const chainStatus = useMemo(
    () => verifyChain(data?.items ?? []),
    [data?.items]
  );

  return (
    <div>
      {/* Header */}
      <div className="editorial-header">
        <div className="flex items-center justify-between">
          <div>
            <span className="eyebrow-label">IMMUTABLE GOVERNANCE RECORD</span>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight mt-1">Audit Trail</h1>
            <p className="text-xs font-medium text-slate-600 max-w-xl mt-1">
              Every automated decision, human intervention, and autonomy change is recorded in a hash-chained log.
            </p>
          </div>

          {/* Dynamic integrity indicator — verifies hash chain */}
          {data && data.items.length > 0 ? (
            chainStatus.valid ? (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 border border-green-200 rounded-[2px]">
                <IconCheckCircle className="w-4 h-4 text-[#5f8914]" />
                <div>
                  <span className="text-xs font-bold text-[#5f8914] block">Hash Chain: Verified</span>
                  <span className="text-[10px] text-green-700">{chainStatus.checkedCount} entries checked</span>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-red-50 border border-red-200 rounded-[2px]">
                <IconShieldAlert className="w-4 h-4 text-red-700" />
                <div>
                  <span className="text-xs font-bold text-red-700 block">Hash Chain: BROKEN</span>
                  <span className="text-[10px] text-red-600">Break at entry {chainStatus.brokenAt}</span>
                </div>
              </div>
            )
          ) : (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-[2px]">
              <IconShieldAlert className="w-4 h-4 text-slate-400" />
              <span className="text-xs font-bold text-slate-500">No entries to verify</span>
            </div>
          )}
        </div>
      </div>

      <div className="editorial-content">
        <div className="flex flex-col xl:flex-row gap-6">
          {/* Main Audit Data Table */}
          <div className="editorial-panel overflow-hidden flex-1">
            {isLoading ? (
              <div className="p-8 text-xs font-bold text-slate-400 uppercase tracking-widest animate-pulse">
                LOADING AUDIT LOG...
              </div>
            ) : (
              <table className="editorial-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Event</th>
                    <th>Actor</th>
                    <th>Entity</th>
                    <th>Hash</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.items.map((entry, idx) => {
                    const isSelected = selectedEntry?.id === entry.id;
                    const badge = EVENT_TYPE_BADGE[entry.event_type] ?? "bg-slate-100 text-slate-700 border-slate-200";
                    // Check if this specific entry's chain link is valid
                    const prevEntry = idx > 0 ? data.items[idx - 1] : null;
                    const linkValid = idx === 0 || (prevEntry && entry.prev_hash === prevEntry.hash);

                    return (
                      <tr
                        key={entry.id}
                        onClick={() => setSelectedEntry(entry)}
                        className={`cursor-pointer transition-colors ${
                          isSelected ? "bg-slate-100 font-semibold" : "hover:bg-slate-50"
                        }`}
                      >
                        <td>
                          <span className="font-mono text-xs font-bold text-slate-900">
                            {entry.id}
                          </span>
                        </td>
                        <td>
                          <span className={`inline-block px-2 py-0.5 text-[10px] font-black uppercase rounded-[2px] border ${badge}`}>
                            {fmtEventType(entry.event_type)}
                          </span>
                        </td>
                        <td>
                          <div>
                            <span className="text-xs font-semibold text-slate-800">{entry.actor}</span>
                            <span className="text-[10px] text-slate-400 ml-1">({entry.actor_type})</span>
                          </div>
                        </td>
                        <td>
                          <div>
                            <span className="text-[10px] font-bold text-slate-500 uppercase">{entry.entity_type}</span>
                            <span className="text-xs font-mono text-slate-700 ml-1">{entry.entity_id}</span>
                          </div>
                        </td>
                        <td>
                          <div className="flex items-center gap-1">
                            {linkValid ? (
                              <span className="w-1.5 h-1.5 rounded-full bg-[#86BC25] inline-block flex-shrink-0" />
                            ) : (
                              <span className="w-1.5 h-1.5 rounded-full bg-red-600 inline-block flex-shrink-0" />
                            )}
                            <span className="font-mono text-[10px] text-slate-400 truncate max-w-[80px]">
                              {entry.hash.slice(0, 12)}…
                            </span>
                          </div>
                        </td>
                        <td>
                          <span className="text-xs text-slate-500 font-medium">
                            {new Date(entry.ts).toLocaleString("en-IN", {
                              month: "short", day: "numeric",
                              hour: "2-digit", minute: "2-digit", hour12: false,
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
          {selectedEntry && (
            <div className="editorial-panel p-6 w-full xl:w-96 flex-shrink-0 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                <span className="eyebrow-label">RECORD INSPECTION</span>
                <button
                  onClick={() => setSelectedEntry(null)}
                  className="text-xs font-bold text-slate-400 hover:text-slate-900"
                >
                  ✕ CLOSE
                </button>
              </div>

              <div className="space-y-3 text-xs font-sans">
                <div>
                  <span className="eyebrow-label block text-[9px]">ENTRY ID</span>
                  <span className="font-mono font-bold text-slate-900">{selectedEntry.id}</span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">EVENT TYPE</span>
                  <span className={`inline-block px-2 py-0.5 text-[10px] font-black uppercase rounded-[2px] border ${EVENT_TYPE_BADGE[selectedEntry.event_type] ?? "bg-slate-100 text-slate-700 border-slate-200"}`}>
                    {fmtEventType(selectedEntry.event_type)}
                  </span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">ACTOR</span>
                  <span className="font-semibold text-slate-800">{selectedEntry.actor}</span>
                  <span className="text-[10px] text-slate-400 ml-1">({selectedEntry.actor_type})</span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">ENTITY</span>
                  <span className="text-[10px] font-bold text-slate-500 uppercase">{selectedEntry.entity_type} </span>
                  <span className="font-mono font-bold text-slate-900">{selectedEntry.entity_id}</span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">TIMESTAMP</span>
                  <span className="font-mono text-slate-600">{selectedEntry.ts}</span>
                </div>

                {/* Hash chain details */}
                <div className="border-t border-slate-200 pt-3 space-y-2">
                  <span className="eyebrow-label block text-[9px]">HASH CHAIN</span>
                  <div>
                    <span className="text-[9px] font-bold text-slate-500 block">PREV HASH</span>
                    <span className="font-mono text-[10px] text-slate-600 break-all leading-relaxed">
                      {selectedEntry.prev_hash}
                    </span>
                  </div>
                  <div>
                    <span className="text-[9px] font-bold text-slate-500 block">HASH</span>
                    <span className="font-mono text-[10px] text-slate-900 break-all leading-relaxed font-bold">
                      {selectedEntry.hash}
                    </span>
                  </div>
                </div>

                {/* Payload */}
                <div className="border-t border-slate-200 pt-3">
                  <span className="eyebrow-label block text-[9px] mb-1">PAYLOAD</span>
                  <pre className="bg-slate-50 border border-slate-200 rounded-[2px] p-3 text-[10px] font-mono text-slate-700 overflow-x-auto leading-relaxed">
                    {JSON.stringify(selectedEntry.payload, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
