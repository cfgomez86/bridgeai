from pathlib import Path
import urllib.request
import urllib.error
import socket
import pytest

FRONTEND_URL = "http://localhost:3000"
API_URL = "http://localhost:8000"
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"


def _is_port_open(host: str, port: int, timeout: int = 2) -> bool:
    """Check if a port is open using socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((host, port))
        is_open = result == 0
        return is_open
    finally:
        sock.close()


def _check_service_available(url: str, service_name: str, timeout: int = 3) -> bool:
    """Check if a service is responding via HTTP."""
    try:
        # First check if port is open
        if "localhost:3000" in url:
            port_open = _is_port_open("localhost", 3000, timeout)
        elif "localhost:8000" in url:
            port_open = _is_port_open("localhost", 8000, timeout)
        else:
            port_open = False
        
        if not port_open:
            return False
        
        # Then try HTTP request
        req = urllib.request.Request(url, headers={"User-Agent": "pytest-e2e"})
        response = urllib.request.urlopen(req, timeout=timeout)
        return response.status in (200, 301, 302, 404)
    except Exception as e:
        # If port was open but HTTP failed, still consider it available
        if "localhost:3000" in url:
            return _is_port_open("localhost", 3000, 1)
        elif "localhost:8000" in url:
            return _is_port_open("localhost", 8000, 1)
        return False


@pytest.fixture(scope="function", autouse=True)
def verify_e2e_services_available(request):
    """
    Verify all required services are running before each e2e test.
    
    If services are not available, skip the test.
    """
    # Only verify for e2e tests
    if "e2e" not in str(request.fspath):
        return
    
    api_ok = _check_service_available(API_URL, "API", timeout=5)
    frontend_ok = _check_service_available(FRONTEND_URL, "Frontend", timeout=5)
    
    if not (frontend_ok and api_ok):
        missing = []
        if not api_ok:
            missing.append("API (http://localhost:8000)")
        if not frontend_ok:
            missing.append("Frontend (http://localhost:3000)")
        
        skip_msg = (
            f"E2E test SKIPPED - Services not available: {', '.join(missing)}\n"
            f"Start these in separate terminals:\n"
            f"  1. python -m uvicorn app.main:app --reload\n"
            f"  2. cd frontend && npm run dev"
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
