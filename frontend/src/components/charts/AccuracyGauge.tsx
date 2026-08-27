"use client";
/**
 * src/components/charts/AccuracyGauge.tsx
 * -----------------------------------------
 * Minimal analytical reliability display for Deloitte enterprise risk UI.
 */

interface Props {
  accuracy: number;       // 0-1
  wilsonLB: number;       // 0-1
  threshold?: number;     // default 0.85
  size?: number;
}

export function AccuracyGauge({
  accuracy,
  wilsonLB,
  threshold = 0.85,
}: Props) {
  const accPct = Math.round(accuracy * 100);
  const wlbPct = Math.round(wilsonLB * 100);
  const threshPct = Math.round(threshold * 100);
  const isHealthy = wilsonLB >= threshold;

  // Minimal circular stroke calculation
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (wlbPct / 100) * circumference;

  return (
    <div className="flex items-center gap-4 bg-slate-50 border border-slate-200 rounded-md p-3">
      {/* Minimal SVG ring */}
      <div className="relative w-16 h-16 flex-shrink-0 flex items-center justify-center">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r={radius}
            stroke="#e2e8f0"
            strokeWidth="6"
            fill="transparent"
          />
          <circle
            cx="50"
            cy="50"
            r={radius}
            stroke={isHealthy ? "#86BC25" : "#ef4444"}
            strokeWidth="6"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
          />
        </svg>
        <span className="absolute text-xs font-bold text-slate-900">
          {wlbPct}%
        </span>
      </div>

      {/* Analytical details */}
      <div className="space-y-0.5 text-xs">
        <p className="font-bold text-slate-900">Current Reliability</p>
        <div className="flex items-center gap-2 text-slate-600">
          <span>Rolling Accuracy:</span>
          <span className="font-semibold text-slate-900">{accPct}%</span>
        </div>
        <div className="flex items-center gap-2 text-slate-600">
          <span>Wilson LB (95%):</span>
          <span className={`font-semibold ${isHealthy ? "text-[#5f8914]" : "text-red-700"}`}>
            {wlbPct}%
          </span>
        </div>
        <div className="flex items-center gap-2 text-slate-500 text-[11px]">
          <span>Safety Threshold:</span>
          <span className="font-medium text-slate-700">{threshPct}%</span>
        </div>
      </div>
    </div>
  );
}
