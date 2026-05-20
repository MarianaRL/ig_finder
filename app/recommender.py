"""Hybrid content-based recommender.

The scoring blends three signals:

1. **Category match** — Jaccard-style overlap between the user's chosen
   categories and a page's categories.
2. **Tag / content similarity** — TF-IDF cosine similarity between a
   pseudo-document built from the user's selections (categories +
   tags inherited from followed pages) and each candidate page's
   bag-of-words representation.
3. **Popularity prior** — a gentle log-scaled boost so we don't surface
   ultra-obscure accounts when nothing else differentiates candidates.

Followed accounts are excluded from the output. Each recommendation
ships with a list of human-readable reasons explaining *why* the
system surfaced it — recruiters love explainability.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models import Page, Recommendation


# ---------------------------------------------------------------------------
# Scoring weights — tweak here to retune the blend.
# ---------------------------------------------------------------------------
W_CATEGORY = 0.50
W_CONTENT = 0.40
W_POPULARITY = 0.10
MAX_REASONS = 3


@dataclass(frozen=True)
class _PageDoc:
    page: Page
    document: str


def _page_to_document(page: Page) -> str:
    """Flatten a page into a single bag-of-words document for TF-IDF."""
    # Repeat categories so they carry a bit more weight than tags.
    parts = list(page.categories) * 2 + list(page.tags) + [page.description.lower()]
    return " ".join(parts)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


class Recommender:
    """Content-based recommender over a fixed catalog of pages."""

    def __init__(self, pages: list[Page] | tuple[Page, ...]):
        if not pages:
            raise ValueError("Recommender requires a non-empty page catalog")
        self._pages: list[Page] = list(pages)
        self._docs: list[_PageDoc] = [
            _PageDoc(page=p, document=_page_to_document(p)) for p in self._pages
        ]
        self._vectorizer = TfidfVectorizer(
            lowercase=True,
            token_pattern=r"[a-z0-9][a-z0-9\-]+",
            min_df=1,
        )
        self._tfidf = self._vectorizer.fit_transform([d.document for d in self._docs])
        self._max_followers = max((p.followers_millions for p in self._pages), default=1.0) or 1.0
        self._username_index: dict[str, int] = {
            p.username: i for i, p in enumerate(self._pages)
        }

    # -- public API ---------------------------------------------------------

    @property
    def pages(self) -> list[Page]:
        return list(self._pages)

    def known_categories(self) -> list[str]:
        cats: set[str] = set()
        for p in self._pages:
            cats.update(p.categories)
        return sorted(cats)

    def recommend(
        self,
        categories: list[str] | None = None,
        following: list[str] | None = None,
        limit: int = 10,
    ) -> list[Recommendation]:
        """Return up to ``limit`` ranked recommendations.

        Either ``categories`` or ``following`` (or both) should be provided.
        If both are empty the method returns the most popular pages as a
        graceful fallback, since cold-start with zero signal is unsolvable.
        """
        categories = [c.lower().strip() for c in (categories or []) if c.strip()]
        following = [f.lstrip("@").lower().strip() for f in (following or []) if f.strip()]
        following_set = set(following)

        # 1) Inherit tags/categories from followed pages
        inherited_cats: set[str] = set()
        inherited_tags: set[str] = set()
        for handle in following:
            idx = self._username_index.get(handle)
            if idx is None:
                continue
            inherited_cats.update(self._pages[idx].categories)
            inherited_tags.update(self._pages[idx].tags)

        effective_cats: set[str] = set(categories) | inherited_cats

        # 2) Build the user "query document" for TF-IDF
        query_tokens: list[str] = list(categories) * 2 + list(inherited_cats) + list(inherited_tags)
        if not query_tokens:
            # Cold start: popularity-only ranking
            return self._popularity_fallback(following_set, limit)

        query_vec = self._vectorizer.transform([" ".join(query_tokens)])
        content_sims = cosine_similarity(query_vec, self._tfidf).ravel()
        content_sims = self._minmax(content_sims)

        # 3) Score each candidate
        scored: list[Recommendation] = []
        for i, page in enumerate(self._pages):
            if page.username in following_set:
                continue

            cat_score = _jaccard(set(page.categories), effective_cats)
            content_score = float(content_sims[i])
            pop_score = self._popularity_score(page.followers_millions)

            final = (
                W_CATEGORY * cat_score
                + W_CONTENT * content_score
                + W_POPULARITY * pop_score
            )

            reasons = self._explain(
                page=page,
                user_cats=set(categories),
                inherited_cats=inherited_cats,
                inherited_tags=inherited_tags,
                cat_score=cat_score,
                content_score=content_score,
            )
            scored.append(Recommendation(page=page, score=round(final, 4), reasons=reasons))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:limit]

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _minmax(values: np.ndarray) -> np.ndarray:
        if values.size == 0:
            return values
        lo, hi = float(values.min()), float(values.max())
        if hi - lo < 1e-12:
            return np.zeros_like(values)
        return (values - lo) / (hi - lo)

    def _popularity_score(self, followers_millions: float) -> float:
        """Log-scaled popularity in [0, 1]."""
        if followers_millions <= 0:
            return 0.0
        return math.log1p(followers_millions) / math.log1p(self._max_followers)

    def _popularity_fallback(
        self, following: set[str], limit: int
    ) -> list[Recommendation]:
        ranked = sorted(self._pages, key=lambda p: p.followers_millions, reverse=True)
        out: list[Recommendation] = []
        for page in ranked:
            if page.username in following:
                continue
            out.append(
                Recommendation(
                    page=page,
                    score=round(self._popularity_score(page.followers_millions), 4),
                    reasons=["Popular fallback — provide categories for personalized picks."],
                )
            )
            if len(out) >= limit:
                break
        return out

    def _explain(
        self,
        page: Page,
        user_cats: set[str],
        inherited_cats: set[str],
        inherited_tags: set[str],
        cat_score: float,
        content_score: float,
    ) -> list[str]:
        reasons: list[str] = []

        cat_overlap = sorted(set(page.categories) & user_cats)
        if cat_overlap:
            reasons.append(f"Matches your interests: {', '.join(cat_overlap)}.")

        inh_cat_overlap = sorted(set(page.categories) & (inherited_cats - user_cats))
        if inh_cat_overlap:
            reasons.append(
                f"Similar to pages you follow (shared categories: {', '.join(inh_cat_overlap)})."
            )

        tag_overlap = sorted(set(page.tags) & inherited_tags)
        if tag_overlap:
            reasons.append(
                f"Shares tags with pages you follow: {', '.join(tag_overlap[:4])}."
            )

        if not reasons and content_score > 0.0:
            reasons.append("Content similar to your stated interests.")

        if cat_score == 0.0 and content_score == 0.0:
            reasons.append("Popular pick.")

        return reasons[:MAX_REASONS]
