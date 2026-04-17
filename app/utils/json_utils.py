import json
import re


def parse_json_field(value: str) -> list:
    """Parse a JSON-encoded list stored as a text column."""
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text.strip())
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON from AI provider: {raw_text[:200]}")
