import base64
import urllib.parse
import urllib.request
import json
from app.services.scm_providers.base import ScmProvider, RemoteFileEntry


class BitbucketProvider(ScmProvider):
    platform = "bitbucket"

    _AUTHORIZE_URL = "https://bitbucket.org/site/oauth2/authorize"
    _TOKEN_URL = "https://bitbucket.org/site/oauth2/access_token"
    _API_BASE = "https://api.bitbucket.org/2.0"

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
        # Bitbucket requires HTTP Basic Auth + form-encoded body (not JSON)
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
            f"{self._API_BASE}/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        login = data.get("username") or data.get("account_id", "")
        name = data.get("display_name") or login
        return {"login": login, "name": name}

    def list_repos(self, access_token: str) -> list[dict]:
        repos: list[dict] = []
        # List all workspaces the user belongs to, then repos per workspace
        ws_url: str | None = f"{self._API_BASE}/workspaces?pagelen=100"
        workspaces: list[str] = []
        while ws_url:
            req = urllib.request.Request(ws_url, headers={"Authorization": f"Bearer {access_token}"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            for ws in data.get("values", []):
                workspaces.append(ws["slug"])
            ws_url = data.get("next")

        for slug in workspaces:
            repo_url: str | None = f"{self._API_BASE}/repositories/{slug}?pagelen=100&sort=-updated_on"
            while repo_url:
                req = urllib.request.Request(repo_url, headers={"Authorization": f"Bearer {access_token}"})
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

    def list_tree(self, access_token: str, repo_full_name: str, branch: str) -> list[RemoteFileEntry]:
        entries: list[RemoteFileEntry] = []
        # BFS over the directory tree — Bitbucket has no single recursive endpoint
        queue: list[str] = [""]
        while queue:
            dir_path = queue.pop(0)
            if dir_path:
                encoded = urllib.parse.quote(dir_path, safe="/")
                url: str | None = (
                    f"{self._API_BASE}/repositories/{repo_full_name}/src"
                    f"/{urllib.parse.quote(branch, safe='')}/{encoded}?pagelen=100"
                )
            else:
                url = (
                    f"{self._API_BASE}/repositories/{repo_full_name}/src"
                    f"/{urllib.parse.quote(branch, safe='')}/?pagelen=100"
                )
            while url:
                req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
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

    def get_file_content(self, access_token: str, repo_full_name: str, path: str, sha: str = "") -> str:
        # sha here is the commit hash returned by list_tree; fall back to HEAD
        node = sha if sha else "HEAD"
        url = (
            f"{self._API_BASE}/repositories/{repo_full_name}/src"
            f"/{node}/{urllib.parse.quote(path, safe='/')}"
        )
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
