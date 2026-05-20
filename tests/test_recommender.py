"""Tests for the recommender's scoring and behavior."""

from __future__ import annotations

import pytest

from app.models import Page
from app.recommender import Recommender


def test_recommender_requires_non_empty_catalog() -> None:
    with pytest.raises(ValueError):
        Recommender([])


def test_top_pick_matches_categories(tiny_catalog: list[Page]) -> None:
    rec = Recommender(tiny_catalog)
    results = rec.recommend(categories=["tech"], limit=3)
    assert results
    assert results[0].page.username == "mkbhd"


def test_following_pages_are_excluded(tiny_catalog: list[Page]) -> None:
    rec = Recommender(tiny_catalog)
    results = rec.recommend(
        categories=["photography", "nature"], following=["natgeo"], limit=10
    )
    handles = [r.page.username for r in results]
    assert "natgeo" not in handles
    # And following natgeo should boost photography/nature siblings
    assert "chrisburkard" in handles or "ourplanet" in handles


def test_following_inherits_tags_even_without_categories(tiny_catalog: list[Page]) -> None:
    rec = Recommender(tiny_catalog)
    # Provide *no* categories — system should infer from followed accounts.
    results = rec.recommend(following=["natgeo"], limit=5)
    handles = [r.page.username for r in results]
    assert "natgeo" not in handles
    # chrisburkard shares ALL three of natgeo's categories — should rank top
    assert results[0].page.username == "chrisburkard"


def test_cold_start_returns_popularity_fallback(tiny_catalog: list[Page]) -> None:
    rec = Recommender(tiny_catalog)
    results = rec.recommend(limit=3)
    # With no signal, the most-followed page should win
    assert results[0].page.username == "natgeo"
    assert "Popular fallback" in results[0].reasons[0]


def test_scores_are_bounded_and_sorted(tiny_catalog: list[Page]) -> None:
    rec = Recommender(tiny_catalog)
    results = rec.recommend(categories=["nature"], limit=5)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= s <= 1.0 for s in scores)


def test_reasons_explain_category_overlap(tiny_catalog: list[Page]) -> None:
    rec = Recommender(tiny_catalog)
    results = rec.recommend(categories=["photography"], limit=1)
    top = results[0]
    assert any("photography" in r.lower() for r in top.reasons)


def test_unknown_following_handle_is_ignored(tiny_catalog: list[Page]) -> None:
    rec = Recommender(tiny_catalog)
    # Should not crash even if handle isn't in the catalog
    results = rec.recommend(categories=["tech"], following=["@someone_not_in_catalog"], limit=3)
    assert results[0].page.username == "mkbhd"


def test_limit_respected(tiny_catalog: list[Page]) -> None:
    rec = Recommender(tiny_catalog)
    results = rec.recommend(categories=["nature"], limit=2)
    assert len(results) == 2


def test_known_categories_lists_everything(tiny_catalog: list[Page]) -> None:
    rec = Recommender(tiny_catalog)
    cats = rec.known_categories()
    assert "tech" in cats
    assert "photography" in cats
    assert cats == sorted(cats)
