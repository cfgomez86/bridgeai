"""Unit tests for story_quality_judge."""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.domain.user_story import UserStory
from app.services.story_quality_judge import (
    AnthropicQualityJudge,
    OpenAIQualityJudge,
    StubQualityJudge,
    _aggregate_samples,
    _parse_scores,
    get_quality_judge,
)

_VALID_JUDGE_JSON = """{
    "completeness": 8.0,
    "specificity": 7.5,
    "feasibility": 9.0,
    "risk_coverage": 6.0,
    "language_consistency": 9.5,
    "justification": "Story is well structured but lacks detailed risk notes.",
    "evidence": {"risk_coverage": "Token expiry must be handled"}
}"""

_REQUIRED_SCORE_FIELDS = {
    "completeness", "specificity", "feasibility",
    "risk_coverage", "language_consistency", "overall", "justification",
    "evidence", "dispersion", "samples_used",
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
    assert result["evidence"] == {}
    assert result["dispersion"] == 0.0
    assert result["samples_used"] == 1


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
    assert scores["evidence"] == {}


def test_parse_scores_raises_on_missing_field():
    raw = {"completeness": 8.0, "specificity": 7.0}
    with pytest.raises(ValueError, match="missing fields"):
        _parse_scores(raw)


def test_parse_scores_clamps_out_of_range():
    raw = {
        "completeness": 12.0,   # over
        "specificity": -3.0,    # under
        "feasibility": 9.0,
        "risk_coverage": 6.0,
        "language_consistency": 10.0,
    }
    scores = _parse_scores(raw)
    assert scores["completeness"] == 10.0
    assert scores["specificity"] == 0.0


def test_parse_scores_extracts_evidence():
    raw = {
        "completeness": 4.0,
        "specificity": 5.0,
        "feasibility": 9.0,
        "risk_coverage": 6.0,
        "language_consistency": 10.0,
        "evidence": {
            "completeness": "Falta DoD",
            "specificity": "AC genéricos",
            "ignored_dim": "no debería aparecer",
        },
    }
    scores = _parse_scores(raw)
    assert scores["evidence"] == {
        "completeness": "Falta DoD",
        "specificity": "AC genéricos",
    }


def test_parse_scores_rejects_non_numeric_score():
    raw = {
        "completeness": "alto",
        "specificity": 7.0,
        "feasibility": 9.0,
        "risk_coverage": 6.0,
        "language_consistency": 10.0,
    }
    with pytest.raises(ValueError, match="not numeric"):
        _parse_scores(raw)


# --- _aggregate_samples ---

def _sample(c: float, sp: float, fe: float, rk: float, lc: float, evidence: dict | None = None) -> dict:
    overall = round((c + sp + fe + rk + lc) / 5, 2)
    return {
        "completeness": c,
        "specificity": sp,
        "feasibility": fe,
        "risk_coverage": rk,
        "language_consistency": lc,
        "overall": overall,
        "justification": "j",
        "evidence": evidence or {},
    }


def test_aggregate_samples_uses_median_per_dimension():
    samples = [
        _sample(8.0, 7.0, 9.0, 6.0, 10.0),
        _sample(6.0, 5.0, 8.0, 4.0, 9.0),
        _sample(7.0, 6.0, 7.0, 5.0, 8.0),
    ]
    agg = _aggregate_samples(samples)
    assert agg["completeness"] == 7.0  # median of 8,6,7
    assert agg["specificity"] == 6.0   # median of 7,5,6
    assert agg["feasibility"] == 8.0
    assert agg["risk_coverage"] == 5.0
    assert agg["language_consistency"] == 9.0
    assert agg["samples_used"] == 3


def test_aggregate_samples_dispersion_zero_for_identical():
    s = _sample(7.0, 7.0, 7.0, 7.0, 7.0)
    agg = _aggregate_samples([s, dict(s), dict(s)])
    assert agg["dispersion"] == 0.0


def test_aggregate_samples_dispersion_positive_when_overall_varies():
    samples = [
        _sample(8.0, 8.0, 8.0, 8.0, 8.0),  # overall = 8.0
        _sample(5.0, 5.0, 5.0, 5.0, 5.0),  # overall = 5.0
        _sample(7.0, 7.0, 7.0, 7.0, 7.0),  # overall = 7.0
    ]
    agg = _aggregate_samples(samples)
    assert agg["dispersion"] > 0.5


def test_aggregate_samples_evidence_taken_from_median_sample():
    samples = [
        _sample(9.0, 9.0, 9.0, 9.0, 9.0, evidence={"risk_coverage": "from-9"}),
        _sample(7.0, 7.0, 7.0, 7.0, 7.0, evidence={"risk_coverage": "from-7"}),
        _sample(5.0, 5.0, 5.0, 5.0, 5.0, evidence={"risk_coverage": "from-5"}),
    ]
    agg = _aggregate_samples(samples)
    assert agg["evidence"] == {"risk_coverage": "from-7"}


def test_aggregate_samples_single_sample_dispersion_zero():
    agg = _aggregate_samples([_sample(7.0, 7.0, 7.0, 7.0, 7.0)])
    assert agg["dispersion"] == 0.0
    assert agg["samples_used"] == 1


def test_aggregate_samples_raises_on_empty():
    with pytest.raises(ValueError, match="zero samples"):
        _aggregate_samples([])


# --- AnthropicQualityJudge ---

def _make_anthropic_settings(samples: int = 1, temperature: float = 0.0):
    settings = MagicMock()
    settings.ANTHROPIC_API_KEY = "test-key"
    settings.AI_JUDGE_MODEL = ""
    settings.AI_MODEL = "claude-haiku-4-5-20251001"
    settings.AI_JUDGE_SAMPLES = samples
    settings.AI_JUDGE_TEMPERATURE = temperature
    return settings


def test_anthropic_judge_parses_valid_response():
    settings = _make_anthropic_settings(samples=1)
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=_VALID_JUDGE_JSON)]

    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_response
        judge = AnthropicQualityJudge(settings)
        result = judge.evaluate(_make_story())

    assert _REQUIRED_SCORE_FIELDS.issubset(result.keys())
    assert result["completeness"] == 8.0
    assert result["evidence"] == {"risk_coverage": "Token expiry must be handled"}
    assert result["samples_used"] == 1
    assert "judge_model" in result


