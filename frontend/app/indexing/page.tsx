"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { indexCode, getActiveConnection, getIndexStatus, type IndexResponse, type ConnectionResponse, type IndexStatusResponse } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"
import { Loader2, Database, Zap, RefreshCw, GitBranch } from "lucide-react"

function timeAgo(isoDate: string): string {
  const utc = isoDate.endsWith("Z") || isoDate.includes("+") ? isoDate : isoDate + "Z"
  const diff = Math.floor((Date.now() - new Date(utc).getTime()) / 1000)
  if (diff < 60) return `${diff}s`
  if (diff < 3600) return `${Math.floor(diff / 60)}min`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`
  return `${Math.floor(diff / 86400)}d`
}

interface StatItem {
  label: string
  value: number
  accent?: boolean
}

function StatBlock({ label, value, accent }: StatItem) {
  return (
    <div style={{
      background: "var(--surface)",
      border: `1px solid ${accent ? "color-mix(in oklch, var(--accent) 30%, var(--border))" : "var(--border)"}`,
      borderRadius: "var(--radius-lg)",
      padding: "16px 20px",
      display: "flex",
      flexDirection: "column",
      gap: "4px",
    }}>
      <div style={{ fontSize: "11px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--muted)" }}>
        {label}
      </div>
      <div style={{ fontSize: "28px", fontWeight: 700, fontFamily: "var(--font-display)", color: accent ? "var(--accent)" : "var(--fg)", lineHeight: 1 }}>
        {value.toLocaleString()}
      </div>
    </div>
  )
}

export default function IndexingPage() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<IndexResponse | null>(null)
  const [activeConn, setActiveConn] = useState<ConnectionResponse | null | undefined>(undefined)
  const [indexStatus, setIndexStatus] = useState<IndexStatusResponse | null | undefined>(undefined)
  const { t } = useLanguage()
  const s = t.indexing

  useEffect(() => {
    getActiveConnection().then(setActiveConn).catch(() => setActiveConn(null))
    getIndexStatus().then(setIndexStatus).catch(() => setIndexStatus(null))
  }, [])

  async function handleIndex(force: boolean) {
    setLoading(true)
    setError(null)
    try {
      const data = await indexCode(force)
      setResult(data)
      // refresh status after indexing
      getIndexStatus().then(setIndexStatus).catch(() => {})
    } catch (err) {
      setError(err instanceof Error ? err.message : s.error_unexpected)
    } finally {
      setLoading(false)
    }
  }

  const hasActiveRepo = activeConn?.repo_full_name

  return (
    <div style={{ padding: "28px 32px", maxWidth: "900px", display: "flex", flexDirection: "column", gap: "24px" }}>

      {/* Header */}
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
          <Database size={16} style={{ color: "var(--accent)" }} />
          <h1 style={{
            fontSize: "20px", fontWeight: 700, fontFamily: "var(--font-display)",
            color: "var(--fg)", margin: 0, letterSpacing: "-0.01em",
          }}>
            {s.title}
          </h1>
        </div>
        <p style={{ fontSize: "13px", color: "var(--muted)", margin: 0 }}>
          {s.description}
        </p>
      </div>

      {/* Active repo info + index status */}
      <div style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        padding: "14px 18px",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
      }}>
        {/* Row 1: active connection */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <GitBranch size={14} style={{ color: "var(--muted)", flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: "12px", color: "var(--muted)", marginBottom: "2px" }}>{s.active_repo}</div>
              {activeConn === undefined ? (
                <div style={{ fontSize: "13px", color: "var(--muted)" }}>{s.loading}</div>
              ) : hasActiveRepo ? (
                <div style={{ fontFamily: "var(--font-mono)", fontSize: "13px", fontWeight: 500, color: "var(--fg)" }}>
                  {activeConn.repo_full_name}
                  {activeConn.default_branch && (
                    <span style={{ color: "var(--muted)", fontWeight: 400 }}> · {activeConn.default_branch}</span>
                  )}
                </div>
              ) : (
                <div style={{ fontSize: "13px", color: "var(--warn-fg)", fontStyle: "italic" }}>
                  {s.no_repo}
                </div>
              )}
            </div>
          </div>
          <Link href="/connections" style={{
            padding: "5px 12px",
            borderRadius: "var(--radius)",
            border: "1px solid var(--border)",
            background: "var(--surface-2)",
            color: "var(--fg-2)",
            fontSize: "12.5px",
            fontWeight: 500,
            textDecoration: "none",
            flexShrink: 0,
          }}>
            {s.change_repo}
          </Link>
        </div>

        {/* Divider */}
        <div style={{ borderTop: "1px solid var(--border)" }} />

        {/* Row 2: index status */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Database size={14} style={{ color: "var(--muted)", flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: "12px", color: "var(--muted)", marginBottom: "2px" }}>{s.index_status}</div>
            {indexStatus === undefined ? (
              <div style={{ fontSize: "13px", color: "var(--muted)" }}>{s.loading}</div>
            ) : indexStatus && indexStatus.total_files > 0 ? (
              <div style={{ fontSize: "13px", fontWeight: 500, color: "var(--fg)" }}>
                <span style={{ fontFamily: "var(--font-mono)" }}>{indexStatus.total_files.toLocaleString()}</span>
                {" "}<span style={{ color: "var(--muted)", fontWeight: 400 }}>{s.indexed_files}</span>
                {indexStatus.last_indexed_at && (
                  <span style={{ color: "var(--muted)", fontWeight: 400 }}>
                    {" · "}{s.last_indexed} {timeAgo(indexStatus.last_indexed_at)}
                  </span>
                )}
              </div>
            ) : (
              <div style={{ fontSize: "13px", color: "var(--warn-fg)", fontStyle: "italic" }}>
                {s.not_indexed_yet}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div style={{ display: "flex", gap: "10px" }}>
        <button
          onClick={() => handleIndex(false)}
          disabled={loading || !hasActiveRepo}
          style={{
            display: "flex", alignItems: "center", gap: "8px",
            padding: "9px 20px", borderRadius: "var(--radius)", border: "none",
            background: loading || !hasActiveRepo ? "var(--surface-3)" : "var(--accent)",
            color: loading || !hasActiveRepo ? "var(--muted)" : "var(--accent-fg)",
            fontSize: "13px", fontWeight: 600,
            cursor: loading || !hasActiveRepo ? "not-allowed" : "pointer",
            fontFamily: "var(--font-display)",
            flex: 1,
            justifyContent: "center",
          }}
        >
          {loading ? (
            <><Loader2 size={14} className="animate-spin" /> {s.indexing_progress}</>
          ) : (
            <><Database size={14} /> {s.index_btn}</>
          )}
        </button>
        <button
          onClick={() => handleIndex(true)}
          disabled={loading || !hasActiveRepo}
          style={{
            display: "flex", alignItems: "center", gap: "8px",
            padding: "9px 20px", borderRadius: "var(--radius)",
            border: "1px solid var(--border)",
            background: loading || !hasActiveRepo ? "var(--surface-3)" : "var(--surface)",
            color: loading || !hasActiveRepo ? "var(--muted)" : "var(--fg-2)",
            fontSize: "13px", fontWeight: 500,
            cursor: loading || !hasActiveRepo ? "not-allowed" : "pointer",
            fontFamily: "var(--font-display)",
            flex: 1,
            justifyContent: "center",
          }}
        >
          <RefreshCw size={14} /> {s.force_reindex}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          padding: "12px 16px", borderRadius: "var(--radius)",
          background: "var(--err-bg)", color: "var(--err-fg)", fontSize: "13px",
          border: "1px solid color-mix(in oklch, var(--err-fg) 20%, transparent)",
        }}>
          {error}
        </div>
      )}

      {/* Result stats */}
      {result && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div style={{
            display: "flex", alignItems: "center", gap: "12px",
            padding: "10px 16px", borderRadius: "var(--radius)",
            background: "var(--ok-bg)", color: "var(--ok-fg)", fontSize: "12.5px", fontWeight: 500,
            border: "1px solid color-mix(in oklch, var(--ok-fg) 20%, transparent)",
          }}>
            <Zap size={13} />
            <span>
              {s.completed_in} <strong>{result.duration_seconds.toFixed(2)}s</strong>
              {result.source && (
                <> · {s.source} <span style={{ fontFamily: "var(--font-mono)" }}>{result.source}</span></>
              )}
              {result.repo_full_name && (
                <> · <span style={{ fontFamily: "var(--font-mono)" }}>{result.repo_full_name}</span></>
              )}
            </span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px" }}>
            <StatBlock label="Scanned" value={result.files_scanned} />
            <StatBlock label="Indexed" value={result.files_indexed} accent />
            <StatBlock label="Updated" value={result.files_updated} accent />
            <StatBlock label="Skipped" value={result.files_skipped} />
          </div>
        </div>
      )}

      {/* Empty / no-repo state */}
      {!result && !loading && !error && (
        <div style={{
          background: "var(--surface)",
          border: "1px dashed var(--border)",
          borderRadius: "var(--radius-lg)",
          padding: "48px 24px",
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "8px",
        }}>
          <Database size={28} style={{ color: "var(--border-strong)", marginBottom: "4px" }} />
          {!hasActiveRepo ? (
            <>
              <p style={{ fontSize: "13.5px", fontWeight: 500, color: "var(--fg-2)", margin: 0 }}>
                {s.no_repo_title}
              </p>
              <p style={{ fontSize: "12.5px", color: "var(--muted)", margin: 0 }}>
                {s.no_repo_desc_pre}{" "}
                <a href="/connections" style={{ color: "var(--accent)", textDecoration: "underline", textUnderlineOffset: "2px" }}>
                  {t.nav.connections}
                </a>{" "}
                {s.no_repo_desc_post}
              </p>
            </>
          ) : (
            <>
              <p style={{ fontSize: "13.5px", fontWeight: 500, color: "var(--fg-2)", margin: 0 }}>
                {s.no_data_title}
              </p>
              <p style={{ fontSize: "12.5px", color: "var(--muted)", margin: 0 }}>
                {s.no_data_desc}
              </p>
            </>
          )}
        </div>
      )}
    </div>
  )
}
