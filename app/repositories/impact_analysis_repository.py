from typing import Optional
from sqlalchemy.orm import Session
from app.models.impact_analysis import ImpactAnalysis, ImpactedFile


class ImpactAnalysisRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def save(self, analysis: ImpactAnalysis, impacted_files: list[ImpactedFile]) -> ImpactAnalysis:
        self._db.add(analysis)
        self._db.add_all(impacted_files)
        self._db.commit()
        self._db.refresh(analysis)
        return analysis

    def find_by_id(self, analysis_id: str) -> Optional[ImpactAnalysis]:
        return self._db.get(ImpactAnalysis, analysis_id)

    def find_files_page(
        self, analysis_id: str, offset: int = 0, limit: int = 100
    ) -> tuple[list[ImpactedFile], int]:
        base = self._db.query(ImpactedFile).filter(ImpactedFile.analysis_id == analysis_id)
        total = base.count()
        files = base.offset(offset).limit(limit).all()
        return files, total
