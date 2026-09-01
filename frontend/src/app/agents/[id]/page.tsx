"use client";
/**
 * Page 2: /agents/[id] — Agent Detail & Governance Hero Page
 * v1.1 contracts: five-rung ladder, TrustEvaluation, data-driven event history,
 * reason codes, drift, score components, sampling rate.
 */

import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { agentsApi } from "@/lib/api-client";
import { AutonomyTimeline } from "@/components/charts/AutonomyTimeline";
import { HorizontalThresholdGauge } from "@/components/charts/HorizontalThresholdGauge";
import { InvoiceCard } from "@/components/domain/InvoiceCard";
import { AutonomyLadder } from "@/components/domain/AutonomyLadder";
import {
  describeReasonCodes,
  AUTONOMY_LADDER,
  samplingRateOf,
} from "@/types/api";
import type { AgentState, AutonomyEvent } from "@/types/api";

const STATE_CLASS: Record<AgentState, string> = {
  probation:  "state-badge state-probation",
  active:     "state-badge state-active",
  restricted: "state-badge state-restricted",
  suspended:  "state-badge state-suspended",
};

function fmtLimit(val: number): string {
  if (val >= 1000) return `₹${(val / 1000).toFixed(val % 1000 === 0 ? 0 : 1)}k`;
  return `₹${val.toLocaleString("en-IN")}`;
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false,
  });
}

