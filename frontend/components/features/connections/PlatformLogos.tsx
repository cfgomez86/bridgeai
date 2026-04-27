// Shared inline SVG logos for SCM and ticket platforms.
// GitHub uses currentColor so it inherits dark/light theme from its container.
// All other logos use official brand hex colors.

export function GitHubLogo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-label="GitHub">
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
    </svg>
  )
}

export function GitLabLogo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-label="GitLab">
      <path d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 01-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 014.82 2a.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.49h8.1l2.44-7.49A.42.42 0 0118.6 2a.43.43 0 01.58 0 .42.42 0 01.11.18l2.44 7.51L23 13.45a.84.84 0 01-.35.94z" fill="#FC6D26" />
    </svg>
  )
}

export function AzureLogo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 18 18" aria-label="Azure DevOps">
      <path d="M17 4v9.74l-4 3.28-6.2-2.26V17l-3.51-4.59 10.23.8V4.44zm-3.41.49L7.85 1v2.29L2.58 4.84 1 6.87v4.61l2.26 1V6.57z" fill="#0078D4" />
    </svg>
  )
}

export function BitbucketLogo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-label="Bitbucket">
      <path d="M.778 1.213a.768.768 0 00-.768.892l3.263 19.81c.084.5.515.865 1.022.865h15.386a.768.768 0 00.768-.633l3.263-19.842a.768.768 0 00-.768-.892L.778 1.213zM14.13 15.538H9.87L8.777 9.116h6.478l-1.124 6.422z" fill="#2684FF" />
    </svg>
  )
}

export function JiraLogo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-label="Jira">
      <path d="M11.53 2c0 2.4 1.97 4.35 4.35 4.35h1.78v1.7c0 2.4 1.94 4.34 4.34 4.35V2.84a.84.84 0 00-.84-.84H11.53zM6.77 6.8a4.362 4.362 0 004.35 4.34h1.78v1.72a4.362 4.362 0 004.35 4.34V7.63a.84.84 0 00-.84-.83H6.77zM2 11.6c0 2.4 1.95 4.34 4.35 4.34h1.78v1.72C8.13 20.06 10.08 22 12.48 22v-9.57a.84.84 0 00-.84-.84L2 11.6z" fill="#2684FF" />
    </svg>
  )
}

/** Dispatches to the correct logo by platform key. Falls back to a mono abbreviation. */
export function PlatformLogo({ platform, size = 22 }: { platform: string; size?: number }) {
  if (platform === "github")       return <GitHubLogo size={size} />
  if (platform === "gitlab")       return <GitLabLogo size={size} />
  if (platform === "azure_devops" || platform === "azure_boards") return <AzureLogo size={size} />
  if (platform === "bitbucket")    return <BitbucketLogo size={size} />
  if (platform === "jira")         return <JiraLogo size={size} />
  return (
    <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", fontWeight: 700 }}>
      {platform.slice(0, 2).toUpperCase()}
    </span>
  )
}
