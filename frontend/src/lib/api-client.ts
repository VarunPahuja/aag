/**
 * src/lib/api-client.ts
 * ----------------------
 * Typed fetch-based API client.
 *
 * DESIGN:
 *  - JWT token read from localStorage (prototype-acceptable tradeoff, documented)
 *  - All requests go to NEXT_PUBLIC_API_BASE_URL (env var)
 *  - Money amounts travel as strings — never parsed to float
 *  - MSW intercepts all fetch calls in dev when NEXT_PUBLIC_MSW_ENABLED=true
 */

import type {
  Agent,
  AgentDecisionRecord,
  AutonomyEvent,
  HumanApproval,
  Invoice,
  PaginatedResponse,
  SimulationRunConfig,
  SimulationRunResult,
  SubmitInvoiceResponse,
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
  list: (): Promise<Agent[]> => apiFetch("/agents"),

  get: (agentId: string): Promise<Agent> =>
    apiFetch(`/agents/${agentId}`),

  getDecisions: (
    agentId: string,
    page = 1,
    pageSize = 50
  ): Promise<PaginatedResponse<AgentDecisionRecord>> =>
    apiFetch(`/agents/${agentId}/decisions?page=${page}&page_size=${pageSize}`),

  getAutonomyHistory: (agentId: string): Promise<AutonomyEvent[]> =>
    apiFetch(`/agents/${agentId}/autonomy-history`),
};

// ---------------------------------------------------------------------------
// Approvals
// ---------------------------------------------------------------------------

export const approvalsApi = {
  list: (status = "pending"): Promise<HumanApproval[]> =>
    apiFetch(`/approvals?status=${status}`),

  resolve: (
    approvalId: string,
    resolution: { status: "approved" | "rejected"; resolution_note?: string }
  ): Promise<HumanApproval> =>
    apiFetch(`/approvals/${approvalId}/resolve`, {
      method: "POST",
      body: JSON.stringify(resolution),
    }),
};

// ---------------------------------------------------------------------------
// Audit trail
// ---------------------------------------------------------------------------

export const auditApi = {
  list: (params?: {
    agent_id?: string;
    decision?: string;
    from_date?: string;
    to_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<AgentDecisionRecord>> => {
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
// Invoices
// ---------------------------------------------------------------------------

export const invoicesApi = {
  get: (invoiceId: string): Promise<Invoice> =>
    apiFetch(`/invoices/${invoiceId}`),

  submit: (
    invoice: Invoice,
    agentId: string
  ): Promise<SubmitInvoiceResponse> =>
    apiFetch("/invoices", {
      method: "POST",
      body: JSON.stringify({ invoice, agent_id: agentId }),
    }),
};

// ---------------------------------------------------------------------------
// Simulation
// ---------------------------------------------------------------------------

export const simulationApi = {
  start: (config: Partial<SimulationRunConfig>): Promise<SimulationRunResult> =>
    apiFetch("/simulation/runs", {
      method: "POST",
      body: JSON.stringify(config),
    }),

  getRun: (runId: string): Promise<SimulationRunResult> =>
    apiFetch(`/simulation/runs/${runId}`),

  listRuns: (): Promise<SimulationRunResult[]> =>
    apiFetch("/simulation/runs"),
};
