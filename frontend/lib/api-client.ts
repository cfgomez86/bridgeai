// Empty string → relative URL → goes through Next.js rewrite proxy (/api/v1/* → backend).
// Works identically in local dev, devtunnels, and production.
// Set NEXT_PUBLIC_API_URL only if you need to bypass the proxy (e.g., direct backend in tests).
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? ""

// ---------------------------------------------------------------------------
// Auth token injection
// Token getter is set by Auth0TokenSync (useEffect on session change).
// On the server side tokens are obtained directly via getAccessToken().
// ---------------------------------------------------------------------------
let _getToken: (() => Promise<string | null>) | null = null
let _inflightToken: Promise<string | null> | null = null

export function setTokenGetter(fn: (() => Promise<string | null>) | null) {
  _getToken = fn
  _inflightToken = null
}

async function resolveToken(): Promise<string | null> {
  if (typeof window === "undefined") return null
  if (!_getToken) return null
  // Deduplicate parallel calls — all share the same in-flight request
  if (!_inflightToken) {
    _inflightToken = _getToken().catch(() => null).finally(() => { _inflightToken = null })
  }
  return _inflightToken
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
  boards_project?: string | null
  default_branch?: string | null
  is_active?: boolean
  created_at: string
  auth_method?: string
}

export interface RepoResponse {
  id: string
  name: string
  full_name: string
  private: boolean
  default_branch?: string | null
}

export interface JiraSiteResponse {
  id: string
  name: string
  url: string
  api_base_url: string
}

export interface JiraProjectResponse {
  key: string
  name: string
}

export interface AzureProjectResponse {
  name: string
  org: string
  full_name: string
  process_template: string
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

export interface IndexStatusResponse {
  total_files: number
  last_indexed_at: string | null
}

export type Subtask = {
  title: string
  description: string
}

export interface StoryDetailResponse {
  story_id: string
  source_connection_id: string
  requirement_id: string
  impact_analysis_id: string
  project_id: string
  title: string
  story_description: string
  acceptance_criteria: string[]
  subtasks: Record<"frontend" | "backend" | "configuration", Subtask[]>
  definition_of_done: string[]
  risk_notes: string[]
  story_points: number
  risk_level: string
  created_at: string
  generation_time_seconds: number
  is_locked?: boolean
}

export interface StoryUpdateRequest {
  source_connection_id: string
  title?: string
  story_description?: string
  acceptance_criteria?: string[]
  subtasks?: Record<string, Subtask[]>
  definition_of_done?: string[]
  risk_notes?: string[]
  story_points?: number
  risk_level?: string
}

export interface FeedbackResponse {
  id: string
  story_id: string
  user_id: string
  rating: string
  comment?: string | null
  created_at: string
  updated_at: string
}

export interface StructuralMetrics {
  schema_valid: boolean
  ac_count: number
  risk_notes_count: number
  subtask_count: number
  cited_paths_total: number
  cited_paths_existing: number
  citation_grounding_ratio: number
}

export interface JudgeScores {
  completeness: number
  specificity: number
  feasibility: number
  risk_coverage: number
  language_consistency: number
  overall: number
  justification?: string | null
  judge_model?: string | null
  evaluated_at?: string | null
  dispersion?: number | null
  samples_used?: number | null
  evidence?: Record<string, string> | null
}

export interface QualityMetricsResponse {
  story_id: string
  structural: StructuralMetrics
  judge?: JudgeScores | null
}

export interface SystemQualityResponse {
  status: string
  data?: Record<string, unknown> | null
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
  return apiFetch<{ url: string; redirect_uri: string }>(
    `/api/v1/connections/oauth/authorize/${platform}`
  )
}


export async function createPatConnection(
  platform: string,
  token: string,
  orgUrl?: string,
  baseUrl?: string,
): Promise<ConnectionResponse> {
  return apiFetch<ConnectionResponse>("/api/v1/connections/pat", {
    method: "POST",
    body: JSON.stringify({ platform, token, org_url: orgUrl, base_url: baseUrl }),
  })
}

// endpoint: POST /api/v1/connections/pat
export async function createPATConnection(
  platform: string,
  payload: { token: string; instance_url?: string; email?: string },
): Promise<ConnectionResponse> {
  // Azure DevOps uses org_url; all other platforms use base_url
  const extra = payload.instance_url
    ? platform === "azure_devops"
      ? { org_url: payload.instance_url }
      : { base_url: payload.instance_url }
    : {}
  return apiFetch<ConnectionResponse>("/api/v1/connections/pat", {
    method: "POST",
    body: JSON.stringify({ platform, token: payload.token, email: payload.email || undefined, ...extra }),
  })
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

export async function activateAzureProject(
  connectionId: string,
  projectFullName: string,
): Promise<void> {
  await apiFetch<unknown>(`/api/v1/connections/${connectionId}/activate-project`, {
    method: "POST",
    body: JSON.stringify({ project_full_name: projectFullName }),
  })
}

export async function listSites(connectionId: string): Promise<JiraSiteResponse[]> {
  return apiFetch<JiraSiteResponse[]>(`/api/v1/connections/${connectionId}/sites`)
}

export async function listAzureProjects(connectionId: string): Promise<AzureProjectResponse[]> {
  return apiFetch<AzureProjectResponse[]>(`/api/v1/connections/${connectionId}/projects`)
}

export async function getAzureProjectProcess(connectionId: string, projectName: string): Promise<string> {
  const encoded = encodeURIComponent(projectName)
  const res = await apiFetch<{ process_template: string }>(
    `/api/v1/connections/${connectionId}/project-process?project=${encoded}`
  )
  return res.process_template ?? ""
}

export async function listJiraProjects(connectionId: string): Promise<JiraProjectResponse[]> {
  return apiFetch<JiraProjectResponse[]>(`/api/v1/connections/${connectionId}/jira-projects`)
}

export async function activateSite(
  connectionId: string,
  cloudId: string,
  apiBaseUrl: string,
  siteUrl: string,
  siteName: string,
): Promise<void> {
  await apiFetch<unknown>(`/api/v1/connections/${connectionId}/activate-site`, {
    method: "POST",
    body: JSON.stringify({
      cloud_id: cloudId,
      api_base_url: apiBaseUrl,
      site_url: siteUrl,
      site_name: siteName,
    }),
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
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 60_000)
  try {
    return await apiFetch<IndexResponse>("/api/v1/index", {
      method: "POST",
      body: JSON.stringify({ force }),
      signal: controller.signal,
    })
  } finally {
    clearTimeout(timer)
  }
}

export async function getIndexStatus(): Promise<IndexStatusResponse> {
  return apiFetch<IndexStatusResponse>("/api/v1/index/status")
}

// ---------------------------------------------------------------------------
// Workflow
// ---------------------------------------------------------------------------

export async function understandRequirement(
  requirementText: string,
  projectId: string,
  sourceConnectionId: string,
  language?: string,
): Promise<{
  requirement_id: string
  source_connection_id: string
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
      source_connection_id: sourceConnectionId,
      language,
    }),
  })
}

