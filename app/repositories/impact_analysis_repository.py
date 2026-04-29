from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.context import get_tenant_id
from app.models.impact_analysis import ImpactAnalysis, ImpactedFile


class ImpactAnalysisRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _tid(self) -> str:
        return get_tenant_id()

    def save(
        self,
        analysis: ImpactAnalysis,
        impacted_files: list[ImpactedFile],
        source_connection_id: str,
    ) -> ImpactAnalysis:
        tid = self._tid()
        analysis.tenant_id = tid
        analysis.source_connection_id = source_connection_id
        for f in impacted_files:
            f.tenant_id = tid
            f.source_connection_id = source_connection_id
        self._db.add(analysis)
        self._db.add_all(impacted_files)
        self._db.commit()
        self._db.refresh(analysis)
        return analysis

    def find_by_id(
        self, analysis_id: str, source_connection_id: str
    ) -> Optional[ImpactAnalysis]:
        return (
            self._db.query(ImpactAnalysis)
            .filter(
                ImpactAnalysis.id == analysis_id,
                ImpactAnalysis.tenant_id == self._tid(),
                ImpactAnalysis.source_connection_id == source_connection_id,
            )
            .first()
        )

    def find_files_page(
        self,
        analysis_id: str,
        source_connection_id: str,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[ImpactedFile], int]:
        base = (
            self._db.query(ImpactedFile)
            .filter(
                ImpactedFile.analysis_id == analysis_id,
                ImpactedFile.tenant_id == self._tid(),
                ImpactedFile.source_connection_id == source_connection_id,
            )
        )
        total = base.count()
        files = base.offset(offset).limit(limit).all()
        return files, total

    def count_since(self, since: Optional[datetime]) -> int:
        q = self._db.query(ImpactAnalysis).filter(ImpactAnalysis.tenant_id == self._tid())
        if since is not None:
            q = q.filter(ImpactAnalysis.created_at >= since)
        return q.count()

    def list_recent(self, limit: int) -> list[ImpactAnalysis]:
        return (
            self._db.query(ImpactAnalysis)
            .filter(ImpactAnalysis.tenant_id == self._tid())
            .order_by(ImpactAnalysis.created_at.desc())
            .limit(limit)
            .all()
        )

    def find_file_paths(
        self, analysis_id: str, source_connection_id: str, limit: int = 20
    ) -> list[str]:
        rows = (
            self._db.query(ImpactedFile.file_path)
            .filter(
                ImpactedFile.analysis_id == analysis_id,
                ImpactedFile.tenant_id == self._tid(),
                ImpactedFile.source_connection_id == source_connection_id,
            )
            .limit(limit)
            .all()
        )
        return [r[0] for r in rows]
