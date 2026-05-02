"""Unit tests for the requirement coherence validator."""
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.domain.coherence_result import CoherenceResult
from app.services.requirement_coherence_validator import (
    AnthropicCoherenceValidator,
    IncoherentRequirementError,
    RequirementCoherenceValidator,
    StubCoherenceValidator,
    _build_validator,
    _parse_coherence_response,
    get_coherence_validator,
)


@pytest.fixture(autouse=True)
def clear_validator_cache():
    _build_validator.cache_clear()
    yield
    _build_validator.cache_clear()


def test_stub_always_returns_coherent():
    validator = StubCoherenceValidator()
    result = validator.validate("anything goes here")
    assert result.is_coherent is True
    assert result.warning is None
    assert result.reason_codes == []


def test_factory_falls_back_to_stub_for_unknown_provider():
    settings = Settings(AI_PROVIDER="something_unknown", AI_JUDGE_PROVIDER="")
    validator = get_coherence_validator(settings)
    assert isinstance(validator, StubCoherenceValidator)


def test_factory_caches_per_provider_and_model():
    settings = Settings(AI_PROVIDER="stub", AI_JUDGE_PROVIDER="", AI_MODEL="", AI_JUDGE_MODEL="")
    a = get_coherence_validator(settings)
    b = get_coherence_validator(settings)
    assert a is b


def test_factory_uses_judge_provider_when_set():
    """If AI_JUDGE_PROVIDER is set, the factory uses it instead of AI_PROVIDER."""
    settings_a = Settings(AI_PROVIDER="anthropic", AI_JUDGE_PROVIDER="stub")
    validator_a = get_coherence_validator(settings_a)
    assert isinstance(validator_a, StubCoherenceValidator)


def test_parse_response_valid_json():
    raw = '{"is_coherent": true, "warning": null, "reason_codes": []}'
    result = _parse_coherence_response(raw)
    assert result.is_coherent is True
    assert result.warning is None
    assert result.reason_codes == []


def test_parse_response_incoherent_with_codes():
    raw = (
        '{"is_coherent": false, '
        '"warning": "El texto describe una escena, no software.", '
        '"reason_codes": ["non_software_request"]}'
    )
    result = _parse_coherence_response(raw)
    assert result.is_coherent is False
    assert "escena" in result.warning
    assert result.reason_codes == ["non_software_request"]


def test_parse_response_strips_markdown_fences():
    raw = '```json\n{"is_coherent": true, "warning": null, "reason_codes": []}\n```'
    result = _parse_coherence_response(raw)
    assert result.is_coherent is True


def test_parse_response_clears_codes_when_coherent():
    """If LLM mistakenly returns codes with is_coherent=true, we discard them."""
    raw = '{"is_coherent": true, "warning": "ignored", "reason_codes": ["foo"]}'
    result = _parse_coherence_response(raw)
    assert result.is_coherent is True
    assert result.warning is None
    assert result.reason_codes == []


def test_parse_response_raises_on_missing_field():
    raw = '{"warning": null, "reason_codes": []}'
    with pytest.raises(ValueError, match="is_coherent"):
        _parse_coherence_response(raw)


def test_parse_response_handles_non_list_reason_codes():
    raw = '{"is_coherent": false, "warning": "x", "reason_codes": "not a list"}'
    result = _parse_coherence_response(raw)
    assert result.is_coherent is False
    assert result.reason_codes == []


def test_anthropic_validator_invokes_client_and_parses():
    """Mock the anthropic SDK client and verify the validator wires it correctly."""
    settings = Settings(AI_PROVIDER="anthropic", ANTHROPIC_API_KEY="test-key")

    fake_message = MagicMock()
    fake_message.content = [MagicMock(text='{"is_coherent": true, "warning": null, "reason_codes": []}')]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_message

    with patch(
        "app.services.requirement_coherence_validator._anthropic_lib"
    ) as fake_lib:
        fake_lib.Anthropic.return_value = fake_client
        validator = AnthropicCoherenceValidator(settings)
        result = validator.validate("agregar login con Google")

    assert result.is_coherent is True
    fake_client.messages.create.assert_called_once()
    call_kwargs = fake_client.messages.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0
    assert call_kwargs["max_tokens"] == settings.AI_COHERENCE_MAX_TOKENS


def test_anthropic_validator_handles_techie_requirement():
    """A technical requirement should be classified as coherent."""
    settings = Settings(AI_PROVIDER="anthropic", ANTHROPIC_API_KEY="test-key")

    fake_message = MagicMock()
    fake_message.content = [MagicMock(text='{"is_coherent": true, "warning": null, "reason_codes": []}')]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_message

    with patch("app.services.requirement_coherence_validator._anthropic_lib") as fake_lib:
        fake_lib.Anthropic.return_value = fake_client
        validator = AnthropicCoherenceValidator(settings)
        result = validator.validate("Agregar endpoint POST /users con validación JWT")

    assert result.is_coherent is True


def test_anthropic_validator_handles_business_requirement():
    """A business / PO style requirement should be classified as coherent."""
    settings = Settings(AI_PROVIDER="anthropic", ANTHROPIC_API_KEY="test-key")

    fake_message = MagicMock()
    fake_message.content = [MagicMock(text='{"is_coherent": true, "warning": null, "reason_codes": []}')]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_message

    with patch("app.services.requirement_coherence_validator._anthropic_lib") as fake_lib:
        fake_lib.Anthropic.return_value = fake_client
        validator = AnthropicCoherenceValidator(settings)
        result = validator.validate(
            "quiero que los clientes reciban un correo cuando se cancele un pedido"
        )

    assert result.is_coherent is True


def test_anthropic_validator_rejects_absurd_requirement():
    settings = Settings(AI_PROVIDER="anthropic", ANTHROPIC_API_KEY="test-key")

    fake_message = MagicMock()
    fake_message.content = [
        MagicMock(
            text=(
                '{"is_coherent": false, '
                '"warning": "El texto describe una escena, no un cambio de software.", '
                '"reason_codes": ["non_software_request"]}'
            )
        )
    ]
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_message

    with patch("app.services.requirement_coherence_validator._anthropic_lib") as fake_lib:
        fake_lib.Anthropic.return_value = fake_client
        validator = AnthropicCoherenceValidator(settings)
        result = validator.validate("una casa roja al amanecer en la tarde de la playa")

    assert result.is_coherent is False
    assert "escena" in result.warning
    assert "non_software_request" in result.reason_codes


def test_incoherent_requirement_error_carries_data():
    err = IncoherentRequirementError("not actionable", ["unintelligible", "conversational"])
    assert err.warning == "not actionable"
    assert err.reason_codes == ["unintelligible", "conversational"]
    # Hereda de ValueError para compat con handlers existentes.
    assert isinstance(err, ValueError)


def test_validator_is_abstract():
    """RequirementCoherenceValidator cannot be instantiated directly."""
    with pytest.raises(TypeError):
        RequirementCoherenceValidator()  # type: ignore[abstract]


def test_coherence_result_is_frozen():
    result = CoherenceResult(is_coherent=True, warning=None, reason_codes=[])
    with pytest.raises(Exception):
        result.is_coherent = False  # type: ignore[misc]
