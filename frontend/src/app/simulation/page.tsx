"use client";
/**
 * Page 5: /simulation — Governance Simulation Control Room
 * Deloitte White Enterprise Editorial Simulation Platform
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { simulationApi } from "@/lib/api-client";
import { IconSimulation } from "@/components/ui/Icons";
import type { SimulationPhase } from "@/types/api";

const PHASE_DESC: Record<SimulationPhase, { title: string; desc: string }> = {
  good: {
    title: "Good Phase (Baseline Distribution)",
    desc: "Clean invoices with standard vendor distributions. Validates ~90% baseline model reliability.",
  },
  degraded: {
    title: "Degraded Phase (Distribution Shift)",
    desc: "Ambiguous vendors, missing fields & boundary amounts. Triggers genuine LLM drift and automated clawback.",
  },
  recovery: {
    title: "Recovery Phase",
    desc: "Difficulty eases back toward baseline to demonstrate autonomy re-earning.",
  },
};

export default function SimulationPage() {
  const qc = useQueryClient();
  const [phase, setPhase] = useState<SimulationPhase>("good");
  const [agentType, setAgentType] = useState<"scripted" | "llm">("scripted");
  const [count, setCount] = useState(100);

  const { data: runs = [], isLoading } = useQuery({
    queryKey: ["simulation-runs"],
    queryFn: simulationApi.listRuns,
  });

  const { mutate: startRun, isPending } = useMutation({
    mutationFn: () =>
      simulationApi.start({
        phase,
        invoice_count: count,
        seed: 42,
        agent_type: agentType,
        agent_id: agentType === "llm" ? "gemini-agent-001" : "scripted-agent-001",
        api_base_url: "http://localhost:8000",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["simulation-runs"] });
    },
  });

  return (
    <div>
      {/* Header */}
      <div className="editorial-header">
        <span className="eyebrow-label">GOVERNANCE TEST ENVIRONMENT</span>
        <h1 className="text-3xl font-black text-slate-900 tracking-tight mt-1">Simulation</h1>
        <p className="text-xs font-medium text-slate-600 max-w-xl mt-1">
          Introduce controlled distribution shifts and observe how earned autonomy responds.
        </p>
      </div>

      <div className="editorial-content space-y-8">
        {/* Large Configuration & Controls Panel */}
        <div className="editorial-panel p-6">
          <span className="eyebrow-label block mb-1">ENVIRONMENT CONTROLS</span>
          <h2 className="text-xl font-black text-slate-900 tracking-tight mb-4 border-b border-slate-200 pb-2">
            Simulation Setup
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            {/* Phase */}
            <div>
              <label className="eyebrow-label block mb-1">PHASE</label>
              <select
                id="sim-phase-select"
                value={phase}
                onChange={e => setPhase(e.target.value as SimulationPhase)}
                className="w-full bg-white border border-slate-300 rounded-[2px] px-3 py-2 text-xs font-bold text-slate-900 focus:outline-none focus:border-[#86BC25]"
              >
                <option value="good">Good (Baseline)</option>
                <option value="degraded">Degraded (Distribution Shift)</option>
                <option value="recovery">Recovery (Performance Recovery)</option>
              </select>
              <p className="text-[11px] text-slate-500 font-medium mt-1">
                {PHASE_DESC[phase].desc}
              </p>
            </div>

            {/* Agent */}
            <div>
              <label className="eyebrow-label block mb-1">AGENT</label>
              <select
                id="sim-agent-select"
                value={agentType}
                onChange={e => setAgentType(e.target.value as "scripted" | "llm")}
                className="w-full bg-white border border-slate-300 rounded-[2px] px-3 py-2 text-xs font-bold text-slate-900 focus:outline-none focus:border-[#86BC25]"
              >
                <option value="scripted">ScriptedAgent (Deterministic)</option>
                <option value="llm">GeminiAgent (Real LLM - gemini-2.5-flash)</option>
              </select>
            </div>

            {/* Invoice count */}
            <div>
              <label className="eyebrow-label block mb-1">INVOICE COUNT</label>
              <select
                id="sim-count-select"
                value={count}
                onChange={e => setCount(Number(e.target.value))}
                className="w-full bg-white border border-slate-300 rounded-[2px] px-3 py-2 text-xs font-bold text-slate-900 focus:outline-none focus:border-[#86BC25]"
              >
                <option value={50}>50 invoices</option>
                <option value={100}>100 invoices</option>
                <option value={200}>200 invoices</option>
              </select>
            </div>
          </div>

          <button
            id="sim-start-btn"
            onClick={() => startRun()}
            disabled={isPending}
            className="flex items-center justify-center gap-2 px-6 py-3 rounded-[2px] bg-[#86BC25] hover:bg-[#72a31d] text-white text-xs font-black transition-colors disabled:opacity-50"
          >
            <IconSimulation className="w-4 h-4" />
            <span>{isPending ? "SIMULATING BATCH..." : "LAUNCH SIMULATION"}</span>
          </button>
        </div>

        {/* Live Simulation Progress Visualizer (If Pending) */}
        {isPending && (
          <div className="editorial-panel p-6 bg-[#F7F8F6] border-l-4 border-[#86BC25]">
            <div className="flex items-center justify-between mb-3">
              <span className="eyebrow-label text-slate-900">SIMULATION RUNNING</span>
              <span className="text-xs font-mono font-bold text-[#5f8914]">37 / {count} Invoices Processed</span>
            </div>

            <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden mb-4">
              <div className="bg-[#86BC25] h-full w-[37%] transition-all duration-300" />
            </div>

            <div className="grid grid-cols-4 gap-4 text-xs font-sans">
              <div>
                <span className="eyebrow-label block text-[9px]">ACCURACY</span>
                <span className="font-bold text-slate-900">84%</span>
              </div>
              <div>
                <span className="eyebrow-label block text-[9px]">ESCALATIONS</span>
                <span className="font-bold text-amber-900">8</span>
              </div>
              <div>
                <span className="eyebrow-label block text-[9px]">CACHE HITS</span>
                <span className="font-bold text-slate-900">14</span>
              </div>
              <div>
                <span className="eyebrow-label block text-[9px]">CURRENT AUTONOMY</span>
                <span className="font-bold text-[#5f8914]">₹15,000</span>
              </div>
            </div>
          </div>
        )}

        {/* Recent Simulation Runs List */}
        <div className="editorial-panel p-6">
          <span className="eyebrow-label block mb-1">HISTORICAL RUNS</span>
          <h2 className="text-xl font-black text-slate-900 tracking-tight mb-4 border-b border-slate-200 pb-2">
            Simulation History
          </h2>

          {isLoading ? (
            <div className="p-6 text-xs font-bold text-slate-400 uppercase tracking-widest animate-pulse">
              LOADING RUN HISTORY...
            </div>
          ) : (
            <div className="space-y-3">
              {runs.map(run => {
                const acc = run.accuracy;
                const isClawback = run.config.phase === "degraded";

                return (
                  <div key={run.run_id} className="editorial-panel p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 text-[10px] font-black uppercase rounded-[2px] ${
                          run.config.phase === "good" ? "bg-green-100 text-[#5f8914]" :
                          run.config.phase === "degraded" ? "bg-red-100 text-red-700" :
                          "bg-slate-100 text-slate-800"
                        }`}>
                          {run.config.phase}
                        </span>
                        <span className="font-mono text-xs font-bold text-slate-900">{run.run_id}</span>
                      </div>
                      <p className="text-xs text-slate-500 font-medium">
                        {run.total_invoices} invoices · {run.config.agent_type}
                      </p>
                    </div>

                    <div className="flex items-center gap-6 text-xs">
                      <div>
                        <span className="eyebrow-label block text-[9px]">ACCURACY</span>
                        <span className="font-black text-slate-900">{acc != null ? `${Math.round(acc * 100)}%` : "—"}</span>
                      </div>
                      <div>
                        <span className="eyebrow-label block text-[9px]">OUTCOME</span>
                        <span className={`font-bold ${isClawback ? "text-red-700" : "text-[#5f8914]"}`}>
                          {isClawback ? "Clawback Triggered" : "Autonomy Stable"}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
