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

    def list_all(self) -> list[CodeFile]:
        return self._db.query(CodeFile).all()
