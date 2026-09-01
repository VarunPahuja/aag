/**
 * src/mocks/handlers.ts
 * ----------------------
 * MSW request handlers — v1.1 contract-aligned.
 * Swap to real API by setting NEXT_PUBLIC_MSW_ENABLED=false.
 */

import { http, HttpResponse } from "msw";
import {
  MOCK_AGENTS,
  MOCK_AUTONOMY_EVENTS,
  MOCK_DECISIONS,
  MOCK_RECOMMENDATIONS,
  MOCK_TRUST_EVALUATION,
  MOCK_AUDIT_SAMPLES,
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

  // ── Trust evaluation ────────────────────────────────────────────────────
  http.get(`${API}/agents/:agentId/trust-evaluation`, ({ params }) => {
    if (params.agentId === MOCK_TRUST_EVALUATION.agent_id) {
      return HttpResponse.json(MOCK_TRUST_EVALUATION);
    }
    // Return a default evaluation for other agents
    return HttpResponse.json({
      ...MOCK_TRUST_EVALUATION,
      agent_id: params.agentId,
    });
  }),

  // ── Recommendations (replaces old approvals) ────────────────────────────
  http.get(`${API}/recommendations`, ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get("status");
    if (status && status !== "all") {
      return HttpResponse.json(
        MOCK_RECOMMENDATIONS.filter(r => r.status === status)
      );
    }
    return HttpResponse.json(MOCK_RECOMMENDATIONS);
  }),

  http.get(`${API}/recommendations/:recId`, ({ params }) => {
    const rec = MOCK_RECOMMENDATIONS.find(r => r.recommendation_id === params.recId);
    return rec
      ? HttpResponse.json(rec)
      : new HttpResponse(null, { status: 404 });
  }),

  http.post(`${API}/recommendations/:recId/resolve`, async ({ params, request }) => {
    const body = await request.json() as { status: string; reason: string };
    const rec = MOCK_RECOMMENDATIONS.find(r => r.recommendation_id === params.recId);
    if (!rec) return new HttpResponse(null, { status: 404 });
    const updated = {
      ...rec,
      status: body.status,
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

  // ── Audit samples ───────────────────────────────────────────────────────
  http.get(`${API}/audit-samples`, ({ request }) => {
    const url = new URL(request.url);
    const agentId = url.searchParams.get("agent_id");
    const items = agentId
      ? MOCK_AUDIT_SAMPLES.filter(s => s.agent_id === agentId)
      : MOCK_AUDIT_SAMPLES;
    return HttpResponse.json(items);
  }),

  // ── Simulation ───────────────────────────────────────────────────────────
  http.get(`${API}/simulation/runs`, () =>
    HttpResponse.json([])
  ),

  http.post(`${API}/simulation/runs`, async () => {
    return HttpResponse.json({
      run_id: `run-${Date.now()}`,
      status: "running",
      started_at: new Date().toISOString(),
    }, { status: 201 });
  }),

  // ── Health ───────────────────────────────────────────────────────────────
  http.get("http://localhost:8000/health", () =>
    HttpResponse.json({ status: "ok" })
  ),
];
