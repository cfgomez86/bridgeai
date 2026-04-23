from app.services.scm_providers.base import ScmProvider
from app.services.scm_providers.github import GitHubProvider
from app.services.scm_providers.gitlab import GitLabProvider
from app.services.scm_providers.azure_devops import AzureDevOpsProvider
from app.services.scm_providers.bitbucket import BitbucketProvider
from app.services.ticket_providers.jira_oauth import JiraOAuthProvider

_PROVIDERS: dict[str, object] = {
    "github": GitHubProvider(),
    "gitlab": GitLabProvider(),
    "azure_devops": AzureDevOpsProvider(),
    "bitbucket": BitbucketProvider(),
    "jira": JiraOAuthProvider(),
}

SCM_PLATFORMS = {"github", "gitlab", "azure_devops", "bitbucket"}
SUPPORTED_PLATFORMS = list(_PROVIDERS.keys())


def get_provider(platform: str) -> object:
    provider = _PROVIDERS.get(platform)
    if provider is None:
        raise ValueError(f"Unsupported platform: {platform!r}. Supported: {SUPPORTED_PLATFORMS}")
    return provider
