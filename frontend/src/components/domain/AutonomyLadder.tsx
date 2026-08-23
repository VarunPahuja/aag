"use client";
/**
 * src/components/domain/AutonomyLadder.tsx
 * -----------------------------------------
 * Governance Autonomy Ladder Component showing progressive authority levels.
 * Levels: ₹50,000 (HIGH), ₹15,000 (MEDIUM), ₹3,000 (LOW).
 */

import type { AutonomyTier } from "@/types/api";

interface Props {
  currentTier: AutonomyTier;
  compact?: boolean;
}

const TIER_STEPS = [
  { tier: "high" as AutonomyTier,   amount: "₹50,000", label: "HIGH AUTHORITY" },
  { tier: "medium" as AutonomyTier, amount: "₹15,000", label: "MEDIUM AUTHORITY" },
  { tier: "low" as AutonomyTier,    amount: "₹3,000",  label: "LOW AUTHORITY" },
];

export function AutonomyLadder({ currentTier, compact = false }: Props) {
  return (
    <div className={`flex flex-col gap-1.5 ${compact ? "w-44" : "w-52"}`}>
      <span className="eyebrow-label text-[9px] mb-0.5">AUTONOMY LADDER</span>
      {TIER_STEPS.map(step => {
        const isActive = step.tier === currentTier;
        return (
          <div
            key={step.tier}
            className={`flex items-center justify-between px-3 py-1.5 rounded-[2px] border text-xs transition-all ${
              isActive
                ? "bg-[#86BC25]/15 border-[#86BC25] text-[#5f8914] font-bold shadow-sm"
                : "bg-slate-50 border-slate-200 text-slate-400 font-medium"
            }`}
          >
            <span className="font-mono font-bold">{step.amount}</span>
            <span className="text-[9px] tracking-wider uppercase font-extrabold">
              {step.tier}
            </span>
          </div>
        );
      })}
    </div>
  );
}
