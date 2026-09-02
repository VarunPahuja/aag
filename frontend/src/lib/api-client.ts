/**
 * src/lib/api-client.ts
 * ----------------------
 * Typed fetch-based API client — v1.1 contract-aligned.
 *
 * DESIGN:
 *  - JWT token read from localStorage (prototype-acceptable tradeoff, documented)
 *  - All requests go to NEXT_PUBLIC_API_BASE_URL (env var)
 *  - MSW intercepts all fetch calls in dev when NEXT_PUBLIC_MSW_ENABLED=true
 */

import type {
  AgentSummary,
  AutonomyEvent,
  DecisionRecord,
  TrustEvaluation,
  Recommendation,
  AuditSample,
  AuditLogEntry,
  PaginatedResponse,
} from "@/types/api";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const API_V1 = `${API_BASE}/api/v1`;

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

function getAuthHeaders(): HeadersInit {
  const token =
    typeof window !== "undefined"
      ? localStorage.getItem("aag_jwt_token")
      : null;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// ---------------------------------------------------------------------------
// Base fetch wrapper
// ---------------------------------------------------------------------------

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_V1}${path}`, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status} on ${path}: ${text}`);
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Agents
// ---------------------------------------------------------------------------

export const agentsApi = {
  list: (): Promise<AgentSummary[]> => apiFetch("/agents"),

  get: (agentId: string): Promise<AgentSummary> =>
    apiFetch(`/agents/${agentId}`),

  getDecisions: (
    agentId: string,
    page = 1,
    pageSize = 50
  ): Promise<PaginatedResponse<DecisionRecord>> =>
    apiFetch(`/agents/${agentId}/decisions?page=${page}&page_size=${pageSize}`),

  getAutonomyHistory: (agentId: string): Promise<AutonomyEvent[]> =>
    apiFetch(`/agents/${agentId}/autonomy-history`),

  getTrustEvaluation: (agentId: string): Promise<TrustEvaluation> =>
    apiFetch(`/agents/${agentId}/trust-evaluation`),
};

// ---------------------------------------------------------------------------
// Recommendations (governance opinions + human authorization)
// ---------------------------------------------------------------------------

export const recommendationsApi = {
  list: (status?: string): Promise<Recommendation[]> =>
    apiFetch(`/recommendations${status ? `?status=${status}` : ""}`),

  get: (recId: string): Promise<Recommendation> =>
    apiFetch(`/recommendations/${recId}`),

  resolve: (
    recId: string,
    resolution: { status: "APPROVED" | "REJECTED"; reason: string }
  ): Promise<Recommendation> =>
    apiFetch(`/recommendations/${recId}/resolve`, {
      method: "POST",
      body: JSON.stringify(resolution),
    }),
};

// ---------------------------------------------------------------------------
// Audit trail (decision records)
// ---------------------------------------------------------------------------

export const auditApi = {
  list: (params?: {
    agent_id?: string;
    action?: string;
    from_date?: string;
    to_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<DecisionRecord>> => {
    const qs = new URLSearchParams(
      Object.fromEntries(
        Object.entries(params ?? {})
          .filter(([, v]) => v !== undefined)
          .map(([k, v]) => [k, String(v)])
      )
    ).toString();
    return apiFetch(`/audit${qs ? `?${qs}` : ""}`);
  },
};

// ---------------------------------------------------------------------------
// Audit log (hash-chained immutable entries)
// ---------------------------------------------------------------------------

export const auditLogApi = {
  list: (params?: {
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<AuditLogEntry>> => {
    const qs = new URLSearchParams(
      Object.fromEntries(
        Object.entries(params ?? {})
          .filter(([, v]) => v !== undefined)
          .map(([k, v]) => [k, String(v)])
      )
    ).toString();
    return apiFetch(`/audit-log${qs ? `?${qs}` : ""}`);
  },
};

// ---------------------------------------------------------------------------
// Audit samples
// ---------------------------------------------------------------------------

export const auditSamplesApi = {
  list: (agentId?: string): Promise<AuditSample[]> =>
    apiFetch(`/audit-samples${agentId ? `?agent_id=${agentId}` : ""}`),
};

// ---------------------------------------------------------------------------
// Simulation
// ---------------------------------------------------------------------------

export const simulationApi = {
  start: (config: Record<string, unknown>): Promise<{ run_id: string; status: string }> =>
    apiFetch("/simulation/runs", {
      method: "POST",
      body: JSON.stringify(config),
    }),

  listRuns: (): Promise<unknown[]> =>
    apiFetch("/simulation/runs"),
};
