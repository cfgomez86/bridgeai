"use client"

import { useState, useEffect } from "react"
import { listRepos, activateRepo, type RepoResponse } from "@/lib/api-client"
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
      .catch((err) => setError(err instanceof Error ? err.message : "Error al cargar repositorios"))
      .finally(() => setLoading(false))
  }, [connectionId])

  async function handleSelect(repo: RepoResponse) {
    setActivating(repo.full_name)
    try {
      await activateRepo(connectionId, repo.full_name, repo.default_branch)
      onActivated()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al activar repositorio")
      setActivating(null)
    }
  }

  const filtered = repos.filter(
    (r) => r.full_name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 50,
      display: "flex", alignItems: "center", justifyContent: "center",
      background: "rgba(0,0,0,0.45)",
    }}>
      <div style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
        width: "100%",
        maxWidth: "480px",
        margin: "0 16px",
        display: "flex",
        flexDirection: "column",
        maxHeight: "75vh",
      }}>
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "14px 18px", borderBottom: "1px solid var(--border)",
        }}>
          <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--fg)", margin: 0, fontFamily: "var(--font-display)" }}>
            Seleccionar repositorio
          </h2>
          <button
            type="button"
            onClick={onClose}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              width: "28px", height: "28px", borderRadius: "var(--radius)",
              border: "none", background: "transparent", color: "var(--muted)", cursor: "pointer",
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Search */}
        <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--border)", position: "relative" }}>
          <Search size={13} style={{
            position: "absolute", left: "26px", top: "50%", transform: "translateY(-50%)",
            color: "var(--muted)", pointerEvents: "none",
          }} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filtrar repositorios…"
            autoFocus
            style={{
              width: "100%", boxSizing: "border-box",
              padding: "6px 10px 6px 32px",
              borderRadius: "var(--radius)", border: "1px solid var(--border)",
              background: "var(--surface-2)", color: "var(--fg)",
              fontSize: "13px", outline: "none",
            }}
          />
        </div>

        {/* List */}
        <div style={{ flex: 1, overflowY: "auto", padding: "6px" }}>
          {loading && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", padding: "32px 0", color: "var(--muted)", fontSize: "13px" }}>
              <Loader2 size={15} className="animate-spin" />
              Cargando repositorios…
            </div>
          )}
          {error && (
            <p style={{ fontSize: "12.5px", color: "var(--err-fg)", padding: "16px 10px", margin: 0 }}>{error}</p>
          )}
          {!loading && !error && filtered.length === 0 && (
            <p style={{ fontSize: "12.5px", color: "var(--muted)", padding: "24px 10px", margin: 0, textAlign: "center" }}>
              No se encontraron repositorios.
            </p>
          )}
          {filtered.map((repo) => (
            <button
              key={repo.full_name}
              type="button"
              onClick={() => handleSelect(repo)}
              disabled={activating !== null}
              style={{
                width: "100%", display: "flex", alignItems: "center",
                justifyContent: "space-between", gap: "10px",
                padding: "8px 10px", borderRadius: "var(--radius)",
                border: "none", background: "transparent",
                cursor: activating !== null ? "not-allowed" : "pointer",
                textAlign: "left", transition: "background 0.1s",
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "var(--surface-2)" }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "transparent" }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "7px", minWidth: 0 }}>
                {repo.private && <Lock size={12} style={{ flexShrink: 0, color: "var(--muted)" }} />}
                <span style={{ fontFamily: "var(--font-mono)", fontSize: "13px", color: "var(--fg)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {repo.full_name}
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "5px", flexShrink: 0 }}>
                <GitBranch size={12} style={{ color: "var(--muted)" }} />
                <span style={{ fontSize: "11.5px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>{repo.default_branch}</span>
                {activating === repo.full_name && <Loader2 size={12} className="animate-spin" style={{ color: "var(--accent)" }} />}
              </div>
            </button>
          ))}
        </div>

        {/* Footer */}
        <div style={{ padding: "10px 14px", borderTop: "1px solid var(--border)", display: "flex", justifyContent: "flex-end" }}>
          <button
            onClick={onClose}
            style={{
              padding: "5px 14px", borderRadius: "var(--radius)",
              border: "1px solid var(--border)", background: "var(--surface-2)",
              color: "var(--fg-2)", fontSize: "12.5px", cursor: "pointer",
            }}
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>
  )
}
