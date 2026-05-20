"""Shared fixtures."""

from __future__ import annotations

import pytest

from app.data_loader import load_default_pages
from app.models import Page
from app.recommender import Recommender


@pytest.fixture(scope="session")
def default_pages() -> tuple[Page, ...]:
    return load_default_pages()


@pytest.fixture(scope="session")
def recommender(default_pages: tuple[Page, ...]) -> Recommender:
    return Recommender(default_pages)


@pytest.fixture()
def tiny_catalog() -> list[Page]:
    """A tiny, fully-deterministic catalog used by unit tests."""
    return [
        Page(
            username="natgeo",
            name="National Geographic",
            categories=["photography", "nature", "travel"],
            tags=["wildlife", "landscape", "earth"],
            followers_millions=280.0,
            description="Photographers capturing the world.",
        ),
        Page(
            username="mkbhd",
            name="Marques Brownlee",
            categories=["tech"],
            tags=["gadgets", "smartphones", "reviews"],
            followers_millions=5.6,
            description="Quality tech videos.",
        ),
        Page(
            username="gordongram",
            name="Gordon Ramsay",
            categories=["food", "celebrity"],
            tags=["cooking", "chef", "recipes"],
            followers_millions=17.0,
            description="Michelin-star chef.",
        ),
        Page(
            username="chrisburkard",
            name="Chris Burkard",
            categories=["photography", "nature", "travel"],
            tags=["landscape", "adventure", "surfing"],
            followers_millions=3.9,
            description="Adventure photography.",
        ),
        Page(
            username="ourplanet",
            name="Our Planet",
            categories=["nature", "science"],
            tags=["wildlife", "earth", "documentary"],
            followers_millions=1.3,
            description="Netflix nature documentary.",
        ),
    ]
