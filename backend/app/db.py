"""SQLite storage helpers for ResearchMap."""

from __future__ import annotations

import sqlite3
from pathlib import Path


DATABASE_PATH = Path(__file__).resolve().parents[2] / "researchmap.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    papers_per_search INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS job_stages (
    job_id TEXT NOT NULL,
    stage_name TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    error TEXT,
    PRIMARY KEY (job_id, stage_name),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
CREATE TABLE IF NOT EXISTS papers (
    arxiv_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    abstract TEXT NOT NULL,
    authors TEXT NOT NULL,
    pdf_url TEXT NOT NULL,
    published_date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS extractions (
    arxiv_id TEXT PRIMARY KEY,
    problem TEXT NOT NULL,
    method TEXT NOT NULL,
    key_results TEXT NOT NULL,
    contribution TEXT NOT NULL,
    limitations TEXT NOT NULL,
    techniques_used_json TEXT NOT NULL,
    extracted_at TEXT NOT NULL,
    FOREIGN KEY (arxiv_id) REFERENCES papers(arxiv_id)
);
CREATE TABLE IF NOT EXISTS landscapes (
    job_id TEXT PRIMARY KEY,
    clusters_json TEXT NOT NULL,
    relationships_json TEXT NOT NULL,
    tensions_json TEXT NOT NULL,
    open_problems_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
"""


def connect(path: Path = DATABASE_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(path: Path = DATABASE_PATH) -> None:
    with connect(path) as connection:
        connection.executescript(SCHEMA)
