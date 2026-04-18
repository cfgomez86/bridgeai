"use client"

import { useState } from "react"
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
      setError(err instanceof Error ? err.message : "Error al desconectar")
      setDeleting(false)
    }
  }

  return (
    <>
      <div style={{
        background: "var(--surface)",
        border: `1px solid ${connection.is_active ? "color-mix(in oklch, var(--accent) 40%, var(--border))" : "var(--border)"}`,
        borderRadius: "var(--radius-lg)",
        padding: "14px 16px",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        boxShadow: connection.is_active ? "0 0 0 1px color-mix(in oklch, var(--accent) 15%, transparent)" : "var(--shadow-sm)",
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px" }}>
          {/* Platform + user */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0 }}>
            <div style={{
              width: "34px", height: "34px", borderRadius: "7px",
              background: "var(--surface-3)", border: "1px solid var(--border)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "10px", fontWeight: 700, color: "var(--fg-2)",
              fontFamily: "var(--font-mono)", flexShrink: 0,
            }}>
              {PLATFORM_ICONS[connection.platform] ?? "?"}
            </div>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: "13.5px", fontWeight: 600, color: "var(--fg)", fontFamily: "var(--font-display)", display: "flex", alignItems: "center", gap: "6px" }}>
                {connection.display_name}
                {connection.is_active && (
                  <span style={{
                    fontSize: "10px", fontWeight: 500, padding: "1px 6px", borderRadius: "3px",
                    background: "var(--accent-soft)", color: "var(--accent-strong)", fontFamily: "var(--font-mono)",
                  }}>activo</span>
                )}
              </div>
              <div style={{ fontSize: "11.5px", color: "var(--muted)" }}>
                {PLATFORM_LABELS[connection.platform] ?? connection.platform}
              </div>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", flexShrink: 0 }}>
            <button
              onClick={() => setShowRepos(true)}
              style={{
                display: "flex", alignItems: "center", gap: "5px",
                padding: "5px 10px", borderRadius: "var(--radius)",
                border: "1px solid var(--border)", background: "var(--surface-2)",
                color: "var(--fg-2)", fontSize: "12px", fontWeight: 500, cursor: "pointer",
              }}
            >
              <FolderGit2 size={13} />
              Seleccionar repo
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              title="Desconectar"
              style={{
                display: "flex", alignItems: "center", justifyContent: "center",
                width: "30px", height: "30px", borderRadius: "var(--radius)",
                border: "1px solid var(--border)", background: "var(--surface-2)",
                color: deleting ? "var(--muted)" : "var(--err-fg)", cursor: deleting ? "not-allowed" : "pointer",
              }}
            >
              {deleting ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
            </button>
          </div>
        </div>

        {/* Active repo */}
        {connection.repo_full_name && (
          <div style={{
            display: "flex", alignItems: "center", gap: "6px",
            padding: "6px 10px", borderRadius: "var(--radius)",
            background: "var(--surface-2)", border: "1px solid var(--border)",
          }}>
            <GitBranch size={12} style={{ color: "var(--muted)", flexShrink: 0 }} />
            <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--fg-2)", flex: 1 }}>
              {connection.repo_full_name}
            </span>
            <span style={{ fontSize: "11px", color: "var(--muted)" }}>{connection.default_branch}</span>
          </div>
        )}

        {error && (
          <p style={{ fontSize: "12px", color: "var(--err-fg)", margin: 0 }}>{error}</p>
        )}
      </div>

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
