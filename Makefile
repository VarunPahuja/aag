# AAGP — development commands. `make help` (or just `make`) lists targets.
#
# Quickstart: `make setup && make up`
#
# No `make` on Windows? Use the PowerShell scripts in scripts/ instead —
# `scripts\setup.ps1` and `scripts\up.ps1` do the same thing without requiring
# make itself. Every target below is written to be OS-portable once make is
# running (no bash-only syntax in any recipe); the one exception is `help`,
# which uses grep/sed and has a PowerShell equivalent at scripts/help.ps1 for
# a make that shells out to cmd.exe instead of sh.

.DEFAULT_GOAL := help

# Forward slashes on both branches, deliberately: Windows accepts them fine,
# and a POSIX-style SHELL (git-bash/msys/WSL make, common on a mixed team)
# mangles backslashes as escape characters in recipe lines.
ifeq ($(OS),Windows_NT)
    VENV_PYTHON := .venv/Scripts/python.exe
else
    VENV_PYTHON := .venv/bin/python
endif

.PHONY: help setup up down db-reset test test-trust openapi lint fmt dev frontend

help: ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sed 's/:.*## / — /'

setup: ## Create .venv and install every Python lane (trust, simulator, governance, backend) in editable mode
	python -m venv .venv
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -e trust -e simulator -e governance -e backend
	$(VENV_PYTHON) -m pip install pytest pytest-cov pytest-asyncio hypothesis httpx ruff
	@echo "Skipped statsmodels (see docs/RISKS.md R7: pulls in numpy/scipy/pandas"
	@echo "for one optional cross-validation test that skips gracefully without"
	@echo "it). Install it yourself if you need that one test: pip install statsmodels"
	@echo "Done. Next: make up"

up: ## Start Postgres (+ Adminer) and wait for the DB healthcheck
	docker compose up -d --wait db adminer
	@echo "db ready on localhost:5432 — Adminer on http://localhost:8080"

down: ## Stop all compose services
	docker compose down

db-reset: ## Drop, recreate, migrate, seed the database (needs backend/alembic — see note)
	docker compose down -v db
	docker compose up -d --wait db
ifneq ($(wildcard backend/alembic.ini),)
	$(VENV_PYTHON) -m alembic -c backend/alembic.ini upgrade head
	$(VENV_PYTHON) -m backend.app.seed
else
	@echo "backend/alembic.ini doesn't exist yet — DB recreated but not migrated/seeded (see docs/DEADLINES.md)"
endif

test: ## Run pytest across all four Python lanes: trust/, simulator/, governance/, backend/
	$(VENV_PYTHON) -m pytest trust/ -q
	$(VENV_PYTHON) -m pytest simulator/tests -q
	$(VENV_PYTHON) -m pytest governance/tests -q
	$(VENV_PYTHON) -m pytest backend/tests -q

test-trust: ## Run only the trust engine's test suite
	$(VENV_PYTHON) -m pytest trust/ -q

openapi: ## Regenerate backend/openapi.json from the FastAPI app
ifneq ($(wildcard backend/app/main.py),)
	$(VENV_PYTHON) -m backend.app.export_openapi
else
	@echo "backend/app/main.py doesn't exist yet — nothing to export (see docs/DEADLINES.md)"
endif

lint: ## ruff check across trust/, backend/, governance/
	$(VENV_PYTHON) -m ruff check trust/ backend/ governance/

fmt: ## ruff format across trust/, backend/, governance/
	$(VENV_PYTHON) -m ruff format trust/ backend/ governance/

dev: ## Run the backend with reload (needs backend/app/main.py)
ifneq ($(wildcard backend/app/main.py),)
	$(VENV_PYTHON) -m uvicorn app.main:app --reload --app-dir backend --port 8000
else
	@echo "backend/app/main.py doesn't exist yet (see docs/DEADLINES.md)"
endif

frontend: ## npm run dev in frontend/ (needs frontend/package.json)
ifneq ($(wildcard frontend/package.json),)
	cd frontend && npm run dev
else
	@echo "frontend/package.json doesn't exist yet (see docs/DEADLINES.md)"
endif
