"use client"

import { useState, useEffect } from "react"
import {
  createTicket,
  checkIntegrationHealth,
  getStoryDetail,
  type CreateTicketResponse,
  type IntegrationHealthResponse,
  type StoryDetailResponse,
} from "@/lib/api-client"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { HealthStatus } from "@/components/features/HealthStatus"
import { RiskBadge } from "@/components/features/RiskBadge"
import { StepSummaryCard } from "@/components/features/StepSummaryCard"
import {
  Loader2, Ticket, ExternalLink, Plus, Search, Zap, GitPullRequest,
  FileText, CheckCircle, Code, ListChecks, AlertTriangle,
} from "lucide-react"

const truncate = (text: string, max: number) =>
  text.length > max ? text.slice(0, max) + "…" : text

const PROVIDERS: Record<string, string> = {
  jira: "Jira",
  azure_devops: "Azure DevOps",
}

interface Step4Props {
  state: WorkflowState
  completeStep4: () => void
  reset: () => void
}

export function Step4Ticket({ state, completeStep4, reset }: Step4Props) {
  const [provider, setProvider] = useState<string>("jira")
  const [projectKey, setProjectKey] = useState("SCRUM")
  const [issueType, setIssueType] = useState("Story")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ticket, setTicket] = useState<CreateTicketResponse | null>(null)
  const [health, setHealth] = useState<IntegrationHealthResponse | null>(null)
  const [story, setStory] = useState<StoryDetailResponse | null>(null)

  useEffect(() => {
    checkIntegrationHealth()
      .then(setHealth)
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (state.storyId) {
      getStoryDetail(state.storyId)
        .then(setStory)
        .catch(() => {})
    }
  }, [state.storyId])

  async function handleCreate() {
    if (!state.storyId) return
    setLoading(true)
    setError(null)
    try {
      const result = await createTicket(state.storyId, provider, projectKey, issueType)
      setTicket(result)
      completeStep4()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create ticket")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Step 1 collapsible summary */}
      <StepSummaryCard
        title="Paso 1: Requirement Analysis"
        icon={<Search className="h-3.5 w-3.5" />}
      >
        <p className="text-sm text-slate-600 italic">
          &ldquo;{truncate(state.requirementText, 120)}&rdquo;
        </p>
        <div className="flex flex-wrap gap-1.5">
          {state.featureType && <Badge variant="secondary">{state.featureType}</Badge>}
          {state.complexity && <Badge variant="outline">Complexity: {state.complexity}</Badge>}
          {state.language && (
            <Badge variant="outline" className="capitalize">Lang: {state.language}</Badge>
          )}
        </div>
        {state.intent && (
          <p className="text-xs text-slate-500">
            Intent: <span className="font-medium text-slate-700">{state.intent}</span>
          </p>
        )}
      </StepSummaryCard>

      {/* Step 2 collapsible summary */}
      <StepSummaryCard
        title="Paso 2: Impact Analysis"
        icon={<Zap className="h-3.5 w-3.5" />}
      >
        <div className="flex flex-wrap gap-3 items-center">
          {state.filesImpacted !== null && (
            <div className="flex items-center gap-1.5">
              <span className="text-sm text-slate-500">Files:</span>
              <Badge variant="secondary">{state.filesImpacted}</Badge>
            </div>
          )}
          {state.riskLevel && (
            <div className="flex items-center gap-1.5">
              <span className="text-sm text-slate-500">Risk:</span>
              <RiskBadge risk={state.riskLevel} />
            </div>
          )}
        </div>
        {state.modulesImpacted.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {state.modulesImpacted.map((m) => (
              <Badge key={m} variant="outline" className="text-xs">{m}</Badge>
            ))}
          </div>
        )}
      </StepSummaryCard>

      {/* Step 3 — full story preview, expanded by default */}
      <StepSummaryCard
        title="Paso 3: Generated Story"
        icon={<GitPullRequest className="h-3.5 w-3.5" />}
        defaultOpen={true}
      >
        {!story ? (
          <div className="flex items-center gap-2 py-2 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading story…
          </div>
        ) : (
          <div className="space-y-4">
            {/* Header */}
            <div>
              <p className="font-semibold text-slate-800">{story.title}</p>
              <div className="flex items-center gap-2 mt-1.5">
                <Badge variant="secondary">
                  {story.story_points} {story.story_points === 1 ? "point" : "points"}
                </Badge>
                <RiskBadge risk={story.risk_level} />
              </div>
            </div>

            {/* Description */}
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <FileText className="h-3.5 w-3.5 text-slate-400" />
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Description
                </span>
              </div>
              <p className="text-sm leading-relaxed text-slate-700">{story.story_description}</p>
            </div>

            <Separator />

            {/* Acceptance criteria */}
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <CheckCircle className="h-3.5 w-3.5 text-slate-400" />
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Acceptance Criteria
                </span>
              </div>
              <ol className="space-y-1.5 list-none pl-0">
                {story.acceptance_criteria.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="flex-shrink-0 inline-flex items-center justify-center h-5 w-5 rounded-full bg-slate-100 text-xs font-medium">
                      {i + 1}
                    </span>
                    <span>{item}</span>
                  </li>
                ))}
              </ol>
            </div>

            <Separator />

            {/* Technical tasks */}
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <Code className="h-3.5 w-3.5 text-slate-400" />
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Technical Tasks
                </span>
              </div>
              <ul className="space-y-1.5">
                {story.technical_tasks.map((task, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="mt-0.5 h-4 w-4 flex-shrink-0 rounded border border-slate-300" />
                    <span>{task}</span>
                  </li>
                ))}
              </ul>
            </div>

            <Separator />

            {/* Definition of done */}
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <ListChecks className="h-3.5 w-3.5 text-slate-400" />
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Definition of Done
                </span>
              </div>
              <ul className="space-y-1.5">
                {story.definition_of_done.map((item, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="mt-0.5 h-4 w-4 flex-shrink-0 rounded border border-slate-300" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Risk notes (if any) */}
            {story.risk_notes && story.risk_notes.length > 0 && (
              <>
                <Separator />
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                    <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Risk Notes
                    </span>
                  </div>
                  <ul className="space-y-1.5">
                    {story.risk_notes.map((note, i) => (
                      <li key={i} className="text-sm text-slate-600 flex items-start gap-2">
                        <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-amber-400" />
                        {note}
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </div>
        )}
      </StepSummaryCard>

      {/* Integration health */}
      {health && (
        <Card className="border-slate-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Integration Status</CardTitle>
          </CardHeader>
          <CardContent>
            <HealthStatus jira={health.jira} azureDevops={health.azure_devops} />
          </CardContent>
        </Card>
      )}

      {/* Ticket creation */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Ticket className="h-5 w-5 text-indigo-500" />
            Create Ticket
          </CardTitle>
          <CardDescription>
            Push the generated story directly to your project management tool.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {ticket ? (
            <div className="space-y-4">
              <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-4 space-y-2">
                <p className="text-sm font-semibold text-green-800">Ticket created successfully!</p>
                <p className="text-sm text-green-700">
                  Ticket ID: <span className="font-mono font-medium">{ticket.ticket_id}</span>
                </p>
                <p className="text-sm text-green-700">
                  Provider: <span className="font-medium capitalize">{ticket.provider}</span>
                </p>
                {ticket.url && (
                  <a
                    href={ticket.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800 underline underline-offset-2 font-medium"
                  >
                    Open in {ticket.provider}
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>
              <Button onClick={reset} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white">
                <Plus className="h-4 w-4" />
                Start New Story
              </Button>
            </div>
          ) : (
            <>
              {/* Provider select */}
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-slate-700">Provider</label>
                <div className="flex gap-2">
                  {Object.entries(PROVIDERS).map(([val, label]) => (
                    <button
                      key={val}
                      type="button"
                      onClick={() => setProvider(val)}
                      className={`flex-1 px-3 py-2 text-sm font-medium rounded-md border transition-colors ${
                        provider === val
                          ? "bg-indigo-600 text-white border-indigo-600"
                          : "bg-white text-slate-600 border-slate-200 hover:border-indigo-300 hover:text-indigo-600"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Project key */}
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-slate-700" htmlFor="project-key">
                  Project Key
                </label>
                <Input
                  id="project-key"
                  value={projectKey}
                  onChange={(e) => setProjectKey(e.target.value)}
                  placeholder="SCRUM"
                />
              </div>

              {/* Issue type */}
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-slate-700" htmlFor="issue-type">
                  Issue Type
                </label>
                <Input
                  id="issue-type"
                  value={issueType}
                  onChange={(e) => setIssueType(e.target.value)}
                  placeholder="Story"
                />
              </div>

              <Button
                onClick={handleCreate}
                disabled={loading || !state.storyId || !projectKey.trim()}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Creating Ticket…
                  </>
                ) : (
                  <>
                    <Ticket className="h-4 w-4" />
                    Create Ticket
                  </>
                )}
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
