import urllib.parse
import urllib.request
import json
from app.services.scm_providers.base import ScmProvider, RemoteFileEntry, validate_instance_url


class GitLabProvider(ScmProvider):
    platform = "gitlab"

    _AUTHORIZE_URL = "https://gitlab.com/oauth/authorize"
    _TOKEN_URL = "https://gitlab.com/oauth/token"
    _API_BASE = "https://gitlab.com/api/v4"

    def _api_headers(self, token: str) -> dict:
        # GitLab PATs start with "glpat-"; OAuth tokens are opaque short strings
        if token.startswith("glpat-"):
            return {"Private-Token": token}
        return {"Authorization": f"Bearer {token}"}

    def get_authorize_url(self, client_id: str, redirect_uri: str, state: str) -> str:
        params = urllib.parse.urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "read_user api",
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
            headers=self._api_headers(access_token),
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return {"login": data.get("username", ""), "name": data.get("name") or data.get("username", "")}

    def validate_pat(self, token: str, base_url: str | None = None, **_kwargs) -> dict:
        api_base = self._effective_api_base(base_url)
        req = urllib.request.Request(
            f"{api_base}/user",
            headers={"Private-Token": token},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except Exception as exc:
            raise ValueError(f"GitLab PAT invalid: {exc}") from exc
        username = data.get("username", "")
        if not username:
            raise ValueError("GitLab PAT did not return a valid user")
        return {"login": username}

    def _effective_api_base(self, base_url: str | None) -> str:
        if base_url:
            validate_instance_url(base_url)
            return f"{base_url.rstrip('/')}/api/v4"
        return self._API_BASE

    def list_repos(self, access_token: str, base_url: str | None = None, **_kwargs) -> list[dict]:
        api = self._effective_api_base(base_url)
        repos: list[dict] = []
        page = 1
        headers = self._api_headers(access_token)
        while True:
            url = f"{api}/projects?membership=true&per_page=100&page={page}&order_by=last_activity_at"
            req = urllib.request.Request(url, headers=headers)
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

    def list_tree(
        self, access_token: str, repo_full_name: str, branch: str, base_url: str | None = None
    ) -> list[RemoteFileEntry]:
        api = self._effective_api_base(base_url)
        encoded_project = urllib.parse.quote(repo_full_name, safe="")
        entries: list[RemoteFileEntry] = []
        page = 1
        headers = self._api_headers(access_token)
        while True:
            url = (
                f"{api}/projects/{encoded_project}/repository/tree"
                f"?recursive=true&per_page=100&page={page}&ref={urllib.parse.quote(branch, safe='')}"
            )
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                batch = json.loads(resp.read())
            if not batch:
                break
            for item in batch:
                if item.get("type") == "blob":
                    entries.append(RemoteFileEntry(path=item["path"], sha=item["id"], size=0))
            if len(batch) < 100:
                break
            page += 1
        return entries

    def get_file_content(
        self, access_token: str, repo_full_name: str, path: str, sha: str = "", base_url: str | None = None
    ) -> str:
        api = self._effective_api_base(base_url)
        encoded_project = urllib.parse.quote(repo_full_name, safe="")
        encoded_path = urllib.parse.quote(path, safe="")
        url = f"{api}/projects/{encoded_project}/repository/files/{encoded_path}/raw"
        req = urllib.request.Request(url, headers=self._api_headers(access_token))
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8", errors="replace")
