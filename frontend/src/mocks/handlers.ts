/**
 * src/mocks/handlers.ts
 * ----------------------
 * MSW request handlers for all 5 pages.
 * Swap to real API by setting NEXT_PUBLIC_MSW_ENABLED=false.
 */

import { http, HttpResponse } from "msw";
import {
  MOCK_AGENTS,
  MOCK_APPROVALS,
  MOCK_AUTONOMY_EVENTS,
  MOCK_DECISIONS,
  MOCK_SIMULATION_RUNS,
} from "./data";

const API = "http://localhost:8000/api/v1";

export const handlers = [
  // ── Agents ──────────────────────────────────────────────────────────────
  http.get(`${API}/agents`, () => HttpResponse.json(MOCK_AGENTS)),

  http.get(`${API}/agents/:agentId`, ({ params }) => {
    const agent = MOCK_AGENTS.find(a => a.agent_id === params.agentId);
    return agent
      ? HttpResponse.json(agent)
      : new HttpResponse(null, { status: 404 });
  }),

  http.get(`${API}/agents/:agentId/decisions`, ({ params, request }) => {
    const url = new URL(request.url);
    const page = Number(url.searchParams.get("page") ?? 1);
    const size = Number(url.searchParams.get("page_size") ?? 50);
    const items = MOCK_DECISIONS.filter(
      d => d.agent_id === params.agentId
    );
    return HttpResponse.json({
      items: items.slice((page - 1) * size, page * size),
      total: items.length,
      page,
      page_size: size,
    });
  }),

  http.get(`${API}/agents/:agentId/autonomy-history`, ({ params }) => {
    const events = MOCK_AUTONOMY_EVENTS.filter(
      e => e.agent_id === params.agentId
    );
    return HttpResponse.json(events);
  }),

  // ── Approvals ────────────────────────────────────────────────────────────
  http.get(`${API}/approvals`, ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get("status") ?? "pending";
    const items = status === "all"
      ? MOCK_APPROVALS
      : MOCK_APPROVALS.filter(a => a.status === status);
    return HttpResponse.json(items);
  }),

  http.post(`${API}/approvals/:approvalId/resolve`, async ({ params, request }) => {
    const body = await request.json() as { status: string; resolution_note?: string };
    const appr = MOCK_APPROVALS.find(a => a.approval_id === params.approvalId);
    if (!appr) return new HttpResponse(null, { status: 404 });
    const updated = {
      ...appr,
      status: body.status,
      resolved_at: new Date().toISOString(),
      resolved_by: "demo-user@company.com",
      resolution_note: body.resolution_note ?? null,
    };
    return HttpResponse.json(updated);
  }),

  // ── Audit ────────────────────────────────────────────────────────────────
  http.get(`${API}/audit`, ({ request }) => {
    const url = new URL(request.url);
    const page = Number(url.searchParams.get("page") ?? 1);
    const size = Number(url.searchParams.get("page_size") ?? 50);
    return HttpResponse.json({
      items: MOCK_DECISIONS.slice((page - 1) * size, page * size),
      total: MOCK_DECISIONS.length,
      page,
      page_size: size,
    });
  }),

  // ── Simulation ───────────────────────────────────────────────────────────
  http.get(`${API}/simulation/runs`, () =>
    HttpResponse.json(MOCK_SIMULATION_RUNS)
  ),

  http.get(`${API}/simulation/runs/:runId`, ({ params }) => {
    const run = MOCK_SIMULATION_RUNS.find(r => r.run_id === params.runId);
    return run
      ? HttpResponse.json(run)
      : new HttpResponse(null, { status: 404 });
  }),

  http.post(`${API}/simulation/runs`, async ({ request }) => {
    const config = await request.json();
    const newRun = {
      ...MOCK_SIMULATION_RUNS[0],
      run_id: `run-${Date.now()}`,
      config,
      started_at: new Date().toISOString(),
      completed_at: null,
    };
    return HttpResponse.json(newRun, { status: 201 });
  }),

  // ── Health ───────────────────────────────────────────────────────────────
  http.get("http://localhost:8000/health", () =>
    HttpResponse.json({ status: "ok" })
  ),
];
