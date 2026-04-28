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
            "frontend": [
                {
                    "title": "Create registration form component",
                    "description": "Build a React form with email and password inputs and a submit handler.\n\nVerify: render the page in dev and submit valid and invalid data.",
                },
            ],
            "backend": [
                {
                    "title": "Create POST register endpoint",
                    "description": "Define the FastAPI route that accepts an email and password, validates format and persists the user.\n\nVerify by exercising the route with valid and invalid input.",
                },
                {
                    "title": "Add email validation logic",
                    "description": "Implement email format validation in the auth service before persisting.\n\nVerify: unit tests for invalid emails return 400.",
                },
            ],
            "configuration": [
                {
                    "title": "Add SMTP env variables to env example",
                    "description": "Document SMTP_HOST, SMTP_PORT and SMTP_USER in the example env file.\n\nVerify: copy the example env and start the app without errors.",
                },
            ],
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


# ─── New subtask shape: title + description ───────────────────────────────


def test_string_subtask_item_is_rejected():
    bad = valid_story()
    bad["subtasks"]["backend"] = ["This is a legacy plain string subtask"]
    gen = make_generator(FixedStoryProvider(bad))
    with pytest.raises(ValueError, match="must be an object with 'title' and 'description'"):
        gen.generate({})


def test_subtask_with_empty_title_is_rejected():
    bad = valid_story()
    bad["subtasks"]["backend"][0]["title"] = "   "
    gen = make_generator(FixedStoryProvider(bad))
    with pytest.raises(ValueError, match="title cannot be empty"):
        gen.generate({})


def test_subtask_with_short_title_is_rejected():
    bad = valid_story()
    bad["subtasks"]["backend"][0]["title"] = "tiny"
    gen = make_generator(FixedStoryProvider(bad))
    with pytest.raises(ValueError, match="title must be at least"):
        gen.generate({})


def test_subtask_with_too_long_title_is_rejected():
    bad = valid_story()
    bad["subtasks"]["backend"][0]["title"] = "x" * 200
    gen = make_generator(FixedStoryProvider(bad))
    with pytest.raises(ValueError, match="title must be at most"):
        gen.generate({})


def test_subtask_with_empty_description_is_rejected():
    bad = valid_story()
    bad["subtasks"]["backend"][0]["description"] = "   "
    gen = make_generator(FixedStoryProvider(bad))
    with pytest.raises(ValueError, match="description cannot be empty"):
        gen.generate({})


def test_subtask_with_short_description_is_rejected():
    bad = valid_story()
    bad["subtasks"]["backend"][0]["description"] = "too short"
    gen = make_generator(FixedStoryProvider(bad))
    with pytest.raises(ValueError, match="description must be at least"):
        gen.generate({})


def test_strip_invalid_paths_preserves_newlines_in_description():
    """When the LLM hallucinates a path and we exhaust retries, _strip_invalid_paths
    must clean the description without collapsing the \\n\\n paragraph separators."""
    from app.core.config import Settings
    bad = valid_story()
    bad["subtasks"]["backend"] = [
        {
            "title": "Add registration handler in app/fake/path.py",
            "description": "First paragraph explaining what to do.\n\nSecond paragraph with steps.\n\nFinal paragraph in app/fake/path.py with verification.",
        },
    ]
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=0)
    gen = AIStoryGenerator(FixedStoryProvider(bad), settings)
    result = gen.generate({"available_file_paths": ["app/real/known.py"]})
    backend = result["subtasks"]["backend"]
    assert len(backend) == 1
    # The paragraph separators must survive
    assert "\n\n" in backend[0]["description"]
    # The fake path must be gone
    assert "app/fake/path.py" not in backend[0]["description"]
    assert "app/fake/path.py" not in backend[0]["title"]


def test_hallucinated_path_in_description_triggers_retry():
    """The path detector must scan title+description, not just one field."""
    bad = valid_story()
    bad["subtasks"]["backend"][0]["description"] = (
        "Edit app/totally/fake.py to add the handler.\n\nVerify with pytest."
    )
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=0)
    gen = AIStoryGenerator(FixedStoryProvider(bad), settings)
    # With 0 retries, _strip_invalid_paths runs and removes the fake path
    result = gen.generate({"available_file_paths": ["app/real/known.py"]})
    assert "app/totally/fake.py" not in result["subtasks"]["backend"][0]["description"]
