import ast
import re
from dataclasses import dataclass


# Key: (tenant_id, source_connection_id, file_path, content_hash).
# El scope incluye connection porque dos repos del mismo tenant pueden tener
# el mismo file_path con contenido distinto (o igual) y no deben compartir análisis.
_analysis_cache: dict[tuple, "FileAnalysis"] = {}


@dataclass(frozen=True)
class FileAnalysis:
    file_path: str
    language: str
    imports: list[str]
    classes: list[str]
    functions: list[str]


# Regex rules per language. Each entry has three lists of pre-compiled
# patterns; capture group 1 of every pattern is the identifier we want.
# Multiple patterns per category are union-ed via concatenation.
#
# Python is parsed with ast (more robust). Go has a multi-line `import (...)`
# block that doesn't fit the findall model and is handled in a helper.
_LANGUAGE_RULES: dict[str, dict[str, list[re.Pattern]]] = {
    "Java": {
        "imports": [re.compile(r"import\s+([\w.]+)\s*;")],
        "classes": [re.compile(r"(?:class|interface|enum)\s+(\w+)")],
        "functions": [re.compile(r"(?:public|private|protected|static)[\s\w<>\[\]]+\s+(\w+)\s*\(")],
    },
    "C#": {
        "imports": [re.compile(r"using\s+(?:static\s+)?([\w.]+)\s*;")],
        "classes": [re.compile(r"(?:class|interface|enum|struct|record)\s+(\w+)")],
        "functions": [
            re.compile(
                r"(?:public|private|protected|internal|static|virtual|override|sealed|async|abstract)"
                r"[\s\w<>\[\],?]+\s+(\w+)\s*\("
            )
        ],
    },
    "C++": {
        "imports": [re.compile(r'#include\s*[<"]([\w./]+)[>"]')],
        "classes": [re.compile(r"(?:class|struct|union)\s+(\w+)")],
        "functions": [
            re.compile(
                r"(?:public|private|protected|virtual|static|inline|explicit)"
                r"\s*[\w&*<>:,\s]+\s+(\w+)\s*\("
            )
        ],
    },
    "C": {
        "imports": [re.compile(r'#include\s*[<"]([\w./]+)[>"]')],
        "classes": [re.compile(r"(?:struct|union|enum)\s+(\w+)")],
        # Conservative: only top-level definitions with a body. Misses static
        # inline ones; that's fine — we prefer fewer false positives.
        "functions": [re.compile(r"(?:^|\n)\s*[\w*\s]+\s+(\w+)\s*\([^;{}]*\)\s*\{", re.MULTILINE)],
    },
    "PHP": {
        "imports": [re.compile(r"use\s+([\w\\]+)(?:\s+as\s+\w+)?\s*;")],
        "classes": [re.compile(r"(?:class|interface|trait|enum)\s+(\w+)")],
        "functions": [re.compile(r"function\s+(\w+)\s*\(")],
    },
    "Ruby": {
        "imports": [re.compile(r"""(?:require|require_relative)\s+["']([\w/]+)["']""")],
        "classes": [re.compile(r"(?:class|module)\s+(\w+)")],
        "functions": [re.compile(r"def\s+(?:self\.)?(\w+)")],
    },
    "Rust": {
        "imports": [re.compile(r"use\s+([\w:]+)")],
        "classes": [re.compile(r"(?:struct|enum|trait)\s+(\w+)")],
        "functions": [re.compile(r"fn\s+(\w+)")],
    },
    "Kotlin": {
        "imports": [re.compile(r"import\s+([\w.]+)")],
        # `data class`, `sealed class`, `enum class` all match `class\s+(\w+)`
        "classes": [re.compile(r"(?:class|interface|object)\s+(\w+)")],
        "functions": [re.compile(r"fun\s+(?:<[^>]*>\s*)?(?:[\w.]+\.)?(\w+)\s*\(")],
    },
    "Swift": {
        "imports": [re.compile(r"import\s+(\w+)")],
        "classes": [re.compile(r"(?:class|struct|enum|protocol|actor|extension)\s+(\w+)")],
        "functions": [re.compile(r"func\s+(\w+)\s*[\(<]")],
    },
    "Scala": {
        "imports": [re.compile(r"import\s+([\w.]+)")],
        # `case class`, `abstract class` collapse into the `class\s+(\w+)` arm
        "classes": [re.compile(r"(?:class|trait|object)\s+(\w+)")],
        "functions": [re.compile(r"def\s+(\w+)\s*[\(\[:]")],
    },
    "Go": {
        # Single-line imports only; the multi-line block is handled separately.
        "imports": [re.compile(r'import\s+"([\w./-]+)"')],
        "classes": [re.compile(r"type\s+(\w+)\s+(?:struct|interface)\b")],
        "functions": [re.compile(r"func\s+(?:\([^)]*\)\s+)?(\w+)\s*[\(<]")],
    },
    "JavaScript": {
        "imports": [
            # ES modules: import X from 'm', import { X } from 'm', import 'm'
            re.compile(r"""(?:^|\n)\s*(?:import|export)\s+(?:[^"';\n]+\s+from\s+)?["']([@\w./\-]+)["']"""),
            # CommonJS: require('m')
            re.compile(r"""require\s*\(\s*["']([@\w./\-]+)["']\s*\)"""),
        ],
        # Classes only — JS has no native interface/enum.
        "classes": [re.compile(r"\bclass\s+(\w+)")],
        "functions": [
            # function NAME ( ...
            re.compile(r"\bfunction\s*\*?\s*(\w+)\s*\("),
            # const/let/var NAME = (...) => ... (with optional async)
            re.compile(r"\b(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|\w+)\s*=>"),
        ],
    },
    "TypeScript": {
        "imports": [
            # Same ES module shape as JS, plus `import type ...`
            re.compile(r"""(?:^|\n)\s*(?:import|export)\s+(?:type\s+)?(?:[^"';\n]+\s+from\s+)?["']([@\w./\-]+)["']"""),
            re.compile(r"""require\s*\(\s*["']([@\w./\-]+)["']\s*\)"""),
        ],
        # TS adds interface, enum, namespace, type alias.
        "classes": [
            re.compile(r"\b(?:class|interface|enum|namespace)\s+(\w+)"),
            re.compile(r"\btype\s+(\w+)\s*="),
        ],
        "functions": [
            re.compile(r"\bfunction\s*\*?\s*(\w+)\s*[\(<]"),
            # Arrow with optional return-type annotation: const foo = (...): T => ...
            re.compile(r"\b(?:const|let|var)\s+(\w+)\s*[:=][^;=\n]{0,200}=>"),
        ],
    },
}

