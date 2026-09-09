"""Download one arXiv paper and extract its text into the local cache."""

from __future__ import annotations

import argparse
from pathlib import Path

import fitz
import requests


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "pdfs"


def normalized_id(arxiv_id: str) -> str:
    return arxiv_id.replace("/", "_").replace(".", "_")


def ingest_paper(arxiv_id: str) -> tuple[Path, str, str]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    paper_id = normalized_id(arxiv_id)
    pdf_path = DATA_DIR / f"{paper_id}.pdf"
    text_path = DATA_DIR / f"{paper_id}.txt"
    if not pdf_path.exists():
        response = requests.get(f"https://arxiv.org/pdf/{arxiv_id}", timeout=60)
        response.raise_for_status()
        pdf_path.write_bytes(response.content)

    document = fitz.open(pdf_path)
    text = "\n".join(page.get_text() for page in document)
    source = "pdf"
    if len(text.strip()) < 1000:
        response = requests.get(f"https://export.arxiv.org/api/query?id_list={arxiv_id}", timeout=30)
        response.raise_for_status()
        text = response.text
        source = "arxiv_api_fallback"
    text_path.write_text(text, encoding="utf-8")
    return text_path, text, source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arxiv_id")
    arguments = parser.parse_args()
    path, text, source = ingest_paper(arguments.arxiv_id)
    print(f"CACHE_PATH={path}")
    print(f"TEXT_SOURCE={source}")
    print(f"TEXT_LENGTH={len(text)}")
    print("TEXT_SNIPPET=" + " ".join(text.split())[:500])


if __name__ == "__main__":
    main()
