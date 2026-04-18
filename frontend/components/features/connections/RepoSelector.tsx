"use client"

import { useState, useEffect } from "react"
import { listRepos, activateRepo, type RepoResponse } from "@/lib/api-client"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Loader2, Search, Lock, GitBranch, X } from "lucide-react"

interface RepoSelectorProps {
  connectionId: string
  onActivated: () => void
  onClose: () => void
}

export function RepoSelector({ connectionId, onActivated, onClose }: RepoSelectorProps) {
  const [repos, setRepos] = useState<RepoResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [activating, setActivating] = useState<string | null>(null)

  useEffect(() => {
    listRepos(connectionId)
      .then(setRepos)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load repos"))
      .finally(() => setLoading(false))
  }, [connectionId])

  async function handleSelect(repo: RepoResponse) {
    setActivating(repo.full_name)
    try {
      await activateRepo(connectionId, repo.full_name, repo.default_branch)
      onActivated()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to activate repo")
      setActivating(null)
    }
  }

  const filtered = repos.filter(
    (r) => r.full_name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <h2 className="font-semibold text-slate-900">Select Repository</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Search */}
        <div className="px-5 py-3 border-b border-slate-100">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter repositories…"
              className="pl-9"
            />
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto px-2 py-2">
          {loading && (
            <div className="flex items-center justify-center py-12 gap-2 text-slate-500 text-sm">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading repositories…
            </div>
          )}
          {error && (
            <p className="text-sm text-red-600 px-3 py-4">{error}</p>
          )}
          {!loading && filtered.length === 0 && !error && (
            <p className="text-sm text-slate-500 px-3 py-4 text-center">No repositories found.</p>
          )}
          {filtered.map((repo) => (
            <button
              key={repo.full_name}
              type="button"
              onClick={() => handleSelect(repo)}
              disabled={activating !== null}
              className="w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-lg hover:bg-slate-50 transition-colors text-left"
            >
              <div className="flex items-center gap-2 min-w-0">
                {repo.private && <Lock className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />}
                <span className="text-sm font-medium text-slate-800 truncate">{repo.full_name}</span>
              </div>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <GitBranch className="h-3.5 w-3.5 text-slate-400" />
                <span className="text-xs text-slate-500">{repo.default_branch}</span>
                {activating === repo.full_name && (
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-500" />
                )}
              </div>
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-100 flex justify-end">
          <Button variant="outline" size="sm" onClick={onClose}>Close</Button>
        </div>
      </div>
    </div>
  )
}
