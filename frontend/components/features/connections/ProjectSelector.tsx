"use client"

import { useState, useEffect } from "react"
import { listAzureProjects, activateAzureProject, type AzureProjectResponse } from "@/lib/api-client"
import { Loader2, FolderKanban, X } from "lucide-react"

interface ProjectSelectorProps {
  connectionId: string
  onActivated: () => void
  onClose: () => void
}

export function ProjectSelector({ connectionId, onActivated, onClose }: ProjectSelectorProps) {
  const [projects, setProjects] = useState<AzureProjectResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activating, setActivating] = useState<string | null>(null)

  useEffect(() => {
    listAzureProjects(connectionId)
      .then(setProjects)
      .catch((err) => setError(err instanceof Error ? err.message : "Error al cargar proyectos"))
      .finally(() => setLoading(false))
  }, [connectionId])

  async function handleSelect(project: AzureProjectResponse) {
    setActivating(project.full_name)
    try {
      await activateAzureProject(connectionId, project.full_name)
      onActivated()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al seleccionar el proyecto")
      setActivating(null)
    }
  }

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
        maxWidth: "440px",
        margin: "0 16px",
        display: "flex",
        flexDirection: "column",
        maxHeight: "60vh",
      }}>
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "14px 18px", borderBottom: "1px solid var(--border)",
        }}>
          <h2 style={{ fontSize: "14px", fontWeight: 600, color: "var(--fg)", margin: 0, fontFamily: "var(--font-display)" }}>
            Seleccionar proyecto de Azure DevOps
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

        {/* List */}
        <div style={{ flex: 1, overflowY: "auto", padding: "6px" }}>
          {loading && (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", padding: "32px 0", color: "var(--muted)", fontSize: "13px" }}>
              <Loader2 size={15} className="animate-spin" />
              Cargando proyectos...
            </div>
          )}
          {error && (
            <p style={{ fontSize: "12.5px", color: "var(--err-fg)", padding: "16px 10px", margin: 0 }}>{error}</p>
          )}
          {!loading && !error && projects.length === 0 && (
            <p style={{ fontSize: "12.5px", color: "var(--muted)", padding: "24px 10px", margin: 0, textAlign: "center" }}>
              No se encontraron proyectos accesibles.
            </p>
          )}
          {projects.map((project) => (
            <button
              key={project.full_name}
              type="button"
              onClick={() => handleSelect(project)}
              disabled={activating !== null}
              style={{
                width: "100%", display: "flex", alignItems: "center",
                justifyContent: "space-between", gap: "10px",
                padding: "10px 12px", borderRadius: "var(--radius)",
                border: "none", background: "transparent",
                cursor: activating !== null ? "not-allowed" : "pointer",
                textAlign: "left",
              }}
              onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "var(--surface-2)" }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "transparent" }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0 }}>
                <FolderKanban size={15} style={{ flexShrink: 0, color: "var(--muted)" }} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: "13px", fontWeight: 500, color: "var(--fg)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {project.name}
                  </div>
                  <div style={{ fontSize: "11.5px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
                    {project.org}
                  </div>
                </div>
              </div>
              {activating === project.full_name && (
                <Loader2 size={13} className="animate-spin" style={{ color: "var(--accent)", flexShrink: 0 }} />
              )}
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
