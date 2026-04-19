from pathlib import Path
import urllib.request
import urllib.error
import pytest

FRONTEND_URL = "http://localhost:3000"
API_URL = "http://localhost:8000"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"


def _check_service_available(url: str, timeout: int = 2) -> bool:
    """Check if a service is responding."""
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionRefusedError):
        return False


@pytest.fixture(scope="function", autouse=True)
def verify_e2e_services_available():
    """
    Verify all required services are running before each e2e test.
    
    If services are not available, skip the test with a clear message.
    This allows the test suite to run without requiring all services.
    """
    frontend_ok = _check_service_available(FRONTEND_URL)
    api_ok = _check_service_available(API_URL)
    
    if not (frontend_ok and api_ok):
        missing = []
        if not api_ok:
            missing.append("API (http://localhost:8000)")
        if not frontend_ok:
            missing.append("Frontend (http://localhost:3000)")
        
        skip_msg = (
            f"E2E test SKIPPED - Required services not available: {', '.join(missing)}\n"
            f"Start these services in separate terminals:\n"
            f"  1. python -m uvicorn app.main:app --reload\n"
            f"  2. cd frontend && npm run dev\n"
            f"  3. docker compose up -d (if needed)\n"
            f"Then run: pytest tests/e2e/ -v -s"
        )
        pytest.skip(skip_msg)


@pytest.fixture(scope="session", autouse=True)
def screenshots_dir():
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    return SCREENSHOTS_DIR


@pytest.fixture(scope="session")
def frontend_url():
    return FRONTEND_URL


@pytest.fixture(scope="session")
def api_url():
    return API_URL
