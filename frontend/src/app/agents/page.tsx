"use client";
/**
 * Page 1: /agents — Governed AI Workforce Overview
 * v1.1 contracts: five-rung ladder, AgentState, trust_score, reason_codes
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { agentsApi } from "@/lib/api-client";
import { AutonomyLadder } from "@/components/domain/AutonomyLadder";
import { describeReasonCodes } from "@/types/api";
import type { AgentSummary, AgentState, DriftSeverity } from "@/types/api";

const STATE_CLASS: Record<AgentState, string> = {
  probation:  "state-badge state-probation",
  active:     "state-badge state-active",
  restricted: "state-badge state-restricted",
  suspended:  "state-badge state-suspended",
};

function fmtLimit(val: number): string {
  if (val >= 1000) return `₹${(val / 1000).toFixed(0)}k`;
  return `₹${val}`;
}

export default function AgentsPage() {
  const { data: agents = [], isLoading, isError } = useQuery({
    queryKey: ["agents"],
    queryFn: agentsApi.list,
  });

  const totalAuthority = agents.reduce((acc, a) => acc + a.current_limit, 0);
  const activeCount = agents.length;
  const attentionCount = agents.filter(a => a.state === "restricted" || a.state === "suspended" || a.drift_severity !== "NONE").length;

  return (
    <div>
      {/* Header */}
      <div className="editorial-header">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <span className="eyebrow-label">GOVERNED AI WORKFORCE</span>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight mt-1">Agents</h1>
            <p className="text-xs font-medium text-slate-600 max-w-xl mt-1 leading-relaxed">
              Monitor earned autonomy, statistical reliability, and human oversight across registered AI agents.
            </p>
          </div>

          {/* Right Summary Block */}
          <div className="flex items-center gap-4 bg-[#F7F8F6] border border-[#E2E8F0] px-4 py-2.5 rounded-[2px] font-sans">
            <div>
              <span className="eyebrow-label text-[9px] block">ACTIVE AGENTS</span>
              <span className="text-sm font-black text-slate-900">{activeCount}</span>
            </div>
            <div className="w-[1px] h-7 bg-slate-200" />
            <div>
              <span className="eyebrow-label text-[9px] block">TOTAL AUTHORITY</span>
              <span className="text-sm font-black text-slate-900">
                ₹{totalAuthority.toLocaleString("en-IN")}
              </span>
            </div>
            <div className="w-[1px] h-7 bg-slate-200" />
            <div>
              <span className="eyebrow-label text-[9px] block">REQUIRES ATTENTION</span>
              <span className={`text-sm font-black ${attentionCount > 0 ? "text-amber-800" : "text-slate-900"}`}>
                {attentionCount}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="editorial-content space-y-6">
        {isLoading && (
          <div className="text-xs text-slate-500 font-bold tracking-wider uppercase animate-pulse">
            LOADING AGENT WORKFORCE REGISTRY...
          </div>
        )}

        {isError && (
          <div className="text-xs text-red-700 font-bold">
            Unable to connect to governance API.
          </div>
        )}

        {!isLoading && agents.map((agent: AgentSummary) => (
          <div
            key={agent.agent_id}
            className="editorial-panel p-6 hover:border-slate-300 transition-colors"
          >
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
              {/* Left Agent identity */}
              <div className="space-y-1.5 min-w-[220px]">
                <div className="flex items-center gap-2">
                  <span className={`rung-tag rung-${agent.current_rung}`}>
                    RUNG {agent.current_rung}
                  </span>
                  <span className={STATE_CLASS[agent.state]}>
                    {agent.state.toUpperCase()}
                  </span>
                  {agent.drift_severity !== "NONE" && (
                    <span className={`state-badge drift-${agent.drift_severity.toLowerCase()}`}>
                      DRIFT: {agent.drift_severity}
                    </span>
                  )}
                </div>
                <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
                  {agent.name}
                </h2>
                <p className="text-xs font-mono text-slate-400">{agent.agent_id}</p>
                {agent.reason_codes.length > 0 && (
                  <p className="text-[11px] text-slate-500 leading-relaxed mt-1">
                    {describeReasonCodes(agent.reason_codes)}
                  </p>
                )}
              </div>

              {/* Autonomy Ladder Visual */}
              <div className="border-l border-slate-200 pl-6 hidden xl:block">
                <AutonomyLadder currentRung={agent.current_rung} compact />
              </div>

              {/* Editorial Metric Strip */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-6 border-t lg:border-t-0 lg:border-l border-slate-200 pt-4 lg:pt-0 lg:pl-6">
                <div>
                  <span className="eyebrow-label block text-[9px]">CURRENT AUTHORITY</span>
                  <span className="text-base font-black text-slate-900">
                    {fmtLimit(agent.current_limit)}
                  </span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">TRUST SCORE</span>
                  <span className="text-base font-black text-slate-900">
                    {agent.trust_score.toFixed(1)}
                  </span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">ACCURACY</span>
                  <span className="text-base font-black text-slate-900">
                    {agent.rolling_accuracy != null ? `${Math.round(agent.rolling_accuracy * 100)}%` : "—"}
                  </span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">DECISIONS</span>
                  <span className="text-base font-black text-slate-900">
                    {agent.total_decisions.toLocaleString()}
                  </span>
                </div>
                <div>
                  <span className="eyebrow-label block text-[9px]">DIRECTION</span>
                  <span className={`state-badge direction-${agent.direction.toLowerCase()}`}>
                    {agent.direction}
                  </span>
                </div>
              </div>

              {/* View Agent Action Link */}
              <div className="flex items-center justify-end">
                <Link
                  href={`/agents/${agent.agent_id}`}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-[2px] bg-[#86BC25] hover:bg-[#72a31d] text-white text-xs font-bold transition-colors"
                >
                  <span>VIEW AGENT</span>
                  <span>→</span>
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
