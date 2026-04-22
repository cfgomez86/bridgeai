// Empty string → relative URL → goes through Next.js rewrite proxy (/api/v1/* → backend).
// Works identically in local dev, devtunnels, and production.
// Set NEXT_PUBLIC_API_URL only if you need to bypass the proxy (e.g., direct backend in tests).
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? ""

// ---------------------------------------------------------------------------
// Auth token injection
// Primary:  window.Clerk.session.getToken() — available as soon as Clerk.js
//           loads, before any React effect runs. No race condition.
// Fallback: _getToken set by ClerkTokenSync via setTokenGetter().
// ---------------------------------------------------------------------------
let _getToken: (() => Promise<string | null>) | null = null

export function setTokenGetter(fn: (() => Promise<string | null>) | null) {
  _getToken = fn
}

async function resolveToken(): Promise<string | null> {
  // Server-side: no window, no token
  if (typeof window === "undefined") return null

  try {
    // Clerk's global is populated before React hydrates
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const clerk = (window as any).Clerk
    if (clerk?.session?.getToken) {
      const token = await clerk.session.getToken()
      if (token) return token
    }
  } catch {}

  // Fallback: token getter set by ClerkTokenSync useEffect
  try {
    if (_getToken) return await _getToken()
  } catch {}

  return null
}

async function buildHeaders(): Promise<Record<string, string>> {
  const h: Record<string, string> = { "Content-Type": "application/json" }
  const token = await resolveToken()
  if (token) h["Authorization"] = `Bearer ${token}`
  return h
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = await buildHeaders()
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }))
    const detail = (body as { detail?: unknown }).detail
    const message =
      typeof detail === "string" ? detail
      : typeof detail === "object" && detail !== null && "error" in detail
        ? String((detail as { error: unknown }).error)
        : `HTTP ${res.status} ${res.statusText}`
    throw new Error(message)
  }
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as unknown as T
  }
  return res.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PlatformResponse {
  platform: string
  label: string
  server_configured: boolean
}

export interface ConnectionResponse {
  id: string
  platform: string
  display_name: string
  active_repo?: string | null
  repo_full_name?: string | null
  default_branch?: string | null
  is_active?: boolean
  created_at: string
}

export interface RepoResponse {
  id: string
  name: string
  full_name: string
  private: boolean
  default_branch?: string | null
}

export interface IndexResponse {
  files_indexed: number
  files_scanned: number
  files_updated: number
  files_skipped: number
  duration_seconds: number
  source?: string | null
  repo_full_name?: string | null
}

export interface StoryDetailResponse {
  story_id: string
  requirement_id: string
  impact_analysis_id: string
  project_id: string
  title: string
  story_description: string
  acceptance_criteria: string[]
  subtasks: Record<string, string[]>
  definition_of_done: string[]
  risk_notes: string[]
  story_points: number
  risk_level: string
  created_at: string
  generation_time_seconds: number
}

export interface CreateTicketResponse {
  ticket_id: string
  url: string
  provider: string
  status: string
  message?: string
  subtask_urls?: string[]
  subtask_titles?: string[]
  failed_subtasks?: string[]
}

export type ServiceStatus = "healthy" | "not_configured" | "unhealthy"

export interface IntegrationHealthResponse {
  jira: ServiceStatus
  azure_devops: ServiceStatus
}

// ---------------------------------------------------------------------------
// Connections
// ---------------------------------------------------------------------------

export async function listPlatforms(): Promise<PlatformResponse[]> {
  return apiFetch<PlatformResponse[]>("/api/v1/connections/platforms")
}

export async function listConnections(): Promise<ConnectionResponse[]> {
  return apiFetch<ConnectionResponse[]>("/api/v1/connections")
}

export async function getOAuthAuthorizeUrl(platform: string): Promise<{ url: string; redirect_uri: string }> {
  const origin = typeof window !== "undefined" ? window.location.origin : undefined
  const params = origin ? `?origin=${encodeURIComponent(origin)}` : ""
  return apiFetch<{ url: string; redirect_uri: string }>(
    `/api/v1/connections/oauth/authorize/${platform}${params}`
  )
}


