# Assistant: page guides — integration notes

For Varun P. (backend owner) and Adhya (frontend owner). Written with `vc/page-guides`.
Every command below was run on that branch before this was written.

## What changed, in one paragraph

The assistant used to answer from a keyword search over `docs/` (`doc_index.py`), with
an embedding index (`assistant/`) waiting to replace it. Neither fits what users
actually ask, which is *"how do I use this screen?"*. Now the chat panel sends the route
the user is on, and the backend puts a hand-written guide for that page into the prompt,
plus a short system overview included every time. There's no search, no embeddings,
no index to rebuild, and no model call beyond the chat model itself.

```
browser (AssistantPanel)            backend                                   model
  usePathname() ──page──▶ POST /api/v1/assistant/chat
                            page_for_route(page) ── allowlist ──▶ "approvals"
                            load approvals.md + overview.md
                            + agent evidence if agent_id set ─────────────▶ generate_text()
```

## Backend

### Files

| File | Role |
|---|---|
| `backend/app/data/page_guides/*.md` | One guide per frontend page, plus `overview.md`. Plain markdown, first line `# Title`. |
| `backend/app/services/page_guides.py` | `ROUTES` (route regex → guide id), `page_for_route()`, `guides_for_route()`. |
| `backend/app/services/assistant.py` | `build_general_context(page)` / `build_agent_context(db, agent, page)`. The system prompt now tells the model to help with the current page. |
| `backend/app/schemas/assistant.py` | `AssistantChatRequest.page: str \| None` (max 200 chars). |
| `backend/tests/test_page_guides.py` | Fails if a frontend `page.tsx` has no guide, or a guide file has no route. |

### The request

```http
POST /api/v1/assistant/chat
{
  "messages": [{"role": "user", "content": "how do I approve this?"}],
  "agent_id": null,
  "page": "/approvals"
}
```

```json
{
  "reply": "…",
  "sources": [
    {"doc": "Page guide", "section": "Approvals"},
    {"doc": "Page guide", "section": "Overview — how the whole system works"}
  ]
}
```

- `page` is optional and backwards compatible. If it's missing or unknown, the model gets
  the overview only.
- `page` is untrusted, because the browser supplies it. It only *selects* a guide from
  `ROUTES`, and the raw string is never put in the prompt.
  `test_an_unknown_page_gets_the_overview_and_its_route_never_reaches_the_prompt` pins that.
- On `/agents/{id}`, send both `page` and `agent_id`. You get the agent-detail guide plus
  that one agent's evidence, the same as before.

### Provider: Azure `gpt-4.1-mini` (PR #51)

#51 merged into `vp/ci-assistant-lane`, **not into `main`**. To use it:

1. Rebase `vp/ci-assistant-lane` onto `main`. #50, which it was based on, is already on main,
   so only the Azure commit is new. If you take the deletions below first, drop the
   `assistant/` test hunks from that branch rather than resolving them.
2. Set these in the deployment environment (Render dashboard or `render.yaml`) and in `.env`:
   ```
   GOVERNANCE_PROVIDER_ASSISTANT=azure-openai
   AZURE_OPENAI_API_KEY=…
   AZURE_OPENAI_ENDPOINT=https://…/openai/v1/responses
   AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
   ASSISTANT_MODE=live
   ```
3. The chat no longer needs a Gemini key at all. Page guides need no embeddings.
   `GEMINI_API_KEY` is still needed by the governance panel if it runs live.

### Modes and recordings

- `ASSISTANT_MODE=live` (default) calls the provider. On failure it falls back to a
  recording, and if there's no recording it returns 503.
- `ASSISTANT_MODE=cached` only replays recordings. The prompt version is now `v2` and the
  six `v1` recordings were deleted, because nothing could ever match them again. To have
  cached replies for a demo, run each demo question once in `live` mode: every successful
  live answer is saved to `backend/app/data/assistant_recordings/` automatically.
