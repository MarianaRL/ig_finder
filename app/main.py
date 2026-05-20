"""FastAPI entrypoint for ig_finder.

Endpoints
---------

* ``GET  /api/health``      — service health
* ``GET  /api/categories``  — every category present in the catalog
* ``GET  /api/pages``       — full catalog (handy for an autocomplete UI)
* ``POST /api/recommend``   — produce ranked recommendations
* ``GET  /``                — serves the bundled web UI
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.data_loader import available_categories, load_default_pages
from app.models import Page, RecommendRequest, RecommendResponse
from app.recommender import Recommender

# ---------------------------------------------------------------------------
# App + state
# ---------------------------------------------------------------------------

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(
    title="ig_finder",
    version=__version__,
    description=(
        "A small, hackable hybrid content-based recommender that suggests "
        "Instagram pages from a user's interests and the accounts they already follow."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Build the recommender once at import time
_PAGES = load_default_pages()
_recommender = Recommender(_PAGES)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "pages": str(len(_PAGES))}


@app.get("/api/categories", tags=["catalog"], response_model=list[str])
def categories() -> list[str]:
    return available_categories(_PAGES)


@app.get("/api/pages", tags=["catalog"], response_model=list[Page])
def pages() -> list[Page]:
    return list(_PAGES)


@app.post("/api/recommend", tags=["recommend"], response_model=RecommendResponse)
def recommend(payload: RecommendRequest) -> RecommendResponse:
    if not payload.categories and not payload.following:
        # We still want to be useful — return a popularity fallback rather
        # than 400, but flag it via the recommendation reasons.
        pass

    # Validate categories against catalog (case-insensitive). Unknown
    # categories aren't an error — they simply don't contribute to scoring.
    known = set(_recommender.known_categories())
    unknown = [c for c in payload.categories if c not in known]
    if unknown and len(unknown) == len(payload.categories) and not payload.following:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "None of the provided categories are known.",
                "unknown_categories": unknown,
                "known_categories": sorted(known),
            },
        )

    recs = _recommender.recommend(
        categories=payload.categories,
        following=payload.following,
        limit=payload.limit,
    )
    return RecommendResponse(count=len(recs), recommendations=recs)


# ---------------------------------------------------------------------------
# Static UI
# ---------------------------------------------------------------------------

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")
