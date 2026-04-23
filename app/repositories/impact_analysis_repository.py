from typing import Optional

from sqlalchemy.orm import Session

from app.core.context import get_tenant_id
from app.models.impact_analysis import ImpactAnalysis, ImpactedFile


class ImpactAnalysisRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _tid(self) -> str:
        return get_tenant_id()

    def save(self, analysis: ImpactAnalysis, impacted_files: list[ImpactedFile]) -> ImpactAnalysis:
        analysis.tenant_id = self._tid()
        self._db.add(analysis)
        self._db.add_all(impacted_files)
        self._db.commit()
        self._db.refresh(analysis)
        return analysis

    def find_by_id(self, analysis_id: str) -> Optional[ImpactAnalysis]:
        return (
            self._db.query(ImpactAnalysis)
            .filter(ImpactAnalysis.id == analysis_id, ImpactAnalysis.tenant_id == self._tid())
            .first()
        )

    def find_files_page(
        self, analysis_id: str, offset: int = 0, limit: int = 100
    ) -> tuple[list[ImpactedFile], int]:
        base = (
            self._db.query(ImpactedFile)
            .join(ImpactAnalysis, ImpactAnalysis.id == ImpactedFile.analysis_id)
            .filter(
                ImpactedFile.analysis_id == analysis_id,
                ImpactAnalysis.tenant_id == self._tid(),
            )
        )
        total = base.count()
        files = base.offset(offset).limit(limit).all()
        return files, total

    def find_file_paths(self, analysis_id: str, limit: int = 20) -> list[str]:
        rows = (
            self._db.query(ImpactedFile.file_path)
            .join(ImpactAnalysis, ImpactAnalysis.id == ImpactedFile.analysis_id)
            .filter(
                ImpactedFile.analysis_id == analysis_id,
                ImpactAnalysis.tenant_id == self._tid(),
            )
            .limit(limit)
            .all()
        )
        return [r[0] for r in rows]
