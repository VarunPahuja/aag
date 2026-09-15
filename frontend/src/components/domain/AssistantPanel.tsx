"use client";
/**
 * src/components/domain/AssistantPanel.tsx
 * ------------------------------------------
 * The read-only assistant: a slide-over chat panel, mounted once in the root
 * layout so it is available from the home page (redirects to /agents), the
 * agents list, the agent detail page, and everywhere else in the shell.
 *
 * Everything is derived from the URL, not chosen in a dropdown. The current
 * route is sent as `page`, and the backend answers from the guide for that
 * page (backend/app/data/page_guides/): what it is for, what its numbers mean,
 * what to click. On `/agents/:id` the conversation is also agent-scoped — the
 * backend adds that one agent's evidence, and nobody else's. Switching pages
 * while the panel is open resets the conversation, so a reply is never left
 * on screen answering for a page or an agent that is no longer showing.
 *
 * This panel only ever sends a question and renders a reply. There is no
 * button here that calls a mutating endpoint, and there never should be —
 * the whole point of this feature is that the assistant reads and explains
 * but cannot act (see the banner below, and the backend's system prompt).
 */

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { agentsApi, assistantApi } from "@/lib/api-client";
import { IconAssistant } from "@/components/ui/Icons";
import type { AssistantMessage, AssistantSource } from "@/types/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: AssistantSource[];
}

interface PageHelp {
  label: string;
  starters: string[];
}

/**
 * Header label and suggested questions for each page. Display only — the
 * backend decides which guide a route gets (backend/app/services/page_guides.py),
 * so a route missing here still gets a real answer, just the fallback below.
 * The agent detail label is the agent's own name, filled in at render time.
 */
const PAGE_HELP: { pattern: RegExp; help: PageHelp }[] = [
  {
    pattern: /^\/$/,
    help: {
      label: "Welcome",
      starters: [
        "what does this system do",
        "why use the Wilson lower bound instead of accuracy",
        "how do I get to the live dashboard",
      ],
    },
  },
  {
    pattern: /^\/agents$/,
    help: {
      label: "Agents",
      starters: [
        "what does this page show",
        "what does requires attention mean",
        "how does an agent move up a rung",
      ],
    },
  },
  {
    pattern: /^\/agents\/[^/]+$/,
    help: {
      label: "Agent",
      starters: [
        "why is this agent not eligible for an increase",
        "what would it take to reach the next rung",
        "explain this agent's most recent clawback",
      ],
    },
  },
  {
    pattern: /^\/approvals$/,
    help: {
      label: "Approvals",
      starters: [
        "how do I approve a recommendation",
        "what does dissent mean",
        "what does clamped mean",
      ],
    },
  },
  {
    pattern: /^\/audit$/,
    help: {
      label: "Audit Trail",
      starters: [
        "what does the hash chain prove",
        "how do I inspect an entry",
        "what should I do if the chain shows broken",
      ],
    },
  },
  {
    pattern: /^\/simulation$/,
    help: {
      label: "Simulation",
      starters: [
        "how do I run a simulation",
        "how do I trigger a clawback",
        "what do the three phases do",
      ],
    },
  },
  {
    pattern: /^\/demo$/,
    help: {
      label: "Demo Console",
      starters: [
        "how do I run the demo",
        "what is the difference between live and replay",
        "why did beat 4 not give an increase",
      ],
    },
  },
];

const FALLBACK_HELP: PageHelp = {
  label: "System-wide",
  starters: [
    "what does this system do",
    "why use the Wilson lower bound instead of accuracy",
    "what stops the AI from raising a limit on its own",
  ],
};

function helpFor(pathname: string): PageHelp {
  const path = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  return PAGE_HELP.find(p => p.pattern.test(path))?.help ?? FALLBACK_HELP;
}

/** `/agents/:id` only — not the list page, and not a nested route under it. */
function agentIdFromPath(pathname: string): string | null {
  const match = pathname.match(/^\/agents\/([^/]+)$/);
  return match ? match[1] : null;
}

/** Pull a human-readable message out of api-client's `Error(\`API ${status} on ${path}: ${text}\`)`. */
function friendlyError(err: unknown): string {
  if (err instanceof Error) {
    const match = err.message.match(/: (\{[\s\S]*\})$/);
    if (match) {
      try {
        const body = JSON.parse(match[1]) as { message?: string };
        if (typeof body.message === "string" && body.message) return body.message;
      } catch {
        // fall through to the raw message below
      }
    }
    return err.message;
  }
  return "Something went wrong.";
}