def test_anthropic_judge_aggregates_three_samples():
    settings = _make_anthropic_settings(samples=3, temperature=0.3)
    mock_response = MagicMock()
    # Same JSON returned three times → median identical, dispersion = 0
    mock_response.content = [MagicMock(text=_VALID_JUDGE_JSON)]

    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = mock_response
        judge = AnthropicQualityJudge(settings)
        result = judge.evaluate(_make_story())

    assert MockAnthropic.return_value.messages.create.call_count == 3
    assert result["samples_used"] == 3
    assert result["dispersion"] == 0.0


def test_anthropic_judge_tolerates_partial_failures():
    settings = _make_anthropic_settings(samples=3, temperature=0.3)
    bad = MagicMock()
    bad.content = [MagicMock(text="not json")]
    good = MagicMock()
    good.content = [MagicMock(text=_VALID_JUDGE_JSON)]

    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.side_effect = [bad, bad, good]
        judge = AnthropicQualityJudge(settings)
        result = judge.evaluate(_make_story())

    assert result["samples_used"] == 1
    assert result["completeness"] == 8.0


def test_anthropic_judge_raises_when_all_samples_fail():
    settings = _make_anthropic_settings(samples=2)
    bad = MagicMock()
    bad.content = [MagicMock(text="not json")]

    with patch("anthropic.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = bad
        judge = AnthropicQualityJudge(settings)
        with pytest.raises(ValueError, match="Invalid JSON"):
            judge.evaluate(_make_story())


# --- OpenAIQualityJudge ---

def _make_openai_settings(samples: int = 1, temperature: float = 0.0):
    settings = MagicMock()
    settings.OPENAI_API_KEY = "test-key"
    settings.AI_JUDGE_MODEL = ""
    settings.AI_MODEL = "gpt-4o-mini"
    settings.AI_JUDGE_SAMPLES = samples
    settings.AI_JUDGE_TEMPERATURE = temperature
    return settings


def test_openai_judge_parses_valid_response():
    settings = _make_openai_settings(samples=1)
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
    assert result["samples_used"] == 1


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
