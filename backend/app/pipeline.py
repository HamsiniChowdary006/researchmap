from __future__ import annotations

import json
import logging
import sqlite3
from datetime import UTC, datetime

from app.db import connect
from scripts.extract import extract_paper
from scripts.fetch import fetch_papers
from scripts.ingest import ingest_paper
from scripts.rerank import rerank_papers
from scripts.synthesize import synthesize

logger = logging.getLogger(__name__)

STAGES = ("fetch", "rerank", "extract", "synthesize")


def now() -> str:
    return datetime.now(UTC).isoformat()


def update_stage(job_id: str, stage: str, status: str, error: str | None = None) -> None:
    with connect() as database:
        if status == "running":
            database.execute("UPDATE job_stages SET status = ?, started_at = ?, error = NULL WHERE job_id = ? AND stage_name = ?", (status, now(), job_id, stage))
        else:
            database.execute("UPDATE job_stages SET status = ?, finished_at = ?, error = ? WHERE job_id = ? AND stage_name = ?", (status, now(), error, job_id, stage))


def update_job_status(job_id: str, status: str) -> None:
    with connect() as database:
        database.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))


def save_paper(paper: dict) -> None:
    with connect() as database:
        database.execute("INSERT OR REPLACE INTO papers (arxiv_id, title, abstract, authors, pdf_url, published_date) VALUES (?, ?, ?, ?, ?, ?)", (paper["arxiv_id"], paper["title"], paper["abstract"], json.dumps(paper["authors"]), paper["pdf_url"], paper["published_date"]))


def reading_list(papers: list[dict], used_ids: set[str]) -> list[dict]:
    used_papers = [paper for paper in papers if paper["arxiv_id"] in used_ids]
    foundational = [paper for paper in used_papers if any(keyword in paper["title"].lower() for keyword in ("survey", "review", "tutorial", "foundations", "introduction"))]
    specialized = [paper for paper in used_papers if paper not in foundational]
    ordered = sorted(foundational, key=lambda paper: paper.get("relevance_score", 0), reverse=True) + sorted(specialized, key=lambda paper: paper.get("relevance_score", 0), reverse=True)
    result = []
    for index, paper in enumerate(ordered):
        if paper in foundational:
            reason = "Placed first as a survey or foundational overview for the field."
        elif foundational:
            reason = "Placed after the overview papers, then ordered by ranked relevance for focused follow-up."
        else:
            reason = "Placed by descending ranked relevance because no overview paper was identified."
        result.append({"order": index + 1, "arxiv_id": paper["arxiv_id"], "title": paper["title"], "url": f"https://arxiv.org/abs/{paper['arxiv_id']}", "relevance_score": paper.get("relevance_score"), "reason": reason})
    return result


def run_job(job_id: str, topic: str, papers_per_search: int) -> None:
    current_stage = "fetch"
    try:
        update_job_status(job_id, "running")
        update_stage(job_id, "fetch", "running")
        try:
            papers = fetch_papers(topic, max(30, papers_per_search * 3))
        except Exception as error:
            logger.exception("arXiv stage failed for job %s: %s", job_id, error)
            with connect() as database:
                rows = database.execute("SELECT * FROM papers ORDER BY published_date DESC LIMIT ?", (max(1, papers_per_search * 3),)).fetchall()
            papers = []
            for row in rows:
                paper = dict(row)
                paper["authors"] = json.loads(paper["authors"])
                papers.append(paper)
        if not papers:
            update_stage(job_id, "fetch", "failed", "No papers found for this topic.")
            with connect() as database:
                database.execute("UPDATE jobs SET status = ? WHERE id = ?", ("no_papers", job_id))
            return
        for paper in papers:
            save_paper(paper)
        update_stage(job_id, "fetch", "completed")

        current_stage = "rerank"
        update_stage(job_id, current_stage, "running")
        papers = rerank_papers(topic, papers)[:papers_per_search]
        update_stage(job_id, current_stage, "completed")

        current_stage = "extract"
        update_stage(job_id, current_stage, "running")
        extractions: list[dict] = []
        used_paper_ids: set[str] = set()
        for paper in papers:
            with connect() as database:
                cached = database.execute("SELECT * FROM extractions WHERE arxiv_id = ?", (paper["arxiv_id"],)).fetchone()
            if cached:
                extraction = dict(cached)
                extraction["techniques_used"] = json.loads(extraction.pop("techniques_used_json"))
                extractions.append({"arxiv_id": paper["arxiv_id"], **extraction})
                used_paper_ids.add(paper["arxiv_id"])
                continue
            try:
                _, text, _ = ingest_paper(paper["arxiv_id"])
                extraction = extract_paper(text).model_dump()
                with connect() as database:
                    database.execute("INSERT OR REPLACE INTO extractions VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (paper["arxiv_id"], extraction["problem"], extraction["method"], extraction["key_results"], extraction["contribution"], extraction["limitations"], json.dumps(extraction["techniques_used"]), now()))
                extractions.append({"arxiv_id": paper["arxiv_id"], **extraction})
                used_paper_ids.add(paper["arxiv_id"])
            except Exception as error:
                logger.exception("Extraction failed for paper %s in job %s: %s", paper["arxiv_id"], job_id, error)
                continue
        if not extractions:
            raise RuntimeError("All paper extractions failed.")
        update_stage(job_id, current_stage, "completed")

        current_stage = "synthesize"
        update_stage(job_id, current_stage, "running")
        landscape = synthesize(extractions).model_dump()
        reading = reading_list(papers, used_paper_ids)
        with connect() as database:
            database.execute("INSERT OR REPLACE INTO landscapes (job_id, clusters_json, relationships_json, tensions_json, open_problems_json, reading_list_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)", (job_id, json.dumps(landscape["clusters"]), json.dumps(landscape["relationships"]), json.dumps(landscape["tensions"]), json.dumps(landscape["open_problems"]), json.dumps(reading), now()))
            database.execute("UPDATE jobs SET status = ? WHERE id = ?", ("completed", job_id))
        update_stage(job_id, current_stage, "completed")
    except Exception as error:
        logger.exception("Job %s failed during %s: %s", job_id, current_stage, error)
        with connect() as database:
            database.execute("UPDATE jobs SET status = ? WHERE id = ?", ("failed", job_id))
        update_stage(job_id, current_stage, "failed", str(error))
