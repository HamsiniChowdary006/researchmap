from __future__ import annotations

import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import connect, initialize_database


def main() -> None:
    database_path = Path(__file__).resolve().parents[1] / "db_smoke_test.db"
    if database_path.exists():
        database_path.unlink()

    initialize_database(database_path)
    with connect(database_path) as connection:
        connection.execute(
            "INSERT INTO jobs (id, topic, papers_per_search, status, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("smoke-job", "retrieval augmented generation", 3, "queued", datetime.now(UTC).isoformat()),
        )
        row = connection.execute("SELECT id, topic, papers_per_search, status FROM jobs WHERE id = ?", ("smoke-job",)).fetchone()

    assert row is not None
    print(dict(row))
    print("SCHEMA_SMOKE_TEST=PASS")


if __name__ == "__main__":
    main()
