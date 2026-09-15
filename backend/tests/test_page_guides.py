"""Every frontend page has a guide, and every guide belongs to a page.

The assistant answers "how does this page work" from `backend/app/data/page_guides/`.
A page added to the frontend without a guide would get only the system overview, and
the assistant would describe it from nothing. This is the test that catches that in the
PR that adds the page, instead of in front of a user.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services import page_guides
from app.services.page_guides import OVERVIEW, ROUTES, guides_for_route, page_for_route

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_APP = REPO_ROOT / "frontend" / "src" / "app"

ROUTED = {OVERVIEW, *(page for _, page in ROUTES)}


def _route_of(page_file: Path) -> str:
    """`(dashboard)/agents/[id]/page.tsx` -> `/agents/sample-id`. Route groups in
    parentheses are not part of the URL; a dynamic segment gets a stand-in value.
    """
    parts = []
    for part in page_file.relative_to(FRONTEND_APP).parent.parts:
        if part.startswith("(") and part.endswith(")"):
            continue
        parts.append("sample-id" if part.startswith("[") else part)
    return "/" + "/".join(parts)


def _frontend_routes() -> list[str]:
    if not FRONTEND_APP.is_dir():
        pytest.skip("frontend/ is not checked out")
    return sorted(_route_of(p) for p in FRONTEND_APP.rglob("page.tsx"))


def test_the_route_scan_finds_the_known_pages():
    # Guards the next test against passing vacuously on an empty or broken scan.
    routes = _frontend_routes()
    assert {"/", "/agents", "/agents/sample-id", "/approvals"} <= set(routes)


def test_every_frontend_page_has_a_guide():
    missing = [route for route in _frontend_routes() if page_for_route(route) is None]
    assert not missing, (
        f"frontend pages with no guide: {missing}. Add a markdown file to "
        "backend/app/data/page_guides/ and a route to ROUTES in app/services/page_guides.py."
    )


def test_every_routed_guide_exists_and_opens_with_its_title():
    for page in ROUTED:
        guide = page_guides.load_guide(page)
        assert guide.text.startswith("# "), page
        assert guide.title, page


def test_no_guide_file_is_orphaned():
    on_disk = {path.stem for path in page_guides.GUIDE_DIR.glob("*.md")}
    assert on_disk == ROUTED


@pytest.mark.parametrize(
    ("route", "page"),
    [
        ("/", "landing"),
        ("/agents", "agents"),
        ("/agents/", "agents"),
        ("/agents?tab=1", "agents"),
        ("/agents/agent-01", "agent-detail"),
        ("/agents/agent-01#decisions", "agent-detail"),
        ("/approvals", "approvals"),
        ("/audit", "audit"),
        ("/simulation", "simulation"),
        ("/demo", "demo"),
        ("/agents/agent-01/extra", None),
        ("/nope", None),
        ("", None),
        (None, None),
    ],
)
def test_page_for_route(route, page):
    assert page_for_route(route) == page


def test_the_page_guide_comes_before_the_overview():
    assert [g.page for g in guides_for_route("/audit")] == ["audit", OVERVIEW]
    assert [g.page for g in guides_for_route("/nope")] == [OVERVIEW]
    assert [g.page for g in guides_for_route(None)] == [OVERVIEW]
