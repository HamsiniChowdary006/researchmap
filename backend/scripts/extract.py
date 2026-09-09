"""Extract structured research facts from cached paper text with Gemini."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas import Extraction


load_dotenv(Path(__file__).resolve().parents[2] / ".env")
logger = logging.getLogger(__name__)


def _log_gemini_error(operation: str, error: Exception) -> None:
    response = getattr(error, "response", None)
    status = getattr(error, "status_code", None) or getattr(response, "status_code", None)
    body = getattr(response, "text", None) or getattr(error, "body", None)
    logger.exception("Gemini %s failed: status=%r, response_body=%r, message=%s", operation, status, body, error)


def gemini_schema(value: object) -> object:
    if isinstance(value, dict):
        return {key: gemini_schema(item) for key, item in value.items() if key not in {"title", "default", "$defs"}}
    if isinstance(value, list):
        return [gemini_schema(item) for item in value]
    return value


def extract_paper(text: str) -> Extraction:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required in .env")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3.6-flash")
    prompt = (
        "Extract the following ML research paper into concise factual fields. "
        "Use only evidence from the supplied text.\n\nPAPER TEXT:\n" + text[:60000]
    )
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": gemini_schema(Extraction.model_json_schema()),
                },
            )
            return Extraction.model_validate_json(response.text)
        except Exception as error:
            last_error = error
            _log_gemini_error("extraction", error)
            if attempt == 2:
                break
            time.sleep(2**attempt)
    raise RuntimeError(f"Gemini extraction failed after 3 attempts: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text_file", type=Path)
    arguments = parser.parse_args()
    extraction = extract_paper(arguments.text_file.read_text(encoding="utf-8"))
    print(json.dumps(extraction.model_dump(), indent=2, ensure_ascii=True))
    print("EXTRACTION_VALIDATION=PASS")


if __name__ == "__main__":
    main()
