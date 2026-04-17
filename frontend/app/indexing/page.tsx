"use client"

import { useState } from "react"
import { indexCode, type IndexResponse } from "@/lib/api-client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Database, RefreshCw, Loader2 } from "lucide-react"

export default function IndexingPage() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<IndexResponse | null>(null)

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
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Code Index</h1>
        <p className="mt-1 text-slate-500">
          Scan and index your codebase to enable accurate impact analysis
        </p>
      </div>

      {/* Actions card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5 text-slate-500" />
            Index Codebase
          </CardTitle>
          <CardDescription>
            Indexes new and modified files. Use force re-index to rebuild from scratch.
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
                Index Codebase
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

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Indexing Results</CardTitle>
            <CardDescription>
              Completed in {result.duration_seconds.toFixed(2)}s
            </CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="rounded-lg bg-slate-50 p-4 text-center border border-slate-200">
                <dt className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">
                  Scanned
                </dt>
                <dd className="text-3xl font-bold text-slate-900">{result.files_scanned}</dd>
              </div>
              <div className="rounded-lg bg-green-50 p-4 text-center border border-green-200">
                <dt className="text-xs font-medium text-green-600 uppercase tracking-wide mb-1">
                  Indexed
                </dt>
                <dd className="text-3xl font-bold text-green-700">{result.files_indexed}</dd>
              </div>
              <div className="rounded-lg bg-indigo-50 p-4 text-center border border-indigo-200">
                <dt className="text-xs font-medium text-indigo-600 uppercase tracking-wide mb-1">
                  Updated
                </dt>
                <dd className="text-3xl font-bold text-indigo-700">{result.files_updated}</dd>
              </div>
              <div className="rounded-lg bg-slate-50 p-4 text-center border border-slate-200">
                <dt className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-1">
                  Skipped
                </dt>
                <dd className="text-3xl font-bold text-slate-600">{result.files_skipped}</dd>
              </div>
            </dl>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