- Editing a guide changes the prompt, so its old recordings stop matching. That's
  deliberate: a stale recording would answer from the old guide.

### Verify

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_assistant.py backend/tests/test_page_guides.py -q
.\.venv\Scripts\python.exe -m backend.app.export_openapi   # openapi.json must not change
```

## Frontend (TypeScript)

### What's wired

- **`frontend/src/app/layout.tsx`** mounts `<AssistantPanel />` inside `<Providers>` again.
  **#46 dropped it** when it moved the sidebar into `(dashboard)/layout.tsx`, so the
  assistant was unreachable from 13 Sept until this branch. It's in the root layout so the
  landing page and `/demo` get it too, since both sit outside the `(dashboard)` group.
- **`AssistantPanel.tsx`**:
  - sends `page: usePathname()` with every question, next to `agent_id`
  - resets the conversation when the route changes
  - shows a per-page header label and three suggested questions (`PAGE_HELP`)
- **`types/api.ts`**: `AssistantChatRequest.page?: string | null`.
- **`types/generated.ts`** is regenerated from `backend/openapi.json`.
- **`mocks/handlers.ts`**: the MSW mock returns page-guide sources.

### After any backend schema change

```powershell
.\.venv\Scripts\python.exe -m backend.app.export_openapi
cd frontend; npm run gen:api; npm run typecheck; npm run build
```

`types/api.ts` is hand-written, so mirror any new field there too. `npm run typecheck`
won't catch a mismatch between the two files, because nothing in `frontend/src` imports
`generated.ts` at all. Everything uses `types/api.ts`.

### Adding or renaming a page

Three places, all in the same PR:

1. `backend/app/data/page_guides/<id>.md`: a new guide, first line `# Title`.
2. `backend/app/services/page_guides.py`: add `(re.compile(r"^/your-route$"), "<id>")` to `ROUTES`.
3. `frontend/src/components/domain/AssistantPanel.tsx`: add a `PAGE_HELP` entry (label
   and starter questions). This is optional, and the page falls back to "System-wide" if
   you skip it.

Skipping steps 1 and 2 fails `test_every_frontend_page_has_a_guide` in CI. That's
intentional. When a page's UI changes (a button renamed, a field added), update its guide
in the same PR. The system prompt tells the model to describe only controls the guide
mentions, so an out-of-date guide means an out-of-date answer, not an invented one.

## What can be deleted now

Nothing below is imported by the backend or the frontend: `grep` for `from assistant` /
`import assistant` outside `assistant/` finds nothing. It's all left for a separate PR
so this one stays reviewable.

| Delete | Why it's safe |
|---|---|
| `assistant/` (the whole package, including the 1.2 MB `index.json` and `tests/query_vectors.json`) | The embedding retrieval index from #49. Nothing calls it, and it has been stale since #48. |
| `.github/workflows/ci.yml`: steps "Install assistant/", "pytest - assistant/", "assistant index is current with the docs" (including its `continue-on-error`), and `assistant/` in the `ruff check` line | They only exist for the package above. This also removes #50's three skipped tests with it. |
| `Makefile`: the `assistant/tests` pytest line, and `assistant/` in `lint` / `fmt` | Same. |
| `governance/governance/llm/gemini.py`: `GeminiEmbeddingClient` (from line 488) | Only `assistant/` used it. This is the governance lane, so Varun C. removes it. **Keep** the `_retry_after` RetryInfo fix added alongside it, because it fixes 429 back-off on the chat path too. |
| `docs/adr/0015-committed-embeddings-file-over-a-vector-database.md` | Still *Proposed*. Mark it **Rejected/withdrawn** with a line pointing here, rather than deleting it, so the reasoning stays on record. |

**Keep:**
- `LLMClient.generate_text()` and the `_send` helpers in `governance/llm/`. The assistant
  calls `generate_text()` on every request.
- `backend/app/services/assistant_llm.py` and the `assistant_recordings/` directory.
- The #49 entry in `docs/DECISION_LOG.md`. History stays; a new entry records the removal.
