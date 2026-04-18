from typing import Optional

from sqlalchemy.orm import Session

from app.models.code_file import CodeFile


class CodeFileRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def save(self, code_file: CodeFile) -> CodeFile:
        self._db.add(code_file)
        self._db.commit()
        self._db.refresh(code_file)
        return code_file

    def update(self, code_file: CodeFile) -> CodeFile:
        merged = self._db.merge(code_file)
        self._db.commit()
        self._db.refresh(merged)
        return merged

    def find_by_path(self, file_path: str) -> Optional[CodeFile]:
        return (
            self._db.query(CodeFile)
            .filter(CodeFile.file_path == file_path)
            .first()
        )

    def save_batch(self, code_files: list[CodeFile]) -> None:
        for cf in code_files:
            self._db.add(cf)
        self._db.commit()

    def update_batch(self, code_files: list[CodeFile]) -> None:
        for cf in code_files:
            self._db.merge(cf)
        self._db.commit()

    def list_all(self) -> list[CodeFile]:
        return self._db.query(CodeFile).all()

    def iter_all(self, chunk_size: int = 500):
        yield from self._db.query(CodeFile).yield_per(chunk_size)

    def delete_by_paths(self, paths: set[str]) -> int:
        deleted = (
            self._db.query(CodeFile)
            .filter(CodeFile.file_path.in_(paths))
            .delete(synchronize_session=False)
        )
        self._db.commit()
        return deleted

    def get_all_paths(self) -> set[str]:
        return {row[0] for row in self._db.query(CodeFile.file_path).all()}

    def get_all_map(self) -> dict[str, "CodeFile"]:
        """Return {file_path: CodeFile} for all indexed files — single query."""
        return {cf.file_path: cf for cf in self._db.query(CodeFile).all()}
