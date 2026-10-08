from __future__ import annotations

import json
import os

from dotenv import load_dotenv

load_dotenv()


def gemma():
    """Return the configured Gemma chat model, or None when no key is set."""
    api_key = os.getenv("GEMMA_API_KEY")
    if not api_key:
        return None
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it"),
        temperature=0,
        google_api_key=api_key,
    )


def structured_call(schema, prompt: str):
    model = gemma()
    if model is None:
        return None
    response = model.invoke(
        prompt + "\nReturn one JSON object only, matching this JSON Schema. Do not add markdown fences.\n"
        + json.dumps(schema.model_json_schema(), ensure_ascii=False)
    )
    content = response.content
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str):
        raise ValueError("Gemma did not return text that could be validated as JSON.")
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Gemma response did not contain a JSON object.")
    return schema.model_validate_json(content[start:end + 1])