export async function analyzeImpact(
  requirementText: string,
  projectId: string,
  sourceConnectionId: string,
): Promise<{
  analysis_id: string
  source_connection_id: string
  files_impacted: number
  modules_impacted: string[]
  risk_level: string
}> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 120_000)
  try {
    return await apiFetch("/api/v1/impact-analysis", {
      method: "POST",
      body: JSON.stringify({
        requirement: requirementText,
        project_id: projectId,
        source_connection_id: sourceConnectionId,
      }),
      signal: controller.signal,
    })
  } finally {
    clearTimeout(timer)
  }
}

export async function generateStory(
  requirementId: string,
  analysisId: string,
  projectId: string,
  sourceConnectionId: string,
  language?: string,
): Promise<{
  story_id: string
  source_connection_id: string
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
      source_connection_id: sourceConnectionId,
      language,
    }),
  })
}

export async function getStoryDetail(storyId: string): Promise<StoryDetailResponse> {
  return apiFetch<StoryDetailResponse>(`/api/v1/stories/${storyId}`)
}

export async function updateStory(
  storyId: string,
  patch: StoryUpdateRequest,
): Promise<StoryDetailResponse> {
  return apiFetch<StoryDetailResponse>(`/api/v1/stories/${storyId}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  })
}

export async function getStoryFeedback(storyId: string): Promise<FeedbackResponse | null> {
  return apiFetch<FeedbackResponse | null>(`/api/v1/stories/${storyId}/feedback`)
}

export async function submitStoryFeedback(
  storyId: string,
  rating: string,
  comment?: string,
): Promise<FeedbackResponse> {
  return apiFetch<FeedbackResponse>(`/api/v1/stories/${storyId}/feedback`, {
    method: "POST",
    body: JSON.stringify({ rating, comment }),
  })
}

export async function getStoryQuality(storyId: string): Promise<QualityMetricsResponse> {
  return apiFetch<QualityMetricsResponse>(`/api/v1/stories/${storyId}/quality`)
}

export async function evaluateStoryQuality(storyId: string): Promise<QualityMetricsResponse> {
  return apiFetch<QualityMetricsResponse>(`/api/v1/stories/${storyId}/quality/evaluate`, {
    method: "POST",
    body: "{}",
  })
}

export async function getSystemQuality(): Promise<SystemQualityResponse> {
  return apiFetch<SystemQualityResponse>("/api/v1/system/quality")
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
  email: string
  name: string | null
  role: string
  tenant_id: string
  tenant_name: string
}

export async function provision(body: {
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
