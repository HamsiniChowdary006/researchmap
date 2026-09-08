"""Rerank arXiv candidates with the MS MARCO cross-encoder."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from sentence_transformers import CrossEncoder

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch import fetch_papers


MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def rerank_papers(topic: str, papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    model = CrossEncoder(MODEL_NAME)
    scores = model.predict([(topic, paper["abstract"]) for paper in papers], show_progress_bar=False)
    ranked = [{**paper, "relevance_score": round(float(score), 4)} for paper, score in zip(papers, scores, strict=True)]
    return sorted(ranked, key=lambda paper: paper["relevance_score"], reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic")
    parser.add_argument("--max-results", type=int, default=5)
    arguments = parser.parse_args()
    papers = fetch_papers(arguments.topic, arguments.max_results)
    started = time.perf_counter()
    ranked = rerank_papers(arguments.topic, papers)
    elapsed = time.perf_counter() - started
    for paper in ranked:
        print(f"{paper['relevance_score']:8.4f}  {paper['arxiv_id']:15}  {paper['title']}")
    print(json.dumps(ranked, indent=2, ensure_ascii=True))
    print(f"RERANK_SECONDS={elapsed:.2f}")


if __name__ == "__main__":
    main()
