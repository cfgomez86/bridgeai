"""
Global pytest configuration and shared fixtures.
"""
import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent
