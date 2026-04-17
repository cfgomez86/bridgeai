"use client"

import { useState, useEffect } from "react"
import {
  createTicket,
  checkIntegrationHealth,
  type CreateTicketResponse,
  type IntegrationHealthResponse,
} from "@/lib/api-client"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { HealthStatus } from "@/components/features/HealthStatus"
import { Loader2, Ticket, ExternalLink, Plus } from "lucide-react"

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

  useEffect(() => {
    checkIntegrationHealth()
      .then(setHealth)
      .catch(() => {
        // silently ignore health check errors
      })
  }, [])

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
      {/* Story summary */}
      {state.storyId && (
        <Card className="bg-slate-50 border-slate-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Story Ready</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-600">
              Story ID:{" "}
              <span className="font-mono text-xs bg-slate-200 rounded px-1.5 py-0.5">
                {state.storyId}
              </span>
            </p>
          </CardContent>
        </Card>
      )}

      {/* Integration health */}
      {health && (
        <Card className="border-slate-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Integration Status</CardTitle>
          </CardHeader>
          <CardContent>
            <HealthStatus
              jira={health.jira}
              azureDevops={health.azure_devops}
            />
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
                  Ticket ID:{" "}
                  <span className="font-mono font-medium">{ticket.ticket_id}</span>
                </p>
                <p className="text-sm text-green-700">
                  Provider:{" "}
                  <span className="font-medium capitalize">{ticket.provider}</span>
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

              <Button
                onClick={reset}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                <Plus className="h-4 w-4" />
                Start New Story
              </Button>
            </div>
          ) : (
            <>
              {/* Provider select */}
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-slate-700" htmlFor="provider-select">
                  Provider
                </label>
                <Select value={provider} onValueChange={setProvider}>
                  <SelectTrigger id="provider-select">
                    <SelectValue
                      placeholder="Select provider"
                      labelMap={{ jira: "Jira", azure_devops: "Azure DevOps" }}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="jira">Jira</SelectItem>
                    <SelectItem value="azure_devops">Azure DevOps</SelectItem>
                  </SelectContent>
                </Select>
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