# Go's grouped import block: `import ( "a/b"  "c/d" )`. Parsed as two stages
# because findall can't return both the block and the strings inside it.
_GO_IMPORT_BLOCK = re.compile(r"import\s*\(([\s\S]*?)\)", re.MULTILINE)
_GO_IMPORT_LINE = re.compile(r'"([\w./-]+)"')


def _extract_go_imports(content: str) -> list[str]:
    out: list[str] = list(re.findall(r'^\s*import\s+"([\w./-]+)"', content, re.MULTILINE))
    for block in _GO_IMPORT_BLOCK.findall(content):
        out.extend(_GO_IMPORT_LINE.findall(block))
    return out


def _extract_with_rules(
    content: str, rules: dict[str, list[re.Pattern]]
) -> tuple[list[str], list[str], list[str]]:
    imports: list[str] = []
    classes: list[str] = []
    functions: list[str] = []
    for p in rules.get("imports", []):
        imports.extend(p.findall(content))
    for p in rules.get("classes", []):
        classes.extend(p.findall(content))
    for p in rules.get("functions", []):
        functions.extend(p.findall(content))
    return imports, classes, functions


class DependencyAnalyzer:
    def __init__(self, tenant_id: str) -> None:
        self._tid: str = tenant_id

    def analyze(
        self, file_path: str, content: str, language: str, source_connection_id: str
    ) -> FileAnalysis:
        key = (self._tid, source_connection_id, file_path, hash(content))
        cached = _analysis_cache.get(key)
        if cached is not None:
            return cached

        if language == "Python":
            result = self._analyze_python(file_path, content)
        elif language in _LANGUAGE_RULES:
            imports, classes, functions = _extract_with_rules(content, _LANGUAGE_RULES[language])
            if language == "Go":
                imports = _extract_go_imports(content)
            result = FileAnalysis(
                file_path=file_path,
                language=language,
                imports=imports,
                classes=classes,
                functions=functions,
            )
        else:
            result = FileAnalysis(
                file_path=file_path, language=language, imports=[], classes=[], functions=[]
            )

        _analysis_cache[key] = result
        return result

    @staticmethod
    def _analyze_python(file_path: str, content: str) -> FileAnalysis:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return FileAnalysis(
                file_path=file_path, language="Python", imports=[], classes=[], functions=[]
            )

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

        return FileAnalysis(
            file_path=file_path,
            language="Python",
            imports=imports,
            classes=classes,
            functions=functions,
        )

    @staticmethod
    def quick_imports(file_path: str, content: str, language: str) -> FileAnalysis:
        """Regex-only import extraction — no AST, no cache. Used for dependency
        graph on non-seed files."""
        if language == "Python":
            imports = re.findall(r"^\s*(?:from|import)\s+([\w.]+)", content, re.MULTILINE)
        elif language == "Go":
            imports = _extract_go_imports(content)
        elif language in _LANGUAGE_RULES:
            imports = []
            for p in _LANGUAGE_RULES[language].get("imports", []):
                imports.extend(p.findall(content))
        else:
            imports = []
        return FileAnalysis(
            file_path=file_path, language=language, imports=imports, classes=[], functions=[]
        )
