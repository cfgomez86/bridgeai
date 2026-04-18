"use client"

import { useState } from "react"
import { analyzeImpact } from "@/lib/api-client"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { RiskBadge } from "@/components/features/RiskBadge"
import { StepSummaryCard } from "@/components/features/StepSummaryCard"
import { Loader2, Zap, Search } from "lucide-react"

const truncate = (text: string, max: number) =>
  text.length > max ? text.slice(0, max) + "…" : text

interface Step2Props {
  state: WorkflowState
  completeStep2: (data: {
    analysisId: string
    filesImpacted: number
    modulesImpacted: string[]
    riskLevel: string
  }) => void
}

export function Step2Impact({ state, completeStep2 }: Step2Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleAnalyze() {
    setLoading(true)
    setError(null)
    try {
      const result = await analyzeImpact(state.requirementText, state.projectId)
      completeStep2({
        analysisId: result.analysis_id,
        filesImpacted: result.files_impacted,
        modulesImpacted: result.modules_impacted,
        riskLevel: result.risk_level,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze impact")
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
        <div className="flex flex-wrap gap-2 items-center">
          {state.intent && (
            <span className="text-xs text-slate-500">
              Intent: <span className="font-medium text-slate-700">{state.intent}</span>
            </span>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {state.featureType && <Badge variant="secondary">{state.featureType}</Badge>}
          {state.complexity && <Badge variant="outline">Complexity: {state.complexity}</Badge>}
          {state.language && (
            <Badge variant="outline" className="capitalize">
              Lang: {state.language}
            </Badge>
          )}
        </div>
        {state.keywords.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {state.keywords.map((kw) => (
              <Badge key={kw} variant="outline" className="text-xs">
                {kw}
              </Badge>
            ))}
          </div>
        )}
      </StepSummaryCard>

      {/* Impact analysis card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-indigo-500" />
            Impact Analysis
          </CardTitle>
          <CardDescription>
            Analyze which files and modules in your codebase are affected by this requirement.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {state.filesImpacted !== null && (
            <div className="space-y-3 mb-4">
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-slate-600">Files impacted:</span>
                <Badge variant="secondary">{state.filesImpacted}</Badge>
              </div>
              {state.modulesImpacted.length > 0 && (
                <div>
                  <span className="text-sm font-medium text-slate-600 block mb-1.5">
                    Modules impacted:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {state.modulesImpacted.map((m) => (
                      <Badge key={m} variant="outline" className="text-xs">
                        {m}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {state.riskLevel && (
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-600">Risk level:</span>
                  <RiskBadge risk={state.riskLevel} />
                </div>
              )}
            </div>
          )}

          <Button
            onClick={handleAnalyze}
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analyzing Impact…
              </>
            ) : (
              "Analyze Impact"
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
