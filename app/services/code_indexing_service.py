import hashlib
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.code_file import CodeFile
from app.repositories.code_file_repository import CodeFileRepository

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".java": "Java",
    ".js": "JavaScript",
    ".ts": "TypeScript",
}

DEFAULT_IGNORE_PATTERNS: list[str] = [
    ".git",
    "node_modules",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "target",
]


@dataclass
class IndexingResult:
    files_scanned: int
    files_indexed: int
    files_skipped: int
    files_updated: int
    duration_seconds: float


class CodeIndexingService:
    def __init__(
        self,
        repository: CodeFileRepository,
        project_root: str,
        language_map: dict[str, str] | None = None,
        ignore_patterns: list[str] | None = None,
        batch_size: int = 500,
    ) -> None:
        self._repository = repository
        self._project_root = os.path.abspath(project_root)
        self._language_map = language_map if language_map is not None else DEFAULT_LANGUAGE_MAP
        self._ignore_patterns = DEFAULT_IGNORE_PATTERNS + (ignore_patterns if ignore_patterns is not None else [])
        self._batch_size = batch_size

    def index_repository(self, force: bool = False) -> IndexingResult:
        self._validate_project_root()
        logger.info("Starting indexing of %s", self._project_root)
        start = time.monotonic()

        files_scanned = 0
        files_indexed = 0
        files_updated = 0
        files_skipped = 0

        for file_path in self._walk_files():
            files_scanned += 1
            try:
                result = self._process_file(file_path, force)
                if result == "indexed":
                    files_indexed += 1
                elif result == "updated":
                    files_updated += 1
                elif result == "skipped":
                    files_skipped += 1
            except Exception as e:
                logger.warning("Error processing %s: %s", file_path, e)

        duration = time.monotonic() - start
        logger.info(
            "Indexing complete: scanned=%d indexed=%d updated=%d skipped=%d duration=%.2fs",
            files_scanned,
            files_indexed,
            files_updated,
            files_skipped,
            duration,
        )
        return IndexingResult(
            files_scanned=files_scanned,
            files_indexed=files_indexed,
            files_skipped=files_skipped,
            files_updated=files_updated,
            duration_seconds=duration,
        )

    def _validate_project_root(self) -> None:
        if not os.path.exists(self._project_root):
            raise ValueError(f"Project root does not exist: {self._project_root}")
        if not os.path.isdir(self._project_root):
            raise ValueError(f"Project root is not a directory: {self._project_root}")

    def _walk_files(self):
        for dirpath, dirnames, filenames in os.walk(self._project_root):
            dirnames[:] = [d for d in dirnames if d not in self._ignore_patterns]
            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in self._language_map:
                    continue
                full_path = os.path.realpath(os.path.join(dirpath, filename))
                try:
                    if os.path.commonpath([full_path, self._project_root]) != self._project_root:
                        logger.warning("Skipping file outside project root: %s", full_path)
                        continue
                except ValueError:
                    logger.warning("Skipping file on different drive: %s", full_path)
                    continue
                yield full_path

    def _process_file(self, full_path: str, force: bool) -> str:
        rel_path = os.path.relpath(full_path, self._project_root)
        file_hash = self._calculate_hash(full_path)
        existing = self._repository.find_by_path(rel_path)

        if existing is not None and not force and existing.hash == file_hash:
            return "skipped"

        stat = os.stat(full_path)
        ext = os.path.splitext(full_path)[1].lower()
        lines = self._count_lines(full_path)
        last_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).replace(tzinfo=None)
        indexed_at = datetime.now(timezone.utc).replace(tzinfo=None)

        if existing is None:
            code_file = CodeFile(
                file_path=rel_path,
                file_name=os.path.basename(full_path),
                extension=ext,
                language=self._language_map[ext],
                size=stat.st_size,
                last_modified=last_modified,
                hash=file_hash,
                lines_of_code=lines,
                indexed_at=indexed_at,
            )
            logger.debug("Indexing new file: %s", rel_path)
            self._repository.save(code_file)
            return "indexed"
        else:
            existing.hash = file_hash
            existing.size = stat.st_size
            existing.last_modified = last_modified
            existing.lines_of_code = lines
            existing.indexed_at = indexed_at
            logger.debug("Updating file: %s", rel_path)
            self._repository.update(existing)
            return "updated"

    @staticmethod
    def _calculate_hash(file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def _count_lines(file_path: str) -> int:
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                return sum(1 for line in f if line.strip())
        except OSError:
            return 0
