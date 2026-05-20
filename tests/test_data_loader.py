"""Tests for the data loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.data_loader import available_categories, load_default_pages, load_pages


def test_load_default_pages_returns_pages() -> None:
    pages = load_default_pages()
    assert len(pages) >= 50
    assert all(p.username == p.username.lower() for p in pages)


def test_available_categories_is_sorted_and_unique() -> None:
    pages = load_default_pages()
    cats = available_categories(pages)
    assert cats == sorted(set(cats))
    assert "tech" in cats
    assert "travel" in cats


def test_load_pages_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_pages(tmp_path / "nope.json")


def test_load_pages_from_custom_path(tmp_path: Path) -> None:
    custom = tmp_path / "p.json"
    custom.write_text(
        json.dumps(
            [
                {
                    "username": "x",
                    "name": "X",
                    "categories": ["tech"],
                    "tags": ["gadgets"],
                    "followers_millions": 1.0,
                    "description": "test",
                }
            ]
        )
    )
    pages = load_pages(custom)
    assert len(pages) == 1
    assert pages[0].username == "x"


def test_load_pages_rejects_non_array(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"oops": True}))
    with pytest.raises(ValueError):
        load_pages(bad)
