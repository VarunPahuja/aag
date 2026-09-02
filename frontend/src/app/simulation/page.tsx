"use client";
/**
 * Page 5: /simulation — Governance Simulation Control Room
 * v1.1 contracts: simulation progress wired to actual state (no hardcoded numbers).
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { simulationApi } from "@/lib/api-client";
import { IconSimulation } from "@/components/ui/Icons";

export default function SimulationPage() {
  const qc = useQueryClient();
  const [agentType, setAgentType] = useState<"scripted" | "llm">("scripted");
  const [count, setCount] = useState(100);

  const { data: runs = [], isLoading } = useQuery<Record<string, unknown>[]>({
    queryKey: ["simulation-runs"],
    queryFn: simulationApi.listRuns as () => Promise<Record<string, unknown>[]>,
  });

  const { mutate: startRun, isPending, data: activeRun } = useMutation<{ run_id: string; status: string }>({
    mutationFn: () =>
      simulationApi.start({
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
        {/* Configuration & Controls Panel */}
        <div className="editorial-panel p-6">
          <span className="eyebrow-label block mb-1">ENVIRONMENT CONTROLS</span>
          <h2 className="text-xl font-black text-slate-900 tracking-tight mb-4 border-b border-slate-200 pb-2">
            Simulation Setup
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
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
            <span>{isPending ? "SIMULATING..." : "LAUNCH SIMULATION"}</span>
          </button>
        </div>

        {/* Simulation Progress — honest: shows actual state, not fake numbers */}
        {isPending && (
          <div className="editorial-panel p-6 bg-[#F7F8F6] border-l-4 border-[#86BC25]">
            <div className="flex items-center justify-between mb-3">
              <span className="eyebrow-label text-slate-900">SIMULATION RUNNING</span>
              <span className="text-xs font-mono font-bold text-[#5f8914]">
                In Progress
              </span>
            </div>

            <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden mb-4">
              <div className="bg-[#86BC25] h-full animate-pulse w-full" />
            </div>

            <div className="text-xs text-slate-600 font-medium">
              Processing {count} invoices. Results will appear below when the run completes.
              Check the agent detail page for live trust evaluation updates.
            </div>
          </div>
        )}

        {/* Simulation History */}
        <div className="editorial-panel p-6">
          <span className="eyebrow-label block mb-1">HISTORICAL RUNS</span>
          <h2 className="text-xl font-black text-slate-900 tracking-tight mb-4 border-b border-slate-200 pb-2">
            Simulation History
          </h2>

          {isLoading ? (
            <div className="p-6 text-xs font-bold text-slate-400 uppercase tracking-widest animate-pulse">
              LOADING RUN HISTORY...
            </div>
          ) : runs.length === 0 ? (
            <div className="p-6 text-xs text-slate-500 font-medium text-center">
              No simulation runs yet. Launch one above.
            </div>
          ) : (
            <div className="space-y-3">
              {runs.map((run) => (
                <div key={String(run.run_id)} className="editorial-panel p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <span className="font-mono text-xs font-bold text-slate-900">{String(run.run_id)}</span>
                    <p className="text-xs text-slate-500 font-medium">
                      {String(run.status ?? "completed")}
                    </p>
                  </div>
                  <div className="text-xs text-slate-500">
                    {run.started_at ? new Date(String(run.started_at)).toLocaleString("en-IN") : "—"}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
