import httpx
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
        "acceptance_criteria": [
            "Given an unauthenticated visitor, When they submit the form with a valid email, Then the account is created and a confirmation message is shown.",
            "Given a duplicate email, When the form is submitted, Then the user sees an error message indicating the email is already in use.",
            "Given a successful registration, When it completes, Then a confirmation email is sent to the user and remains valid for 24 hours.",
        ],
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
    """Simulates a transient (retryable) network failure followed by success."""

    def __init__(self, fail_times: int = 1):
        self._fail_times = fail_times
        self._calls = 0

    def generate_story(self, context: dict) -> dict:
        self._calls += 1
        if self._calls <= self._fail_times:
            raise httpx.ConnectError("Simulated transient network failure")
        return valid_story()


class AlwaysFailValueErrorProvider(StoryAIProvider):
    """Simulates a deterministic (non-retryable) error like JSON parse failure."""

    def __init__(self):
        self.calls = 0

    def generate_story(self, context: dict) -> dict:
        self.calls += 1
        raise ValueError("Invalid JSON from AI provider: ...")


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
    from app.services.ai_story_generator import TransientGenerationError
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=1)
    provider = FailThenSucceedProvider(fail_times=10)
    gen = AIStoryGenerator(provider, settings)
    with pytest.raises(TransientGenerationError, match="Story generation failed after"):
        gen.generate({})
    assert provider._calls == 2  # initial + 1 retry


def test_non_retryable_error_fails_fast_without_retries():
    """ValueError (parse/shape) must fail fast, not retry."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    provider = AlwaysFailValueErrorProvider()
    gen = AIStoryGenerator(provider, settings)
    with pytest.raises(ValueError, match="Invalid JSON from AI provider"):
        gen.generate({})
    assert provider.calls == 1  # no retry on deterministic error


def test_shape_validation_error_fails_fast():
    """Missing required field must fail fast, not retry 3 times."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    bad = valid_story()
    del bad["title"]

    class CountingProvider(StoryAIProvider):
        def __init__(self, response):
            self.response = response
            self.calls = 0

        def generate_story(self, context):
            self.calls += 1
            return dict(self.response)

    provider = CountingProvider(bad)
    gen = AIStoryGenerator(provider, settings)
    with pytest.raises(ValueError, match="missing required fields"):
        gen.generate({})
    assert provider.calls == 1  # no retry


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


# ─── Quality checks: G/W/T acceptance criteria + explicit frontend ────────


class CountingProvider(StoryAIProvider):
    """Returns a different response per call to simulate retry behaviour."""

    def __init__(self, responses: list):
        self._responses = list(responses)
        self.calls = 0
        self.contexts: list[dict] = []

    def generate_story(self, context: dict) -> dict:
        self.contexts.append(dict(context))
        idx = min(self.calls, len(self._responses) - 1)
        self.calls += 1
        return dict(self._responses[idx])


def _ac_legacy() -> list[str]:
    return ["Email is validated", "Password is hashed", "User receives confirmation"]


def test_valid_gwt_ac_passes_quality_check():
    gen = make_generator(FixedStoryProvider(valid_story()))
    result = gen.generate({})
    assert result["title"] == "User Registration"


def test_legacy_ac_triggers_retry_then_succeeds():
    """If the first response has free-form AC but the second has G/W/T, we
    retry and end up with the good story."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    bad = valid_story()
    bad["acceptance_criteria"] = _ac_legacy()
    provider = CountingProvider([bad, valid_story()])
    gen = AIStoryGenerator(provider, settings)
    result = gen.generate({})
    assert provider.calls == 2
    assert "Given" in result["acceptance_criteria"][0]
    # The second prompt must include the quality reason
    assert "Given/When/Then" in (provider.contexts[1].get("quality_warning_reason") or "")


def test_legacy_ac_falls_back_after_max_retries():
    """If every attempt has bad AC, we don't crash — we return the last
    shape-valid response and log a warning."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=1)
    bad = valid_story()
    bad["acceptance_criteria"] = _ac_legacy()
    provider = CountingProvider([bad])
    gen = AIStoryGenerator(provider, settings)
    result = gen.generate({})
    assert provider.calls == 2  # initial + 1 retry
    # We get a story back even though AC quality is suboptimal
    assert result["acceptance_criteria"] == _ac_legacy()


