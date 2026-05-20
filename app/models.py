"""Pydantic models shared by the API and the recommender core."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Page(BaseModel):
    """A single Instagram page in the catalog."""

    username: str = Field(..., description="The Instagram handle, without the leading '@'.")
    name: str = Field(..., description="Human-readable display name.")
    categories: list[str] = Field(default_factory=list, description="Broad interest categories.")
    tags: list[str] = Field(default_factory=list, description="Fine-grained descriptive tags.")
    followers_millions: float = Field(0.0, ge=0.0, description="Approximate follower count in millions.")
    description: str = Field("", description="Short editorial blurb.")

    @field_validator("username", mode="before")
    @classmethod
    def _strip_at(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("username must be a string")
        return value.lstrip("@").strip().lower()

    @field_validator("categories", "tags", mode="before")
    @classmethod
    def _normalize_list(cls, value: list[str]) -> list[str]:
        if value is None:
            return []
        return [str(v).strip().lower() for v in value if str(v).strip()]


class RecommendRequest(BaseModel):
    """Input to the recommendation endpoint."""

    categories: list[str] = Field(default_factory=list, description="User-selected interest categories.")
    following: list[str] = Field(
        default_factory=list,
        description="Optional list of IG handles the user already follows.",
    )
    limit: int = Field(10, ge=1, le=50, description="Maximum number of suggestions to return.")

    @field_validator("categories", mode="before")
    @classmethod
    def _normalize_categories(cls, value: list[str]) -> list[str]:
        if value is None:
            return []
        return [str(v).strip().lower() for v in value if str(v).strip()]

    @field_validator("following", mode="before")
    @classmethod
    def _normalize_following(cls, value: list[str]) -> list[str]:
        if value is None:
            return []
        return [str(v).lstrip("@").strip().lower() for v in value if str(v).strip()]


class Recommendation(BaseModel):
    """A single ranked recommendation."""

    page: Page
    score: float = Field(..., description="Final blended score in [0, 1].")
    reasons: list[str] = Field(default_factory=list, description="Human-readable explanations.")


class RecommendResponse(BaseModel):
    """The recommend endpoint's response payload."""

    count: int
    recommendations: list[Recommendation]
