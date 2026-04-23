import ast
import re
from dataclasses import dataclass
from typing import Callable

from app.core.context import get_tenant_id

# Module-level cache: survives across DependencyAnalyzer instances (one per request).
# Key: (tenant_id, file_path, content_hash) — stale entries evicted when file content changes.
_analysis_cache: dict[tuple, "FileAnalysis"] = {}


@dataclass(frozen=True)
class FileAnalysis:
    file_path: str
    language: str
    imports: list[str]
    classes: list[str]
    functions: list[str]


class DependencyAnalyzer:
    def __init__(self) -> None:
        self._parsers: dict[str, Callable[[str, str], FileAnalysis]] = {
            "Python": self._analyze_python,
            "Java": self._analyze_java,
        }
        # Resolve tenant once per instance — all analyze() calls for a given request
        # share the same tenant context, so a single lookup suffices.
        try:
            self._tid: str = get_tenant_id()
        except RuntimeError:
            self._tid = ""

    def analyze(self, file_path: str, content: str, language: str) -> FileAnalysis:
        key = (self._tid, file_path, hash(content))
        cached = _analysis_cache.get(key)
        if cached is not None:
            return cached
        parser = self._parsers.get(language)
        if parser is None:
            result = FileAnalysis(file_path=file_path, language=language, imports=[], classes=[], functions=[])
        else:
            result = parser(file_path, content)
        _analysis_cache[key] = result
        return result

    def _analyze_python(self, file_path: str, content: str) -> FileAnalysis:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return FileAnalysis(file_path=file_path, language="Python", imports=[], classes=[], functions=[])

        imports: list[str] = []
        classes: list[str] = []
        functions: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module is not None:
                    imports.append(node.module)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)

        return FileAnalysis(file_path=file_path, language="Python", imports=imports, classes=classes, functions=functions)

    def _analyze_java(self, file_path: str, content: str) -> FileAnalysis:
        imports: list[str] = re.findall(r'import\s+([\w.]+)\s*;', content)
        classes: list[str] = re.findall(r'(?:class|interface|enum)\s+(\w+)', content)
        functions: list[str] = re.findall(r'(?:public|private|protected|static)[\s\w<>\[\]]+\s+(\w+)\s*\(', content)

        return FileAnalysis(file_path=file_path, language="Java", imports=imports, classes=classes, functions=functions)
