from abc import ABC, abstractmethod


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
    def list_repos(self, access_token: str) -> list[dict]:
        """List repositories accessible with this token.

        Returns list of dicts with keys: full_name, name, owner, default_branch, private.
        """
        ...