def test_ac_check_accepts_spanish_gwt():
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=0)
    story = valid_story()
    story["acceptance_criteria"] = [
        "Dado un usuario nuevo, Cuando se registra, Entonces se crea la cuenta y se muestra el mensaje 'Cuenta creada'.",
        "Dado un email duplicado, Cuando envía el formulario, Entonces se muestra un error indicando que el email ya está registrado.",
        "Dado un registro exitoso, Cuando termina, Entonces se envía un email de confirmación al usuario.",
    ]
    gen = AIStoryGenerator(FixedStoryProvider(story), settings)
    result = gen.generate({})
    assert "Dado" in result["acceptance_criteria"][0]


def test_backend_only_story_keeps_frontend_empty():
    """If the context has NO UI signals, an empty frontend array is allowed
    and must NOT trigger a quality retry."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    story = valid_story()
    story["subtasks"]["frontend"] = []
    provider = CountingProvider([story])
    gen = AIStoryGenerator(provider, settings)
    result = gen.generate({
        "requirement_text": "Add a nightly cron job that recomputes statistics",
        "intent": "schedule recurring backend job",
        "feature_type": "backend",
        "keywords": ["cron", "stats", "scheduler"],
    })
    assert provider.calls == 1  # no retry
    assert result["subtasks"]["frontend"] == []


def test_ui_story_with_empty_frontend_triggers_retry():
    """When the requirement clearly involves UI but the response leaves
    frontend empty, we retry asking explicitly for frontend tasks."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    bad = valid_story()
    bad["subtasks"]["frontend"] = []
    provider = CountingProvider([bad, valid_story()])
    gen = AIStoryGenerator(provider, settings)
    result = gen.generate({
        "requirement_text": "Add a registration form for new users",
        "keywords": ["registro", "formulario"],
    })
    assert provider.calls == 2
    assert len(result["subtasks"]["frontend"]) >= 1
    # Second prompt got a quality reason about frontend
    second_reason = provider.contexts[1].get("quality_warning_reason") or ""
    assert "frontend" in second_reason.lower()


def test_ui_story_with_populated_frontend_passes():
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=0)
    provider = CountingProvider([valid_story()])
    gen = AIStoryGenerator(provider, settings)
    result = gen.generate({
        "requirement_text": "Build a dashboard with login form",
        "keywords": ["dashboard", "login"],
    })
    assert provider.calls == 1
    assert result["subtasks"]["frontend"]


def test_ambiguous_text_does_not_trigger_ui_retry():
    """'lista' / 'list' alone is ambiguous (could be a list of records in a
    backend report). The conservative pattern must not match it."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    story = valid_story()
    story["subtasks"]["frontend"] = []
    provider = CountingProvider([story])
    gen = AIStoryGenerator(provider, settings)
    result = gen.generate({
        "requirement_text": "Procesar la lista de pedidos pendientes en background",
        "keywords": ["lista", "pedidos", "background"],
    })
    assert provider.calls == 1
    assert result["subtasks"]["frontend"] == []


# --- Functional AC detector ---------------------------------------------------


def test_ac_with_file_path_triggers_retry():
    """An AC referencing a source file path is implementation jargon, not PO language."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    bad = valid_story()
    bad["acceptance_criteria"] = [
        "Given a registered user, When they sign in, Then app/services/auth_service.py validates the credentials and grants access.",
        "Given a wrong password, When they sign in, Then an error message is shown.",
        "Given a successful sign-in, When it completes, Then the user lands on the welcome screen.",
    ]
    provider = CountingProvider([bad, valid_story()])
    gen = AIStoryGenerator(provider, settings)
    result = gen.generate({})
    assert provider.calls == 2
    reason = provider.contexts[1].get("quality_warning_reason") or ""
    assert "jerga técnica" in reason
    assert "auth_service.py" in reason
    # Final result is the clean retry response
    assert "Given an unauthenticated visitor" in result["acceptance_criteria"][0]


