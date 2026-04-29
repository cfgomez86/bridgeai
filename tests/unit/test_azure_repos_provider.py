"""Unit tests for AzureDevOpsProvider (SCM/Repos), not the ticket provider."""
import io
import json
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from app.services.scm_providers.azure_devops import AzureDevOpsProvider


def _mock_response(payload: dict):
    """Return a context-manager-compatible mock for urllib.request.urlopen."""
    body = json.dumps(payload).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


def test_list_tree_url_encodes_org_project_repo():
    provider = AzureDevOpsProvider()
    captured: dict = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        return _mock_response({"value": []})

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        provider.list_tree(
            access_token="patabc",
            repo_full_name="my org/My Project/repo with spaces",
            branch="main",
        )

    url = captured["url"]
    assert "my%20org" in url
    assert "My%20Project" in url
    assert "repo%20with%20spaces" in url
    # And NOT raw spaces
    assert " " not in url


def test_list_tree_wraps_404_with_url_and_body():
    provider = AzureDevOpsProvider()

    def raise_404(req, timeout=None):
        raise HTTPError(
            url=req.full_url,
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=io.BytesIO(b'{"message":"repository not found"}'),
        )

    with patch("urllib.request.urlopen", side_effect=raise_404):
        with pytest.raises(RuntimeError) as exc_info:
            provider.list_tree(
                access_token="patabc",
                repo_full_name="myorg/MyProject/myrepo",
                branch="main",
            )

    msg = str(exc_info.value)
    assert "404" in msg
    assert "dev.azure.com/myorg/MyProject/_apis/git/repositories/myrepo/items" in msg
    assert "repository not found" in msg


def test_list_tree_detects_empty_repo_no_branches():
    """Azure returns VS403403 when the repo has no commits — should give a friendly error."""
    provider = AzureDevOpsProvider()
    body = (
        b'{"$id":"1","innerException":null,'
        b'"message":"VS403403: Cannot find any branches for the bridgeia repository.",'
        b'"typeName":"Microsoft.TeamFoundation.Git.Server.GitItemNotFoundException"}'
    )

    def raise_404(req, timeout=None):
        raise HTTPError(
            url=req.full_url, code=404, msg="Not Found",
            hdrs=None, fp=io.BytesIO(body),
        )

    with patch("urllib.request.urlopen", side_effect=raise_404):
        with pytest.raises(RuntimeError) as exc_info:
            provider.list_tree(
                access_token="patabc",
                repo_full_name="bridgeia/bridgeia/bridgeia",
                branch="main",
            )

    msg = str(exc_info.value)
    assert "no branches" in msg
    assert "Push" in msg
    assert "bridgeia" in msg


def test_get_file_content_wraps_404_with_url():
    provider = AzureDevOpsProvider()

    def raise_404(req, timeout=None):
        raise HTTPError(
            url=req.full_url,
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=io.BytesIO(b'{"message":"file not found"}'),
        )

    with patch("urllib.request.urlopen", side_effect=raise_404):
        with pytest.raises(RuntimeError) as exc_info:
            provider.get_file_content(
                access_token="patabc",
                repo_full_name="myorg/MyProject/myrepo",
                path="src/main.py",
            )

    msg = str(exc_info.value)
    assert "404" in msg
    assert "items" in msg


def test_validate_pat_detects_missing_code_scope():
    """If projects+wit succeed but git/repositories returns 401/403/404, raise clear error."""
    provider = AzureDevOpsProvider()

    def fake_urlopen(req, timeout=None):
        url = req.full_url
        if "_apis/projects" in url and "git" not in url:
            return _mock_response({"value": [{"name": "P1"}]})
        if "wit/workitemtypes" in url:
            return _mock_response({"value": []})
        if "_apis/git/repositories" in url:
            raise HTTPError(
                url=url, code=401, msg="Unauthorized",
                hdrs=None, fp=io.BytesIO(b'{"message":"missing scope"}'),
            )
        return _mock_response({})

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        with pytest.raises(ValueError) as exc_info:
            provider.validate_pat(token="patabc", org_url="https://dev.azure.com/myorg")

    assert "Code: Read" in str(exc_info.value)


def test_validate_pat_succeeds_with_all_scopes():
    """All probes pass → returns user info, no error."""
    provider = AzureDevOpsProvider()

    def fake_urlopen(req, timeout=None):
        return _mock_response({"value": [{"name": "P1"}]})

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        info = provider.validate_pat(token="patabc", org_url="https://dev.azure.com/myorg")

    assert info["login"] == "PAT@myorg"
