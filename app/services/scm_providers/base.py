import ipaddress
import urllib.parse
from abc import ABC, abstractmethod
from dataclasses import dataclass


def validate_instance_url(url: str) -> None:
    """Reject user-supplied base_url values that could enable SSRF.

    Allows only http/https schemes and blocks private, loopback, link-local,
    and reserved IP ranges. Hostname-based URLs pass here; DNS rebinding is
    not addressed at this layer (requires connection-time IP resolution).
    Raises ValueError with a safe message on any violation.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        raise ValueError("Invalid instance URL")

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Instance URL must use http or https, got {parsed.scheme!r}")

    host = parsed.hostname or ""
    if not host:
        raise ValueError("Instance URL must include a hostname")

    try:
        addr = ipaddress.ip_address(host)
        if any([addr.is_private, addr.is_loopback, addr.is_link_local, addr.is_reserved]):
            raise ValueError("Instance URL points to a disallowed IP range")
    except ValueError as exc:
        # ip_address() raises ValueError for hostnames — re-raise only for actual IP violations
        if "disallowed" in str(exc) or "Invalid" in str(exc):
            raise


@dataclass(frozen=True)
class RemoteFileEntry:
    path: str    # relative path in repo, e.g. "app/main.py"
    sha: str     # git blob SHA — used as content hash
    size: int    # bytes


class ScmProvider(ABC):
    platform: str  # set as class variable in each subclass

    @abstractmethod
    def get_authorize_url(self, client_id: str, redirect_uri: str, state: str) -> str:
        """Return the OAuth authorization URL to redirect the user to."""
        ...

    @abstractmethod
    def exchange_code(
        self, code: str, client_id: str, client_secret: str, redirect_uri: str
    ) -> dict:
        """Exchange an authorization code for tokens.

        Returns dict with keys: access_token, refresh_token (or None), expires_in (or None).
        """
        ...

    @abstractmethod
    def get_user_info(self, access_token: str) -> dict:
        """Fetch authenticated user info.

        Returns dict with keys: login, name.
        """
        ...

    @abstractmethod
    def list_repos(self, access_token: str, **kwargs) -> list[dict]:
        """List repositories accessible with this token.

        Returns list of dicts with keys: full_name, name, owner, default_branch, private.
        kwargs may include base_url (self-hosted) or org_url (Azure DevOps).
        """
        ...

    @abstractmethod
    def list_tree(
        self, access_token: str, repo_full_name: str, branch: str, base_url: str | None = None
    ) -> list[RemoteFileEntry]:
        """Return all blob entries in the repo tree recursively.

        base_url: override for self-hosted instances (GitHub Enterprise, GitLab, Bitbucket DC).
        """
        ...

    @abstractmethod
    def get_file_content(
        self, access_token: str, repo_full_name: str, path: str, sha: str = "", base_url: str | None = None
    ) -> str:
        """Return decoded text content of a single file.

        sha: git blob SHA — providers may use it for faster cached fetching.
        base_url: override for self-hosted instances.
        """
        ...
