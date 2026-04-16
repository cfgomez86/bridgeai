from datetime import datetime
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.file_info import FileInfo

logger = get_logger(__name__)

IGNORED_DIRS: frozenset[str] = frozenset(
    {".git", "node_modules", "venv", "__pycache__", ".venv", "dist", "build"}
)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py", ".js", ".ts", ".tsx", ".jsx",
        ".java", ".cs", ".go", ".rb", ".php",
        ".cpp", ".c", ".h", ".rs", ".kt",
        ".swift", ".scala", ".sh", ".yaml", ".yml",
        ".json", ".toml", ".md",
    }
)


class CodeScanner:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def root(self) -> Path:
        return self._settings.project_root_path

    def scan(self) -> list[FileInfo]:
        """Recursively list all supported source files under PROJECT_ROOT."""
        results: list[FileInfo] = []
        logger.info("scan_start root=%s", self.root)

        for file_path in self._walk(self.root):
            try:
                stat = file_path.stat()
                results.append(
                    FileInfo(
                        path=str(file_path),
                        size=stat.st_size,
                        extension=file_path.suffix.lower(),
                        last_modified=datetime.fromtimestamp(stat.st_mtime),
                    )
                )
            except OSError as exc:
                logger.warning("scan_skip path=%s reason=%s", file_path, exc)

        logger.info("scan_complete total_files=%d", len(results))
        return results

    def _walk(self, directory: Path):  # type: ignore[no-untyped-def]
        for entry in directory.iterdir():
            if entry.is_dir():
                if entry.name not in IGNORED_DIRS:
                    yield from self._walk(entry)
            elif entry.is_file() and entry.suffix.lower() in SUPPORTED_EXTENSIONS:
                yield entry

    def supported_extensions(self) -> list[str]:
        return sorted(SUPPORTED_EXTENSIONS)