def test_ac_with_http_status_code_triggers_retry():
    """AC that mention HTTP codes (responde 201, returns 404) leak implementation."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    bad = valid_story()
    bad["acceptance_criteria"] = [
        "Given a valid request, When the form is submitted, Then the system returns 201.",
        "Given a duplicate email, When submitting, Then the API responds with 409.",
        "Given an unknown error, When it occurs, Then the system logs the failure.",
    ]
    provider = CountingProvider([bad, valid_story()])
    gen = AIStoryGenerator(provider, settings)
    gen.generate({})
    assert provider.calls == 2
    reason = provider.contexts[1].get("quality_warning_reason") or ""
    assert "jerga técnica" in reason


def test_ac_with_rest_method_and_endpoint_triggers_retry():
    """AC like 'POST /api/users' or '/v1/orders' belong in subtasks, not in AC."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    bad = valid_story()
    bad["acceptance_criteria"] = [
        "Given a registered user, When they call POST /api/users with valid data, Then the resource is created.",
        "Given an authenticated client, When they hit /v1/orders, Then the list of orders is shown.",
        "Given an unknown endpoint, When called, Then the user sees an error.",
    ]
    provider = CountingProvider([bad, valid_story()])
    gen = AIStoryGenerator(provider, settings)
    gen.generate({})
    assert provider.calls == 2


def test_ac_with_visible_ui_elements_passes():
    """Mentioning UI elements by name ('button Save', 'message Account created') is
    legitimate PO language, NOT a technicalism — the detector must accept it."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=0)
    story = valid_story()
    story["acceptance_criteria"] = [
        "Given a visitor on the registration page, When they click the 'Create account' button, Then the form is submitted and the message 'Account created' is shown for 3 seconds.",
        "Given an empty email field, When the visitor presses 'Create account', Then the field shows the error 'Email is required'.",
        "Given a successful registration, When the page reloads, Then the welcome screen is displayed.",
    ]
    provider = CountingProvider([story])
    gen = AIStoryGenerator(provider, settings)
    result = gen.generate({})
    assert provider.calls == 1  # no retry triggered
    assert "Create account" in result["acceptance_criteria"][0]


def test_ac_with_plain_numbers_does_not_trigger_retry():
    """Plain numbers like '8 characters' or '200 productos' must not be
    confused with HTTP status codes — context (a verb of response) is required."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=0)
    story = valid_story()
    story["acceptance_criteria"] = [
        "Given a password with 8 characters, When the form is submitted, Then it is accepted.",
        "Given a customer with 200 products in their cart, When they check out, Then the order is created.",
        "Given a slow network, When a request takes 500 milliseconds, Then a loading indicator is shown.",
    ]
    provider = CountingProvider([story])
    gen = AIStoryGenerator(provider, settings)
    result = gen.generate({})
    assert provider.calls == 1
    assert "8 characters" in result["acceptance_criteria"][0]


