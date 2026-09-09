"""Fetch a candidate set of arXiv papers for a research topic."""

from __future__ import annotations

import argparse
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any

import arxiv

logger = logging.getLogger(__name__)
ARXIV_TIMEOUT_SECONDS = 45
ARXIV_MAX_ATTEMPTS = 3


def _error_details(error: Exception) -> str:
    status = getattr(error, "status", None) or getattr(error, "code", None)
    body = getattr(error, "read", lambda: b"")()
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    details = f"status={status!r}, response_body={body[:1000]!r}, message={error}"
    return details


def _fetch_once(topic: str, max_results: int) -> list[dict[str, Any]]:
    search = arxiv.Search(
        query=topic,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
        sort_order=arxiv.SortOrder.Descending,
    )
    client = arxiv.Client(page_size=100, delay_seconds=3, num_retries=0)
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


def fetch_papers(topic: str, max_results: int = 35) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(1, ARXIV_MAX_ATTEMPTS + 1):
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_fetch_once, topic, max_results)
        try:
            result = future.result(timeout=ARXIV_TIMEOUT_SECONDS)
            executor.shutdown(wait=True)
            return result
        except (FutureTimeoutError, Exception) as error:
            future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
            last_error = error
            logger.exception(
                "arXiv fetch failed (attempt %s/%s, timeout=%ss): %s",
                attempt,
                ARXIV_MAX_ATTEMPTS,
                ARXIV_TIMEOUT_SECONDS,
                _error_details(error),
            )
            if attempt < ARXIV_MAX_ATTEMPTS:
                time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"arXiv fetch failed after {ARXIV_MAX_ATTEMPTS} attempts: {_error_details(last_error)}") from last_error


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
