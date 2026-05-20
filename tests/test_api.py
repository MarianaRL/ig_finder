"""Tests for the FastAPI surface."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert int(data["pages"]) >= 50


def test_categories_endpoint() -> None:
    resp = client.get("/api/categories")
    assert resp.status_code == 200
    cats = resp.json()
    assert isinstance(cats, list)
    assert "tech" in cats
    assert "travel" in cats


def test_pages_endpoint_returns_catalog() -> None:
    resp = client.get("/api/pages")
    assert resp.status_code == 200
    pages = resp.json()
    assert isinstance(pages, list)
    assert len(pages) >= 50
    assert "username" in pages[0]


def test_recommend_with_categories() -> None:
    resp = client.post(
        "/api/recommend",
        json={"categories": ["tech"], "limit": 3},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == len(data["recommendations"])
    assert len(data["recommendations"]) == 3
    top = data["recommendations"][0]
    assert "tech" in top["page"]["categories"]


def test_recommend_excludes_followed_handles() -> None:
    resp = client.post(
        "/api/recommend",
        json={
            "categories": ["photography", "nature"],
            "following": ["natgeo"],
            "limit": 5,
        },
    )
    assert resp.status_code == 200
    handles = [r["page"]["username"] for r in resp.json()["recommendations"]]
    assert "natgeo" not in handles


def test_recommend_cold_start_returns_fallback() -> None:
    resp = client.post("/api/recommend", json={"limit": 3})
    assert resp.status_code == 200
    recs = resp.json()["recommendations"]
    assert len(recs) == 3


def test_recommend_rejects_only_unknown_categories() -> None:
    resp = client.post(
        "/api/recommend",
        json={"categories": ["nonsense-xyz"], "limit": 3},
    )
    assert resp.status_code == 400
    assert "unknown_categories" in resp.json()["detail"]


def test_recommend_limit_validation() -> None:
    resp = client.post("/api/recommend", json={"categories": ["tech"], "limit": 999})
    assert resp.status_code == 422  # Pydantic validation error
