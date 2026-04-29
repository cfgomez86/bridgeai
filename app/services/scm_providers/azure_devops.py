import base64
import urllib.parse
import urllib.request
import urllib.error
import json
from app.services.scm_providers.base import ScmProvider, RemoteFileEntry


class AzureDevOpsProvider(ScmProvider):
    platform = "azure_devops"

    # Microsoft Entra ID (AAD) OAuth 2.0 endpoints
    _AUTHORIZE_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    _TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    _PROFILE_URL = "https://app.vssps.visualstudio.com/_apis/profile/profiles/me?api-version=7.1"
    _ACCOUNTS_URL = "https://app.vssps.visualstudio.com/_apis/accounts?api-version=7.1"
    # Azure DevOps resource ID in Entra ID — .default uses the permissions
    # configured in the app registration (user_impersonation)
    _SCOPE = "499b84ac-1321-427f-aa17-267ca6975798/.default offline_access"

    def _auth_header(self, token: str) -> str:
        # Entra ID access tokens are JWTs (Base64url JSON — always start with "eyJ")
        # Azure DevOps PATs are opaque alphanumeric strings — use HTTP Basic Auth
        if token.startswith("eyJ"):
            return f"Bearer {token}"
        credentials = base64.b64encode(f":{token}".encode()).decode()
        return f"Basic {credentials}"

    def get_authorize_url(self, client_id: str, redirect_uri: str, state: str) -> str:
        params = urllib.parse.urlencode({
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "prompt": "select_account",
        })
        # Encode scope separately to preserve '/' — urlencode encodes it as %2F
        # which Entra ID rejects in the scope parameter
        scope_encoded = urllib.parse.quote(self._SCOPE, safe="/")
        return f"{self._AUTHORIZE_URL}?{params}&scope={scope_encoded}"

    def exchange_code(self, code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        payload = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": self._SCOPE,
        }).encode()
        req = urllib.request.Request(
            self._TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            raise ValueError(f"Azure Repos token exchange {e.code}: {body}")
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
            headers={"Authorization": self._auth_header(access_token)},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        login = data.get("emailAddress") or data.get("coreAttributes", {}).get("PublicAlias", {}).get("value", "")
        name = data.get("displayName") or login
        return {"login": login, "name": name}

    def validate_pat(self, token: str, org_url: str | None = None, **_kwargs) -> dict:
        if not org_url:
            raise ValueError("org_url is required for Azure DevOps PAT validation (e.g. https://dev.azure.com/my-org)")
        org = org_url.rstrip("/").split("/")[-1]
        projects_url = f"https://dev.azure.com/{org}/_apis/projects?api-version=7.1"
        req = urllib.request.Request(projects_url, headers={"Authorization": self._auth_header(token)})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise ValueError(f"Azure DevOps PAT invalid or org_url wrong: HTTP {e.code}") from e
        except Exception as exc:
            raise ValueError(f"Azure DevOps PAT validation failed: {exc}") from exc
        # Probe Work Items scope using the first accessible project
        projects = data.get("value", [])
        if projects:
            first_project = urllib.parse.quote(projects[0]["name"])
            wi_url = f"https://dev.azure.com/{org}/{first_project}/_apis/wit/workitemtypes?api-version=7.1"
            wi_req = urllib.request.Request(wi_url, headers={"Authorization": self._auth_header(token)})
            try:
                with urllib.request.urlopen(wi_req, timeout=15) as _resp:
                    pass
            except urllib.error.HTTPError as e:
                if e.code in (401, 403):
                    raise ValueError(
                        "Azure DevOps PAT is missing 'Work Items: Read & Write' scope. "
                        "Regenerate the PAT and enable: Work Items › Read & Write."
                    )
            except Exception:
                pass  # network or other transient error — don't block connection
        # Probe Code scope — required for repository indexing.
        # Azure returns 404 (not 401) when this scope is missing, so check that too.
        code_url = f"https://dev.azure.com/{org}/_apis/git/repositories?api-version=7.1"
        code_req = urllib.request.Request(code_url, headers={"Authorization": self._auth_header(token)})
        try:
            with urllib.request.urlopen(code_req, timeout=15) as _resp:
                pass
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404):
                raise ValueError(
                    "Azure DevOps PAT is missing 'Code: Read' scope. "
                    "Regenerate the PAT and enable: Code › Read."
                )
        except Exception:
            pass  # network or other transient error — don't block connection
        return {"login": f"PAT@{org}", "display_name": f"PAT@{org}"}

    def get_project_process(self, access_token: str, org_url: str, project_name: str) -> str:
        """Returns the process template name (e.g. 'Agile', 'Scrum', 'Basic', 'CMMI') for a project."""
        org = org_url.rstrip("/").split("/")[-1]
        project_encoded = urllib.parse.quote(project_name, safe="")
        url = f"https://dev.azure.com/{org}/_apis/projects/{project_encoded}?includeCapabilities=true&api-version=7.1"
        req = urllib.request.Request(url, headers={"Authorization": self._auth_header(access_token)})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            return data.get("capabilities", {}).get("processTemplate", {}).get("templateName", "")
        except Exception:
            return ""

    def list_projects(self, access_token: str, org_url: str | None = None, **_kwargs) -> list[dict]:
        if org_url or not access_token.startswith("eyJ"):
            if not org_url:
                raise ValueError("org_url required for PAT-based Azure DevOps connections")
            org = org_url.rstrip("/").split("/")[-1]
            return self._get_org_projects(access_token, org)
        return self._list_projects_oauth(access_token)

    def _get_org_projects(self, token: str, org: str) -> list[dict]:
        url = f"https://dev.azure.com/{org}/_apis/projects?$expand=capabilities&api-version=7.1"
        req = urllib.request.Request(url, headers={"Authorization": self._auth_header(token)})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except Exception:
            return []
        return [
            {
                "name": p["name"],
                "org": org,
                "full_name": f"{org}/{p['name']}",
                "process_template": p.get("capabilities", {}).get("processTemplate", {}).get("templateName", ""),
            }
            for p in data.get("value", [])
        ]

    def _list_projects_oauth(self, access_token: str) -> list[dict]:
        profile_req = urllib.request.Request(
            self._PROFILE_URL,
            headers={"Authorization": self._auth_header(access_token)},
        )
        with urllib.request.urlopen(profile_req, timeout=15) as resp:
            profile = json.loads(resp.read())
        member_id = profile.get("id", "")
        accounts_url = self._ACCOUNTS_URL + (f"&memberId={member_id}" if member_id else "")
        req = urllib.request.Request(
            accounts_url,
            headers={"Authorization": self._auth_header(access_token)},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            accounts_data = json.loads(resp.read())
        projects: list[dict] = []
        for account in accounts_data.get("value", []):
            org = account.get("accountName", "")
            projects.extend(self._get_org_projects(access_token, org))
        return projects

    def list_repos(self, access_token: str, org_url: str | None = None, **_kwargs) -> list[dict]:
        if org_url or not access_token.startswith("eyJ"):
            if not org_url:
                raise ValueError("org_url required for PAT-based Azure DevOps connections")
            return self._list_org_repos(access_token, org_url.rstrip("/").split("/")[-1])
        return self._list_repos_oauth(access_token)

    def _list_repos_oauth(self, access_token: str) -> list[dict]:
        profile_req = urllib.request.Request(
            self._PROFILE_URL,
            headers={"Authorization": self._auth_header(access_token)},
        )
        with urllib.request.urlopen(profile_req, timeout=15) as resp:
            profile = json.loads(resp.read())
        member_id = profile.get("id", "")
        accounts_url = self._ACCOUNTS_URL + (f"&memberId={member_id}" if member_id else "")
        req = urllib.request.Request(
            accounts_url,
            headers={"Authorization": self._auth_header(access_token)},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            accounts_data = json.loads(resp.read())

        repos: list[dict] = []
        for account in accounts_data.get("value", []):
            org = account.get("accountName", "")
            repos.extend(self._list_org_repos(access_token, org))
        return repos

    def _list_org_repos(self, token: str, org: str) -> list[dict]:
        auth = self._auth_header(token)
        projects_url = f"https://dev.azure.com/{org}/_apis/projects?api-version=7.1"
        repos: list[dict] = []
        try:
            req = urllib.request.Request(projects_url, headers={"Authorization": auth})
            with urllib.request.urlopen(req, timeout=15) as resp:
                projects_data = json.loads(resp.read())
            for proj in projects_data.get("value", []):
                proj_name = proj["name"]
                repos_url = f"https://dev.azure.com/{org}/{proj_name}/_apis/git/repositories?api-version=7.1"
                req = urllib.request.Request(repos_url, headers={"Authorization": auth})
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
            pass
        return repos

    def list_tree(
        self, access_token: str, repo_full_name: str, branch: str, base_url: str | None = None
    ) -> list[RemoteFileEntry]:
        parts = repo_full_name.split("/", 2)
        org, project, repo = parts[0], parts[1], parts[2] if len(parts) > 2 else parts[-1]
        org_e = urllib.parse.quote(org, safe="")
        project_e = urllib.parse.quote(project, safe="")
        repo_e = urllib.parse.quote(repo, safe="")
        url = (
            f"https://dev.azure.com/{org_e}/{project_e}/_apis/git/repositories/{repo_e}/items"
            f"?recursionLevel=Full&versionDescriptor.version={urllib.parse.quote(branch, safe='')}"
            f"&versionDescriptor.versionType=branch&api-version=7.1"
        )
        req = urllib.request.Request(url, headers={"Authorization": self._auth_header(access_token)})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            # Azure returns 404 with this specific message when the repo has no commits/branches.
            if "Cannot find any branches" in body or "VS403403" in body:
                raise RuntimeError(
                    f"Azure DevOps repository '{repo}' has no branches yet. "
                    f"Push at least one commit to branch '{branch}' before indexing."
                ) from e
            raise RuntimeError(f"Azure DevOps {e.code} on {url}: {body[:200]}") from e
        entries: list[RemoteFileEntry] = []
        for item in data.get("value", []):
            if item.get("gitObjectType") == "blob":
                entries.append(RemoteFileEntry(
                    path=item["path"].lstrip("/"),
                    sha=item.get("objectId", ""),
                    size=0,
                ))
        return entries

    def get_file_content(
        self, access_token: str, repo_full_name: str, path: str, sha: str = "", base_url: str | None = None
    ) -> str:
        parts = repo_full_name.split("/", 2)
        org, project, repo = parts[0], parts[1], parts[2] if len(parts) > 2 else parts[-1]
        org_e = urllib.parse.quote(org, safe="")
        project_e = urllib.parse.quote(project, safe="")
        repo_e = urllib.parse.quote(repo, safe="")
        url = (
            f"https://dev.azure.com/{org_e}/{project_e}/_apis/git/repositories/{repo_e}/items"
            f"?path={urllib.parse.quote('/' + path.lstrip('/'), safe='/')}&api-version=7.1"
        )
        req = urllib.request.Request(
            url,
            headers={"Authorization": self._auth_header(access_token), "Accept": "text/plain"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:200]
            raise RuntimeError(f"Azure DevOps {e.code} on {url}: {body}") from e
