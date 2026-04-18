from app.services.scm_providers.base import ScmProvider
from app.services.scm_providers.github import GitHubProvider
from app.services.scm_providers.gitlab import GitLabProvider
from app.services.scm_providers.azure_devops import AzureDevOpsProvider

_PROVIDERS: dict[str, ScmProvider] = {
    "github": GitHubProvider(),
    "gitlab": GitLabProvider(),
    "azure_devops": AzureDevOpsProvider(),
}

SUPPORTED_PLATFORMS = list(_PROVIDERS.keys())


def get_provider(platform: str) -> ScmProvider:
    provider = _PROVIDERS.get(platform)
    if provider is None:
        raise ValueError(f"Unsupported SCM platform: {platform!r}. Supported: {SUPPORTED_PLATFORMS}")
    return provider
