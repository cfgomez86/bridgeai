from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.story_ai_provider import (
    AnthropicStoryProvider,
    GeminiStoryProvider,
    OpenAIStoryProvider,
)
from app.services.ai_story_generator import AIStoryGenerator
from app.services.story_ai_provider import StoryAIProvider
from app.utils.json_utils import extract_json

_VALID_STORY_JSON = """{
    "title": "User Registration",
    "story_description": "As a user, I want to register so that I can access the platform.",
    "acceptance_criteria": ["Criterion 1", "Criterion 2", "Criterion 3"],
    "subtasks": {
        "frontend": [
            {"title": "Create form component", "description": "Render the form and wire submit handler."}
        ],
        "backend": [
            {"title": "Task 1", "description": "Define the auth route."},
            {"title": "Task 2", "description": "Validate the email format."},
            {"title": "Task 3", "description": "Persist the user record."}
        ],
        "configuration": []
    },
    "definition_of_done": ["Done 1", "Done 2", "Done 3"],
    "risk_notes": []
}"""

_REQUIRED_FIELDS = {
    "title", "story_description", "acceptance_criteria",
    "subtasks", "definition_of_done", "risk_notes",
}

_CONTEXT = {
    "requirement_text": "Add user registration",
    "intent": "create_user",
    "feature_type": "feature",
    "business_domain": "authentication",
    "estimated_complexity": "MEDIUM",
    "keywords": ["user", "registration"],
    "files_impacted": 3,
    "modules_impacted": 2,
    "risk_level": "LOW",
}


# --- extract_json tests ---

def test_extract_json_handles_plain_json():
    result = extract_json('{"key": "value"}')
    assert result == {"key": "value"}


def test_extract_json_handles_markdown_fences():
    result = extract_json('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_extract_json_raises_on_invalid():
    with pytest.raises(ValueError, match="Invalid JSON"):
        extract_json("not json")


# --- AnthropicStoryProvider tests ---

def _make_anthropic_settings(model="claude-haiku-4-5-20251001"):
    settings = MagicMock()
    settings.ANTHROPIC_API_KEY = "test-key"
    settings.AI_MODEL = model
    settings.AI_TIMEOUT_SECONDS = 30
    return settings


def test_anthropic_story_provider_returns_valid_dict():
    settings = _make_anthropic_settings()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=_VALID_STORY_JSON)]

    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_response
        provider = AnthropicStoryProvider(settings)
        result = provider.generate_story(_CONTEXT)

    assert isinstance(result, dict)
    assert _REQUIRED_FIELDS.issubset(result.keys())


def test_anthropic_story_provider_handles_markdown_fences():
    settings = _make_anthropic_settings()
    fenced = f"```json\n{_VALID_STORY_JSON}\n```"
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=fenced)]

    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_response
        provider = AnthropicStoryProvider(settings)
        result = provider.generate_story(_CONTEXT)

    assert isinstance(result, dict)
    assert "title" in result


def test_anthropic_story_provider_raises_on_invalid_json():
    settings = _make_anthropic_settings()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json at all")]

    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_response
        provider = AnthropicStoryProvider(settings)
        with pytest.raises(ValueError, match="Invalid JSON"):
            provider.generate_story(_CONTEXT)


# --- OpenAIStoryProvider tests ---

def _make_openai_settings(model="gpt-4o-mini"):
    settings = MagicMock()
    settings.OPENAI_API_KEY = "test-key"
    settings.AI_MODEL = model
    settings.AI_TIMEOUT_SECONDS = 30
    return settings