/** Build a data-driven governance event timeline from AutonomyEvent[] */
function buildEventTimeline(events: AutonomyEvent[]) {
  const significant = events.filter(
    e => e.is_promotion_event || e.is_clawback_event || e.drift_severity === "CONFIRMED" || e.drift_severity === "CRITICAL"
      || e.state === "restricted" || e.state === "suspended"
  );

  return significant.reverse().map(e => {
    let color = "bg-slate-400";
    let title = "";
    let description = "";

    if (e.is_clawback_event) {
      color = "bg-red-600";
      title = `Automatic clawback → ${fmtLimit(e.current_limit)}`;
      description = `Autonomy reduced to rung ${e.current_rung}. ${describeReasonCodes(e.reason_codes)}`;
    } else if (e.is_promotion_event) {
      color = "bg-[#86BC25]";
      title = `Promotion granted → ${fmtLimit(e.current_limit)}`;
      description = `Earned rung ${e.current_rung}. ${describeReasonCodes(e.reason_codes)}`;
    } else if (e.drift_severity === "CRITICAL") {
      color = "bg-red-600";
      title = "Critical drift detected";
      description = `Performance degradation severity: CRITICAL. ${describeReasonCodes(e.reason_codes)}`;
    } else if (e.drift_severity === "CONFIRMED") {
      color = "bg-amber-500";
      title = "Drift confirmed";
      description = `Performance drift confirmed. ${describeReasonCodes(e.reason_codes)}`;
    } else if (e.state === "restricted") {
      color = "bg-red-400";
      title = "Agent restricted";
      description = describeReasonCodes(e.reason_codes);
    } else {
      title = "State change";
      description = describeReasonCodes(e.reason_codes);
    }

    return { time: fmtTime(e.evaluated_at), color, title, description };
  });
}

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

  const { data: trustEval } = useQuery({
    queryKey: ["agent-trust", id],
    queryFn: () => agentsApi.getTrustEvaluation(id),
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
  const eventTimeline = buildEventTimeline(history);
  const samplingRate = samplingRateOf(agent.current_rung);

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
            </div>
            <div className="flex items-center gap-2 mt-2">
              <span className={STATE_CLASS[agent.state]}>
                {agent.state.toUpperCase()}
              </span>
              <span className={`rung-tag rung-${agent.current_rung}`}>
                RUNG {agent.current_rung}
              </span>
              {agent.drift_severity !== "NONE" && (
                <span className={`state-badge drift-${agent.drift_severity.toLowerCase()}`}>
                  DRIFT: {agent.drift_severity}
                </span>
              )}
            </div>
          </div>

          {/* Right Hero Autonomy Metric */}
          <div className="text-right">
            <span className="eyebrow-label block mb-1">CURRENT AUTONOMY</span>
            <div className="flex items-center justify-end gap-2">
              <span className="w-1.5 h-8 bg-[#86BC25] rounded-full inline-block" />
              <p className="text-4xl font-black text-slate-900 tracking-tight">
                ₹{agent.current_limit.toLocaleString("en-IN")}
              </p>
            </div>
            <div className="flex items-center justify-end gap-2 mt-1.5">
              {agent.direction !== "HOLD" && (
                <span className={`state-badge direction-${agent.direction.toLowerCase()}`}>
                  {agent.direction}
                </span>
              )}
              {agent.eligible_for_increase && (
                <span className="state-badge state-active">
                  ELIGIBLE FOR INCREASE
                </span>
              )}
              {hasClawback && (
                <div className="flex items-center gap-1.5 text-xs text-red-700 font-bold bg-red-50 border border-red-200 px-2 py-0.5 rounded-[2px]">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-600 inline-block" />
                  <span>AUTONOMY CLAWED BACK</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="editorial-content space-y-8">
        {/* Horizontal Performance Band (Strip) */}
        <div className="editorial-panel grid grid-cols-2 sm:grid-cols-6 divide-y sm:divide-y-0 sm:divide-x divide-slate-200">
          <div className="metric-strip-item">
            <span className="eyebrow-label text-[9px]">TRUST SCORE</span>
            <span className="text-2xl font-black text-slate-900">{agent.trust_score.toFixed(1)}</span>
          </div>
          <div className="metric-strip-item">
            <span className="eyebrow-label text-[9px]">TOTAL DECISIONS</span>
            <span className="text-2xl font-black text-slate-900">{agent.total_decisions.toLocaleString()}</span>
          </div>
          <div className="metric-strip-item">
            <span className="eyebrow-label text-[9px]">ACCURACY</span>
            <span className="text-2xl font-black text-slate-900">
              {agent.rolling_accuracy != null ? `${Math.round(agent.rolling_accuracy * 100)}%` : "—"}
            </span>
          </div>
          <div className="metric-strip-item">
            <span className="eyebrow-label text-[9px]">WILSON BAND</span>
            <span className="text-2xl font-black text-blue-700">
              {agent.wilson_lower != null && agent.wilson_upper != null
                ? `${Math.round(agent.wilson_lower * 100)}–${Math.round(agent.wilson_upper * 100)}%`
                : "—"}
            </span>
          </div>
          <div className="metric-strip-item">
            <span className="eyebrow-label text-[9px]">SAMPLING RATE</span>
            <span className="text-2xl font-black text-slate-900">{Math.round(samplingRate * 100)}%</span>
          </div>
          <div className="metric-strip-item">
            <span className="eyebrow-label text-[9px]">PENDING</span>
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
              The shaded band narrows as evidence accumulates — that narrowing unlocks higher rungs.
            </p>
          </div>

          <AutonomyTimeline events={history} height={380} />
        </div>

        {/* Two-Column: Why Autonomy Changed & Horizontal Threshold Visualization */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Explanation Panel: Why Autonomy Changed — data-driven from reason codes */}
          <div className="editorial-panel p-6">
            <span className="eyebrow-label block mb-1">GOVERNANCE DIAGNOSTICS</span>
            <h3 className="text-lg font-black text-slate-900 mb-4 border-b border-slate-200 pb-2">
              Why autonomy changed
            </h3>

            <div className="space-y-4 text-xs font-sans">
              {trustEval && trustEval.reason_codes.length > 0 ? (
                <>
                  <div className={`${trustEval.direction === "CLAWBACK" ? "bg-red-50/80 border-red-200" : trustEval.direction === "INCREASE" ? "bg-green-50/80 border-green-200" : "bg-slate-50 border-slate-200"} border rounded-[2px] p-4`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className={`font-extrabold text-xs ${trustEval.direction === "CLAWBACK" ? "text-red-900" : trustEval.direction === "INCREASE" ? "text-green-900" : "text-slate-900"}`}>
                        {trustEval.direction}
                      </span>
                      <span className={`state-badge direction-${trustEval.direction.toLowerCase()}`}>
                        {trustEval.direction}
                      </span>
                    </div>
                    <p className="text-slate-700 font-medium leading-relaxed">
                      {describeReasonCodes(trustEval.reason_codes)}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div className="bg-slate-50 border border-slate-200 p-3 rounded-[2px]">
                      <span className="eyebrow-label text-[9px] block">CURRENT LIMIT</span>
                      <span className="text-base font-black text-slate-900">{fmtLimit(trustEval.current_limit)}</span>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 p-3 rounded-[2px]">
                      <span className="eyebrow-label text-[9px] block">RECOMMENDED</span>
                      <span className="text-base font-black text-slate-900">{fmtLimit(trustEval.recommended_limit)}</span>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 p-3 rounded-[2px]">
                      <span className="eyebrow-label text-[9px] block">ELIGIBLE</span>
                      <span className={`text-base font-black ${trustEval.eligible_for_increase ? "text-[#5f8914]" : "text-slate-500"}`}>
                        {trustEval.eligible_for_increase ? "YES" : "NO"}
                      </span>
                    </div>
                    <div className="bg-slate-50 border border-slate-200 p-3 rounded-[2px]">
                      <span className="eyebrow-label text-[9px] block">SINCE LAST CHANGE</span>
                      <span className="text-base font-black text-slate-900">{trustEval.decisions_since_last_change}</span>
                    </div>
                  </div>

                  {/* Reason codes as individual tags */}
                  <div className="flex flex-wrap gap-1.5 pt-2">
                    {trustEval.reason_codes.map(code => (
                      <span key={code} className="px-2 py-0.5 text-[10px] font-bold font-mono bg-slate-100 text-slate-700 rounded border border-slate-200">
                        {code}
                      </span>
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-slate-500">No diagnostics available.</p>
              )}
            </div>
          </div>

          {/* Horizontal Reliability Visual */}
          <div className="editorial-panel p-6 flex flex-col justify-between">
            <div>
              <span className="eyebrow-label block mb-1">STATISTICAL EVIDENCE</span>
              <h3 className="text-lg font-black text-slate-900 mb-4 border-b border-slate-200 pb-2">
                Reliability Position
              </h3>

              {agent.rolling_accuracy != null && agent.wilson_lower != null && (
                <HorizontalThresholdGauge
                  accuracy={agent.rolling_accuracy}
                  wilsonLB={agent.wilson_lower}
                />
              )}
            </div>

            {/* Trust score component breakdown */}
            {trustEval && trustEval.components.length > 0 && (
              <div className="mt-4">
                <span className="eyebrow-label block text-[9px] mb-2">SCORE COMPONENTS</span>
                <div className="space-y-1.5">
                  {trustEval.components.map(comp => (
                    <div key={comp.name} className="flex items-center justify-between text-xs bg-slate-50 border border-slate-200 px-3 py-1.5 rounded-[2px]">
                      <span className="font-semibold text-slate-700 capitalize">{comp.name.replace(/_/g, " ")}</span>
                      <div className="flex items-center gap-3">
                        <span className="text-slate-500 text-[10px]">w={comp.effective_weight.toFixed(2)}</span>
                        <span className="font-bold text-slate-900">
                          {comp.value != null ? `${Math.round(comp.value * 100)}%` : "—"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
                {trustEval.weights_renormalised && (
                  <p className="text-[10px] text-amber-700 font-medium mt-1">
                    ⚠ Weights renormalised (some components unavailable)
                  </p>
                )}
              </div>
            )}

            {/* Drift section */}
            {trustEval && trustEval.drift.detected && (
              <div className="mt-4 bg-amber-50 border border-amber-200 p-3 rounded-[2px]">
                <span className="eyebrow-label block text-[9px] text-amber-900 mb-1">DRIFT DETECTED</span>
                <div className="flex items-center gap-4 text-xs">
                  <div>
                    <span className="text-slate-600">Recent: </span>
                    <span className="font-bold text-slate-900">
                      {trustEval.drift.recent_accuracy != null ? `${Math.round(trustEval.drift.recent_accuracy * 100)}%` : "—"}
                    </span>
                  </div>
                  <span className="text-slate-300">vs</span>
                  <div>
                    <span className="text-slate-600">Baseline: </span>
                    <span className="font-bold text-slate-900">
                      {trustEval.drift.baseline_accuracy != null ? `${Math.round(trustEval.drift.baseline_accuracy * 100)}%` : "—"}
                    </span>
                  </div>
                  <span className={`state-badge drift-${trustEval.drift.severity.toLowerCase()}`}>
                    {trustEval.drift.severity}
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Autonomy Ladder + Sampling Rate */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="editorial-panel p-6">
            <AutonomyLadder currentRung={agent.current_rung} />
          </div>
          <div className="editorial-panel p-6 lg:col-span-2">
            <span className="eyebrow-label block mb-1">AUDIT SAMPLING</span>
            <h3 className="text-lg font-black text-slate-900 mb-4 border-b border-slate-200 pb-2">
              Review burden by rung
            </h3>
            <p className="text-xs text-slate-600 mb-3">
              As an agent climbs the ladder, its autonomous decisions are sampled at a lower rate. This shrinking review burden is the system's ROI.
            </p>
            <div className="grid grid-cols-5 gap-2">
              {AUTONOMY_LADDER.map((limit, rung) => (
                <div
                  key={rung}
                  className={`text-center p-3 rounded-[2px] border ${rung === agent.current_rung ? `rung-tag rung-${rung}` : "bg-slate-50 border-slate-200"}`}
                >
                  <span className="block text-[10px] font-bold text-slate-600">{fmtLimit(limit)}</span>
                  <span className="block text-lg font-black text-slate-900 mt-1">{Math.round(samplingRateOf(rung) * 100)}%</span>
                  <span className="block text-[9px] text-slate-500">sampled</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Governance Event Timeline — data-driven from AutonomyEvent[] */}
        {eventTimeline.length > 0 && (
          <div className="editorial-panel p-6">
            <span className="eyebrow-label block mb-1">CHRONOLOGICAL AUDIT</span>
            <h3 className="text-lg font-black text-slate-900 mb-4 border-b border-slate-200 pb-2">
              Governance Event History
            </h3>

            <div className="relative border-l-2 border-slate-200 ml-4 space-y-6 pl-6 py-2 text-xs font-sans">
              {eventTimeline.map((evt, i) => (
                <div key={i} className="relative">
                  <div className={`absolute -left-[29px] w-2.5 h-2.5 rounded-full ${evt.color}`} />
                  <span className="font-mono text-slate-400 text-[11px] block">{evt.time}</span>
                  <p className="font-bold text-slate-900 text-xs">{evt.title}</p>
                  <p className="text-slate-500">{evt.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Decisions Editorial Feed */}
        <div className="editorial-panel p-6">
          <span className="eyebrow-label block mb-1">DECISION LOG</span>
          <h3 className="text-lg font-black text-slate-900 mb-4 border-b border-slate-200 pb-2">
            Recent Decisions
          </h3>
          {decisions?.items?.length ? (
            <div className="space-y-2">
              {decisions.items.map(r => (
                <InvoiceCard key={r.decision_id} record={r} />
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
