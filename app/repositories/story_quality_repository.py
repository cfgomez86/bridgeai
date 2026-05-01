import json
from datetime import datetime
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.context import get_tenant_id
from app.models.story_quality_score import StoryQualityScore
from app.models.user_story import UserStory


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

    def avg_overall_since(
        self, since: Optional[datetime], *, forced: Optional[bool] = None
    ) -> Optional[float]:
        q = (
            self._db.query(func.avg(StoryQualityScore.overall))
            .filter(StoryQualityScore.tenant_id == self._tid())
        )
        if since is not None:
            q = q.filter(StoryQualityScore.evaluated_at >= since)
        if forced is not None:
            q = q.join(UserStory, UserStory.id == StoryQualityScore.story_id).filter(
                UserStory.entity_not_found.is_(forced)
            )
        result = q.scalar()
        return float(result) if result is not None else None

    def count_evaluated_since(
        self, since: Optional[datetime], *, forced: Optional[bool] = None
    ) -> int:
        q = self._db.query(StoryQualityScore).filter(
            StoryQualityScore.tenant_id == self._tid()
        )
        if since is not None:
            q = q.filter(StoryQualityScore.evaluated_at >= since)
        if forced is not None:
            q = q.join(UserStory, UserStory.id == StoryQualityScore.story_id).filter(
                UserStory.entity_not_found.is_(forced)
            )
        return q.count()

    def summary_since(self, since: Optional[datetime]) -> dict:
        """Aggregate scores partitioned by `user_stories.entity_not_found`,
        with the forced bucket sub-divided by `user_stories.was_forced`.

        Returns three buckets:
          - `organic` (entity_not_found=False) — clean baseline
          - `forced` (entity_not_found=True) — degraded inputs; sub-divided into:
              * `creation_bypass_count`: was_forced=False (system-driven creation)
              * `override_count`: was_forced=True (user explicit override)
          - `all` — everything

        Each bucket has `avg_overall`, `count`, and `avg_dispersion`. Uses CASE
        expressions so it stays portable across PostgreSQL and SQLite (tests).
        """
        organic_pred = UserStory.entity_not_found.is_(False)
        forced_pred = UserStory.entity_not_found.is_(True)
        creation_bypass_pred = forced_pred & UserStory.was_forced.is_(False)
        override_pred = forced_pred & UserStory.was_forced.is_(True)

        organic_overall = func.avg(case((organic_pred, StoryQualityScore.overall)))
        forced_overall = func.avg(case((forced_pred, StoryQualityScore.overall)))
        organic_count = func.count(case((organic_pred, 1)))
        forced_count = func.count(case((forced_pred, 1)))
        organic_dispersion = func.avg(case((organic_pred, StoryQualityScore.dispersion)))
        forced_dispersion = func.avg(case((forced_pred, StoryQualityScore.dispersion)))
        creation_bypass_count = func.count(case((creation_bypass_pred, 1)))
        override_count = func.count(case((override_pred, 1)))
        # Per-dimension averages, organic only — forced has hard caps that
        # would distort the picture; the goal is to see where the LLM is
        # weakest under normal generation.
        organic_completeness = func.avg(case((organic_pred, StoryQualityScore.completeness)))
        organic_specificity = func.avg(case((organic_pred, StoryQualityScore.specificity)))
        organic_feasibility = func.avg(case((organic_pred, StoryQualityScore.feasibility)))
        organic_risk_coverage = func.avg(case((organic_pred, StoryQualityScore.risk_coverage)))
        organic_language_consistency = func.avg(case((organic_pred, StoryQualityScore.language_consistency)))

        q = (
            self._db.query(
                organic_overall,
                forced_overall,
                organic_count,
                forced_count,
                organic_dispersion,
                forced_dispersion,
                func.avg(StoryQualityScore.overall),
                func.count(StoryQualityScore.id),
                func.avg(StoryQualityScore.dispersion),
                creation_bypass_count,
                override_count,
                organic_completeness,
                organic_specificity,
                organic_feasibility,
                organic_risk_coverage,
                organic_language_consistency,
            )
            .join(UserStory, UserStory.id == StoryQualityScore.story_id)
            .filter(
                StoryQualityScore.tenant_id == self._tid(),
                # Defense-in-depth: ensure the joined story belongs to the same
                # tenant — never rely solely on the score-side scope.
                UserStory.tenant_id == self._tid(),
            )
        )
        if since is not None:
            q = q.filter(StoryQualityScore.evaluated_at >= since)
        row = q.one()

        def _f(value) -> Optional[float]:
            return float(value) if value is not None else None

        return {
            "organic": {
                "avg_overall": _f(row[0]),
                "count": int(row[2] or 0),
                "avg_dispersion": _f(row[4]),
                "avg_completeness": _f(row[11]),
                "avg_specificity": _f(row[12]),
                "avg_feasibility": _f(row[13]),
                "avg_risk_coverage": _f(row[14]),
                "avg_language_consistency": _f(row[15]),
            },
            "forced": {
                "avg_overall": _f(row[1]),
                "count": int(row[3] or 0),
                "avg_dispersion": _f(row[5]),
                "creation_bypass_count": int(row[9] or 0),
                "override_count": int(row[10] or 0),
            },
            "all": {
                "avg_overall": _f(row[6]),
                "count": int(row[7] or 0),
                "avg_dispersion": _f(row[8]),
            },
        }

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
