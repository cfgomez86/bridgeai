import base64
import urllib.parse
import urllib.request
import json
from app.services.scm_providers.base import ScmProvider, RemoteFileEntry


class GitHubProvider(ScmProvider):
    platform = "github"

    _AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    _TOKEN_URL = "https://github.com/login/oauth/access_token"
    _API_BASE = "https://api.github.com"

    def get_authorize_url(self, client_id: str, redirect_uri: str, state: str) -> str:
        params = urllib.parse.urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": "repo read:user",
            "state": state,
        })
        return f"{self._AUTHORIZE_URL}?{params}"

    def exchange_code(self, code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        payload = json.dumps({
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }).encode()
        req = urllib.request.Request(
            self._TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if "error" in data:
            raise ValueError(f"GitHub OAuth error: {data.get('error_description', data['error'])}")
        return {
            "access_token": data["access_token"],
            "refresh_token": None,
            "expires_in": None,
        }

    def get_user_info(self, access_token: str) -> dict:
        req = urllib.request.Request(
            f"{self._API_BASE}/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return {"login": data.get("login", ""), "name": data.get("name") or data.get("login", "")}

    def list_repos(self, access_token: str) -> list[dict]:
        repos: list[dict] = []
        page = 1
        while True:
            url = f"{self._API_BASE}/user/repos?per_page=100&page={page}&sort=updated"
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                batch = json.loads(resp.read())
            if not batch:
                break
            for r in batch:
                repos.append({
                    "full_name": r["full_name"],
                    "name": r["name"],
                    "owner": r["owner"]["login"],
                    "default_branch": r.get("default_branch", "main"),
                    "private": r.get("private", False),
                })
            if len(batch) < 100:
                break
            page += 1
        return repos

    def list_tree(self, access_token: str, repo_full_name: str, branch: str) -> list[RemoteFileEntry]:
        url = f"{self._API_BASE}/repos/{repo_full_name}/git/trees/{urllib.parse.quote(branch, safe='')}?recursive=1"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return [
            RemoteFileEntry(path=item["path"], sha=item["sha"], size=item.get("size", 0))
            for item in data.get("tree", [])
            if item["type"] == "blob"
        ]

    def get_file_content(self, access_token: str, repo_full_name: str, path: str, sha: str = "") -> str:
        if sha:
            # Blobs API returns raw bytes directly — no JSON parsing or base64 decoding.
            # GitHub CDN caches blobs by SHA, so this is significantly faster.
            url = f"{self._API_BASE}/repos/{repo_full_name}/git/blobs/{sha}"
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.raw",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")

        url = f"{self._API_BASE}/repos/{repo_full_name}/contents/{urllib.parse.quote(path)}"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
