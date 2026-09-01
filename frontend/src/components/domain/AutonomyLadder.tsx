"use client";
/**
 * src/components/domain/AutonomyLadder.tsx
 * -----------------------------------------
 * Five-rung autonomy ladder visualization.
 * Rungs: ₹500 → ₹1,000 → ₹2,500 → ₹5,000 → ₹10,000
 */

import { AUTONOMY_LADDER } from "@/types/api";

interface Props {
  currentRung: number; // 0–4
  compact?: boolean;
}

const RUNG_LABELS = ["FLOOR", "RUNG 1", "RUNG 2", "RUNG 3", "MAX"];

function fmtLimit(val: number): string {
  if (val >= 1000) return `₹${(val / 1000).toFixed(val % 1000 === 0 ? 0 : 1)}k`;
  return `₹${val}`;
}

export function AutonomyLadder({ currentRung, compact = false }: Props) {
  return (
    <div className={`flex flex-col gap-1.5 ${compact ? "w-44" : "w-56"}`}>
      <span className="eyebrow-label text-[9px] mb-0.5">AUTONOMY LADDER</span>
      {[...AUTONOMY_LADDER].reverse().map((limit, revIdx) => {
        const rung = AUTONOMY_LADDER.length - 1 - revIdx;
        const isActive = rung === currentRung;
        const isPast = rung < currentRung;
        return (
          <div
            key={rung}
            className={`flex items-center justify-between px-3 py-1.5 rounded-[2px] border text-xs transition-all ${
              isActive
                ? `rung-tag rung-${rung} font-bold shadow-sm`
                : isPast
                ? "bg-slate-50 border-slate-200 text-slate-500 font-medium"
                : "bg-white border-slate-200 text-slate-300 font-medium"
            }`}
          >
            <span className="font-mono font-bold">{fmtLimit(limit)}</span>
            <span className="text-[9px] tracking-wider uppercase font-extrabold">
              {isActive ? "● " : ""}{RUNG_LABELS[rung]}
            </span>
          </div>
        );
      })}
    </div>
  );
}
