"use client"

import { useState, useEffect } from "react"
import { indexCode, getActiveConnection, type IndexResponse, type ConnectionResponse } from "@/lib/api-client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Database, RefreshCw, Loader2, GitBranch, HardDrive } from "lucide-react"

export default function IndexingPage() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<IndexResponse | null>(null)
  const [activeConn, setActiveConn] = useState<ConnectionResponse | null | undefined>(undefined)

  useEffect(() => {
    getActiveConnection().then(setActiveConn)
  }, [])

  const isRemote = activeConn && activeConn.repo_full_name

  async function handleIndex(force: boolean) {
    setLoading(true)
    setError(null)
    try {
      const data = await indexCode(force)
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Code Index</h1>
        <p className="mt-1 text-slate-500">
          Scan and index your codebase to enable accurate impact analysis
        </p>
      </div>

      {/* Source indicator */}
      {activeConn !== undefined && (
        <div className={`rounded-lg border px-4 py-3 flex items-center gap-3 text-sm ${
          isRemote
            ? "border-indigo-200 bg-indigo-50 text-indigo-800"
            : "border-slate-200 bg-slate-50 text-slate-600"
        }`}>
          {isRemote ? (
            <>
              <GitBranch className="h-4 w-4 flex-shrink-0" />
              <span>
                Indexing from <strong>{activeConn.platform}</strong>:{" "}
                <strong>{activeConn.repo_full_name}</strong> ({activeConn.default_branch})
              </span>
            </>
          ) : (
            <>
              <HardDrive className="h-4 w-4 flex-shrink-0" />
              <span>
                Indexing from <strong>local filesystem</strong>. Connect a repository in{" "}
                <a href="/connections" className="underline font-medium">Connections</a> to index remote code.
              </span>
            </>
          )}
        </div>
      )}

      {/* Actions card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5 text-slate-500" />
            {isRemote ? "Index Remote Repository" : "Index Codebase"}
          </CardTitle>
          <CardDescription>
            {isRemote
              ? "Fetches and indexes files from your connected repository."
              : "Indexes new and modified files. Use force re-index to rebuild from scratch."}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <Button
            onClick={() => handleIndex(false)}
            disabled={loading}
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Indexing…
              </>
            ) : (
              <>
                <Database className="h-4 w-4" />
                {isRemote ? "Index Repository" : "Index Codebase"}
              </>
            )}
          </Button>

          <Button
            variant="outline"
            onClick={() => handleIndex(true)}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Re-indexing…
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4" />
                Force Re-index
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Indexing Results
              {result.source === "remote" && result.repo_full_name && (
                <span className="text-xs font-normal bg-indigo-100 text-indigo-700 rounded-full px-2 py-0.5 ml-1">
                  {result.repo_full_name}
                </span>
              )}
            </CardTitle>
            <CardDescription>
              Completed in {result.duration_seconds.toFixed(2)}s
              {result.source && (
                <> · source: <strong>{result.source}</strong></>
              )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="rounded-lg bg-slate-50 p-4 text-center border border-slate-200">
                <dt className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Scanned</dt>
                <dd className="text-3xl font-bold text-slate-900">{result.files_scanned}</dd>
              </div>
              <div className="rounded-lg bg-green-50 p-4 text-center border border-green-200">
                <dt className="text-xs font-medium text-green-600 uppercase tracking-wide mb-1">Indexed</dt>
                <dd className="text-3xl font-bold text-green-700">{result.files_indexed}</dd>
              </div>
              <div className="rounded-lg bg-indigo-50 p-4 text-center border border-indigo-200">
                <dt className="text-xs font-medium text-indigo-600 uppercase tracking-wide mb-1">Updated</dt>
                <dd className="text-3xl font-bold text-indigo-700">{result.files_updated}</dd>
              </div>
              <div className="rounded-lg bg-slate-50 p-4 text-center border border-slate-200">
                <dt className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">Skipped</dt>
                <dd className="text-3xl font-bold text-slate-600">{result.files_skipped}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
