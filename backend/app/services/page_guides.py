"""Page guides for the assistant: which page the user is on, and how that page works.

Replaces `app/services/doc_index.py`, a keyword search over `docs/`. The assistant is a
help panel for the screen in front of the user, not a search engine over design docs, so
what it needs is a hand-written guide to that page plus one short overview of the system —
chosen by route, never by matching words in the question.

**The route is untrusted.** It arrives from the browser, so it only ever *selects* a guide
from `ROUTES`; the raw string never reaches the prompt. An unknown route gets the overview
alone rather than an error — a help panel that 422s on a page it doesn't recognise helps
nobody.

**Nothing to rebuild.** Guides are plain markdown in `app/data/page_guides/`, read when a
question is asked. Editing one takes effect on the next question; there is no index to go
stale. `backend/tests/test_page_guides.py` fails if a frontend page exists without a guide,
which is the one way these can drift from the UI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# backend/app/services/page_guides.py -> backend/app/data/page_guides/
GUIDE_DIR = Path(__file__).resolve().parents[1] / "data" / "page_guides"

# Always included, whatever the page: what the numbers mean is asked on every page.
OVERVIEW = "overview"

# Pathname -> guide id. First match wins. Mirrors frontend/src/app/**/page.tsx, with route
# groups like `(dashboard)` dropped because they are not part of the URL.
ROUTES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^/$"), "landing"),
    (re.compile(r"^/agents$"), "agents"),
    (re.compile(r"^/agents/[^/]+$"), "agent-detail"),
    (re.compile(r"^/approvals$"), "approvals"),
    (re.compile(r"^/audit$"), "audit"),
    (re.compile(r"^/simulation$"), "simulation"),
    (re.compile(r"^/demo$"), "demo"),
)


@dataclass(frozen=True, slots=True)
class PageGuide:
    """One guide. `title` is the file's first heading — what a citation shows."""

    page: str
    title: str
    text: str


def page_for_route(route: str | None) -> str | None:
    """The guide id for a browser pathname, or None if this app has no such page.

    Tolerates what a browser might plausibly send: a query string, a fragment, a
    trailing slash.
    """
    if not route:
        return None
    path = route.split("?", 1)[0].split("#", 1)[0]
    if len(path) > 1:
        path = path.rstrip("/")
    for pattern, page in ROUTES:
        if pattern.match(path):
            return page
    return None


def load_guide(page: str) -> PageGuide:
    text = (GUIDE_DIR / f"{page}.md").read_text(encoding="utf-8").strip()
    title = text.splitlines()[0].lstrip("#").strip()
    return PageGuide(page=page, title=title, text=text)


def guides_for_route(route: str | None) -> list[PageGuide]:
    """The current page's guide first, then the overview — the order the system prompt
    tells the model to read them in. Overview alone when the route is unknown.
    """
    page = page_for_route(route)
    pages = [OVERVIEW] if page is None else [page, OVERVIEW]
    return [load_guide(p) for p in pages]
