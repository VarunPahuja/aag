"""Writes `backend/openapi.json` from the live FastAPI app.

Invoked as `python -m backend.app.export_openapi` from the repo root
(`make openapi`, and the CI staleness check in `.github/workflows/ci.yml`)
— run after `pip install -e backend` so `app` itself is also directly
importable, matching how every route module inside `app/` imports its
siblings.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app

OUTPUT_PATH = Path(__file__).resolve().parents[1] / "openapi.json"


def main() -> None:
    schema = app.openapi()
    OUTPUT_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
