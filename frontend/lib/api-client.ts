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
let _authSettled = false  // true once setTokenGetter is called for the first time
let _inflightToken: Promise<string | null> | null = null
const _tokenWaiters: Array<() => void> = []

export function setTokenGetter(fn: (() => Promise<string | null>) | null) {
  _getToken = fn
  _authSettled = true
  _inflightToken = null
  // Notify waiters whether we got a getter or null — both states are actionable.
  for (const cb of _tokenWaiters.splice(0)) cb()
}

async function resolveToken(): Promise<string | null> {
  if (typeof window === "undefined") return null
  if (!_getToken && !_authSettled) {
    // Auth0TokenSync hasn't settled yet — wait up to 5s before giving up.
    // Once _authSettled is true (even with a null getter), skip this wait
    // so subsequent calls return immediately instead of re-waiting.
    await new Promise<void>((resolve) => {
      const timer = setTimeout(() => {
        const idx = _tokenWaiters.indexOf(resolve)
        if (idx !== -1) _tokenWaiters.splice(idx, 1)
        resolve()
      }, 5000)
      _tokenWaiters.push(() => { clearTimeout(timer); resolve() })
    })
  }
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

export class ApiError extends Error {
  status: number
  detail: unknown
  constructor(message: string, status: number, detail: unknown) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.detail = detail
  }
}

export interface EntityNotFoundDetail {
  code: "ENTITY_NOT_FOUND"
  entity: string
  message: string
  suggestions: string[]
  hint: string
}

export interface IncoherentRequirementErrorDetail {
  code: "INCOHERENT_REQUIREMENT"
  message: string
  reason_codes: string[]
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
    let message: string
    if (typeof detail === "string") {
      message = detail
    } else if (detail && typeof detail === "object") {
      const d = detail as Record<string, unknown>
      message =
        typeof d.message === "string" ? d.message
        : typeof d.error === "string" ? d.error
        : `HTTP ${res.status} ${res.statusText}`
    } else {
      message = `HTTP ${res.status} ${res.statusText}`
    }
    throw new ApiError(message, res.status, detail)
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
  repo_name?: string | null
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
  generator_model?: string | null
  generator_calls?: number
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
  entity_not_found?: boolean
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
  evaluated_by_model: string | null
  coherence_model: string | null
  coherence_calls: number
  parser_model: string | null
  parser_calls: number
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

export type ForceReason = "intentional_new" | "ambiguous"

export async function generateStory(
  requirementId: string,
  analysisId: string,
  projectId: string,
  sourceConnectionId: string,
  language?: string,
  force?: boolean,
  forceReason?: ForceReason,
): Promise<{
  story_id: string
  source_connection_id: string
  title: string
  story_points: number
  risk_level: string
  generation_time_seconds: number
  entity_not_found?: boolean
}> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 270_000)
  try {
    return await apiFetch("/api/v1/generate-story", {
      method: "POST",
      body: JSON.stringify({
        requirement_id: requirementId,
        impact_analysis_id: analysisId,
        project_id: projectId,
        source_connection_id: sourceConnectionId,
        language,
        ...(force ? { force: true } : {}),
        ...(force && forceReason ? { force_reason: forceReason } : {}),
      }),
      signal: controller.signal,
    })
  } finally {
    clearTimeout(timer)
  }
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

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export interface DashboardStats {
  window_days: number | null
  requirements_count: number
  stories_count: number
  impact_analyses_count: number
  tickets_count: number
  conversion_rate: number | null
  feedback_total: number
  feedback_thumbs_up: number
  feedback_thumbs_down: number
  feedback_approval_rate: number | null
  quality_avg_overall: number | null
  quality_evaluated_count: number
  quality_avg_organic: number | null
  quality_count_organic: number
  quality_avg_forced: number | null
  quality_count_forced: number
  quality_count_creation_bypass: number
  quality_count_override: number
  tickets_failed_count: number
  avg_generation_time_seconds: number | null
  unnecessary_force_count: number
  quality_organic_avg_completeness: number | null
  quality_organic_avg_specificity: number | null
  quality_organic_avg_feasibility: number | null
  quality_organic_avg_risk_coverage: number | null
  quality_organic_avg_language_consistency: number | null
  tickets_by_provider: Record<string, number>
  stories_by_risk: Record<string, number>
}

export interface DashboardActivityEvent {
  tone: "ok" | "accent" | "warn" | "neutral"
  title: string
  meta: string
  time: string
  badge?: string | null
  link?: string | null
}

export interface NegativeFeedbackItem {
  id: string
  story_id: string
  story_title: string
  user_id: string
  rating: string
  comment: string
  created_at: string
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return apiFetch<DashboardStats>("/api/v1/dashboard/stats")
}

export async function getDashboardActivity(limit = 10): Promise<DashboardActivityEvent[]> {
  return apiFetch<DashboardActivityEvent[]>(`/api/v1/dashboard/activity?limit=${limit}`)
}

export async function getNegativeFeedback(
  limit = 20,
  offset = 0,
  rating?: string | null,
): Promise<NegativeFeedbackItem[]> {
  const ratingParam = rating ? `&rating=${encodeURIComponent(rating)}` : ""
  return apiFetch<NegativeFeedbackItem[]>(
    `/api/v1/feedback/comments?limit=${limit}&offset=${offset}${ratingParam}`,
  )
}

// ---------------------------------------------------------------------------
// Coherence pre-filter — admin review
// ---------------------------------------------------------------------------

export interface IncoherentRequirementItem {
  id: string
  requirement_text_preview: string  // first 200 chars; full text available via detail endpoint
  warning: string | null
  reason_codes: string[]
  user_id: string
  user_email: string | null
  project_id: string | null
  source_connection_id: string | null
  model_used: string | null
  created_at: string
}

export interface IncoherentRequirementListResponse {
  items: IncoherentRequirementItem[]
  total: number
  limit: number
  offset: number
}

export async function getIncoherentRequirements(
  limit = 20,
  offset = 0,
  reason?: string | null,
): Promise<IncoherentRequirementListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })
  if (reason) params.set("reason", reason)
  return apiFetch<IncoherentRequirementListResponse>(
    `/api/v1/admin/incoherent-requirements?${params.toString()}`,
  )
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
