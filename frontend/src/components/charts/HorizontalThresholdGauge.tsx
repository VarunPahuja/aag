"use client";
/**
 * src/components/charts/HorizontalThresholdGauge.tsx
 * ----------------------------------------------------
 * Horizontal analytical threshold visualization for Deloitte AI reliability.
 * Visualizes: 50% ──── 79% (WLB) ──── 85% (Threshold) ──── 100%
 */

interface Props {
  accuracy: number;     // 0-1
  wilsonLB: number;     // 0-1
  threshold?: number;   // default 0.85
  /** Pass from backend when available. Falls back to client-side derivation. */
  isHealthy?: boolean;
}

export function HorizontalThresholdGauge({ accuracy, wilsonLB, threshold = 0.85, isHealthy: isHealthyProp }: Props) {
  const accPct = Math.round(accuracy * 100);
  const wlbPct = Math.round(wilsonLB * 100);
  const threshPct = Math.round(threshold * 100);
  const isHealthy = isHealthyProp ?? wilsonLB >= threshold;

  // Convert percentage (50 to 100 domain) into position percentage (0% to 100%)
  const toPos = (pct: number) => Math.max(0, Math.min(100, ((pct - 50) / 50) * 100));

  const wlbPos = toPos(wlbPct);
  const threshPos = toPos(threshPct);

  return (
    <div className="bg-[#F7F8F6] border border-[#E2E8F0] rounded-[2px] p-4 text-xs font-sans">
      <div className="flex items-center justify-between mb-3 border-b border-slate-200 pb-2">
        <span className="eyebrow-label text-[10px]">RELIABILITY ANALYSIS</span>
        <div className="flex items-center gap-3 font-semibold text-xs">
          <span className="text-slate-600">Accuracy: <strong className="text-slate-900">{accPct}%</strong></span>
          <span className="text-slate-300">·</span>
          <span className="text-slate-600">Wilson LB: <strong className={isHealthy ? "text-[#5f8914]" : "text-red-700"}>{wlbPct}%</strong></span>
          <span className="text-slate-300">·</span>
          <span className="text-slate-600">Threshold: <strong className="text-slate-900">{threshPct}%</strong></span>
        </div>
      </div>

      {/* Horizontal threshold track */}
      <div className="relative pt-6 pb-4 px-2">
        {/* Track bar */}
        <div className="h-2 bg-slate-200 rounded-full w-full relative">
          {/* Fill up to Wilson LB */}
          <div
            className={`h-full rounded-full ${isHealthy ? "bg-[#86BC25]" : "bg-red-500"}`}
            style={{ width: `${wlbPos}%` }}
          />
        </div>

        {/* Safety Threshold Marker (85%) */}
        <div
          className="absolute top-0 bottom-0 flex flex-col items-center"
          style={{ left: `${threshPos}%` }}
        >
          <span className="text-[9px] font-black text-slate-700 uppercase bg-slate-200 px-1 py-0.5 rounded-[2px] mb-1">
            THRESHOLD (85%)
          </span>
          <div className="w-0.5 h-6 bg-slate-900 z-10" />
        </div>

        {/* Wilson Lower Bound Marker */}
        <div
          className="absolute top-1 flex flex-col items-center transform -translate-x-1/2"
          style={{ left: `${wlbPos}%` }}
        >
          <div className={`w-3 h-3 rounded-full border-2 border-white shadow-sm z-20 ${isHealthy ? "bg-[#5f8914]" : "bg-red-600"}`} />
          <span className={`text-[10px] font-extrabold mt-1 ${isHealthy ? "text-[#5f8914]" : "text-red-700"}`}>
            WLB {wlbPct}%
          </span>
        </div>
      </div>

      <div className="flex justify-between text-[9px] font-mono text-slate-400 mt-1">
        <span>50%</span>
        <span>75%</span>
        <span>100%</span>
      </div>
    </div>
  );
}
