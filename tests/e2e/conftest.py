from pathlib import Path
import pytest

FRONTEND_URL = "http://localhost:3000"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"


@pytest.fixture(scope="session", autouse=True)
def screenshots_dir():
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    return SCREENSHOTS_DIR


@pytest.fixture(scope="session")
def frontend_url():
    return FRONTEND_URL
