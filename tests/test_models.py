"""Tests for the Pydantic models in app.models."""

from __future__ import annotations

import pytest

from app.models import Page, RecommendRequest


def test_page_strips_leading_at_and_lowercases() -> None:
    page = Page(username="@NatGeo", name="National Geographic")
    assert page.username == "natgeo"


def test_page_normalizes_categories_and_tags() -> None:
    page = Page(
        username="x",
        name="X",
        categories=["  Travel ", "Photography"],
        tags=["  Wildlife"],
    )
    assert page.categories == ["travel", "photography"]
    assert page.tags == ["wildlife"]


def test_page_defaults() -> None:
    page = Page(username="x", name="X")
    assert page.categories == []
    assert page.tags == []
    assert page.followers_millions == 0.0


def test_recommend_request_normalizes_following() -> None:
    req = RecommendRequest(
        categories=["TRAVEL", " food "],
        following=["@NatGeo", " mkbhd "],
        limit=5,
    )
    assert req.categories == ["travel", "food"]
    assert req.following == ["natgeo", "mkbhd"]
    assert req.limit == 5


def test_recommend_request_limit_bounds() -> None:
    with pytest.raises(ValueError):
        RecommendRequest(categories=["travel"], limit=0)
    with pytest.raises(ValueError):
        RecommendRequest(categories=["travel"], limit=51)
