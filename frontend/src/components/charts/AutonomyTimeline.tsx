"use client";
/**
 * src/components/charts/AutonomyTimeline.tsx
 * --------------------------------------------
 * Executive Financial & Performance Autonomy Chart.
 * Clean, restrained Deloitte design system.
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
    limit: parseFloat(e.limit_amount),
    accuracy: Math.round(e.rolling_accuracy * 1000) / 10,
    wilson: Math.round(e.wilson_lower_bound * 1000) / 10,
    phase: e.phase,
    is_clawback: e.is_clawback_event,
    is_promotion: e.is_promotion_event,
    drift: e.drift_direction,
  }));

  const driftEvt = events.find(e => e.drift_direction === "degrading");
  const clawbackEvt = events.find(e => e.is_clawback_event);
  const promotionEvt = events.find(e => e.is_promotion_event);

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
            <span className="font-bold text-[#5f8914]">{fmtLimit(d?.limit)}</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-slate-600 font-medium">Rolling Accuracy:</span>
            <span className="font-bold text-slate-900">{d?.accuracy}%</span>
          </div>
          <div className="flex justify-between gap-4">
            <span className="text-slate-600 font-medium">Wilson Lower Bound:</span>
            <span className="font-bold text-amber-700">{d?.wilson}%</span>
          </div>
        </div>
        {d?.is_clawback && (
          <div className="mt-2 text-[11px] text-red-700 font-bold bg-red-50 p-1 border border-red-200 rounded">
            CLAWBACK: ₹15,000 → ₹3,000
          </div>
        )}
        {d?.is_promotion && (
          <div className="mt-2 text-[11px] text-[#5f8914] font-bold bg-green-50 p-1 border border-green-200 rounded">
            PROMOTION: ₹3,000 → ₹15,000
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

          {/* Left Y-axis: Autonomy Limit (Step Function) */}
          <YAxis
            yAxisId="limit"
            orientation="left"
            tick={{ fill: "#64748b", fontSize: 10, fontFamily: "Open Sans" }}
            tickLine={false}
            axisLine={{ stroke: "#cbd5e1" }}
            tickFormatter={fmtLimit}
            ticks={[0, 3000, 15000, 50000]}
            domain={[0, 55000]}
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
                value: "PROMOTION (₹3k→₹15k)",
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
                value: "DRIFT DETECTED (Shift)",
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
                value: "CLAWBACK (₹15k→₹3k)",
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

          {/* Rolling Accuracy Line */}
          <Line
            yAxisId="pct"
            type="monotone"
            dataKey="accuracy"
            name="Rolling Accuracy"
            stroke="#0f172a"
            strokeWidth={2}
            dot={false}
          />

          {/* Wilson Lower Bound Line */}
          <Line
            yAxisId="pct"
            type="monotone"
            dataKey="wilson"
            name="Wilson Lower Bound (95%)"
            stroke="#d97706"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
