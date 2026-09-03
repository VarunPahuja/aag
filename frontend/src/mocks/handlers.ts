/**
 * src/mocks/handlers.ts
 * ----------------------
 * MSW request handlers — aligned to backend/openapi.json endpoints.
 * Swap to real API by setting NEXT_PUBLIC_MSW_ENABLED=false (the default).
 */

import { http, HttpResponse } from "msw";
import {
  MOCK_AGENTS,
  MOCK_POLICY_VERSIONS,
  MOCK_DECISIONS,
  MOCK_RECOMMENDATIONS,
  MOCK_TRUST_EVALUATION,
  MOCK_AUDIT_SAMPLES,
  MOCK_AUDIT_LOG,
} from "./data";

const API = "http://localhost:8000/api/v1";

function paginate<T>(items: T[], request: Request) {
  const url = new URL(request.url);
  const page = Number(url.searchParams.get("page") ?? 1);
  const size = Number(url.searchParams.get("page_size") ?? 50);
  return {
    items: items.slice((page - 1) * size, page * size),
    total: items.length,
    page,
    page_size: size,
  };
}

export const handlers = [
  // ── Agents ──────────────────────────────────────────────────────────────
  http.get(`${API}/agents`, ({ request }) =>
    HttpResponse.json(paginate(MOCK_AGENTS, request))
  ),

  http.get(`${API}/agents/:agentId`, ({ params }) => {
    const agent = MOCK_AGENTS.find(a => a.id === params.agentId);
    return agent
      ? HttpResponse.json(agent)
      : HttpResponse.json(
          { code: "not_found", message: "Agent not found", detail: null },
          { status: 404 }
        );
  }),

  // ── Trust (not /trust-evaluation) ───────────────────────────────────────
  http.get(`${API}/agents/:agentId/trust`, ({ params }) => {
    if (params.agentId === MOCK_TRUST_EVALUATION.agent_id) {
      return HttpResponse.json(MOCK_TRUST_EVALUATION);
    }
    return HttpResponse.json({
      ...MOCK_TRUST_EVALUATION,
      agent_id: params.agentId,
    });
  }),

  http.get(`${API}/agents/:agentId/trust/history`, ({ request }) =>
    HttpResponse.json(paginate([MOCK_TRUST_EVALUATION], request))
  ),

  // ── Policy versions (not /autonomy-history) ─────────────────────────────
  http.get(`${API}/agents/:agentId/policy-versions`, ({ params, request }) => {
    const versions = MOCK_POLICY_VERSIONS.filter(
      v => v.agent_id === params.agentId
    );
    return HttpResponse.json(paginate(versions, request));
  }),

  // ── Decisions ───────────────────────────────────────────────────────────
  http.get(`${API}/decisions`, ({ request }) =>
    HttpResponse.json(paginate(MOCK_DECISIONS, request))
  ),

  http.get(`${API}/decisions/:decisionId`, ({ params }) => {
    const decision = MOCK_DECISIONS.find(d => d.decision_id === params.decisionId);
    return decision
      ? HttpResponse.json(decision)
      : HttpResponse.json(
          { code: "not_found", message: "Decision not found", detail: null },
          { status: 404 }
        );
  }),

  // ── Recommendations ─────────────────────────────────────────────────────
  http.get(`${API}/recommendations`, ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get("status");
    const filtered = status
      ? MOCK_RECOMMENDATIONS.filter(r => r.status === status)
      : MOCK_RECOMMENDATIONS;
    return HttpResponse.json(paginate(filtered, request));
  }),

  http.get(`${API}/recommendations/:recId`, ({ params }) => {
    const rec = MOCK_RECOMMENDATIONS.find(r => r.recommendation_id === params.recId);
    return rec
      ? HttpResponse.json(rec)
      : HttpResponse.json(
          { code: "not_found", message: "Recommendation not found", detail: null },
          { status: 404 }
        );
  }),

  // Approve and reject are separate endpoints
  http.post(`${API}/recommendations/:recId/approve`, async ({ params, request }) => {
    const body = await request.json() as { reason: string };
    const rec = MOCK_RECOMMENDATIONS.find(r => r.recommendation_id === params.recId);
    if (!rec) {
      return HttpResponse.json(
        { code: "not_found", message: "Recommendation not found", detail: null },
        { status: 404 }
      );
    }
    if (rec.status !== "PENDING") {
      return HttpResponse.json(
        { code: "conflict", message: "Recommendation already resolved", detail: null },
        { status: 409 }
      );
    }
    return HttpResponse.json({ ...rec, status: "APPROVED" });
  }),

  http.post(`${API}/recommendations/:recId/reject`, async ({ params, request }) => {
    const body = await request.json() as { reason: string };
    const rec = MOCK_RECOMMENDATIONS.find(r => r.recommendation_id === params.recId);
    if (!rec) {
      return HttpResponse.json(
        { code: "not_found", message: "Recommendation not found", detail: null },
        { status: 404 }
      );
    }
    if (rec.status !== "PENDING") {
      return HttpResponse.json(
        { code: "conflict", message: "Recommendation already resolved", detail: null },
        { status: 409 }
      );
    }
    return HttpResponse.json({ ...rec, status: "REJECTED" });
  }),

  // ── Audit log (with chain_valid) ────────────────────────────────────────
  http.get(`${API}/audit-log`, ({ request }) => {
    const paged = paginate(MOCK_AUDIT_LOG, request);
    return HttpResponse.json({
      ...paged,
      chain_valid: true,
      chain_verified_scope: "full",
    });
  }),

  // ── Audit samples ───────────────────────────────────────────────────────
  http.get(`${API}/audit-samples`, ({ request }) => {
    const url = new URL(request.url);
    const agentId = url.searchParams.get("agent_id");
    const items = agentId
      ? MOCK_AUDIT_SAMPLES.filter(s => s.agent_id === agentId)
      : MOCK_AUDIT_SAMPLES;
    return HttpResponse.json(paginate(items, request));
  }),

  // ── Simulation ──────────────────────────────────────────────────────────
  // No GET /simulation/runs list endpoint

  http.post(`${API}/simulation/runs`, async ({ request }) => {
    const body = await request.json() as { agent_id: string; invoice_count: number; phase: string; reason: string; seed?: number };
    return HttpResponse.json({
      run_id: `run-${Date.now()}`,
      agent_id: body.agent_id,
      phase: body.phase,
      invoice_count: body.invoice_count,
      seed: body.seed ?? 42,
      status: "pending",
      started_at: new Date().toISOString(),
      completed_at: null,
      decisions_submitted: 0,
      accuracy: null,
      wilson_lower_bound: null,
    }, { status: 201 });
  }),

  http.get(`${API}/simulation/runs/:runId`, ({ params }) => {
    return HttpResponse.json({
      run_id: params.runId,
      agent_id: "agent-01",
      phase: "good",
      invoice_count: 100,
      seed: 42,
      status: "completed",
      started_at: new Date(Date.now() - 60_000).toISOString(),
      completed_at: new Date().toISOString(),
      decisions_submitted: 100,
      accuracy: 0.94,
      wilson_lower_bound: 0.88,
    });
  }),

  // ── Health ──────────────────────────────────────────────────────────────
  http.get(`${API}/health`, () =>
    HttpResponse.json({ status: "ok", schema_version: "1.1" })
  ),
];
