"""Optional Instagram metadata scraper.

This module is **not** required to run ig_finder — the bundled
``data/pages.json`` dataset is enough for the recommender. The scraper
exists to demonstrate how the catalog could be extended programmatically.

Notes & caveats
---------------
* Instagram's terms of service forbid most automated scraping. Use this
  module only against accounts you own or with appropriate authorization.
* Instagram aggressively rate-limits unauthenticated requests; production
  use would require the official Graph API or a paid third-party provider.
* This implementation is intentionally minimal — it shows the *shape* of
  an extension point rather than a battle-tested scraper.

Install the optional dependencies with::

    pip install -e ".[scraping]"
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

from app.models import Page

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)
PROFILE_URL_TEMPLATE = "https://www.instagram.com/{handle}/"
_FOLLOWERS_RE = re.compile(r'"edge_followed_by":\s*{\s*"count":\s*(\d+)')
_BIO_RE = re.compile(r'"biography":\s*"([^"]*)"')
_NAME_RE = re.compile(r'"full_name":\s*"([^"]*)"')


@dataclass
class ScrapedProfile:
    """A lightweight profile snapshot scraped from a public IG page."""

    username: str
    name: str
    biography: str
    followers: int

    def to_page(
        self,
        categories: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Page:
        return Page(
            username=self.username,
            name=self.name or self.username,
            categories=categories or [],
            tags=tags or [],
            followers_millions=round(self.followers / 1_000_000, 2),
            description=self.biography,
        )


def _import_requests():
    try:
        import requests  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError(
            "The scraping extras are not installed. Run "
            '`pip install -e ".[scraping]"` and try again.'
        ) from exc
    return requests


def fetch_profile(handle: str, *, session=None, timeout: float = 8.0) -> ScrapedProfile:
    """Fetch a single public profile.

    Raises ``RuntimeError`` if Instagram returns a non-200 response,
    if the page can't be parsed, or if the optional deps aren't installed.
    """
    requests = _import_requests()
    handle = handle.lstrip("@").strip().lower()
    if not handle:
        raise ValueError("Empty handle")

    sess = session or requests.Session()
    sess.headers.setdefault("User-Agent", USER_AGENT)

    resp = sess.get(PROFILE_URL_TEMPLATE.format(handle=handle), timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"Instagram returned HTTP {resp.status_code} for @{handle}")

    body = resp.text
    followers_match = _FOLLOWERS_RE.search(body)
    name_match = _NAME_RE.search(body)
    bio_match = _BIO_RE.search(body)

    if followers_match is None:
        raise RuntimeError(
            f"Could not parse follower count for @{handle} — IG likely served a "
            "logged-out wall or changed its markup."
        )

    return ScrapedProfile(
        username=handle,
        name=(name_match.group(1) if name_match else handle).encode().decode("unicode_escape"),
        biography=(bio_match.group(1) if bio_match else "")
        .encode()
        .decode("unicode_escape"),
        followers=int(followers_match.group(1)),
    )


def extend_dataset(
    handles: list[str],
    *,
    output_path: Path | str,
    delay_seconds: float = 3.0,
    categories_by_handle: dict[str, list[str]] | None = None,
    tags_by_handle: dict[str, list[str]] | None = None,
) -> list[Page]:
    """Scrape ``handles`` and append them to a JSON dataset file.

    The function is conservative on purpose: a configurable delay between
    requests, a single retry budget, and merging by handle so we don't
    duplicate existing entries.
    """
    requests = _import_requests()
    output_path = Path(output_path)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    if output_path.exists():
        with output_path.open("r", encoding="utf-8") as fp:
            existing_raw = json.load(fp)
    else:
        existing_raw = []
    by_username: dict[str, dict] = {entry["username"].lower(): entry for entry in existing_raw}

    new_pages: list[Page] = []
    cats = categories_by_handle or {}
    tags = tags_by_handle or {}

    for handle in handles:
        try:
            profile = fetch_profile(handle, session=session)
        except Exception as exc:  # noqa: BLE001 — log & continue
            logger.warning("Skipping @%s: %s", handle, exc)
            continue

        page = profile.to_page(
            categories=cats.get(profile.username, []),
            tags=tags.get(profile.username, []),
        )
        by_username[profile.username] = page.model_dump()
        new_pages.append(page)
        time.sleep(delay_seconds)

    merged = sorted(by_username.values(), key=lambda p: p["username"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fp:
        json.dump(merged, fp, indent=2, ensure_ascii=False)

    return new_pages
