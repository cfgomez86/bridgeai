import urllib.parse
import urllib.request
import json
from app.services.scm_providers.base import ScmProvider


class GitLabProvider(ScmProvider):
    platform = "gitlab"

    _AUTHORIZE_URL = "https://gitlab.com/oauth/authorize"
    _TOKEN_URL = "https://gitlab.com/oauth/token"
    _API_BASE = "https://gitlab.com/api/v4"

    def get_authorize_url(self, client_id: str, redirect_uri: str, state: str) -> str:
        params = urllib.parse.urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "read_user read_api",
            "state": state,
        })
        return f"{self._AUTHORIZE_URL}?{params}"

    def exchange_code(self, code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        payload = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }).encode()
        req = urllib.request.Request(
            self._TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if "error" in data:
            raise ValueError(f"GitLab OAuth error: {data.get('error_description', data['error'])}")
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
        }

    def get_user_info(self, access_token: str) -> dict:
        req = urllib.request.Request(
            f"{self._API_BASE}/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return {"login": data.get("username", ""), "name": data.get("name") or data.get("username", "")}

    def list_repos(self, access_token: str) -> list[dict]:
        repos: list[dict] = []
        page = 1
        while True:
            url = f"{self._API_BASE}/projects?membership=true&per_page=100&page={page}&order_by=last_activity_at"
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                batch = json.loads(resp.read())
            if not batch:
                break
            for r in batch:
                namespace = r.get("namespace", {})
                repos.append({
                    "full_name": r["path_with_namespace"],
                    "name": r["name"],
                    "owner": namespace.get("path", ""),
                    "default_branch": r.get("default_branch") or "main",
                    "private": r.get("visibility", "public") != "public",
                })
            if len(batch) < 100:
                break
            page += 1
        return repos
