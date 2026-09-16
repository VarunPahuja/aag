# Running this locally, on your own machine

For anyone cloning the repo fresh — a teammate, or a laptop that isn't the one
this project was originally set up on. Nothing here is shared with anyone
else's checkout: your `.env`, your keys, your Postgres data.

## 1. Clone & install

```powershell
git clone https://github.com/VarunPahuja/aag.git
cd aag

make setup                 # or scripts\setup.ps1 on Windows without make
```

`make setup` installs `governance` **without** the `openai` extra. Add it if
you'll use Azure OpenAI or OpenAI as a provider for anything (the assistant
chat, or a governance panel agent) — Gemini doesn't need it:

```powershell
.venv\Scripts\pip install "governance[openai]"    # Windows
.venv/bin/pip install "governance[openai]"         # macOS/Linux
```

## 2. Start Postgres

```powershell
make up          # docker compose up -d --wait db adminer
```

Adminer (a DB browser) is on http://localhost:8080 — server `db`, credentials
from `POSTGRES_USER`/`POSTGRES_PASSWORD` in your `.env`.

## 3. Create your own `.env`

```powershell
cp .env.example .env
```

Every variable is documented inline in `.env.example`. The one section worth
a second look is the assistant (read-only chat panel) — pick one:

| Option | What to set | Notes |
|---|---|---|
| **Gemini (recommended)** | `GEMINI_API_KEY=<your own key>` | Free tier from [Google AI Studio](https://aistudio.google.com/apikey). Already the default provider — no `GOVERNANCE_PROVIDER_ASSISTANT` line needed. |
| **Your own Azure resource** | `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `GOVERNANCE_PROVIDER_ASSISTANT=azure-openai` | Needs your own Azure OpenAI resource. See `docs/ASSISTANT-INTEGRATION.md` for the exact API shape it calls. |
| **No key at all** | `ASSISTANT_MODE=cached` | Only answers the page/question pairs already recorded in `backend/app/data/assistant_recordings/`. Anything else returns 503. |
| **No key, just to see it plumb through** | `ASSISTANT_MODE=stub` | Zero LLM calls — dumps the raw assembled context instead of a real answer. |

Leave `GOVERNANCE_MODE=stub` alone unless you're specifically working on the
4-agent governance panel — that's a separate feature from the assistant, and
stub mode there needs no key at all.

**Never commit `.env` or send it to anyone** — it's gitignored on purpose. A
teammate needs their own keys, not yours: sharing one means shared quota,
cost on your bill, and one leak burns it for everyone.

## 4. Load `.env` into the shell before starting the backend

This is the part that's easy to miss: **the backend never reads `.env` on its
own** — nothing in `backend/` calls `python-dotenv` or touches the file.
Whatever's in it has to be exported into the process environment first, in
the same shell you launch the server from.

Bash / macOS / Linux:

```bash
set -a; source .env; set +a
make dev
```

PowerShell:

```powershell
Get-Content .env | ForEach-Object {
    if ($_ -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$' -and -not $_.StartsWith('#')) {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim('"'), 'Process')
    }
}
make dev
```

Do this in every new terminal — it doesn't persist across sessions.

## 5. Start the frontend

```powershell
make frontend       # cd frontend && npm run dev (npm install first if needed)
```

## 6. Try it

Open http://localhost:3000. `/docs` on http://localhost:8000 confirms the API
is up if the frontend looks empty (usually a `CORS_ALLOW_ORIGINS` or
`DATABASE_URL` mismatch — see the comments in `.env.example`).

The database starts empty. `make db-reset` (drops, recreates, migrates, and
seeds it) gives you agents and invoices to look at rather than a blank
dashboard.

## Running the tests

```powershell
make test
```

Or target one lane directly, e.g. the assistant's own tests:

```powershell
.venv\Scripts\python.exe -m pytest backend/tests/test_assistant.py backend/tests/test_page_guides.py -q
.venv\Scripts\python.exe -m pytest governance/tests -q
```

None of the test suites need a real API key — every provider client is
exercised through injected stubs (`governance/tests/test_providers.py`,
`test_azure_openai.py`, `test_llm.py`).
