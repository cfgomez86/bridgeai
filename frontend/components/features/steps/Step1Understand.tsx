"use client"

import { useState } from "react"
import { understandRequirement } from "@/lib/api-client"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, Search, Globe } from "lucide-react"

const LANGUAGES = [
  { code: "es", label: "Español" },
  { code: "en", label: "English" },
  { code: "fr", label: "Français" },
  { code: "de", label: "Deutsch" },
  { code: "pt", label: "Português" },
]

interface Step1Props {
  state: WorkflowState
  setProjectId: (id: string) => void
  setRequirementText: (text: string) => void
  setLanguage: (lang: string) => void
  completeStep1: (data: {
    requirementId: string
    intent: string
    featureType: string
    complexity: string
    keywords: string[]
  }) => void
}

export function Step1Understand({
  state,
  setProjectId,
  setRequirementText,
  setLanguage,
  completeStep1,
}: Step1Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isValid = state.requirementText.trim().length >= 10

  async function handleSubmit() {
    if (!isValid) return
    setLoading(true)
    setError(null)
    try {
      const result = await understandRequirement(state.requirementText, state.projectId)
      completeStep1({
        requirementId: result.requirement_id,
        intent: result.intent,
        featureType: result.feature_type,
        complexity: result.estimated_complexity,
        keywords: result.keywords ?? [],
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze requirement")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="h-5 w-5 text-indigo-500" />
          Understand Requirement
        </CardTitle>
        <CardDescription>
          Provide your requirement text and project ID. The AI will extract intent,
          complexity, and domain keywords.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Project ID */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-700" htmlFor="project-id">
            Project ID
          </label>
          <Input
            id="project-id"
            value={state.projectId}
            onChange={(e) => setProjectId(e.target.value)}
            placeholder="my-project"
          />
        </div>

        {/* Language selector */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-700 flex items-center gap-1.5">
            <Globe className="h-3.5 w-3.5 text-slate-400" />
            Story language
          </label>
          <div className="flex flex-wrap gap-2">
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                type="button"
                onClick={() => setLanguage(lang.code)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium border transition-colors ${
                  state.language === lang.code
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "bg-white text-slate-600 border-slate-200 hover:border-indigo-300 hover:text-indigo-600"
                }`}
              >
                {lang.label}
              </button>
            ))}
          </div>
        </div>

        {/* Requirement text */}
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-slate-700" htmlFor="requirement-text">
            Requirement
          </label>
          <Textarea
            id="requirement-text"
            value={state.requirementText}
            onChange={(e) => setRequirementText(e.target.value)}
            rows={6}
            placeholder={
              "Example: As a registered user, I want to reset my password via email so that I can regain access to my account if I forget my credentials."
            }
            className="resize-none"
          />
          {state.requirementText.length > 0 && state.requirementText.trim().length < 10 && (
            <p className="text-xs text-red-500">
              Requirement must be at least 10 characters.
            </p>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Submit */}
        <Button
          onClick={handleSubmit}
          disabled={loading || !isValid}
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyzing…
            </>
          ) : (
            "Analyze Requirement"
          )}
        </Button>
      </CardContent>
    </Card>
  )
}
