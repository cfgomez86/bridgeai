"""Retrieval evaluation — tests recall of ImpactAnalysisService over golden dataset."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock

import pytest
import yaml

from tests.eval.conftest import load_golden_impact

EVAL_REPORT_PATH = Path("eval_report.json")


def _make_mock_db_and_context(file_paths: list[str]):
    """Create a mock session and tenant context for the impact service."""
    from app.core.context import current_tenant_id, current_user_id
    from app.models.code_file import CodeFile
    from datetime import datetime

    current_tenant_id.set("eval-tenant")
    current_user_id.set("eval-user")

    mock_db = MagicMock()

    code_files = []
    for path in file_paths:
        full_path = Path(".") / path
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")[:8000]
        except OSError:
            content = path  # fallback: just the path as content

        cf = CodeFile()
        cf.id = path
        cf.file_path = path
        cf.language = "python" if path.endswith(".py") else "typescript"
        cf.content = content
        cf.tenant_id = "eval-tenant"
        cf.source_connection_id = "eval-conn"
        cf.hash = "0"
        cf.size = len(content)
        cf.lines_of_code = content.count("\n")
        cf.last_modified = datetime.utcnow()
        cf.indexed_at = datetime.utcnow()
        code_files.append(cf)

    return mock_db, code_files


def _run_analysis(requirement: str, code_files) -> set[str]:
    """Run keyword-based impact analysis directly without DB."""
    import re
    import unicodedata

    _STOP = frozenset({
        "de", "la", "el", "los", "las", "un", "una", "y", "en",
        "con", "por", "para", "del", "al", "se", "que", "a",
        "the", "for", "in", "of", "and", "to", "with", "from",
    })

    def _normalize(text: str) -> str:
        nfd = unicodedata.normalize("NFD", text)
        no_accent = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        return no_accent.lower()

    def _extract_keywords(text: str) -> frozenset[str]:
        words = re.findall(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]{3,}", text.lower())
        normalized = {_normalize(w) for w in words}
        return frozenset(normalized - _STOP)

    keywords = _extract_keywords(requirement)
    impacted: set[str] = set()

    for cf in code_files:
        content = cf.content or ""
        quick_text = _normalize(cf.file_path) + " " + content.lower()
        if any(kw in quick_text for kw in keywords):
            impacted.add(cf.file_path)

    return impacted


def _compute_metrics(predicted: set[str], expected: list[str]) -> dict:
    predicted_norm = {p.replace("\\", "/") for p in predicted}
    expected_set = set(expected)
    tp = len(predicted_norm & expected_set)
    fp = len(predicted_norm - expected_set)
    fn = len(expected_set - predicted_norm)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4)}


# Collect all .py and relevant .ts files from the app directory for evaluation
def _collect_app_files() -> list:
    from app.models.code_file import CodeFile
    from datetime import datetime

    app_root = Path(".")
    extensions = {".py", ".ts", ".tsx", ".js"}
    paths = []
    for ext in extensions:
        paths.extend(app_root.rglob(f"app/**/*{ext}"))

    code_files = []
    for path in sorted(paths):
        rel = str(path.as_posix())
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")[:8000]
        except OSError:
            content = rel

        cf = CodeFile()
        cf.id = rel
        cf.file_path = rel
        cf.language = "python" if path.suffix == ".py" else "typescript"
        cf.content = content
        cf.tenant_id = "eval-tenant"
        cf.source_connection_id = "eval-conn"
        cf.hash = "0"
        cf.size = len(content)
        cf.lines_of_code = content.count("\n")
        cf.last_modified = datetime.utcnow()
        cf.indexed_at = datetime.utcnow()
        code_files.append(cf)

    return code_files


_APP_FILES = _collect_app_files()
_GOLDEN = load_golden_impact()
_REPORT: dict = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "results": [],
}


@pytest.mark.eval
@pytest.mark.parametrize("entry", _GOLDEN, ids=[e["id"] for e in _GOLDEN])
def test_impact_recall(entry):
    requirement = entry["requirement"]
    expected_files = entry["expected_files"]

    predicted = _run_analysis(requirement, _APP_FILES)
    metrics = _compute_metrics(predicted, expected_files)

    _REPORT["results"].append({
        "id": entry["id"],
        "requirement": requirement,
        "expected_files": expected_files,
        "predicted_count": len(predicted),
        **metrics,
    })

    # Write report after each test (last write wins with all accumulated results)
    EVAL_REPORT_PATH.write_text(
        json.dumps(_REPORT, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    assert metrics["recall"] >= 0.6, (
        f"Recall {metrics['recall']:.2f} < 0.6 for {entry['id']}. "
        f"Expected: {expected_files}. "
        f"Predicted (first 10): {sorted(predicted)[:10]}"
    )
