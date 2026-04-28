"""Unit tests for story_quality_judge."""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.domain.user_story import UserStory
from app.services.story_quality_judge import (
    AnthropicQualityJudge,
    OpenAIQualityJudge,
    StubQualityJudge,
    get_quality_judge,
    _parse_scores,
)

_VALID_JUDGE_JSON = """{
    "completeness": 8.0,
    "specificity": 7.5,
    "feasibility": 9.0,
    "risk_coverage": 6.0,
    "language_consistency": 9.5,
    "justification": "Story is well structured but lacks detailed risk notes."
}"""

_REQUIRED_SCORE_FIELDS = {
    "completeness", "specificity", "feasibility",
    "risk_coverage", "language_consistency", "overall", "justification",
}


def _make_story() -> UserStory:
    return UserStory(
        story_id="story-001",
        requirement_id="req-001",
        impact_analysis_id="ana-001",
        project_id="proj-001",
        title="Add OAuth Login",
        story_description="As a user I want to login with OAuth.",
        acceptance_criteria=["User can login", "Token is issued", "Session persists"],
        subtasks={
            "frontend": [],
            "backend": [
                {"title": "Create OAuth handler", "description": "Implement OAuth flow."},
                {"title": "Validate token", "description": "Validate received token."},
            ],
            "configuration": [],
        },
        definition_of_done=["Tests pass", "Code reviewed", "Deployed to staging"],
        risk_notes=["Token expiry must be handled"],
        story_points=3,
        risk_level="LOW",
        created_at=datetime.utcnow(),
        generation_time_seconds=1.0,
    )


# --- StubQualityJudge ---

def test_stub_judge_returns_all_fields():
    judge = StubQualityJudge()
    result = judge.evaluate(_make_story())
    assert _REQUIRED_SCORE_FIELDS.issubset(result.keys())
    assert result["overall"] == 7.0
    assert result["justification"] == "Stub evaluation"
    assert result["judge_model"] == "stub"


def test_stub_judge_scores_are_floats():
    judge = StubQualityJudge()
    result = judge.evaluate(_make_story())
    for field in ("completeness", "specificity", "feasibility", "risk_coverage", "language_consistency", "overall"):
        assert isinstance(result[field], float)


# --- _parse_scores ---

def test_parse_scores_computes_overall():
    raw = {
        "completeness": 8.0,
        "specificity": 7.0,
        "feasibility": 9.0,
        "risk_coverage": 6.0,
        "language_consistency": 10.0,
    }
    scores = _parse_scores(raw)
    expected_overall = round((8.0 + 7.0 + 9.0 + 6.0 + 10.0) / 5, 2)
    assert scores["overall"] == expected_overall


def test_parse_scores_raises_on_missing_field():
    raw = {"completeness": 8.0, "specificity": 7.0}
    with pytest.raises(ValueError, match="missing fields"):
        _parse_scores(raw)


# --- AnthropicQualityJudge ---

def _make_anthropic_settings():
    settings = MagicMock()
    settings.ANTHROPIC_API_KEY = "test-key"
    settings.AI_JUDGE_MODEL = ""
    settings.AI_MODEL = "claude-haiku-4-5-20251001"
    return settings


def test_anthropic_judge_parses_valid_response():
    settings = _make_anthropic_settings()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=_VALID_JUDGE_JSON)]

    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_response
        judge = AnthropicQualityJudge(settings)
        result = judge.evaluate(_make_story())

    assert _REQUIRED_SCORE_FIELDS.issubset(result.keys())
    assert result["completeness"] == 8.0
    assert "judge_model" in result


def test_anthropic_judge_raises_on_invalid_json():
    settings = _make_anthropic_settings()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json at all")]

    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_response
        judge = AnthropicQualityJudge(settings)
        with pytest.raises(ValueError, match="Invalid JSON"):
            judge.evaluate(_make_story())


# --- OpenAIQualityJudge ---

def _make_openai_settings():
    settings = MagicMock()
    settings.OPENAI_API_KEY = "test-key"
    settings.AI_JUDGE_MODEL = ""
    settings.AI_MODEL = "gpt-4o-mini"
    return settings


def test_openai_judge_parses_valid_response():
    settings = _make_openai_settings()
    mock_message = MagicMock()
    mock_message.content = _VALID_JUDGE_JSON
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("openai.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.chat.completions.create.return_value = mock_response
        judge = OpenAIQualityJudge(settings)
        result = judge.evaluate(_make_story())

    assert _REQUIRED_SCORE_FIELDS.issubset(result.keys())
    assert result["specificity"] == 7.5


# --- Factory ---

def test_get_quality_judge_returns_stub_by_default():
    settings = MagicMock()
    settings.AI_JUDGE_ENABLED = True
    settings.AI_JUDGE_PROVIDER = ""
    settings.AI_PROVIDER = "stub"
    judge = get_quality_judge(settings)
    assert isinstance(judge, StubQualityJudge)


def test_get_quality_judge_returns_stub_when_disabled():
    settings = MagicMock()
    settings.AI_JUDGE_ENABLED = False
    judge = get_quality_judge(settings)
    assert isinstance(judge, StubQualityJudge)
