import urllib.parse
import urllib.request
import json
import base64
from app.services.scm_providers.base import ScmProvider, RemoteFileEntry


class AzureDevOpsProvider(ScmProvider):
    platform = "azure_devops"

    _AUTHORIZE_URL = "https://app.vssps.visualstudio.com/oauth2/authorize"
    _TOKEN_URL = "https://app.vssps.visualstudio.com/oauth2/token"
    _PROFILE_URL = "https://app.vssps.visualstudio.com/_apis/profile/profiles/me?api-version=7.1"
    _ACCOUNTS_URL = "https://app.vssps.visualstudio.com/_apis/accounts?api-version=7.1"

    def get_authorize_url(self, client_id: str, redirect_uri: str, state: str) -> str:
        params = urllib.parse.urlencode({
            "client_id": client_id,
            "response_type": "Assertion",
            "scope": "vso.code vso.project",
            "redirect_uri": redirect_uri,
            "state": state,
        })
        return f"{self._AUTHORIZE_URL}?{params}"

    def exchange_code(self, code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        payload = urllib.parse.urlencode({
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": client_secret,
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": code,
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
            raise ValueError(f"Azure Repos OAuth error: {data.get('error_description', data['error'])}")
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
        }

    def get_user_info(self, access_token: str) -> dict:
        req = urllib.request.Request(
            self._PROFILE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        login = data.get("emailAddress") or data.get("coreAttributes", {}).get("PublicAlias", {}).get("value", "")
        name = data.get("displayName") or login
        return {"login": login, "name": name}

    def list_repos(self, access_token: str) -> list[dict]:
        # Get accounts first
        req = urllib.request.Request(
            self._ACCOUNTS_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            accounts_data = json.loads(resp.read())

        repos: list[dict] = []
        for account in accounts_data.get("value", []):
            org = account.get("accountName", "")
            projects_url = f"https://dev.azure.com/{org}/_apis/projects?api-version=7.1"
            try:
                req = urllib.request.Request(
                    projects_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    projects_data = json.loads(resp.read())
                for proj in projects_data.get("value", []):
                    proj_name = proj["name"]
                    repos_url = f"https://dev.azure.com/{org}/{proj_name}/_apis/git/repositories?api-version=7.1"
                    req = urllib.request.Request(
                        repos_url,
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        repos_data = json.loads(resp.read())
                    for r in repos_data.get("value", []):
                        repos.append({
                            "full_name": f"{org}/{proj_name}/{r['name']}",
                            "name": r["name"],
                            "owner": org,
                            "default_branch": (r.get("defaultBranch") or "refs/heads/main").replace("refs/heads/", ""),
                            "private": True,
                        })
            except Exception:
                continue
        return repos

    def list_tree(self, access_token: str, repo_full_name: str, branch: str) -> list[RemoteFileEntry]:
        # repo_full_name = "org/project/repo"
        parts = repo_full_name.split("/", 2)
        org, project, repo = parts[0], parts[1], parts[2] if len(parts) > 2 else parts[-1]
        url = (
            f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/items"
            f"?recursionLevel=Full&versionDescriptor.version={urllib.parse.quote(branch, safe='')}"
            f"&versionDescriptor.versionType=branch&api-version=7.1"
        )
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        entries: list[RemoteFileEntry] = []
        for item in data.get("value", []):
            if item.get("gitObjectType") == "blob":
                entries.append(RemoteFileEntry(
                    path=item["path"].lstrip("/"),
                    sha=item.get("objectId", ""),
                    size=item.get("contentMetadata", {}).get("encoding", 0) if False else 0,
                ))
        return entries

    def get_file_content(self, access_token: str, repo_full_name: str, path: str, sha: str = "") -> str:
        parts = repo_full_name.split("/", 2)
        org, project, repo = parts[0], parts[1], parts[2] if len(parts) > 2 else parts[-1]
        url = (
            f"https://dev.azure.com/{org}/{project}/_apis/git/repositories/{repo}/items"
            f"?path={urllib.parse.quote('/' + path.lstrip('/'), safe='/')}&api-version=7.1"
        )
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}", "Accept": "text/plain"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read().decode("utf-8", errors="replace")
