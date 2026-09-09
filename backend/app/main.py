from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.db import connect, initialize_database
from app.pipeline import STAGES, run_job


app = FastAPI(title="ResearchMap API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


@app.on_event("startup")
def startup() -> None:
    initialize_database()


class SearchRequest(BaseModel):
    topic: str = Field(min_length=2)
    papers_per_search: int = Field(default=15, ge=1, le=40)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/search")
def search(request: SearchRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    job_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).isoformat()
    with connect() as database:
        database.execute("INSERT INTO jobs VALUES (?, ?, ?, ?, ?)", (job_id, request.topic, request.papers_per_search, "queued", created_at))
        database.executemany("INSERT INTO job_stages (job_id, stage_name, status) VALUES (?, ?, ?)", [(job_id, stage, "pending") for stage in STAGES])
    background_tasks.add_task(run_job, job_id, request.topic, request.papers_per_search)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def job(job_id: str) -> dict:
    with connect() as database:
        job_row = database.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        stages = database.execute("SELECT stage_name, status, started_at, finished_at, error FROM job_stages WHERE job_id = ? ORDER BY rowid", (job_id,)).fetchall()
    if not job_row:
        raise HTTPException(404, "Job not found")
    return {"job": dict(job_row), "stages": [dict(stage) for stage in stages]}


@app.get("/api/landscape/{job_id}")
def landscape(job_id: str) -> dict:
    with connect() as database:
        row = database.execute("SELECT * FROM landscapes WHERE job_id = ?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Landscape not ready")
    return {"job_id": job_id, "clusters": json.loads(row["clusters_json"]), "relationships": json.loads(row["relationships_json"]), "tensions": json.loads(row["tensions_json"]), "open_problems": json.loads(row["open_problems_json"]), "reading_list": json.loads(row["reading_list_json"])}


@app.get("/api/papers/{arxiv_id}")
def paper(arxiv_id: str) -> dict:
    with connect() as database:
        paper_row = database.execute("SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,)).fetchone()
        extraction = database.execute("SELECT * FROM extractions WHERE arxiv_id = ?", (arxiv_id,)).fetchone()
    if not paper_row:
        raise HTTPException(404, "Paper not found")
    result = dict(paper_row)
    result["authors"] = json.loads(result["authors"])
    if extraction:
        result["extraction"] = dict(extraction)
        result["extraction"]["techniques_used"] = json.loads(result["extraction"].pop("techniques_used_json"))
    return result
