"""Load the curated catalog of Instagram pages from disk."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.models import Page

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_PAGES_FILE = DATA_DIR / "pages.json"


def load_pages(path: Path | str | None = None) -> list[Page]:
    """Load pages from ``path`` (defaults to the bundled dataset)."""
    target = Path(path) if path is not None else DEFAULT_PAGES_FILE
    if not target.exists():
        raise FileNotFoundError(f"Pages dataset not found at {target}")
    with target.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    if not isinstance(raw, list):
        raise ValueError("pages.json must contain a JSON array")
    return [Page(**entry) for entry in raw]


@lru_cache(maxsize=4)
def load_default_pages() -> tuple[Page, ...]:
    """Cached loader for the bundled dataset (immutable tuple for safety)."""
    return tuple(load_pages())


def available_categories(pages: list[Page] | tuple[Page, ...]) -> list[str]:
    """Return the sorted set of categories present in ``pages``."""
    seen: set[str] = set()
    for page in pages:
        seen.update(page.categories)
    return sorted(seen)
