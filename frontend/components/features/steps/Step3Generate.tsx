"use client"

import { useState } from "react"
import { generateStory, getStoryDetail, type StoryDetailResponse } from "@/lib/api-client"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { RiskBadge } from "@/components/features/RiskBadge"
import { StepSummaryCard } from "@/components/features/StepSummaryCard"
import { Loader2, GitPullRequest, CheckCircle, Code, ListChecks, FileText, Search, Zap } from "lucide-react"

const truncate = (text: string, max: number) =>
  text.length > max ? text.slice(0, max) + "…" : text

interface Step3Props {
  state: WorkflowState
  completeStep3: (storyId: string, storyTitle: string, storyPoints: number) => void
}

export function Step3Generate({ state, completeStep3 }: Step3Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [story, setStory] = useState<StoryDetailResponse | null>(null)

  async function handleGenerate() {
    if (!state.requirementId || !state.analysisId) return
    setLoading(true)
    setError(null)
    try {
      const genResult = await generateStory(
        state.requirementId,
        state.analysisId,
        state.projectId,
        state.language
      )
      const detail = await getStoryDetail(genResult.story_id)
      setStory(detail)
      completeStep3(genResult.story_id, detail.title, detail.story_points)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate story")
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
        {state.keywords.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {state.keywords.map((kw) => (
              <Badge key={kw} variant="outline" className="text-xs">{kw}</Badge>
            ))}
          </div>
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

      {/* Generate card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <GitPullRequest className="h-5 w-5 text-indigo-500" />
            Generate Story
          </CardTitle>
          <CardDescription>
            Create a complete user story with acceptance criteria, technical tasks, and
            definition of done.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Story detail */}
          {story && (
            <div className="space-y-5">
              <div>
                <h3 className="font-semibold text-lg">{story.title}</h3>
                <div className="flex items-center gap-2 mt-1.5">
                  <Badge variant="secondary">
                    {story.story_points} {story.story_points === 1 ? "point" : "points"}
                  </Badge>
                  <RiskBadge risk={story.risk_level} />
                </div>
              </div>

              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <FileText className="h-4 w-4 text-slate-400" />
                  <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Description
                  </span>
                </div>
                <p className="text-sm leading-relaxed text-slate-700">{story.story_description}</p>
              </div>

              <Separator />

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle className="h-4 w-4 text-slate-400" />
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

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Code className="h-4 w-4 text-slate-400" />
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

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <ListChecks className="h-4 w-4 text-slate-400" />
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
            </div>
          )}

          {!story && (
            <Button
              onClick={handleGenerate}
              disabled={loading || !state.requirementId || !state.analysisId}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating Story…
                </>
              ) : (
                "Generate Story"
              )}
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
