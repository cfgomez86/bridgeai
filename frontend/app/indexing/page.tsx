"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { indexCode, getActiveConnection, type IndexResponse, type ConnectionResponse } from "@/lib/api-client"
import { Loader2, Database, Zap, RefreshCw, GitBranch } from "lucide-react"

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

  useEffect(() => {
    getActiveConnection().then(setActiveConn).catch(() => setActiveConn(null))
  }, [])

  async function handleIndex(force: boolean) {
    setLoading(true)
    setError(null)
    try {
      const data = await indexCode(force)
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error inesperado al indexar")
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
            Indexado de código
          </h1>
        </div>
        <p style={{ fontSize: "13px", color: "var(--muted)", margin: 0 }}>
          Escanea el codebase y construye el índice de archivos para el análisis de impacto
        </p>
      </div>

      {/* Active repo info */}
      <div style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        padding: "14px 18px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "16px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <GitBranch size={14} style={{ color: "var(--muted)", flexShrink: 0 }} />
          <div>
            <div style={{ fontSize: "12px", color: "var(--muted)", marginBottom: "2px" }}>Repositorio activo</div>
            {activeConn === undefined ? (
              <div style={{ fontSize: "13px", color: "var(--muted)" }}>Cargando…</div>
            ) : hasActiveRepo ? (
              <div style={{ fontFamily: "var(--font-mono)", fontSize: "13px", fontWeight: 500, color: "var(--fg)" }}>
                {activeConn.repo_full_name}
                {activeConn.default_branch && (
                  <span style={{ color: "var(--muted)", fontWeight: 400 }}> · {activeConn.default_branch}</span>
                )}
              </div>
            ) : (
              <div style={{ fontSize: "13px", color: "var(--warn-fg)", fontStyle: "italic" }}>
                Sin repo activo
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
          Cambiar repo
        </Link>
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
            <><Loader2 size={14} className="animate-spin" /> Indexando…</>
          ) : (
            <><Database size={14} /> Index Codebase</>
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
          <RefreshCw size={14} /> Force Re-index
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
          {/* Meta info */}
          <div style={{
            display: "flex", alignItems: "center", gap: "12px",
            padding: "10px 16px", borderRadius: "var(--radius)",
            background: "var(--ok-bg)", color: "var(--ok-fg)", fontSize: "12.5px", fontWeight: 500,
            border: "1px solid color-mix(in oklch, var(--ok-fg) 20%, transparent)",
          }}>
            <Zap size={13} />
            <span>
              Completado en <strong>{result.duration_seconds.toFixed(2)}s</strong>
              {result.source && (
                <> · fuente: <span style={{ fontFamily: "var(--font-mono)" }}>{result.source}</span></>
              )}
              {result.repo_full_name && (
                <> · <span style={{ fontFamily: "var(--font-mono)" }}>{result.repo_full_name}</span></>
              )}
            </span>
          </div>

          {/* 4 stat blocks */}
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
                No hay repositorio activo
              </p>
              <p style={{ fontSize: "12.5px", color: "var(--muted)", margin: 0 }}>
                Conecta una cuenta y seleccioná un repositorio en{" "}
                <a href="/connections" style={{ color: "var(--accent)", textDecoration: "underline", textUnderlineOffset: "2px" }}>
                  Conexiones
                </a>{" "}
                para poder indexar
              </p>
            </>
          ) : (
            <>
              <p style={{ fontSize: "13.5px", fontWeight: 500, color: "var(--fg-2)", margin: 0 }}>
                Sin datos de indexado todavía
              </p>
              <p style={{ fontSize: "12.5px", color: "var(--muted)", margin: 0 }}>
                Presioná <strong>Index Codebase</strong> para escanear el repositorio activo
              </p>
            </>
          )}
        </div>
      )}
    </div>
  )
}
