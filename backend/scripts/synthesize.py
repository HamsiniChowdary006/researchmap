"""Synthesize extracted papers into a research landscape with Gemini."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.schemas import Extraction, Landscape

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
logger = logging.getLogger(__name__)


def _log_gemini_error(error: Exception) -> None:
    response = getattr(error, "response", None)
    status = getattr(error, "status_code", None) or getattr(response, "status_code", None)
    body = getattr(response, "text", None) or getattr(error, "body", None)
    logger.exception("Gemini synthesis failed: status=%r, response_body=%r, message=%s", status, body, error)


def _schema(value: object) -> object:
    if isinstance(value, dict):
        return {key: _schema(item) for key, item in value.items() if key not in {"title", "default", "$defs"}}
    if isinstance(value, list):
        return [_schema(item) for item in value]
    return value


def synthesize(extractions: list[dict]) -> Landscape:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is required in .env")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-3.6-flash")
    prompt = "Synthesize this ML research set into clusters, relationships, tensions, and open problems. Return only structured facts.\n\n" + json.dumps(extractions)
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json", "response_schema": {"type": "object", "properties": {"clusters": {"type": "array", "items": {"type": "object", "properties": {"name": {"type": "string"}, "description": {"type": "string"}, "paper_indices": {"type": "array", "items": {"type": "integer"}}}, "required": ["name", "description", "paper_indices"]}}, "relationships": {"type": "array", "items": {"type": "object", "properties": {"source_cluster": {"type": "string"}, "target_cluster": {"type": "string"}, "relationship": {"type": "string"}}, "required": ["source_cluster", "target_cluster", "relationship"]}}, "tensions": {"type": "array", "items": {"type": "string"}}, "open_problems": {"type": "array", "items": {"type": "string"}}}, "required": ["clusters", "relationships", "tensions", "open_problems"]}})
            return Landscape.model_validate_json(response.text)
        except Exception as error:
            last_error = error
            _log_gemini_error(error)
            time.sleep(2**attempt)
    raise RuntimeError(f"Gemini synthesis failed: {last_error}")


if __name__ == "__main__":
    samples = [
        Extraction(problem="RAG image generation", method="AR-RAG", key_results="Improved image benchmarks", contribution="Patch retrieval", limitations="Retrieval overhead", techniques_used=["RAG", "FAISS"]).model_dump(),
        Extraction(problem="Automated literature reviews", method="LLM RAG", key_results="Best ROUGE-1", contribution="Pipeline comparison", limitations="Single dataset", techniques_used=["RAG", "GPT-3.5", "SciTLDR"]).model_dump(),
        Extraction(problem="Reliable retrieval", method="Dense retrieval", key_results="Improves evidence use", contribution="Retrieval evaluation", limitations="Domain shift", techniques_used=["retrieval", "transformers"]).model_dump(),
    ]
    print(json.dumps(synthesize(samples).model_dump(), indent=2, ensure_ascii=True))
    print("SYNTHESIS_VALIDATION=PASS")
