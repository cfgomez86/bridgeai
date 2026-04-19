import pytest
from app.services.ai_provider import AIProvider, StubAIProvider
from app.services.ai_requirement_parser import AIRequirementParser


def make_parser(provider: AIProvider = None) -> AIRequirementParser:
    return AIRequirementParser(provider or StubAIProvider())


def valid_response() -> dict:
    return {
        "intent": "create_feature",
        "action": "create",
        "entity": "user",
        "feature_type": "feature",
        "priority": "medium",
        "business_domain": "user_management",
        "technical_scope": "backend",
        "estimated_complexity": "MEDIUM",
        "keywords": ["user", "feature"],
    }


class FixedAIProvider(AIProvider):
    def __init__(self, response: dict):
        self._response = response

    def parse_requirement(self, requirement_text: str) -> dict:
        return dict(self._response)


def test_stub_provider_returns_valid_dict():
    parser = make_parser()
    result = parser.parse("Add email validation")
    assert isinstance(result, dict)
    assert "intent" in result
    assert "feature_type" in result


def test_valid_response_passes_validation():
    parser = make_parser(FixedAIProvider(valid_response()))
    result = parser.parse("Any requirement")
    assert result["feature_type"] == "feature"
    assert result["estimated_complexity"] == "MEDIUM"


def test_missing_field_raises_value_error():
    incomplete = valid_response()
    del incomplete["intent"]
    parser = make_parser(FixedAIProvider(incomplete))
    with pytest.raises(ValueError, match="missing required fields"):
        parser.parse("requirement")


def test_invalid_feature_type_raises_value_error():
    bad = valid_response()
    bad["feature_type"] = "unknown_type"
    parser = make_parser(FixedAIProvider(bad))
    with pytest.raises(ValueError, match="feature_type"):
        parser.parse("requirement")


def test_invalid_estimated_complexity_raises_value_error():
    bad = valid_response()
    bad["estimated_complexity"] = "medium"  # should be uppercase
    parser = make_parser(FixedAIProvider(bad))
    with pytest.raises(ValueError, match="estimated_complexity"):
        parser.parse("requirement")


def test_invalid_business_domain_raises_value_error():
    bad = valid_response()
    bad["business_domain"] = "unknown_domain"
    parser = make_parser(FixedAIProvider(bad))
    with pytest.raises(ValueError, match="business_domain"):
        parser.parse("requirement")


def test_keywords_not_list_raises_value_error():
    bad = valid_response()
    bad["keywords"] = "user, feature"
    parser = make_parser(FixedAIProvider(bad))
    with pytest.raises(ValueError, match="keywords"):
        parser.parse("requirement")
