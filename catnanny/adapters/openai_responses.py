"""Responses REST API adapter. No credentials or raw upstream errors in responses."""
import json
from pathlib import Path

import httpx
from pydantic import ValidationError

from catnanny.domain.extraction import ExtractionError, ExtractionResult

PROMPT = (Path(__file__).resolve().parents[1] / "prompts" / "extract_observations.txt").read_text(encoding="utf-8")


def extract_with_responses(text: str, context: dict, settings) -> ExtractionResult:
    return call_structured_response(text,context,settings,ExtractionResult,PROMPT,"cat_observation_patch")


def call_structured_response(text, context, settings, output_model, instructions, schema_name):
    if not settings.api_key or not settings.model:
        raise ExtractionError("ai_not_configured", "AI extraction is not configured on the server.", 503)
    body = {
        "model": settings.model,
        "store": False,
        "instructions": instructions,
        "input": [{"role": "user", "content": json.dumps(
            {"context": context, "latest_message": text}, ensure_ascii=False)}],
        "text": {"format": {"type": "json_schema", "name": schema_name,
                            "strict": True, "schema": output_model.model_json_schema()}},
        "max_output_tokens": 1600,
    }
    # This extraction task does not need extended reasoning. Keep the selected
    # low-cost model within the small output budget and reduce latency.
    if settings.model == "gpt-5.6-luna":
        body["reasoning"] = {"effort": "none"}
    try:
        with httpx.Client(timeout=settings.timeout_seconds) as client:
            response = client.post("https://api.openai.com/v1/responses", json=body,
                headers={"Authorization": f"Bearer {settings.api_key.get_secret_value()}"})
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise ExtractionError("ai_timeout", "AI extraction timed out; retry this request.", 504) from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        code = "ai_rate_limited" if status == 429 else "ai_upstream_error"
        raise ExtractionError(code, "AI extraction is temporarily unavailable.", 503 if status == 429 else 502) from exc
    except httpx.RequestError as exc:
        raise ExtractionError("ai_connection_error", "Cannot reach the AI extraction service.", 503) from exc
    try:
        data = response.json()
        if data.get("status") != "completed":
            raise ExtractionError("ai_incomplete", "AI extraction did not complete.")
        chunks = []
        for item in data.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "refusal":
                    raise ExtractionError("ai_refusal", "AI could not extract this message.")
                if content.get("type") == "output_text":
                    chunks.append(content["text"])
        return output_model.model_validate_json("".join(chunks), strict=True)
    except (ValueError, TypeError, KeyError, AttributeError, ValidationError) as exc:
        raise ExtractionError("ai_invalid_output", "AI returned an invalid observation structure.") from exc
