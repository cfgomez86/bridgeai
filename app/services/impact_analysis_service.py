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
from app.services.dependency_analyzer import DependencyAnalyzer, FileAnalysis

logger = logging.getLogger(__name__)


@dataclass
class ImpactAnalysisResult:
    analysis_id: str
    files_impacted: int
    modules_impacted: int
    risk_level: str
    duration_seconds: float


class ImpactAnalysisService:
    def __init__(
        self,
        code_file_repo: CodeFileRepository,
        impact_repo: ImpactAnalysisRepository,
        project_root: str,
        analyzer: DependencyAnalyzer | None = None,
    ) -> None:
        self._code_file_repo = code_file_repo
        self._impact_repo = impact_repo
        self._project_root = os.path.abspath(project_root)
        self._analyzer = analyzer if analyzer is not None else DependencyAnalyzer()

    def analyze(self, requirement: str, project_id: str) -> ImpactAnalysisResult:
        if requirement.strip() == "":
            raise ValueError("requirement cannot be empty")

        logger.info("Impact analysis started requirement=%r project_id=%s", requirement, project_id)

        start = time.monotonic()

        all_files = self._code_file_repo.list_all()
        logger.info("Files available for analysis: %d", len(all_files))

        keywords = self._extract_keywords(requirement)

        file_analyses: dict[str, FileAnalysis] = {}
        file_contents: dict[str, str] = {}
        for cf in all_files:
            full_path = os.path.join(self._project_root, cf.file_path)
            try:
                content = Path(full_path).read_text(encoding="utf-8", errors="ignore")
                fa = self._analyzer.analyze(cf.file_path, content, cf.language)
                file_analyses[cf.file_path] = fa
                file_contents[cf.file_path] = content
            except OSError:
                continue

        seed_files: set[str] = set()
        impacted_reasons: dict[str, str] = {}

        for path, fa in file_analyses.items():
            search_text = (
                path.lower()
                + " "
                + " ".join(fa.classes).lower()
                + " "
                + " ".join(fa.functions).lower()
                + " "
                + file_contents.get(path, "").lower()
            )
            if any(keyword in search_text for keyword in keywords):
                seed_files.add(path)
                impacted_reasons[path] = "keyword_match"

        logger.info("Files matched by keywords: %d", len(seed_files))

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

        modules = {p.split("/")[0] for p in impacted_reasons if "/" in p}

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
            modules_impacted=len(modules),
            risk_level=risk_level,
            duration_seconds=duration,
        )

    def _extract_keywords(self, requirement: str) -> list[str]:
        stop_words = {
            "the", "a", "an", "in", "of", "for", "to", "and", "or",
            "is", "are", "with", "on", "at", "by", "that", "this", "add", "change",
        }
        words = re.findall(r'[a-zA-Z][a-zA-Z0-9_]*', requirement.lower())
        return [w for w in words if w not in stop_words and len(w) >= 3]

    def _resolve_import(self, import_str: str, language: str) -> Optional[str]:
        lang = language.lower()
        if lang == "python":
            return import_str.replace(".", "/") + ".py"
        if lang == "java":
            return import_str.replace(".", "/") + ".java"
        return None
