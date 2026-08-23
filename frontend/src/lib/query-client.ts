/**
 * src/lib/query-client.ts
 * ------------------------
 * TanStack Query client configured for 2s polling.
 */

import { QueryClient } from "@tanstack/react-query";

export function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // 2-second polling matches spec (no WebSocket)
        refetchInterval: 2_000,
        staleTime: 1_000,
        retry: 2,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

export function getQueryClient() {
  if (typeof window === "undefined") {
    // Server: new client per request
    return makeQueryClient();
  }
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}
