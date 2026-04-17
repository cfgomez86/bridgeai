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


def _fix_mojibake(obj: object) -> object:
    """Recursively fix UTF-8 bytes misread as Latin-1 (common in LLM output)."""
    if isinstance(obj, str):
        try:
            return obj.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return obj
    if isinstance(obj, list):
        return [_fix_mojibake(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _fix_mojibake(v) for k, v in obj.items()}
    return obj


def extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text.strip())
    try:
        parsed = json.loads(text.strip())
        return _fix_mojibake(parsed)  # type: ignore[return-value]
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON from AI provider: {raw_text[:200]}")
