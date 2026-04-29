import json
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.context import get_tenant_id
from app.models.story_quality_score import StoryQualityScore


def _serialize_evidence(scores: dict) -> Optional[str]:
    evidence = scores.get("evidence")
    if not evidence:
        return None
    try:
        return json.dumps(evidence, ensure_ascii=False)
    except (TypeError, ValueError):
        return None


class StoryQualityRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _tid(self) -> str:
        return get_tenant_id()

    def upsert(self, story_id: str, scores: dict) -> StoryQualityScore:
        """Insert or update quality scores for a story."""
        now = datetime.utcnow()
        existing = self.find_by_story(story_id)
        if existing:
            existing.completeness = scores["completeness"]
            existing.specificity = scores["specificity"]
            existing.feasibility = scores["feasibility"]
            existing.risk_coverage = scores["risk_coverage"]
            existing.language_consistency = scores["language_consistency"]
            existing.overall = scores["overall"]
            existing.justification = scores.get("justification")
            existing.judge_model = scores.get("judge_model")
            existing.dispersion = scores.get("dispersion")
            existing.samples_used = scores.get("samples_used")
            existing.evidence = _serialize_evidence(scores)
            existing.evaluated_at = now
            self._db.commit()
            self._db.refresh(existing)
            return existing

        record = StoryQualityScore(
            tenant_id=self._tid(),
            story_id=story_id,
            completeness=scores["completeness"],
            specificity=scores["specificity"],
            feasibility=scores["feasibility"],
            risk_coverage=scores["risk_coverage"],
            language_consistency=scores["language_consistency"],
            overall=scores["overall"],
            justification=scores.get("justification"),
            judge_model=scores.get("judge_model"),
            dispersion=scores.get("dispersion"),
            samples_used=scores.get("samples_used"),
            evidence=_serialize_evidence(scores),
            evaluated_at=now,
        )
        self._db.add(record)
        self._db.commit()
        self._db.refresh(record)
        return record

    def find_by_story(self, story_id: str) -> Optional[StoryQualityScore]:
        return (
            self._db.query(StoryQualityScore)
            .filter(
                StoryQualityScore.tenant_id == self._tid(),
                StoryQualityScore.story_id == story_id,
            )
            .first()
        )

    def avg_overall_since(self, since: Optional[datetime]) -> Optional[float]:
        q = (
            self._db.query(func.avg(StoryQualityScore.overall))
            .filter(StoryQualityScore.tenant_id == self._tid())
        )
        if since is not None:
            q = q.filter(StoryQualityScore.evaluated_at >= since)
        result = q.scalar()
        return float(result) if result is not None else None

    def count_evaluated_since(self, since: Optional[datetime]) -> int:
        q = self._db.query(StoryQualityScore).filter(
            StoryQualityScore.tenant_id == self._tid()
        )
        if since is not None:
            q = q.filter(StoryQualityScore.evaluated_at >= since)
        return q.count()

    def delete_by_story(self, story_id: str) -> None:
        (
            self._db.query(StoryQualityScore)
            .filter(
                StoryQualityScore.tenant_id == self._tid(),
                StoryQualityScore.story_id == story_id,
            )
            .delete(synchronize_session=False)
        )
        self._db.commit()
