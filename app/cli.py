"""Minimal CLI wrapper around the recommender — handy for quick demos."""

from __future__ import annotations

import argparse
import json
import sys

from app.data_loader import load_default_pages
from app.recommender import Recommender


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ig-finder",
        description="Suggest Instagram pages based on your interests.",
    )
    parser.add_argument(
        "-c",
        "--category",
        action="append",
        default=[],
        help="Add a category (repeat for multiple).",
    )
    parser.add_argument(
        "-f",
        "--follow",
        action="append",
        default=[],
        help="Add an IG handle you already follow (repeat for multiple).",
    )
    parser.add_argument("-n", "--limit", type=int, default=10, help="Max number of suggestions.")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of a table.")
    args = parser.parse_args(argv)

    rec = Recommender(load_default_pages())
    results = rec.recommend(
        categories=args.category, following=args.follow, limit=args.limit
    )

    if args.json:
        json.dump([r.model_dump() for r in results], sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if not results:
        print("No recommendations.")
        return 0

    print(f"\n{'Rank':<5}{'Score':<8}{'Handle':<28}{'Name'}")
    print("-" * 72)
    for i, r in enumerate(results, start=1):
        print(f"{i:<5}{r.score:<8.3f}@{r.page.username:<27}{r.page.name}")
        if r.reasons:
            print(f"     {'·':<7}{r.reasons[0]}")
    print()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
