import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.models.impact_analysis import ImpactAnalysis, ImpactedFile
from app.repositories.code_file_repository import CodeFileRepository
from app.repositories.impact_analysis_repository import ImpactAnalysisRepository
from app.repositories.source_connection_repository import SourceConnectionRepository
from app.services.dependency_analyzer import DependencyAnalyzer, FileAnalysis
from app.services.semantic_impact_filter import SemanticImpactFilter

logger = logging.getLogger(__name__)


@dataclass
class ImpactAnalysisResult:
    analysis_id: str
    files_impacted: int
    modules_impacted: list[str]
    risk_level: str
    duration_seconds: float


class ImpactAnalysisService:
    def __init__(
        self,
        code_file_repo: CodeFileRepository,
        impact_repo: ImpactAnalysisRepository,
        project_root: str,
        analyzer: DependencyAnalyzer | None = None,
        semantic_filter: SemanticImpactFilter | None = None,
        source_connection_repo: SourceConnectionRepository | None = None,
    ) -> None:
        self._code_file_repo = code_file_repo
        self._impact_repo = impact_repo
        self._project_root = os.path.abspath(project_root)
        self._analyzer = analyzer if analyzer is not None else DependencyAnalyzer()
        self._semantic_filter = semantic_filter
        self._source_connection_repo = source_connection_repo

    def analyze(self, requirement: str, project_id: str) -> ImpactAnalysisResult:
        if requirement.strip() == "":
            raise ValueError("requirement cannot be empty")

        logger.info("Impact analysis started requirement=%r project_id=%s", requirement, project_id)

        start = time.monotonic()

        keywords = self._extract_keywords(requirement)

        # Scope file iteration to the active repository connection when available
        active_connection_id: Optional[str] = None
        if self._source_connection_repo is not None:
            try:
                active = self._source_connection_repo.get_active()
                if active is not None:
                    active_connection_id = active.id
            except Exception as exc:
                logger.warning("Could not resolve active connection; falling back to unscoped query: %s", exc)

        file_analyses: dict[str, FileAnalysis] = {}
        seed_files: set[str] = set()
        impacted_reasons: dict[str, str] = {}
        files_seen = 0

        for cf in self._code_file_repo.iter_all(source_connection_id=active_connection_id):
            files_seen += 1
            full_path = os.path.join(self._project_root, cf.file_path)
            try:
                content = self._read_capped(full_path)
                fa = self._analyzer.analyze(cf.file_path, content, cf.language)
                file_analyses[cf.file_path] = fa
            except OSError:
                continue

            search_text = (
                cf.file_path.lower()
                + " "
                + " ".join(fa.classes).lower()
                + " "
                + " ".join(fa.functions).lower()
                + " "
                + content.lower()
            )
            if any(keyword in search_text for keyword in keywords):
                seed_files.add(cf.file_path)
                impacted_reasons[cf.file_path] = "keyword_match"

        logger.info("Files available for analysis: %d, keyword matches: %d", files_seen, len(seed_files))

        if self._semantic_filter is not None and seed_files:
            seed_candidates = {p: file_analyses[p] for p in seed_files if p in file_analyses}
            seed_files = self._semantic_filter.filter(requirement, seed_candidates)
            logger.info("After semantic filter: %d seed files", len(seed_files))

        dep_map: dict[str, set[str]] = {}
        for path, fa in file_analyses.items():
            resolved_deps: set[str] = set()
            for imp in fa.imports:
                resolved = self._resolve_import(imp, fa.language)
                if resolved is not None and resolved in file_analyses:
                    resolved_deps.add(resolved)
            dep_map[path] = resolved_deps

        for path, deps in dep_map.items():
            if path not in impacted_reasons:
                if deps & seed_files:
                    impacted_reasons[path] = "imports_impacted_file"

        for seed_path in seed_files:
            for dep in dep_map.get(seed_path, set()):
                if dep not in impacted_reasons:
                    impacted_reasons[dep] = "imported_by_impacted_file"

        logger.info("Dependencies resolved, total impacted: %d", len(impacted_reasons))

        total_impacted = len(impacted_reasons)
        if total_impacted < 3:
            risk_level = "LOW"
        elif total_impacted <= 10:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        logger.info("Risk calculated: %s", risk_level)

        _EXCLUDED_MODULES = {"tests", "test", ".next", "node_modules", "__pycache__"}
        modules = {
            Path(p).parts[0]
            for p in impacted_reasons
            if len(Path(p).parts) > 1 and Path(p).parts[0] not in _EXCLUDED_MODULES
        }

        analysis_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        impact_analysis = ImpactAnalysis(
            id=analysis_id,
            requirement=requirement,
            risk_level=risk_level,
            files_impacted=total_impacted,
            modules_impacted=len(modules),
            analysis_summary=f"Analyzed {len(file_analyses)} files, {total_impacted} impacted",
            created_at=now,
        )
        module_names = sorted(modules)

        impacted_file_models = [
            ImpactedFile(analysis_id=analysis_id, file_path=path, reason=reason)
            for path, reason in impacted_reasons.items()
        ]

        self._impact_repo.save(impact_analysis, impacted_file_models)

        duration = time.monotonic() - start

        logger.info(
            "Impact analysis completed risk=%s files=%d duration=%.2fs",
            risk_level,
            total_impacted,
            duration,
        )

        return ImpactAnalysisResult(
            analysis_id=analysis_id,
            files_impacted=total_impacted,
            modules_impacted=module_names,
            risk_level=risk_level,
            duration_seconds=duration,
        )

    def _extract_keywords(self, requirement: str) -> list[str]:
        stop_words = {
            # English
            "the", "a", "an", "in", "of", "for", "to", "and", "or",
            "is", "are", "with", "on", "at", "by", "that", "this", "add", "change",
            # Spanish
            "que", "con", "del", "los", "las", "una", "uno", "por", "para",
            "como", "cuando", "donde", "quiero", "tener", "poder", "hacer",
            "este", "esta", "estos", "estas", "cual", "cuales", "sea", "ser",
            "hay", "han", "sus", "sin", "más", "mas", "nos", "les", "fue",
        }
        words = re.findall(r'[a-zA-Z\u00c0-\u024f][a-zA-Z0-9_\u00c0-\u024f]*', requirement.lower())
        return [w for w in words if w not in stop_words and len(w) >= 4]

    @staticmethod
    def _read_capped(full_path: str, max_bytes: int = 51_200) -> str:
        with open(full_path, encoding="utf-8", errors="ignore") as f:
            return f.read(max_bytes)

    def _resolve_import(self, import_str: str, language: str) -> Optional[str]:
        lang = language.lower()
        if lang == "python":
            return import_str.replace(".", "/") + ".py"
        if lang == "java":
            return import_str.replace(".", "/") + ".java"
        return None
