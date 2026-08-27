"use client";
/**
 * Page 1: /agents — Governed AI Workforce Overview
 * Deloitte White Enterprise Editorial Product Structure
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { agentsApi } from "@/lib/api-client";
import { AutonomyLadder } from "@/components/domain/AutonomyLadder";
import type { Agent, AutonomyTier } from "@/types/api";

const TIER_TAG_CLASS: Record<AutonomyTier, string> = {
  low:    "tier-low",
  medium: "tier-medium",
  high:   "tier-high",
};

export default function AgentsPage() {
  const { data: agents = [], isLoading, isError } = useQuery({
    queryKey: ["agents"],
    queryFn: agentsApi.list,
  });

  const totalAuthority = agents.reduce((acc, a) => acc + Number(a.current_limit), 0);
  const activeCount = agents.length;
  const attentionCount = agents.filter(a => (a.wilson_lower_bound ?? 1) < 0.85).length;

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

        {!isLoading && agents.map((agent: Agent) => {
          const wlb = agent.wilson_lower_bound ?? 0;
          const isHealthy = wlb >= 0.85;

          return (
            <div
              key={agent.agent_id}
              className="editorial-panel p-6 hover:border-slate-300 transition-colors"
            >
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                {/* Left Agent identity */}
                <div className="space-y-1.5 min-w-[220px]">
                  <div className="flex items-center gap-2">
                    <span className={`tier-tag ${TIER_TAG_CLASS[agent.tier]}`}>
                      {agent.tier.toUpperCase()}
                    </span>
                    <span className={`text-[10px] font-extrabold uppercase px-1.5 py-0.5 rounded-[2px] ${
                      isHealthy ? "bg-green-100 text-[#5f8914]" : "bg-amber-100 text-amber-900"
                    }`}>
                      {isHealthy ? "HEALTHY" : "ATTENTION REQUIRED"}
                    </span>
                  </div>
                  <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
                    {agent.name}
                  </h2>
                  <p className="text-xs font-mono text-slate-400">{agent.agent_id}</p>
                </div>

                {/* Autonomy Ladder Visual */}
                <div className="border-l border-slate-200 pl-6 hidden xl:block">
                  <AutonomyLadder currentTier={agent.tier} compact />
                </div>

                {/* Editorial Metric Strip */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-6 border-t lg:border-t-0 lg:border-l border-slate-200 pt-4 lg:pt-0 lg:pl-6">
                  <div>
                    <span className="eyebrow-label block text-[9px]">CURRENT AUTHORITY</span>
                    <span className="text-base font-black text-slate-900">
                      ₹{Number(agent.current_limit).toLocaleString("en-IN")}
                    </span>
                  </div>
                  <div>
                    <span className="eyebrow-label block text-[9px]">ACCURACY</span>
                    <span className="text-base font-black text-slate-900">
                      {agent.rolling_accuracy != null ? `${Math.round(agent.rolling_accuracy * 100)}%` : "—"}
                    </span>
                  </div>
                  <div>
                    <span className="eyebrow-label block text-[9px]">WILSON LOWER BOUND</span>
                    <span className={`text-base font-black ${isHealthy ? "text-[#5f8914]" : "text-amber-800"}`}>
                      {agent.wilson_lower_bound != null ? `${Math.round(agent.wilson_lower_bound * 100)}%` : "—"}
                    </span>
                  </div>
                  <div>
                    <span className="eyebrow-label block text-[9px]">DECISIONS</span>
                    <span className="text-base font-black text-slate-900">
                      {agent.total_decisions.toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="eyebrow-label block text-[9px]">PENDING</span>
                    <span className="text-base font-black text-slate-900">
                      {agent.pending_approvals}
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
          );
        })}
      </div>
    </div>
  );
}
