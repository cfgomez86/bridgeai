from datetime import datetime
from typing import Optional

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.core.context import get_tenant_id
from app.models.code_file import CodeFile


class CodeFileRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def _tid(self) -> str:
        return get_tenant_id()

    def _base_query(self, source_connection_id: Optional[str] = None):
        q = self._db.query(CodeFile).filter(CodeFile.tenant_id == self._tid())
        if source_connection_id is not None:
            q = q.filter(CodeFile.source_connection_id == source_connection_id)
        return q

    def save(self, code_file: CodeFile) -> CodeFile:
        code_file.tenant_id = self._tid()
        self._db.add(code_file)
        self._db.commit()
        self._db.refresh(code_file)
        return code_file

    def update(self, code_file: CodeFile) -> CodeFile:
        merged = self._db.merge(code_file)
        self._db.commit()
        self._db.refresh(merged)
        return merged

    def find_by_path(
        self, file_path: str, source_connection_id: Optional[str] = None
    ) -> Optional[CodeFile]:
        return (
            self._base_query(source_connection_id)
            .filter(CodeFile.file_path == file_path)
            .first()
        )

    def save_batch(
        self, code_files: list[CodeFile], source_connection_id: Optional[str] = None
    ) -> None:
        tid = self._tid()
        for cf in code_files:
            cf.tenant_id = tid
            cf.source_connection_id = source_connection_id
        self._db.add_all(code_files)
        self._db.commit()

    def update_batch(self, code_files: list[CodeFile]) -> None:
        if not code_files:
            return
        self._db.execute(
            update(CodeFile),
            [
                {
                    "id": cf.id,
                    "hash": cf.hash,
                    "size": cf.size,
                    "last_modified": cf.last_modified,
                    "lines_of_code": cf.lines_of_code,
                    "indexed_at": cf.indexed_at,
                    "content": cf.content,
                }
                for cf in code_files
            ],
        )
        self._db.commit()

    def list_all(self, source_connection_id: Optional[str] = None) -> list[CodeFile]:
        return self._base_query(source_connection_id).all()

    def iter_all(self, chunk_size: int = 500, source_connection_id: Optional[str] = None):
        yield from self._base_query(source_connection_id).yield_per(chunk_size)

    def delete_by_paths(
        self, paths: set[str], source_connection_id: Optional[str] = None
    ) -> int:
        deleted = (
            self._base_query(source_connection_id)
            .filter(CodeFile.file_path.in_(paths))
            .delete(synchronize_session=False)
        )
        self._db.commit()
        return deleted

    def get_all_paths(self, source_connection_id: Optional[str] = None) -> set[str]:
        rows = self._base_query(source_connection_id).with_entities(CodeFile.file_path).all()
        return {row[0] for row in rows}

    def get_all_map(self, source_connection_id: Optional[str] = None) -> dict[str, "CodeFile"]:
        return {
            cf.file_path: cf
            for cf in self._base_query(source_connection_id).all()
        }

    def delete_by_connection(self, source_connection_id: str) -> int:
        deleted = (
            self._base_query(source_connection_id)
            .delete(synchronize_session=False)
        )
        self._db.commit()
        return deleted

    def get_status(self, source_connection_id: Optional[str] = None) -> tuple[int, Optional[datetime]]:
        total, last = (
            self._base_query(source_connection_id)
            .with_entities(func.count(CodeFile.id), func.max(CodeFile.indexed_at))
            .one()
        )
        return total or 0, last
