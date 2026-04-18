"use client"

import { useState, useEffect, useCallback, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { listPlatforms, listConnections, getActiveConnection, type PlatformResponse, type ConnectionResponse } from "@/lib/api-client"
import { PlatformCard } from "@/components/features/connections/PlatformCard"
import { ConnectionCard } from "@/components/features/connections/ConnectionCard"
import { Badge } from "@/components/ui/badge"
import { GitBranch, CheckCircle2 } from "lucide-react"

const PLATFORM_LABELS: Record<string, string> = {
  github: "GitHub",
  gitlab: "GitLab",
  azure_devops: "Azure DevOps",
}

function ConnectionsContent() {
  const searchParams = useSearchParams()
  const [platforms, setPlatforms] = useState<PlatformResponse[]>([])
  const [connections, setConnections] = useState<ConnectionResponse[]>([])
  const [active, setActive] = useState<ConnectionResponse | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    const [p, c, a] = await Promise.all([
      listPlatforms(),
      listConnections(),
      getActiveConnection(),
    ])
    setPlatforms(p)
    setConnections(c)
    setActive(a)
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  useEffect(() => {
    const connected = searchParams.get("connected")
    const error = searchParams.get("error")
    if (connected) {
      setToast(`Successfully connected to ${PLATFORM_LABELS[connected] ?? connected}`)
      refresh()
      setTimeout(() => setToast(null), 5000)
    } else if (error) {
      setToast(`Failed to connect to ${PLATFORM_LABELS[error] ?? error}. Check your OAuth App settings.`)
      setTimeout(() => setToast(null), 6000)
    }
  }, [searchParams, refresh])

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-8">
      {/* Toast */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-slate-900 text-white text-sm px-4 py-3 rounded-lg shadow-lg flex items-center gap-2 max-w-sm">
          <CheckCircle2 className="h-4 w-4 text-green-400 flex-shrink-0" />
          {toast}
        </div>
      )}

      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Connections</h1>
        <p className="mt-1 text-slate-500">
          Connect your GitHub, GitLab, or Azure DevOps account to use your own repositories
        </p>
      </div>

      {/* Active repo */}
      {active?.repo_full_name && (
        <div className="rounded-xl border border-indigo-200 bg-indigo-50 px-5 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <GitBranch className="h-5 w-5 text-indigo-500 flex-shrink-0" />
            <div>
              <p className="text-xs font-medium text-indigo-600 uppercase tracking-wide">Active Repository</p>
              <p className="text-sm font-semibold text-slate-800 mt-0.5 font-mono">{active.repo_full_name}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className="bg-indigo-100 text-indigo-700 border-indigo-200">
              {PLATFORM_LABELS[active.platform] ?? active.platform}
            </Badge>
            <Badge variant="outline" className="font-mono text-xs">
              {active.default_branch}
            </Badge>
          </div>
        </div>
      )}

      {/* Platforms */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-800">Platforms</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {platforms.map((p) => (
            <PlatformCard key={p.platform} platform={p} onUpdated={refresh} />
          ))}
        </div>
      </section>

      {/* Connected accounts */}
      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-800">Connected Accounts</h2>
        {connections.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 px-6 py-10 text-center">
            <GitBranch className="h-8 w-8 text-slate-300 mx-auto mb-3" />
            <p className="text-sm text-slate-500">No accounts connected yet.</p>
            <p className="text-xs text-slate-400 mt-1">
              Configure a platform above and click Connect to get started.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {connections.map((c) => (
              <ConnectionCard key={c.id} connection={c} onUpdated={refresh} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

export default function ConnectionsPage() {
  return (
    <Suspense>
      <ConnectionsContent />
    </Suspense>
  )
}
