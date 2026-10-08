from __future__ import annotations

import json
import os

from dotenv import load_dotenv

load_dotenv()

_cached_model = None


def gemma():
    """Return the configured Gemma chat model, or None when no key is set."""
    global _cached_model
    api_key = os.getenv("GEMMA_API_KEY")
    if not api_key:
        return None
    if _cached_model is not None:
        return _cached_model
    from langchain_google_genai import ChatGoogleGenerativeAI

    _cached_model = ChatGoogleGenerativeAI(
        model=os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it"),
        temperature=0,
        google_api_key=api_key,
        max_output_tokens=1024,
        timeout=30,
    )
    return _cached_model


def structured_call(schema, prompt: str):
    model = gemma()
    if model is None:
        return None
    try:
        response = model.invoke(
            prompt + "\nReturn one JSON object only, matching this JSON Schema. Do not add markdown fences.\n"
            + json.dumps(schema.model_json_schema(), ensure_ascii=False)
        )
    except Exception:
        return None
    content = response.content
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str):
        return None
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        return schema.model_validate_json(content[start:end + 1])
    except Exception:
        return None
