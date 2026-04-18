import hashlib
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.code_file import CodeFile
from app.repositories.code_file_repository import CodeFileRepository
from app.services.scm_providers.base import ScmProvider

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
    ".next",
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

        new_batch: list = []
        update_batch: list = []
        scanned_rel_paths: set[str] = set()

        for file_path in self._walk_files():
            files_scanned += 1
            try:
                rel_path = os.path.relpath(file_path, self._project_root)
                scanned_rel_paths.add(rel_path)
                action, obj = self._prepare_file(file_path, force)
                if action == "new":
                    new_batch.append(obj)
                    files_indexed += 1
                elif action == "update":
                    update_batch.append(obj)
                    files_updated += 1
                else:
                    files_skipped += 1

                if len(new_batch) >= self._batch_size:
                    self._repository.save_batch(new_batch)
                    new_batch = []
                if len(update_batch) >= self._batch_size:
                    self._repository.update_batch(update_batch)
                    update_batch = []
            except Exception as e:
                logger.warning("Error processing %s: %s", file_path, e)

        if new_batch:
            self._repository.save_batch(new_batch)
        if update_batch:
            self._repository.update_batch(update_batch)

        stale_paths = self._repository.get_all_paths() - scanned_rel_paths
        if stale_paths:
            self._repository.delete_by_paths(stale_paths)
            logger.info("Removed %d stale entries from index", len(stale_paths))

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

    def _prepare_file(self, full_path: str, force: bool) -> tuple[str, object]:
        """Returns (action, obj) where action is 'new'|'update'|'skip' and obj is the model."""
        rel_path = os.path.relpath(full_path, self._project_root)
        file_hash = self._calculate_hash(full_path)
        existing = self._repository.find_by_path(rel_path)

        if existing is not None and not force and existing.hash == file_hash:
            return "skip", None

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
            return "new", code_file
        else:
            existing.hash = file_hash
            existing.size = stat.st_size
            existing.last_modified = last_modified
            existing.lines_of_code = lines
            existing.indexed_at = indexed_at
            logger.debug("Updating file: %s", rel_path)
            return "update", existing

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

    def index_remote(
        self,
        provider: ScmProvider,
        access_token: str,
        repo_full_name: str,
        branch: str,
        force: bool = False,
    ) -> IndexingResult:
        logger.info("Starting remote indexing repo=%s branch=%s", repo_full_name, branch)
        start = time.monotonic()

        files_scanned = 0
        files_indexed = 0
        files_updated = 0
        files_skipped = 0

        entries = provider.list_tree(access_token, repo_full_name, branch)
        relevant = [
            e for e in entries
            if os.path.splitext(e.path)[1].lower() in self._language_map
            and not any(pat in e.path for pat in self._ignore_patterns)
        ]
        files_scanned = len(relevant)

        new_batch: list = []
        update_batch: list = []
        scanned_paths: set[str] = set()

        for entry in relevant:
            scanned_paths.add(entry.path)
            existing = self._repository.find_by_path(entry.path)
            if existing is not None and not force and existing.hash == entry.sha:
                files_skipped += 1
                continue
            try:
                content = provider.get_file_content(access_token, repo_full_name, entry.path)
            except Exception as exc:
                logger.warning("Failed to fetch remote file %s: %s", entry.path, exc)
                continue

            ext = os.path.splitext(entry.path)[1].lower()
            lines = sum(1 for line in content.splitlines() if line.strip())
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            if existing is None:
                code_file = CodeFile(
                    file_path=entry.path,
                    file_name=os.path.basename(entry.path),
                    extension=ext,
                    language=self._language_map[ext],
                    size=entry.size or len(content.encode()),
                    last_modified=now,
                    hash=entry.sha,
                    lines_of_code=lines,
                    indexed_at=now,
                )
                new_batch.append(code_file)
                files_indexed += 1
            else:
                existing.hash = entry.sha
                existing.size = entry.size or len(content.encode())
                existing.last_modified = now
                existing.lines_of_code = lines
                existing.indexed_at = now
                update_batch.append(existing)
                files_updated += 1

            if len(new_batch) >= self._batch_size:
                self._repository.save_batch(new_batch)
                new_batch = []
            if len(update_batch) >= self._batch_size:
                self._repository.update_batch(update_batch)
                update_batch = []

        if new_batch:
            self._repository.save_batch(new_batch)
        if update_batch:
            self._repository.update_batch(update_batch)

        stale_paths = self._repository.get_all_paths() - scanned_paths
        if stale_paths:
            self._repository.delete_by_paths(stale_paths)
            logger.info("Removed %d stale entries from remote index", len(stale_paths))

        duration = time.monotonic() - start
        logger.info(
            "Remote indexing complete: scanned=%d indexed=%d updated=%d skipped=%d duration=%.2fs",
            files_scanned, files_indexed, files_updated, files_skipped, duration,
        )
        return IndexingResult(
            files_scanned=files_scanned,
            files_indexed=files_indexed,
            files_skipped=files_skipped,
            files_updated=files_updated,
            duration_seconds=duration,
        )
