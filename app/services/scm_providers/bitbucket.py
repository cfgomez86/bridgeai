import base64
import urllib.parse
import urllib.request
import json
from app.services.scm_providers.base import ScmProvider, RemoteFileEntry, validate_instance_url

_BEARER = "Authorization"


class BitbucketProvider(ScmProvider):
    platform = "bitbucket"

    _AUTHORIZE_URL = "https://bitbucket.org/site/oauth2/authorize"
    _TOKEN_URL = "https://bitbucket.org/site/oauth2/access_token"
    _CLOUD_API = "https://api.bitbucket.org/2.0"

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _is_dc(self, base_url: str | None) -> bool:
        return bool(base_url)

    def _dc_api(self, base_url: str) -> str:
        validate_instance_url(base_url)
        return f"{base_url.rstrip('/')}/rest/api/1.0"

    def _bearer(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def _parse_dc_full_name(self, full_name: str) -> tuple[str, str]:
        parts = full_name.split("/", 1)
        return parts[0], parts[1] if len(parts) == 2 else parts[0]

    # ── OAuth flow (Cloud only) ────────────────────────────────────────────────

    def get_authorize_url(self, client_id: str, redirect_uri: str, state: str) -> str:
        params = urllib.parse.urlencode({
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "account repository",
            "state": state,
        })
        return f"{self._AUTHORIZE_URL}?{params}"

    def exchange_code(self, code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        payload = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
        }).encode()
        req = urllib.request.Request(
            self._TOKEN_URL,
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {credentials}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if "error" in data:
            raise ValueError(f"Bitbucket OAuth error: {data.get('error_description', data['error'])}")
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
        }

    def get_user_info(self, access_token: str) -> dict:
        req = urllib.request.Request(
            f"{self._CLOUD_API}/user",
            headers=self._bearer(access_token),
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        login = data.get("username") or data.get("account_id", "")
        name = data.get("display_name") or login
        return {"login": login, "name": name}

    # ── PAT validation ─────────────────────────────────────────────────────────

    def validate_pat(self, token: str, base_url: str | None = None, **_kwargs) -> dict:
        if self._is_dc(base_url):
            return self._validate_pat_dc(token, base_url)  # type: ignore[arg-type]
        return self._validate_pat_cloud(token)

    def _validate_pat_cloud(self, token: str) -> dict:
        req = urllib.request.Request(
            f"{self._CLOUD_API}/user",
            headers=self._bearer(token),
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except Exception as exc:
            raise ValueError(f"Bitbucket token invalid: {exc}") from exc
        login = data.get("username") or data.get("account_id", "")
        if not login:
            raise ValueError("Bitbucket token did not return a valid user")
        return {"login": login}

    def _validate_pat_dc(self, token: str, base_url: str) -> dict:
        api = self._dc_api(base_url)
        req = urllib.request.Request(
            f"{api}/users/~",
            headers=self._bearer(token),
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except Exception as exc:
            raise ValueError(f"Bitbucket Data Center token invalid: {exc}") from exc
        login = data.get("name", "")
        if not login:
            raise ValueError("Bitbucket Data Center token did not return a valid user")
        return {"login": login, "display_name": data.get("displayName", login)}

    # ── List repos ─────────────────────────────────────────────────────────────

    def list_repos(self, access_token: str, base_url: str | None = None, **_kwargs) -> list[dict]:
        if self._is_dc(base_url):
            return self._list_repos_dc(access_token, base_url)  # type: ignore[arg-type]
        return self._list_repos_cloud(access_token)

    def _list_repos_cloud(self, access_token: str) -> list[dict]:
        repos: list[dict] = []
        ws_url: str | None = f"{self._CLOUD_API}/workspaces?pagelen=100"
        workspaces: list[str] = []
        while ws_url:
            req = urllib.request.Request(ws_url, headers=self._bearer(access_token))
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            for ws in data.get("values", []):
                workspaces.append(ws["slug"])
            ws_url = data.get("next")

        for slug in workspaces:
            repo_url: str | None = f"{self._CLOUD_API}/repositories/{slug}?pagelen=100&sort=-updated_on"
            while repo_url:
                req = urllib.request.Request(repo_url, headers=self._bearer(access_token))
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read())
                for r in data.get("values", []):
                    main_branch = r["mainbranch"]["name"] if r.get("mainbranch") else "main"
                    repos.append({
                        "full_name": r["full_name"],
                        "name": r["slug"],
                        "owner": r["workspace"]["slug"],
                        "default_branch": main_branch,
                        "private": r.get("is_private", False),
                    })
                repo_url = data.get("next")
        return repos

    def _list_repos_dc(self, access_token: str, base_url: str) -> list[dict]:
        # BB Data Center: lists all repos the token has access to across all projects
        api = self._dc_api(base_url)
        repos: list[dict] = []
        start = 0
        while True:
            url = f"{api}/repos?limit=100&start={start}"
            req = urllib.request.Request(url, headers=self._bearer(access_token))
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            for r in data.get("values", []):
                project_key = r.get("project", {}).get("key", "")
                slug = r.get("slug", "")
                # BB Server default branch comes from links/branches or may be absent
                default_branch = r.get("defaultBranch", {}).get("displayId", "") or "main"
                repos.append({
                    "full_name": f"{project_key}/{slug}",
                    "name": slug,
                    "owner": project_key,
                    "default_branch": default_branch,
                    "private": not r.get("public", False),
                })
            if data.get("isLastPage", True):
                break
            start = data["nextPageStart"]
        return repos

    # ── List tree ──────────────────────────────────────────────────────────────

    def list_tree(
        self, access_token: str, repo_full_name: str, branch: str, base_url: str | None = None
    ) -> list[RemoteFileEntry]:
        if self._is_dc(base_url):
            return self._list_tree_dc(access_token, repo_full_name, branch, base_url)  # type: ignore[arg-type]
        return self._list_tree_cloud(access_token, repo_full_name, branch)

    def _list_tree_cloud(self, access_token: str, repo_full_name: str, branch: str) -> list[RemoteFileEntry]:
        entries: list[RemoteFileEntry] = []
        queue: list[str] = [""]
        while queue:
            dir_path = queue.pop(0)
            if dir_path:
                encoded = urllib.parse.quote(dir_path, safe="/")
                url: str | None = (
                    f"{self._CLOUD_API}/repositories/{repo_full_name}/src"
                    f"/{urllib.parse.quote(branch, safe='')}/{encoded}?pagelen=100"
                )
            else:
                url = (
                    f"{self._CLOUD_API}/repositories/{repo_full_name}/src"
                    f"/{urllib.parse.quote(branch, safe='')}/?pagelen=100"
                )
            while url:
                req = urllib.request.Request(url, headers=self._bearer(access_token))
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read())
                for item in data.get("values", []):
                    if item["type"] == "commit_file":
                        entries.append(RemoteFileEntry(
                            path=item["path"],
                            sha=item.get("commit", {}).get("hash", ""),
                            size=item.get("size", 0),
                        ))
                    elif item["type"] == "commit_directory":
                        queue.append(item["path"])
                url = data.get("next")
        return entries

    def _list_tree_dc(
        self, access_token: str, repo_full_name: str, branch: str, base_url: str
    ) -> list[RemoteFileEntry]:
        # BB Data Center /files endpoint returns all file paths recursively (flat list)
        api = self._dc_api(base_url)
        project_key, repo_slug = self._parse_dc_full_name(repo_full_name)
        entries: list[RemoteFileEntry] = []
        start = 0
        encoded_branch = urllib.parse.quote(branch, safe="")
        while True:
            url = (
                f"{api}/projects/{project_key}/repos/{repo_slug}"
                f"/files?at={encoded_branch}&limit=1000&start={start}"
            )
            req = urllib.request.Request(url, headers=self._bearer(access_token))
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            for path in data.get("values", []):
                # BB Server /files endpoint returns flat path strings with no SHA
                entries.append(RemoteFileEntry(path=path, sha="", size=0))
            if data.get("isLastPage", True):
                break
            start = data["nextPageStart"]
        return entries

    # ── Get file content ───────────────────────────────────────────────────────

    def get_file_content(
        self, access_token: str, repo_full_name: str, path: str, sha: str = "", base_url: str | None = None
    ) -> str:
        if self._is_dc(base_url):
            return self._get_file_dc(access_token, repo_full_name, path, sha, base_url)  # type: ignore[arg-type]
        return self._get_file_cloud(access_token, repo_full_name, path, sha)

    def _get_file_cloud(self, access_token: str, repo_full_name: str, path: str, sha: str) -> str:
        node = sha if sha else "HEAD"
        url = (
            f"{self._CLOUD_API}/repositories/{repo_full_name}/src"
            f"/{node}/{urllib.parse.quote(path, safe='/')}"
        )
        req = urllib.request.Request(url, headers=self._bearer(access_token))
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def _get_file_dc(
        self, access_token: str, repo_full_name: str, path: str, sha: str, base_url: str
    ) -> str:
        api = self._dc_api(base_url)
        project_key, repo_slug = self._parse_dc_full_name(repo_full_name)
        encoded_path = urllib.parse.quote(path, safe="/")
        url = f"{api}/projects/{project_key}/repos/{repo_slug}/raw/{encoded_path}"
        req = urllib.request.Request(url, headers=self._bearer(access_token))
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
