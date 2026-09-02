"use client";
/**
 * src/components/charts/AutonomyTimeline.tsx
 * --------------------------------------------
 * Executive Financial & Performance Autonomy Chart.
 *
 * KEY CHANGE (v1.1): Accuracy is now a shaded confidence band
 * [wilson_lower, wilson_upper] with the point estimate as a line on top.
 * The band narrows as evidence accumulates — that narrowing is what
 * unlocks the next rung. This is the single most important visualisation.
 *
 * Y-axis ticks updated from the old 3-tier limits to the five-rung ladder.
 */

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AutonomyEvent } from "@/types/api";
import { AUTONOMY_LADDER } from "@/types/api";

interface Props {
  events: AutonomyEvent[];
  height?: number;
}

function fmtTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("en-IN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function fmtLimit(val: number): string {
  if (val >= 1000) return `₹${(val / 1000).toFixed(0)}k`;
  return `₹${val}`;
}

export function AutonomyTimeline({ events, height = 400 }: Props) {
  const data = events.map(e => ({
    time: e.evaluated_at,
    timeLabel: fmtTime(e.evaluated_at),
    limit: e.current_limit,
    accuracy: e.rolling_accuracy != null ? Math.round(e.rolling_accuracy * 1000) / 10 : null,
    wilsonLower: Math.round(e.wilson_lower * 1000) / 10,
    wilsonUpper: Math.round(e.wilson_upper * 1000) / 10,
    // Recharts Area needs a [min, max] array for the band
    wilsonBand: [Math.round(e.wilson_lower * 1000) / 10, Math.round(e.wilson_upper * 1000) / 10] as [number, number],
    state: e.state,
    is_clawback: e.is_clawback_event,
    is_promotion: e.is_promotion_event,
    drift_severity: e.drift_severity,
    direction: e.direction,
    rung: e.current_rung,
  }));

  // Find annotation events
  const promotionEvt = events.find(e => e.is_promotion_event);
  const driftEvt = events.find(e => e.drift_severity === "CONFIRMED" || e.drift_severity === "CRITICAL");
  const clawbackEvt = events.find(e => e.is_clawback_event);

  // Derive label text from actual data rather than hardcoding
  const promotionLabel = promotionEvt
    ? `PROMOTION → ${fmtLimit(promotionEvt.current_limit)}`
    : "PROMOTION";
  const clawbackLabel = clawbackEvt
    ? `CLAWBACK → ${fmtLimit(clawbackEvt.current_limit)}`
    : "CLAWBACK";

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    return (
      <div className="bg-white border border-slate-300 rounded p-3 text-xs shadow-md text-slate-900 font-sans">
        <p className="font-bold text-slate-900 border-b border-slate-200 pb-1 mb-2">
          {d?.timeLabel}
        </p>
        <div className="space-y-1">
          <div className="flex justify-between gap-4">
            <span className="text-slate-600 font-medium">Autonomy Limit:</span>
            <span className="font-bold text-[#5f8914]">{fmtLimit(d?.limit)} (Rung {d?.rung})</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-slate-600 font-medium">Rolling Accuracy:</span>
            <span className="font-bold text-slate-900">{d?.accuracy}%</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-slate-600 font-medium">Wilson Band:</span>
            <span className="font-bold text-blue-700">{d?.wilsonLower}% – {d?.wilsonUpper}%</span>
          </div>
          {d?.drift_severity && d.drift_severity !== "NONE" && (
            <div className="flex justify-between gap-4">
              <span className="text-slate-600 font-medium">Drift:</span>
              <span className={`font-bold ${d.drift_severity === "CRITICAL" ? "text-red-700" : "text-amber-700"}`}>
                {d.drift_severity}
              </span>
            </div>
          )}
        </div>
        {d?.is_clawback && (
          <div className="mt-2 text-[11px] text-red-700 font-bold bg-red-50 p-1 border border-red-200 rounded">
            CLAWBACK — Autonomy reduced
          </div>
        )}
        {d?.is_promotion && (
          <div className="mt-2 text-[11px] text-[#5f8914] font-bold bg-green-50 p-1 border border-green-200 rounded">
            PROMOTION — Autonomy increased
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 15, right: 60, left: 10, bottom: 15 }}>
          <CartesianGrid strokeDasharray="2 2" stroke="#e2e8f0" vertical={false} />

          <XAxis
            dataKey="timeLabel"
            tick={{ fill: "#64748b", fontSize: 10, fontFamily: "Open Sans" }}
            tickLine={false}
            axisLine={{ stroke: "#cbd5e1" }}
            interval="preserveStartEnd"
          />

          {/* Left Y-axis: Autonomy Limit (Step Function) — five-rung ladder */}
          <YAxis
            yAxisId="limit"
            orientation="left"
            tick={{ fill: "#64748b", fontSize: 10, fontFamily: "Open Sans" }}
            tickLine={false}
            axisLine={{ stroke: "#cbd5e1" }}
            tickFormatter={fmtLimit}
            ticks={[...AUTONOMY_LADDER]}
            domain={[0, 12000]}
          />

          {/* Right Y-axis: Performance Metrics (%) */}
          <YAxis
            yAxisId="pct"
            orientation="right"
            tick={{ fill: "#64748b", fontSize: 10, fontFamily: "Open Sans" }}
            tickLine={false}
            axisLine={{ stroke: "#cbd5e1" }}
            tickFormatter={v => `${v}%`}
            ticks={[50, 60, 70, 80, 85, 90, 100]}
            domain={[50, 100]}
          />

          <Tooltip content={<CustomTooltip />} />

          <Legend
            wrapperStyle={{ color: "#334155", fontSize: 11, paddingTop: 10, fontFamily: "Open Sans" }}
          />

          {/* Governance Event vertical annotations */}
          {promotionEvt && (
            <ReferenceLine
              yAxisId="limit"
              x={fmtTime(promotionEvt.evaluated_at)}
              stroke="#86BC25"
              strokeDasharray="4 2"
              strokeWidth={1.5}
              label={{
                value: promotionLabel,
                fill: "#5f8914",
                fontSize: 9,
                position: "insideTopLeft",
                fontWeight: 700,
              }}
            />
          )}

          {driftEvt && (
            <ReferenceLine
              yAxisId="limit"
              x={fmtTime(driftEvt.evaluated_at)}
              stroke="#ef4444"
              strokeDasharray="4 2"
              strokeWidth={1.5}
              label={{
                value: `DRIFT ${driftEvt.drift_severity}`,
                fill: "#dc2626",
                fontSize: 9,
                position: "insideTopRight",
                fontWeight: 700,
              }}
            />
          )}

          {clawbackEvt && (
            <ReferenceLine
              yAxisId="limit"
              x={fmtTime(clawbackEvt.evaluated_at)}
              stroke="#b91c1c"
              strokeDasharray="2 2"
              strokeWidth={2}
              label={{
                value: clawbackLabel,
                fill: "#b91c1c",
                fontSize: 9,
                position: "insideTopLeft",
                fontWeight: 700,
              }}
            />
          )}

          {/* Safety Threshold Horizontal Line at 85% */}
          <ReferenceLine
            yAxisId="pct"
            y={85}
            stroke="#475569"
            strokeDasharray="3 3"
            strokeWidth={1}
            label={{ value: "Safety Threshold (85%)", fill: "#475569", fontSize: 9, position: "right" }}
          />

          {/* Autonomy Limit Step Area */}
          <Area
            yAxisId="limit"
            type="stepAfter"
            dataKey="limit"
            name="Autonomy Limit (INR)"
            stroke="#86BC25"
            fill="#86BC25"
            fillOpacity={0.1}
            strokeWidth={2}
          />

          {/* Wilson Confidence Band — the key visualization */}
          <Area
            yAxisId="pct"
            type="monotone"
            dataKey="wilsonBand"
            name="Wilson 95% Confidence Band"
            stroke="none"
            fill="#3b82f6"
            fillOpacity={0.15}
            connectNulls
          />

          {/* Wilson Lower Bound Line (bottom of band) */}
          <Line
            yAxisId="pct"
            type="monotone"
            dataKey="wilsonLower"
            name="Wilson Lower Bound"
            stroke="#93c5fd"
            strokeWidth={1}
            strokeDasharray="3 3"
            dot={false}
            legendType="none"
          />

          {/* Wilson Upper Bound Line (top of band) */}
          <Line
            yAxisId="pct"
            type="monotone"
            dataKey="wilsonUpper"
            name="Wilson Upper Bound"
            stroke="#93c5fd"
            strokeWidth={1}
            strokeDasharray="3 3"
            dot={false}
            legendType="none"
          />

          {/* Rolling Accuracy Point Estimate Line — on top of the band */}
          <Line
            yAxisId="pct"
            type="monotone"
            dataKey="accuracy"
            name="Rolling Accuracy"
            stroke="#0f172a"
            strokeWidth={2}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
