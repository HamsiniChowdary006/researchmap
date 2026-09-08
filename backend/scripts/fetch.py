"""Fetch a candidate set of arXiv papers for a research topic."""

from __future__ import annotations

import argparse
import json
from typing import Any

import arxiv


def fetch_papers(topic: str, max_results: int = 35) -> list[dict[str, Any]]:
    search = arxiv.Search(
        query=topic,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
        sort_order=arxiv.SortOrder.Descending,
    )
    client = arxiv.Client(page_size=100, delay_seconds=3, num_retries=3)
    results: list[dict[str, Any]] = []
    for result in client.results(search):
        results.append(
            {
                "arxiv_id": result.get_short_id(),
                "title": " ".join(result.title.split()),
                "abstract": " ".join(result.summary.split()),
                "authors": [author.name for author in result.authors],
                "pdf_url": result.pdf_url,
                "published_date": result.published.date().isoformat(),
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic")
    parser.add_argument("--max-results", type=int, default=35)
    arguments = parser.parse_args()
    papers = fetch_papers(arguments.topic, arguments.max_results)
    print(json.dumps(papers, indent=2, ensure_ascii=True))
    print(f"FETCHED_PAPERS={len(papers)}")


if __name__ == "__main__":
    main()
