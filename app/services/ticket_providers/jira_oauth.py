import json
import urllib.parse
import urllib.request


class JiraOAuthProvider:
    """Atlassian OAuth 2.0 (3LO) provider for Jira Cloud."""

    platform = "jira"

    _AUTH_URL  = "https://auth.atlassian.com/authorize"
    _TOKEN_URL = "https://auth.atlassian.com/oauth/token"
    _ME_URL    = "https://api.atlassian.com/me"
    _SITES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"
    _SCOPES    = "read:jira-work write:jira-work read:me offline_access"

    def get_authorize_url(self, client_id: str, redirect_uri: str, state: str) -> str:
        params = urllib.parse.urlencode({
            "audience": "api.atlassian.com",
            "client_id": client_id,
            "scope": self._SCOPES,
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
        })
        return f"{self._AUTH_URL}?{params}"

    def exchange_code(self, code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        payload = json.dumps({
            "grant_type": "authorization_code",
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
            raise ValueError(f"Jira OAuth error: {data.get('error_description', data['error'])}")
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_in": data.get("expires_in"),
        }

    def get_user_info(self, access_token: str) -> dict:
        req = urllib.request.Request(
            self._ME_URL,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        login = data.get("email") or data.get("account_id", "jira-user")
        return {"login": login, "name": data.get("name") or login}

    def list_sites(self, access_token: str) -> list[dict]:
        """Return Jira Cloud sites the user has access to.

        Each site: {id, name, url} where url is e.g. https://mycompany.atlassian.net
        """
        req = urllib.request.Request(
            self._SITES_URL,
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            sites = json.loads(resp.read())
        return [
            {
                "id": s["id"],
                "name": s["name"],
                "url": s["url"],
                "api_base_url": f"https://api.atlassian.com/ex/jira/{s['id']}",
            }
            for s in sites
        ]
