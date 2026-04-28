"""Integration tests for GET /api/v1/system/quality."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app
from tests.integration.auth_helpers import apply_mock_auth


def _make_client_with_settings(settings: Settings) -> TestClient:
    app = apply_mock_auth(create_app())
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_system_quality_not_evaluated_when_no_file():
    settings = MagicMock(spec=Settings)
    settings.EVAL_REPORT_PATH = "/nonexistent/path/eval_report.json"
    # Provide all settings fields needed by app startup
    settings.TRUSTED_PROXY_IPS = "127.0.0.1,::1"
    settings.CORS_ORIGINS = "http://localhost:3000"
    settings.CORS_ORIGIN_REGEX = ""
    client = _make_client_with_settings(settings)

    response = client.get("/api/v1/system/quality")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_evaluated"


def test_system_quality_returns_content_when_file_exists():
    report_data = {
        "timestamp": "2026-04-28T00:00:00Z",
        "dataset_size": 3,
        "overall_recall": 0.85,
        "results": [],
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        json.dump(report_data, f)
        tmp_path = f.name

    try:
        settings = MagicMock(spec=Settings)
        settings.EVAL_REPORT_PATH = tmp_path
        settings.TRUSTED_PROXY_IPS = "127.0.0.1,::1"
        settings.CORS_ORIGINS = "http://localhost:3000"
        settings.CORS_ORIGIN_REGEX = ""

        client = _make_client_with_settings(settings)
        response = client.get("/api/v1/system/quality")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["overall_recall"] == 0.85
        assert data["data"]["dataset_size"] == 3
    finally:
        os.unlink(tmp_path)
