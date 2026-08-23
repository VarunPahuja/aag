/**
 * src/mocks/browser.ts
 * ---------------------
 * MSW browser worker setup.
 * Called once at app startup when NEXT_PUBLIC_MSW_ENABLED=true.
 */

import { setupWorker } from "msw/browser";
import { handlers } from "./handlers";

export const worker = setupWorker(...handlers);
