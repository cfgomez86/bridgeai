import pytest
from app.services.story_ai_provider import StoryAIProvider, StubStoryProvider
from app.services.ai_story_generator import AIStoryGenerator


def make_generator(provider: StoryAIProvider = None) -> AIStoryGenerator:
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    return AIStoryGenerator(provider or StubStoryProvider(), settings)


def valid_story() -> dict:
    return {
        "title": "User Registration",
        "story_description": "As a user, I want to register so that I can log in.",
        "acceptance_criteria": ["Email is validated", "Password is hashed"],
        "subtasks": {
            "frontend": ["Create registration form component"],
            "backend": ["Create POST /auth/register endpoint", "Add email validation logic"],
            "configuration": ["Add SMTP env variables to .env.example"],
        },
        "definition_of_done": ["Tests pass", "Code reviewed"],
        "risk_notes": ["Email service dependency"],
    }


class FixedStoryProvider(StoryAIProvider):
    def __init__(self, response: dict):
        self._response = response

    def generate_story(self, context: dict) -> dict:
        return dict(self._response)


class FailThenSucceedProvider(StoryAIProvider):
    def __init__(self, fail_times: int = 1):
        self._fail_times = fail_times
        self._calls = 0

    def generate_story(self, context: dict) -> dict:
        self._calls += 1
        if self._calls <= self._fail_times:
            raise ValueError("Simulated failure")
        return valid_story()


def test_stub_provider_returns_valid_dict():
    gen = make_generator()
    result = gen.generate({"requirement_text": "test"})
    assert isinstance(result, dict)
    assert "title" in result
    assert "acceptance_criteria" in result


def test_valid_response_passes_validation():
    gen = make_generator(FixedStoryProvider(valid_story()))
    result = gen.generate({})
    assert result["title"] == "User Registration"


def test_missing_title_raises_value_error():
    bad = valid_story()
    del bad["title"]
    gen = make_generator(FixedStoryProvider(bad))
    with pytest.raises(ValueError, match="missing required fields"):
        gen.generate({})


def test_empty_story_description_raises_value_error():
    bad = valid_story()
    bad["story_description"] = "   "
    gen = make_generator(FixedStoryProvider(bad))
    with pytest.raises(ValueError, match="story_description"):
        gen.generate({})


def test_empty_acceptance_criteria_raises_value_error():
    bad = valid_story()
    bad["acceptance_criteria"] = []
    gen = make_generator(FixedStoryProvider(bad))
    with pytest.raises(ValueError, match="acceptance_criteria"):
        gen.generate({})


def test_retry_succeeds_on_second_attempt():
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    provider = FailThenSucceedProvider(fail_times=1)
    gen = AIStoryGenerator(provider, settings)
    result = gen.generate({})
    assert result["title"] == "User Registration"
    assert provider._calls == 2


def test_raises_after_max_retries():
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=1)
    provider = FailThenSucceedProvider(fail_times=10)
    gen = AIStoryGenerator(provider, settings)
    with pytest.raises(ValueError, match="Story generation failed after"):
        gen.generate({})
