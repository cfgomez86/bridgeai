"""Unit tests for story_quality_metrics.compute_structural_metrics."""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.domain.user_story import UserStory
from app.services.story_quality_metrics import compute_structural_metrics


def _make_story(
    title="Add OAuth login",
    story_description="As a user I want to login with OAuth.",
    acceptance_criteria=None,
    subtasks=None,
    definition_of_done=None,
    risk_notes=None,
    story_points=3,
    risk_level="MEDIUM",
):
    return UserStory(
        story_id="story-001",
        requirement_id="req-001",
        impact_analysis_id="ana-001",
        project_id="proj-001",
        title=title,
        story_description=story_description,
        acceptance_criteria=acceptance_criteria or ["AC1", "AC2"],
        subtasks=subtasks or {
            "frontend": [],
            "backend": [
                {
                    "title": "Create endpoint POST /auth/register",
                    "description": "Add route in app/api/routes/auth.py for registration.",
                }
            ],
            "configuration": [],
        },
        definition_of_done=definition_of_done or ["Tests pass"],
        risk_notes=risk_notes or [],
        story_points=story_points,
        risk_level=risk_level,
        created_at=datetime.utcnow(),
        generation_time_seconds=1.0,
    )


def _make_mock_repo(existing_paths: set[str]):
    repo = MagicMock()
    repo.exists_by_path.side_effect = (
        lambda path, conn_id: path in existing_paths
    )
    return repo


def test_basic_counts():
    story = _make_story(
        acceptance_criteria=["AC1", "AC2", "AC3"],
        risk_notes=["Risk 1", "Risk 2"],
    )
    repo = _make_mock_repo(set())
    metrics = compute_structural_metrics(story, repo, "conn-001")

    assert metrics["ac_count"] == 3
    assert metrics["risk_notes_count"] == 2
    assert metrics["subtask_count"] == 1  # one backend subtask


def test_schema_valid_when_complete():
    story = _make_story()
    repo = _make_mock_repo(set())
    metrics = compute_structural_metrics(story, repo, "conn-001")
    assert metrics["schema_valid"] is True


def test_schema_invalid_when_empty_title():
    story = _make_story(title="")
    repo = _make_mock_repo(set())
    metrics = compute_structural_metrics(story, repo, "conn-001")
    assert metrics["schema_valid"] is False


def test_citation_grounding_ratio_perfect():
    story = _make_story(
        subtasks={
            "frontend": [],
            "backend": [
                {
                    "title": "Implement auth in app/api/routes/auth.py",
                    "description": "Modify app/api/routes/auth.py to add OAuth.",
                }
            ],
            "configuration": [],
        }
    )
    repo = _make_mock_repo({"app/api/routes/auth.py"})
    metrics = compute_structural_metrics(story, repo, "conn-001")
    assert metrics["cited_paths_total"] >= 1
    assert metrics["citation_grounding_ratio"] == 1.0


def test_citation_grounding_ratio_zero():
    story = _make_story(
        subtasks={
            "frontend": [],
            "backend": [
                {
                    "title": "Implement auth in app/api/routes/fake.py",
                    "description": "Modify app/nonexistent/file.py to add OAuth.",
                }
            ],
            "configuration": [],
        }
    )
    repo = _make_mock_repo(set())
    metrics = compute_structural_metrics(story, repo, "conn-001")
    assert metrics["cited_paths_total"] >= 1
    assert metrics["citation_grounding_ratio"] == 0.0


def test_no_citations_ratio_is_one():
    """When there are no cited paths, citation_grounding_ratio should be 1.0 (nothing to hallucinate)."""
    story = _make_story(
        subtasks={
            "frontend": [],
            "backend": [
                {"title": "Implement auth backend logic", "description": "Add OAuth handler."}
            ],
            "configuration": [],
        },
        risk_notes=[],
    )
    repo = _make_mock_repo(set())
    metrics = compute_structural_metrics(story, repo, "conn-001")
    assert metrics["cited_paths_total"] == 0
    assert metrics["citation_grounding_ratio"] == 1.0


def test_subtask_count_across_categories():
    story = _make_story(
        subtasks={
            "frontend": [
                {"title": "Create login form component", "description": "Build the form."}
            ],
            "backend": [
                {"title": "Add OAuth route in backend", "description": "Add route."},
                {"title": "Validate the token", "description": "Validate."},
            ],
            "configuration": [
                {"title": "Add env variables to config", "description": "Add to env."}
            ],
        }
    )
    repo = _make_mock_repo(set())
    metrics = compute_structural_metrics(story, repo, "conn-001")
    assert metrics["subtask_count"] == 4