def test_openai_story_provider_returns_valid_dict():
    settings = _make_openai_settings()
    mock_message = MagicMock()
    mock_message.content = _VALID_STORY_JSON
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("openai.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.chat.completions.create.return_value = mock_response
        provider = OpenAIStoryProvider(settings)
        result = provider.generate_story(_CONTEXT)

    assert isinstance(result, dict)
    assert _REQUIRED_FIELDS.issubset(result.keys())


def test_openai_story_provider_raises_on_invalid_json():
    settings = _make_openai_settings()
    mock_message = MagicMock()
    mock_message.content = "totally not json"
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("openai.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.chat.completions.create.return_value = mock_response
        provider = OpenAIStoryProvider(settings)
        with pytest.raises(ValueError, match="Invalid JSON"):
            provider.generate_story(_CONTEXT)


# --- GeminiStoryProvider tests ---

def _make_gemini_settings(model="gemini-2.0-flash"):
    settings = MagicMock()
    settings.GEMINI_API_KEY = "test-key"
    settings.AI_MODEL = model
    settings.AI_MAX_OUTPUT_TOKENS = 8192
    return settings


def test_gemini_story_provider_returns_valid_dict():
    settings = _make_gemini_settings()
    mock_candidate = MagicMock()
    mock_candidate.finish_reason.name = "STOP"
    mock_response = MagicMock()
    mock_response.text = _VALID_STORY_JSON
    mock_response.candidates = [mock_candidate]

    with patch("google.genai.Client") as MockClient:
        MockClient.return_value.models.generate_content.return_value = mock_response
        provider = GeminiStoryProvider(settings)
        result = provider.generate_story(_CONTEXT)

    assert isinstance(result, dict)
    assert _REQUIRED_FIELDS.issubset(result.keys())


def test_gemini_story_provider_raises_on_truncation():
    settings = _make_gemini_settings()
    mock_candidate = MagicMock()
    mock_candidate.finish_reason.name = "MAX_TOKENS"
    mock_response = MagicMock()
    mock_response.text = _VALID_STORY_JSON
    mock_response.candidates = [mock_candidate]

    with patch("google.genai.Client") as MockClient:
        MockClient.return_value.models.generate_content.return_value = mock_response
        provider = GeminiStoryProvider(settings)
        with pytest.raises(ValueError, match="truncated"):
            provider.generate_story(_CONTEXT)


def test_gemini_story_provider_raises_on_invalid_json():
    settings = _make_gemini_settings()
    mock_candidate = MagicMock()
    mock_candidate.finish_reason.name = "STOP"
    mock_response = MagicMock()
    mock_response.text = "not valid json"
    mock_response.candidates = [mock_candidate]

    with patch("google.genai.Client") as MockClient:
        MockClient.return_value.models.generate_content.return_value = mock_response
        provider = GeminiStoryProvider(settings)
        with pytest.raises(ValueError, match="Invalid JSON"):
            provider.generate_story(_CONTEXT)


def test_gemini_story_provider_uses_json_mime_type():
    settings = _make_gemini_settings()
    mock_candidate = MagicMock()
    mock_candidate.finish_reason.name = "STOP"
    mock_response = MagicMock()
    mock_response.text = _VALID_STORY_JSON
    mock_response.candidates = [mock_candidate]

    with patch("google.genai.Client") as MockClient:
        MockClient.return_value.models.generate_content.return_value = mock_response
        provider = GeminiStoryProvider(settings)
        provider.generate_story(_CONTEXT)

    call_kwargs = MockClient.return_value.models.generate_content.call_args.kwargs
    assert call_kwargs["config"].response_mime_type == "application/json"


# --- Retry tests ---

class _FailThenSucceedStoryProvider(StoryAIProvider):
    def __init__(self, fail_times: int) -> None:
        self._calls = 0
        self._fail_times = fail_times

    def generate_story(self, context: dict) -> dict:
        self._calls += 1
        if self._calls <= self._fail_times:
            raise httpx.ConnectError("Simulated transient network failure")
        return {
            "title": "Test Story",
            "story_description": "As a user, I want X so that Y.",
            "acceptance_criteria": ["AC1", "AC2", "AC3"],
            "subtasks": {
                "frontend": [],
                "backend": [
                    {"title": "Define the API route", "description": "Create the FastAPI handler for this feature."},
                    {"title": "Add input validation", "description": "Validate request payloads with Pydantic models."},
                    {"title": "Persist the record", "description": "Use the repository to write the row to the database."},
                ],
                "configuration": [],
            },
            "definition_of_done": ["D1", "D2", "D3"],
            "risk_notes": [],
        }


class _AlwaysFailStoryProvider(StoryAIProvider):
    def generate_story(self, context: dict) -> dict:
        raise httpx.ConnectError("Always fails")


def _make_settings_with_retries(max_retries: int) -> MagicMock:
    settings = MagicMock()
    settings.AI_MAX_RETRIES = max_retries
    return settings


def test_story_generator_retries_on_failure_then_succeeds():
    provider = _FailThenSucceedStoryProvider(fail_times=1)
    generator = AIStoryGenerator(provider=provider, settings=_make_settings_with_retries(2))
    result = generator.generate(_CONTEXT)
    assert result["title"] == "Test Story"


def test_story_generator_raises_after_max_retries():
    from app.services.ai_story_generator import TransientGenerationError
    provider = _AlwaysFailStoryProvider()
    generator = AIStoryGenerator(provider=provider, settings=_make_settings_with_retries(0))
    with pytest.raises(TransientGenerationError, match="Story generation failed after"):
        generator.generate(_CONTEXT)
