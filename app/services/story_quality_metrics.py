"""Structural quality metrics for a UserStory — no LLM, no external calls."""

from app.domain.user_story import UserStory
from app.services.ai_story_generator import _PATH_RE


def compute_structural_metrics(
    story: UserStory,
    code_file_repo,
    source_connection_id: str,
) -> dict:
    """Return a dict of structural metrics computed purely from story data."""
    ac_count = len(story.acceptance_criteria)
    risk_notes_count = len(story.risk_notes)

    subtasks = story.subtasks or {}
    subtask_count = sum(
        len(subtasks.get(cat, [])) for cat in ("frontend", "backend", "configuration")
    )

    # Validate required shape fields
    schema_valid = (
        bool(story.title)
        and bool(story.story_description)
        and ac_count >= 1
        and subtask_count >= 1
    )

    # Extract file paths cited across subtask titles/descriptions and risk notes
    cited_paths: set[str] = set()

    for cat in ("frontend", "backend", "configuration"):
        for item in subtasks.get(cat, []):
            if isinstance(item, dict):
                combined = f"{item.get('title', '')}\n{item.get('description', '')}"
            else:
                combined = str(item)
            for path in _PATH_RE.findall(combined):
                cited_paths.add(path)

    for note in story.risk_notes:
        for path in _PATH_RE.findall(str(note)):
            cited_paths.add(path)

    cited_paths_total = len(cited_paths)

    if cited_paths_total == 0:
        cited_paths_existing = 0
        citation_grounding_ratio = 1.0  # no citations → nothing to hallucinate
    else:
        cited_paths_existing = sum(
            1
            for p in cited_paths
            if code_file_repo.exists_by_path(p, source_connection_id)
        )
        citation_grounding_ratio = cited_paths_existing / cited_paths_total

    return {
        "schema_valid": schema_valid,
        "ac_count": ac_count,
        "risk_notes_count": risk_notes_count,
        "subtask_count": subtask_count,
        "cited_paths_total": cited_paths_total,
        "cited_paths_existing": cited_paths_existing,
        "citation_grounding_ratio": round(citation_grounding_ratio, 4),
    }