export function AssistantPanel() {
  const pathname = usePathname() ?? "";
  const agentId = agentIdFromPath(pathname);
  const isAgentScope = agentId !== null;
  const help = helpFor(pathname);

  // Shares the query cache with the agent detail page (same queryKey) — opening
  // the panel there costs no extra request.
  const { data: agent } = useQuery({
    queryKey: ["agent", agentId],
    queryFn: () => agentsApi.get(agentId as string),
    enabled: isAgentScope,
  });

  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // The route itself: a new page is a new conversation, and an agent's id is
  // part of its route, so moving between agents resets too.
  const scopeKey = pathname;
  const prevScopeKey = useRef(scopeKey);
  useEffect(() => {
    if (prevScopeKey.current !== scopeKey) {
      prevScopeKey.current = scopeKey;
      setMessages([]);
      setError(null);
    }
  }, [scopeKey]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading, error]);

  async function send(rawText: string) {
    const question = rawText.trim();
    if (!question || loading) return;

    const history: AssistantMessage[] = [
      ...messages.map(({ role, content }) => ({ role, content })),
      { role: "user", content: question },
    ];
    setMessages(prev => [...prev, { role: "user", content: question }]);
    setInput("");
    setError(null);
    setLoading(true);
    try {
      const res = await assistantApi.chat({ messages: history, agent_id: agentId, page: pathname });
      setMessages(prev => [...prev, { role: "assistant", content: res.reply, sources: res.sources }]);
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      setLoading(false);
    }
  }

  const starters = help.starters;
  const scopeLabel = isAgentScope ? agent?.name ?? agentId : help.label;

  return (
    <>
      {/* No aria-label here — the visible <span> text below is the accessible
          name. An aria-label wins over text content for screen readers, so one
          that just paraphrased ("Open assistant") would have silently replaced
          the real, more specific label with a vaguer one. */}
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        aria-expanded={open}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-3 rounded-full bg-[#86BC25] hover:bg-[#72a31d] text-white text-xs font-bold shadow-lg transition-colors"
      >
        <IconAssistant className="w-4 h-4" />
        <span>{isAgentScope ? "Ask about this agent" : "Ask about this page"}</span>
      </button>

      {open && (
        <div
          className="fixed inset-0 bg-black/10 z-40"
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed top-0 right-0 h-screen w-full sm:w-[420px] bg-white border-l border-[#E2E8F0] shadow-2xl z-50 flex flex-col font-sans transition-transform duration-200 ease-out ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
        aria-hidden={!open}
      >
        <div className="px-5 py-4 border-b border-[#E2E8F0] flex-shrink-0">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <span className="eyebrow-label">ASSISTANT</span>
              <h2 className="text-lg font-black text-slate-900 tracking-tight truncate">
                {scopeLabel}
              </h2>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="text-slate-400 hover:text-slate-700 text-xl leading-none px-1 flex-shrink-0"
              aria-label="Close"
            >
              ×
            </button>
          </div>

          {isAgentScope && (
            <div className="mt-2 inline-flex items-center gap-1.5 px-2 py-1 rounded-[2px] bg-[#86BC25]/10 border border-[#86BC25]/30">
              <span className="w-1.5 h-1.5 rounded-full bg-[#5f8914] flex-shrink-0" />
              <span className="text-[10px] font-bold text-[#5f8914] font-mono">
                SCOPED TO {agentId}
              </span>
            </div>
          )}

          {/* Required, and the whole point of the feature: turn "an LLM in a
              governance product" from a risk into a demonstration of the design. */}
          <p className="text-[11px] text-slate-500 font-medium mt-2 leading-relaxed">
            This assistant reads and explains — it cannot approve anything, change a
            limit, or start a simulation.
          </p>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {messages.length === 0 && (
            <div className="space-y-2">
              <span className="eyebrow-label text-[9px]">TRY ASKING</span>
              {starters.map(q => (
                <button
                  key={q}
                  type="button"
                  onClick={() => send(q)}
                  className="block w-full text-left text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-[3px] px-3 py-2 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[90%] rounded-[6px] px-3 py-2 text-xs leading-relaxed ${
                  m.role === "user"
                    ? "bg-[#86BC25] text-white"
                    : "bg-slate-50 border border-slate-200 text-slate-800"
                }`}
              >
                <p className="whitespace-pre-wrap">{m.content}</p>
                {m.sources && m.sources.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-slate-200 flex flex-wrap gap-1">
                    {m.sources.map((s, j) => (
                      <span
                        key={j}
                        className="text-[9px] font-bold font-mono bg-white border border-slate-200 text-slate-500 px-1.5 py-0.5 rounded"
                        title={`${s.doc} — ${s.section}`}
                      >
                        {s.doc} — {s.section}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-slate-50 border border-slate-200 rounded-[6px] px-3 py-2 text-xs text-slate-500 flex items-center gap-2">
                <span className="w-3 h-3 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin" />
                Thinking…
              </div>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-[3px] px-3 py-2 text-xs text-red-700">
              {error}
            </div>
          )}
        </div>

        <form
          onSubmit={e => {
            e.preventDefault();
            void send(input);
          }}
          className="border-t border-[#E2E8F0] p-3 flex items-end gap-2 flex-shrink-0"
        >
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send(input);
              }
            }}
            placeholder="Ask a question…"
            rows={1}
            className="flex-1 resize-none text-xs border border-slate-200 rounded-[3px] px-3 py-2 focus:outline-none focus:border-[#86BC25]"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-3 py-2 rounded-[3px] bg-[#86BC25] hover:bg-[#72a31d] disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-bold transition-colors flex-shrink-0"
          >
            Send
          </button>
        </form>
      </aside>
    </>
  );
}