export async function deleteConnection(connectionId: string): Promise<void> {
  await apiFetch<unknown>(`/api/v1/connections/${connectionId}`, {
    method: "DELETE",
  })
}

export async function listRepos(connectionId: string): Promise<RepoResponse[]> {
  return apiFetch<RepoResponse[]>(`/api/v1/connections/${connectionId}/repos`)
}

export async function activateRepo(
  connectionId: string,
  repoFullName: string,
  defaultBranch?: string | null,
): Promise<void> {
  await apiFetch<unknown>(`/api/v1/connections/${connectionId}/activate`, {
    method: "POST",
    body: JSON.stringify({ repo_full_name: repoFullName, default_branch: defaultBranch ?? "main" }),
  })
}

export async function getActiveConnection(): Promise<ConnectionResponse | null> {
  try {
    return await apiFetch<ConnectionResponse>("/api/v1/connections/active")
  } catch {
    return null
  }
}

// ---------------------------------------------------------------------------
// Indexing
// ---------------------------------------------------------------------------

export async function indexCode(force = false): Promise<IndexResponse> {
  return apiFetch<IndexResponse>("/api/v1/index", {
    method: "POST",
    body: JSON.stringify({ force }),
  })
}

// ---------------------------------------------------------------------------
// Workflow
// ---------------------------------------------------------------------------

export async function understandRequirement(
  requirementText: string,
  projectId: string,
  language?: string,
): Promise<{
  requirement_id: string
  intent: string
  feature_type: string
  estimated_complexity: string
  keywords: string[]
}> {
  return apiFetch("/api/v1/understand-requirement", {
    method: "POST",
    body: JSON.stringify({
      requirement: requirementText,
      project_id: projectId,
      language,
    }),
  })
}

export async function analyzeImpact(
  requirementText: string,
  projectId: string,
): Promise<{
  analysis_id: string
  files_impacted: number
  modules_impacted: string[]
  risk_level: string
}> {
  return apiFetch("/api/v1/impact-analysis", {
    method: "POST",
    body: JSON.stringify({ requirement: requirementText, project_id: projectId }),
  })
}

export async function generateStory(
  requirementId: string,
  analysisId: string,
  projectId: string,
  language?: string,
): Promise<{
  story_id: string
  title: string
  story_points: number
  risk_level: string
  generation_time_seconds: number
}> {
  return apiFetch("/api/v1/generate-story", {
    method: "POST",
    body: JSON.stringify({
      requirement_id: requirementId,
      impact_analysis_id: analysisId,
      project_id: projectId,
      language,
    }),
  })
}

export async function getStoryDetail(storyId: string): Promise<StoryDetailResponse> {
  return apiFetch<StoryDetailResponse>(`/api/v1/stories/${storyId}`)
}

export async function createTicket(
  storyId: string,
  provider: string,
  projectKey: string,
  issueType: string,
  createSubtasks = false,
): Promise<CreateTicketResponse> {
  return apiFetch<CreateTicketResponse>("/api/v1/tickets", {
    method: "POST",
    body: JSON.stringify({
      story_id: storyId,
      integration_type: provider,
      project_key: projectKey,
      issue_type: issueType,
      create_subtasks: createSubtasks,
    }),
  })
}

export async function checkIntegrationHealth(): Promise<IntegrationHealthResponse> {
  return apiFetch<IntegrationHealthResponse>("/api/v1/integration/health")
}

// ---------------------------------------------------------------------------
// Auth / provisioning
// ---------------------------------------------------------------------------

export interface UserResponse {
  user_id: string
  clerk_user_id: string
  email: string
  name: string | null
  role: string
  tenant_id: string
  tenant_slug: string
  tenant_name: string
}

export async function provision(body: {
  tenant_name: string
  tenant_slug: string
  clerk_org_id: string
  user_email: string
  user_name?: string | null
}): Promise<UserResponse> {
  return apiFetch<UserResponse>("/api/v1/auth/provision", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export async function getMe(): Promise<UserResponse> {
  return apiFetch<UserResponse>("/api/v1/auth/me")
}
