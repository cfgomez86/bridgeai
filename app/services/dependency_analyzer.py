import ast
import re
from dataclasses import dataclass
from typing import Callable


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

    def analyze(self, file_path: str, content: str, language: str) -> FileAnalysis:
        parser = self._parsers.get(language)
        if parser is None:
            return FileAnalysis(file_path=file_path, language=language, imports=[], classes=[], functions=[])
        return parser(file_path, content)

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
