"use client"

import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { deleteConnection, type ConnectionResponse } from "@/lib/api-client"
import { RepoSelector } from "./RepoSelector"
import { GitBranch, FolderGit2, Trash2, Loader2 } from "lucide-react"

const PLATFORM_LABELS: Record<string, string> = {
  github: "GitHub",
  gitlab: "GitLab",
  azure_devops: "Azure DevOps",
}

const PLATFORM_ICONS: Record<string, string> = {
  github: "GH",
  gitlab: "GL",
  azure_devops: "AZ",
}

interface ConnectionCardProps {
  connection: ConnectionResponse
  onUpdated: () => void
}

export function ConnectionCard({ connection, onUpdated }: ConnectionCardProps) {
  const [deleting, setDeleting] = useState(false)
  const [showRepos, setShowRepos] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleDelete() {
    setDeleting(true)
    setError(null)
    try {
      await deleteConnection(connection.id)
      onUpdated()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disconnect")
      setDeleting(false)
    }
  }

  return (
    <>
      <Card className={`border-slate-200 ${connection.is_active ? "ring-2 ring-indigo-400" : ""}`}>
        <CardContent className="py-4 px-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <span className="inline-flex items-center justify-center h-8 w-8 rounded-md bg-slate-800 text-white text-xs font-bold flex-shrink-0">
                {PLATFORM_ICONS[connection.platform] ?? "?"}
              </span>
              <div>
                <p className="text-sm font-semibold text-slate-800">{connection.display_name}</p>
                <p className="text-xs text-slate-500">{PLATFORM_LABELS[connection.platform] ?? connection.platform}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {connection.is_active && (
                <Badge className="bg-indigo-50 text-indigo-700 border-indigo-200 text-xs">Active</Badge>
              )}
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowRepos(true)}
                className="gap-1.5 text-xs"
              >
                <FolderGit2 className="h-3.5 w-3.5" />
                Select Repo
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleDelete}
                disabled={deleting}
                className="text-red-500 hover:text-red-700 hover:border-red-300"
              >
                {deleting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
              </Button>
            </div>
          </div>

          {connection.repo_full_name && (
            <div className="flex items-center gap-1.5 text-xs text-slate-600 bg-slate-50 rounded-md px-2.5 py-1.5">
              <GitBranch className="h-3.5 w-3.5 text-slate-400" />
              <span className="font-mono">{connection.repo_full_name}</span>
              <span className="text-slate-400 mx-1">·</span>
              <span>{connection.default_branch}</span>
            </div>
          )}

          {error && <p className="text-xs text-red-600">{error}</p>}
        </CardContent>
      </Card>

      {showRepos && (
        <RepoSelector
          connectionId={connection.id}
          onActivated={() => { setShowRepos(false); onUpdated() }}
          onClose={() => setShowRepos(false)}
        />
      )}
    </>
  )
}