def test_technical_ac_falls_back_after_max_retries():
    """If every retry still produces technical AC, return last shape-valid story
    (best-effort) rather than crashing — same fallback as the G/W/T retry."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=1)
    bad = valid_story()
    bad["acceptance_criteria"] = [
        "Given a request to POST /api/users, When it arrives, Then app/auth.py returns 201.",
        "Given a duplicate, When posted, Then the API responds with 409.",
        "Given a server error, When triggered, Then the system returns 500.",
    ]
    provider = CountingProvider([bad])
    gen = AIStoryGenerator(provider, settings)
    result = gen.generate({})
    assert provider.calls == 2  # initial + 1 retry, both bad
    # Best-effort: returns the (technical) shape-valid story
    assert "POST /api/users" in result["acceptance_criteria"][0]


def test_find_ac_technicalisms_returns_citations():
    """The helper returns up to 5 deduped citations for the retry feedback."""
    citations = AIStoryGenerator._find_ac_technicalisms([
        "Given a request, When made, Then app/services/foo.py runs.",
        "Given a duplicate, When posted, Then the system returns 409.",
        "Given an admin, When they call POST /api/users, Then the user is created.",
    ])
    assert citations  # non-empty
    joined = " | ".join(citations)
    assert "app/services/foo.py" in joined
    assert "returns 409" in joined.lower() or "returns 409" in joined
    assert "POST /api/users" in joined


def test_find_ac_technicalisms_returns_empty_for_clean_ac():
    """Pure PO-language AC produce no citations."""
    citations = AIStoryGenerator._find_ac_technicalisms([
        "Given a visitor, When they fill the form correctly, Then the account is created.",
        "Given a duplicate email, When submitting, Then the user sees an inline error message.",
        "Given a successful sign-up, When it completes, Then a welcome screen is displayed.",
    ])
    assert citations == []


def test_stub_response_acs_are_functional():
    """The stub used as fallback / few-shot example must itself pass the detector,
    or the LLM may copy its bad pattern (returns 201, etc.) into real responses."""
    from app.services.story_ai_provider import _STUB_STORY_RESPONSE
    citations = AIStoryGenerator._find_ac_technicalisms(
        _STUB_STORY_RESPONSE["acceptance_criteria"]
    )
    assert citations == [], (
        f"Stub AC contain technical jargon: {citations}. "
        "Keep the stub as a clean PO-language example."
    )


# ─── Mechanical AC repair (mini-prompt) ───────────────────────────────────


_CLEAN_REPAIRED_AC = [
    "Given an unauthenticated visitor, When they submit the form with a valid email and a password of at least 8 characters, Then the account is created and a confirmation message is shown.",
    "Given a duplicate email, When the form is submitted, Then the user sees an inline error message.",
    "Given a successful registration, When it completes, Then a welcome screen is displayed.",
]


class RepairableProvider(StoryAIProvider):
    """Returns a bad story on generate_story; serves a clean AC list on repair."""

    def __init__(self, bad_story: dict, repair_response: list[str] | None):
        self._bad_story = bad_story
        self._repair_response = repair_response
        self.generate_calls = 0
        self.repair_calls = 0
        self.last_repair_kwargs: dict | None = None

    def generate_story(self, context: dict) -> dict:
        self.generate_calls += 1
        return dict(self._bad_story)

    def repair_acceptance_criteria(self, story: dict, reason: str, language: str):
        self.repair_calls += 1
        self.last_repair_kwargs = {
            "story_title": story.get("title"),
            "reason": reason,
            "language": language,
        }
        return list(self._repair_response) if self._repair_response else None


def test_ac_repair_succeeds_avoids_full_retry():
    """When the provider can repair AC mechanically, the loop should accept the
    repaired story without a second full-prompt regeneration."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    bad = valid_story()
    bad["acceptance_criteria"] = [
        "Given a request, When made, Then app/services/auth.py returns 201.",
        "Given a duplicate, When posted, Then the API responds with 409.",
        "Given an error, When triggered, Then the system returns 500.",
    ]
    provider = RepairableProvider(bad, _CLEAN_REPAIRED_AC)
    gen = AIStoryGenerator(provider, settings)
    result = gen.generate({"language": "en"})
    assert provider.generate_calls == 1, "no full retry needed when repair works"
    assert provider.repair_calls == 1
    assert result["acceptance_criteria"] == _CLEAN_REPAIRED_AC
    assert provider.last_repair_kwargs["language"] == "en"
    assert "jerga técnica" in provider.last_repair_kwargs["reason"]


