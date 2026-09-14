"use client";
/**
 * src/components/charts/HorizontalThresholdGauge.tsx
 * ----------------------------------------------------
 * Observed accuracy against what the evidence actually proves (the Wilson
 * lower bound), with the line the trust engine really polices.
 *
 * WHAT CHANGED, AND WHY IT MATTERED
 * ---------------------------------
 * This component used to mark a "safety threshold" at a hardcoded 85% and
 * colour the bar red or green against it. That number appears nowhere in
 * `trust/` or `backend/` — the engine has no accuracy threshold at all.
 * Promotion gates on the *trust score* (`MIN_TRUST_SCORE_FOR_INCREASE = 70`),
 * and the accuracy axis is policed by drift detection, which compares recent
 * accuracy against the agent's **own baseline** rather than any fixed line.
 *
 * So this was not a rule duplicated in the wrong place. It was a rule the
 * system does not have, drawn on screen as though it did — and it was the
 * last piece of business logic left in the frontend.
 *
 * Now: the line is `baseline − drift_accuracy_drop_pp`, both from the API, and
 * health is `drift.severity`, which the engine decided. This component derives
 * nothing. When there is no baseline yet (a young agent, where everything
 * still counts as "recent"), it says so rather than inventing a line to draw.
 */

import type { DriftResult, TrustThresholds } from "@/types/api";

interface Props {
  /** Observed accuracy, 0-1. */
  accuracy: number;
  /** Wilson lower bound on that accuracy, 0-1. */
  wilsonLB: number;
  /** The engine's drift verdict. Supplies the baseline and the health colour. */
  drift: DriftResult;
  /** The engine's gate values, from the same evaluation. */
  thresholds?: TrustThresholds;
}

export function HorizontalThresholdGauge({ accuracy, wilsonLB, drift, thresholds }: Props) {
  const accPct = Math.round(accuracy * 100);
  const wlbPct = Math.round(wilsonLB * 100);

  // Health is the engine's verdict, not ours. NONE is the only clean state:
  // WARNING means a drop was seen but could not be confirmed, and CONFIRMED
  // and CRITICAL both cost the agent a rung.
  const isHealthy = drift.severity === "NONE";

  // The real line: drift fires when recent accuracy falls this far below the
  // agent's own baseline. No baseline means no line to draw — a fact worth
  // showing rather than papering over.
  const dropPp = thresholds?.drift_accuracy_drop_pp ?? null;
  const baselinePct =
    drift.baseline_accuracy != null ? Math.round(drift.baseline_accuracy * 100) : null;
  const threshPct =
    baselinePct != null && dropPp != null ? Math.round(baselinePct - dropPp) : null;

  // Convert a percentage (50-100 domain) into a position along the track.
  const toPos = (pct: number) => Math.max(0, Math.min(100, ((pct - 50) / 50) * 100));

  const wlbPos = toPos(wlbPct);
  const threshPos = threshPct != null ? toPos(threshPct) : null;

  return (
    <div className="bg-[#F7F8F6] border border-[#E2E8F0] rounded-[2px] p-4 text-xs font-sans">
      <div className="flex items-center justify-between mb-3 border-b border-slate-200 pb-2 gap-2 flex-wrap">
        <span className="eyebrow-label text-[10px]">RELIABILITY ANALYSIS</span>
        <div className="flex items-center gap-3 font-semibold text-xs">
          <span className="text-slate-600">
            Accuracy: <strong className="text-slate-900">{accPct}%</strong>
          </span>
          <span className="text-slate-300">·</span>
          <span className="text-slate-600">
            Wilson LB:{" "}
            <strong className={isHealthy ? "text-[#5f8914]" : "text-red-700"}>{wlbPct}%</strong>
          </span>
          <span className="text-slate-300">·</span>
          <span className="text-slate-600">
            Drift: <strong className="text-slate-900">{drift.severity}</strong>
          </span>
        </div>
      </div>

      <div className="relative pt-6 pb-4 px-2">
        <div className="h-2 bg-slate-200 rounded-full w-full relative">
          <div
            className={`h-full rounded-full ${isHealthy ? "bg-[#86BC25]" : "bg-red-500"}`}
            style={{ width: `${wlbPos}%` }}
          />
        </div>

        {/* The drift line: baseline minus the engine's own drop threshold. */}
        {threshPos != null && threshPct != null && (
          <div
            className="absolute top-0 bottom-0 flex flex-col items-center"
            style={{ left: `${threshPos}%` }}
          >
            <span className="text-[9px] font-black text-slate-700 uppercase bg-slate-200 px-1 py-0.5 rounded-[2px] mb-1 whitespace-nowrap">
              DRIFT AT {threshPct}%
            </span>
            <div className="w-0.5 h-6 bg-slate-900 z-10" />
          </div>
        )}

        {/* Wilson lower bound marker. */}
        <div
          className="absolute top-1 flex flex-col items-center transform -translate-x-1/2"
          style={{ left: `${wlbPos}%` }}
        >
          <div
            className={`w-3 h-3 rounded-full border-2 border-white shadow-sm z-20 ${
              isHealthy ? "bg-[#5f8914]" : "bg-red-600"
            }`}
          />
          <span
            className={`text-[10px] font-extrabold mt-1 ${
              isHealthy ? "text-[#5f8914]" : "text-red-700"
            }`}
          >
            WLB {wlbPct}%
          </span>
        </div>
      </div>

      <div className="flex justify-between text-[9px] font-mono text-slate-400 mt-1">
        <span>50%</span>
        <span>75%</span>
        <span>100%</span>
      </div>

      <p className="text-[10px] text-slate-500 mt-2 leading-snug">
        {threshPct != null && baselinePct != null ? (
          <>
            Drift fires if recent accuracy falls {dropPp} points below this agent&apos;s baseline
            of {baselinePct}%. There is no fixed accuracy target — the bar is the agent&apos;s own
            past performance.
          </>
        ) : (
          <>
            No baseline yet: every decision so far still counts as recent, so there is nothing to
            compare against and drift cannot fire.
          </>
        )}
      </p>
    </div>
  );
}
