"use client";
/**
 * Page 2: /agents/[id] — Agent Detail & Governance Hero Page
 * Deloitte White Enterprise Editorial Product Architecture
 */

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { agentsApi } from "@/lib/api-client";
import { AutonomyTimeline } from "@/components/charts/AutonomyTimeline";
import { HorizontalThresholdGauge } from "@/components/charts/HorizontalThresholdGauge";
import { InvoiceCard } from "@/components/domain/InvoiceCard";
import type { AutonomyTier } from "@/types/api";

const TIER_TAG_CLASS: Record<AutonomyTier, string> = {
  low:    "tier-low",
  medium: "tier-medium",
  high:   "tier-high",
};

export default function AgentDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: agent, isLoading: agentLoading } = useQuery({
    queryKey: ["agent", id],
    queryFn: () => agentsApi.get(id),
  });

  const { data: history = [] } = useQuery({
    queryKey: ["agent-history", id],
    queryFn: () => agentsApi.getAutonomyHistory(id),
  });

  const { data: decisions } = useQuery({
    queryKey: ["agent-decisions", id],
    queryFn: () => agentsApi.getDecisions(id),
  });

  if (agentLoading) {
    return (
      <div className="editorial-content text-xs font-bold text-slate-400 uppercase tracking-widest animate-pulse">
        LOADING GOVERNANCE AGENT PROFILE...
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="editorial-content text-xs font-bold text-red-700 uppercase tracking-widest">
        GOVERNANCE RECORD NOT FOUND.
      </div>
    );
  }

  const hasClawback = history.some(e => e.is_clawback_event);

  return (
    <div>
      {/* Editorial Hero Header */}
      <div className="editorial-header">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div>
            <span className="eyebrow-label">AGENT GOVERNANCE</span>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight mt-1">
              {agent.name.split(" ")[0]}
            </h1>
            <div className="flex items-center gap-3 text-xs text-slate-500 font-mono mt-1">
              <span>{agent.agent_id}</span>
              <span>·</span>
              <span className="font-sans font-medium">gemini-2.5-flash</span>
            </div>
          </div>

          {/* Right Hero Autonomy Metric */}
          <div className="text-right">
            <span className="eyebrow-label block mb-1">CURRENT AUTONOMY</span>
            <div className="flex items-center justify-end gap-2">
              <span className="w-1.5 h-8 bg-[#86BC25] rounded-full inline-block" />
              <p className="text-4xl font-black text-slate-900 tracking-tight">
                ₹{Number(agent.current_limit).toLocaleString("en-IN")}
              </p>
            </div>
            <div className="flex items-center justify-end gap-2 mt-1.5">
              <span className={`tier-tag ${TIER_TAG_CLASS[agent.tier]}`}>
                {agent.tier.toUpperCase()}
              </span>
              {hasClawback && (
                <div className="flex items-center gap-1.5 text-xs text-red-700 font-bold bg-red-50 border border-red-200 px-2 py-0.5 rounded-[2px]">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-600 inline-block" />
                  <span>AUTONOMY CLAWED BACK</span>
                </div>
              )}
            </div>
            {hasClawback && (
              <p className="text-[11px] text-slate-500 font-medium mt-1">
                from previous limit of ₹15,000 <strong className="text-red-700">(−80% authority)</strong>
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="editorial-content space-y-8">
        {/* Horizontal Performance Band (Strip) */}
        <div className="editorial-panel grid grid-cols-2 sm:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x divide-slate-200">
          <div className="metric-strip-item">
            <span className="eyebrow-label text-[9px]">TOTAL DECISIONS</span>
            <span className="text-2xl font-black text-slate-900">{agent.total_decisions.toLocaleString()}</span>
          </div>
          <div className="metric-strip-item">
            <span className="eyebrow-label text-[9px]">ROLLING ACCURACY</span>
            <span className="text-2xl font-black text-slate-900">
              {agent.rolling_accuracy != null ? `${Math.round(agent.rolling_accuracy * 100)}%` : "—"}
            </span>
          </div>
          <div className="metric-strip-item">
            <span className="eyebrow-label text-[9px]">WILSON LOWER BOUND</span>
            <span className={`text-2xl font-black ${(agent.wilson_lower_bound ?? 0) >= 0.85 ? "text-[#5f8914]" : "text-amber-800"}`}>
              {agent.wilson_lower_bound != null ? `${Math.round(agent.wilson_lower_bound * 100)}%` : "—"}
            </span>
          </div>
          <div className="metric-strip-item bg-slate-50/60">
            <span className="eyebrow-label text-[9px]">SAFETY THRESHOLD</span>
            <span className="text-2xl font-black text-slate-700">85%</span>
          </div>
          <div className="metric-strip-item">
            <span className="eyebrow-label text-[9px]">PENDING APPROVALS</span>
            <span className={`text-2xl font-black ${agent.pending_approvals > 0 ? "text-amber-900" : "text-slate-900"}`}>
              {agent.pending_approvals}
            </span>
          </div>
        </div>

        {/* Hero Visual — How Autonomy Changed (Timeline Chart) */}
        <div className="editorial-panel p-6">
          <div className="border-b border-slate-200 pb-4 mb-4">
            <span className="eyebrow-label">GOVERNANCE TRAJECTORY</span>
            <h2 className="text-xl font-black text-slate-900 tracking-tight mt-0.5">
              How autonomy changed
            </h2>
            <p className="text-xs text-slate-500 font-medium mt-1">
              The agent's financial authority follows statistically validated performance.
            </p>
          </div>

          <AutonomyTimeline events={history} height={380} />
        </div>

        {/* Two-Column: Why Autonomy Changed & Horizontal Threshold Visualization */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Explanation Panel: Why Autonomy Changed */}
          <div className="editorial-panel p-6">
            <span className="eyebrow-label block mb-1">GOVERNANCE DIAGNOSTICS</span>
            <h3 className="text-lg font-black text-slate-900 mb-4 border-b border-slate-200 pb-2">
              Why autonomy changed
            </h3>

            <div className="space-y-4 text-xs font-sans">
              <div className="bg-red-50/80 border border-red-200 rounded-[2px] p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-extrabold text-red-900 text-xs">TRIGGER</span>
                  <span className="text-[10px] font-mono text-red-700 font-bold">WLB &lt; 85%</span>
                </div>
                <p className="text-slate-700 font-medium leading-relaxed">
                  Wilson 95% lower bound fell below the safety threshold following a hard invoice distribution shift.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs">
                <div className="bg-slate-50 border border-slate-200 p-3 rounded-[2px]">
                  <span className="eyebrow-label text-[9px] block">THRESHOLD</span>
                  <span className="text-base font-black text-slate-900">85%</span>
                </div>
                <div className="bg-slate-50 border border-slate-200 p-3 rounded-[2px]">
                  <span className="eyebrow-label text-[9px] block">OBSERVED WLB</span>
                  <span className="text-base font-black text-amber-800">79%</span>
                </div>
                <div className="bg-slate-50 border border-slate-200 p-3 rounded-[2px]">
                  <span className="eyebrow-label text-[9px] block">PREVIOUS AUTHORITY</span>
                  <span className="text-base font-black text-slate-900">₹15,000</span>
                </div>
                <div className="bg-slate-50 border border-slate-200 p-3 rounded-[2px]">
                  <span className="eyebrow-label text-[9px] block">CURRENT AUTHORITY</span>
                  <span className="text-base font-black text-red-700">₹3,000</span>
                </div>
              </div>

              <div className="border-t border-slate-200 pt-3 flex items-center justify-between text-[11px]">
                <span className="text-slate-500 font-medium">Governance Action:</span>
                <span className="font-bold text-red-700 uppercase tracking-wider">
                  AUTOMATICALLY EXECUTED
                </span>
              </div>
            </div>
          </div>

          {/* Horizontal Reliability Visual */}
          <div className="editorial-panel p-6 flex flex-col justify-between">
            <div>
              <span className="eyebrow-label block mb-1">STATISTICAL EVIDENCE</span>
              <h3 className="text-lg font-black text-slate-900 mb-4 border-b border-slate-200 pb-2">
                Reliability Position
              </h3>

              {agent.rolling_accuracy != null && agent.wilson_lower_bound != null && (
                <HorizontalThresholdGauge
                  accuracy={agent.rolling_accuracy}
                  wilsonLB={agent.wilson_lower_bound}
                />
              )}
            </div>

            <div className="bg-[#F7F8F6] border border-slate-200 p-3 rounded-[2px] text-xs text-slate-600 mt-4">
              <span className="font-bold text-slate-900 block mb-0.5">Wilson Score Interval (95%)</span>
              Lower confidence limit ensures financial authority is only granted when precision is statistically proven.
            </div>
          </div>
        </div>

        {/* Governance Event Timeline */}
        <div className="editorial-panel p-6">
          <span className="eyebrow-label block mb-1">CHRONOLOGICAL AUDIT</span>
          <h3 className="text-lg font-black text-slate-900 mb-4 border-b border-slate-200 pb-2">
            Governance Event History
          </h3>

          <div className="relative border-l-2 border-slate-200 ml-4 space-y-6 pl-6 py-2 text-xs font-sans">
            <div>
              <div className="absolute -left-[5px] w-2.5 h-2.5 rounded-full bg-[#86BC25]" />
              <span className="font-mono text-slate-400 text-[11px] block">15:11</span>
              <p className="font-bold text-slate-900 text-xs">Performance returned above threshold</p>
              <p className="text-slate-500">Rolling accuracy reached 90%, Wilson LB at 81%.</p>
            </div>
            <div>
              <div className="absolute -left-[5px] w-2.5 h-2.5 rounded-full bg-blue-500" />
              <span className="font-mono text-slate-400 text-[11px] block">14:10</span>
              <p className="font-bold text-slate-900 text-xs">Recovery phase initiated</p>
              <p className="text-slate-500">Invoice difficulty relaxed back toward baseline.</p>
            </div>
            <div>
              <div className="absolute -left-[5px] w-2.5 h-2.5 rounded-full bg-red-600" />
              <span className="font-mono text-slate-400 text-[11px] block">13:22</span>
              <p className="font-bold text-red-700 text-xs">Automatic clawback executed → ₹3,000</p>
              <p className="text-slate-500">Autonomy reduced from ₹15,000 to ₹3,000.</p>
            </div>
            <div>
              <div className="absolute -left-[5px] w-2.5 h-2.5 rounded-full bg-amber-500" />
              <span className="font-mono text-slate-400 text-[11px] block">13:21</span>
              <p className="font-bold text-slate-900 text-xs">Wilson lower bound crossed threshold (79%)</p>
              <p className="text-slate-500">Performance degraded under distribution shift.</p>
            </div>
            <div>
              <div className="absolute -left-[5px] w-2.5 h-2.5 rounded-full bg-slate-400" />
              <span className="font-mono text-slate-400 text-[11px] block">13:08</span>
              <p className="font-bold text-slate-900 text-xs">Distribution shift detected</p>
              <p className="text-slate-500">Hard invoice batch introduced into simulation stream.</p>
            </div>
            <div>
              <div className="absolute -left-[5px] w-2.5 h-2.5 rounded-full bg-[#86BC25]" />
              <span className="font-mono text-slate-400 text-[11px] block">11:42</span>
              <p className="font-bold text-[#5f8914] text-xs">Promotion granted → ₹50,000</p>
              <p className="text-slate-500">Sustained performance earned HIGH autonomy tier.</p>
            </div>
          </div>
        </div>

        {/* Recent Decisions Editorial Feed */}
        <div className="editorial-panel p-6">
          <span className="eyebrow-label block mb-1">DECISION LOG</span>
          <h3 className="text-lg font-black text-slate-900 mb-4 border-b border-slate-200 pb-2">
            Recent Decisions
          </h3>
          {decisions?.items?.length ? (
            <div className="space-y-2">
              {decisions.items.map(r => (
                <InvoiceCard key={r.record_id} record={r} />
              ))}
            </div>
          ) : (
            <p className="text-slate-500 text-xs">No decision records found.</p>
          )}
        </div>
      </div>
    </div>
  );
}