def test_ac_repair_returning_none_falls_back_to_full_retry():
    """If repair returns None (provider can't repair), the loop must do the
    full-prompt retry just like before — preserving prior behaviour."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    bad = valid_story()
    bad["acceptance_criteria"] = [
        "Given a request, When made, Then app/services/auth.py is invoked.",
        "Given a duplicate, When posted, Then an error message is shown.",
        "Given an unknown error, When triggered, Then the user is informed.",
    ]
    provider = RepairableProvider(bad, repair_response=None)

    # After the failed repair we want the next generate_story to return a clean
    # story so the loop can succeed via full retry.
    original = provider.generate_story
    clean = valid_story()

    def fake_generate(context: dict) -> dict:
        provider.generate_calls += 1
        return dict(clean) if provider.generate_calls > 1 else dict(bad)

    provider.generate_story = fake_generate  # type: ignore[assignment]
    gen = AIStoryGenerator(provider, settings)
    result = gen.generate({"language": "es"})
    assert provider.generate_calls == 2, "fallback to full retry expected when repair fails"
    assert provider.repair_calls == 1
    assert "Given an unauthenticated visitor" in result["acceptance_criteria"][0]


def test_ac_repair_with_still_invalid_output_falls_back():
    """If the repair output STILL contains technical jargon, treat as failed
    repair and fall back to full retry."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    bad = valid_story()
    bad["acceptance_criteria"] = [
        "Given a request, When made, Then app/services/auth.py is invoked.",
        "Given a duplicate, When posted, Then an error message is shown.",
        "Given an unknown error, When triggered, Then the user is informed.",
    ]
    still_bad_repair = [
        "Given a registered user, When they sign in, Then app/services/auth_service.py validates credentials.",
        "Given a wrong password, When they sign in, Then an error is shown.",
        "Given a successful sign-in, When it completes, Then the user lands on the welcome screen.",
    ]
    provider = RepairableProvider(bad, still_bad_repair)
    clean = valid_story()
    original_generate = provider.generate_story

    def fake_generate(context: dict) -> dict:
        provider.generate_calls += 1
        return dict(clean) if provider.generate_calls > 1 else dict(bad)

    provider.generate_story = fake_generate  # type: ignore[assignment]
    gen = AIStoryGenerator(provider, settings)
    result = gen.generate({})
    assert provider.repair_calls == 1
    assert provider.generate_calls == 2  # repair invalid → fall back to full retry
    assert "Given an unauthenticated visitor" in result["acceptance_criteria"][0]


def test_ac_repair_attempted_at_most_once_per_generate():
    """Even across multiple retries, repair is attempted at most once — never
    let the loop spam the repair endpoint."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    bad = valid_story()
    bad["acceptance_criteria"] = [
        "Given a request, When made, Then /api/users returns 201.",
        "Given a duplicate, When posted, Then 409 is returned.",
        "Given an error, When triggered, Then 500 is returned.",
    ]
    provider = RepairableProvider(bad, repair_response=None)
    # Always return the same bad story to force every retry to fail.
    gen = AIStoryGenerator(provider, settings)
    gen.generate({})
    assert provider.repair_calls == 1, "repair must be attempted at most once"
    assert provider.generate_calls == 3  # initial + 2 retries (max_retries=2)


def test_ac_repair_skipped_for_frontend_missing_kind():
    """frontend_missing is not an AC quality issue — must NOT trigger AC repair,
    only a full retry that adds frontend tasks."""
    from app.core.config import Settings
    settings = Settings(DATABASE_URL="sqlite:///:memory:", AI_MAX_RETRIES=2)
    bad = valid_story()
    bad["subtasks"]["frontend"] = []  # UI context but empty frontend → triggers retry
    good = valid_story()  # has frontend tasks

    provider = RepairableProvider(bad, repair_response=_CLEAN_REPAIRED_AC)
    original = provider.generate_story

    def fake_generate(context: dict) -> dict:
        provider.generate_calls += 1
        return dict(good) if provider.generate_calls > 1 else dict(bad)

    provider.generate_story = fake_generate  # type: ignore[assignment]
    gen = AIStoryGenerator(provider, settings)
    # UI-implying context so _check_frontend_explicit fires.
    result = gen.generate({"requirement_text": "registration form for new users"})
    assert provider.repair_calls == 0, "AC repair must not run for frontend_missing"
    assert provider.generate_calls == 2  # full retry path
