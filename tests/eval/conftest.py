"""Eval test fixtures."""
import yaml
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_golden_impact() -> list[dict]:
    path = FIXTURES_DIR / "golden_impact.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
