"use client"

import { useState } from "react"
import { understandRequirement } from "@/lib/api-client"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { Loader2, Globe } from "lucide-react"

const LANGUAGES = [
  { code: "es", label: "Español" },
  { code: "en", label: "English" },
  { code: "fr", label: "Français" },
  { code: "de", label: "Deutsch" },
  { code: "pt", label: "Português" },
]

interface Step1Props {
  state: WorkflowState
  setProjectId: (id: string) => void
  setRequirementText: (text: string) => void
  setLanguage: (lang: string) => void
  completeStep1: (data: {
    requirementId: string
    intent: string
    featureType: string
    complexity: string
    keywords: string[]
  }) => void
}

const card: React.CSSProperties = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius-lg)",
  boxShadow: "var(--shadow-sm)",
  padding: "20px 22px",
  display: "flex",
  flexDirection: "column",
  gap: "18px",
}

const label: React.CSSProperties = {
  fontSize: "12.5px",
  fontWeight: 500,
  color: "var(--fg-2)",
  display: "block",
  marginBottom: "6px",
}

const inputStyle: React.CSSProperties = {
  width: "100%",
  background: "var(--surface-2)",
  border: "1px solid var(--border)",
  borderRadius: "var(--radius)",
  padding: "7px 10px",
  fontSize: "13px",
  color: "var(--fg)",
  fontFamily: "var(--font-sans)",
  outline: "none",
}

export function Step1Understand({
  state,
  setProjectId,
  setRequirementText,
  setLanguage,
  completeStep1,
}: Step1Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isValid = state.requirementText.trim().length >= 10

  async function handleSubmit() {
    if (!isValid) return
    setLoading(true)
    setError(null)
    try {
      const result = await understandRequirement(state.requirementText, state.projectId)
      completeStep1({
        requirementId: result.requirement_id,
        intent: result.intent,
        featureType: result.feature_type,
        complexity: result.estimated_complexity,
        keywords: result.keywords ?? [],
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to analyze requirement")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={card}>
      <div>
        <h2 style={{ fontSize: "15px", fontWeight: 600, fontFamily: "var(--font-display)", margin: "0 0 4px", color: "var(--fg)" }}>
          Requerimiento
        </h2>
        <p style={{ fontSize: "12.5px", color: "var(--muted)", margin: 0 }}>
          Describí el requerimiento. La IA extraerá intención, complejidad y keywords de dominio.
        </p>
      </div>

      {/* Project ID */}
      <div>
        <label style={label} htmlFor="project-id">Project ID</label>
        <input
          id="project-id"
          style={inputStyle}
          value={state.projectId}
          onChange={(e) => setProjectId(e.target.value)}
          placeholder="mi-proyecto"
        />
      </div>

      {/* Language */}
      <div>
        <label style={{ ...label, display: "flex", alignItems: "center", gap: "6px" }}>
          <Globe size={13} style={{ color: "var(--muted)" }} />
          Idioma de la historia
        </label>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              type="button"
              onClick={() => setLanguage(lang.code)}
              style={{
                padding: "4px 12px",
                borderRadius: "var(--radius)",
                border: "1px solid",
                fontSize: "12.5px",
                fontWeight: 500,
                cursor: "pointer",
                transition: "all .12s",
                background: state.language === lang.code ? "var(--accent)" : "var(--surface)",
                borderColor: state.language === lang.code ? "transparent" : "var(--border)",
                color: state.language === lang.code ? "var(--accent-fg)" : "var(--fg-2)",
              }}
            >
              {lang.label}
            </button>
          ))}
        </div>
      </div>

      {/* Requirement text */}
      <div>
        <label style={label} htmlFor="requirement-text">Requerimiento</label>
        <textarea
          id="requirement-text"
          value={state.requirementText}
          onChange={(e) => setRequirementText(e.target.value)}
          rows={6}
          placeholder="Como usuario registrado, quiero poder restablecer mi contraseña por correo electrónico para recuperar el acceso a mi cuenta si la olvido."
          style={{ ...inputStyle, resize: "none", lineHeight: 1.6 }}
        />
        {state.requirementText.length > 0 && !isValid && (
          <p style={{ fontSize: "11.5px", color: "var(--err-fg)", marginTop: "4px" }}>
            Mínimo 10 caracteres.
          </p>
        )}
      </div>

      {error && (
        <div style={{ padding: "10px 14px", borderRadius: "var(--radius)", background: "var(--err-bg)", color: "var(--err-fg)", fontSize: "12.5px" }}>
          {error}
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={loading || !isValid}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
          padding: "9px 18px",
          borderRadius: "var(--radius)",
          border: "none",
          background: loading || !isValid ? "var(--surface-3)" : "var(--accent)",
          color: loading || !isValid ? "var(--muted)" : "var(--accent-fg)",
          fontSize: "13px",
          fontWeight: 600,
          cursor: loading || !isValid ? "not-allowed" : "pointer",
          fontFamily: "var(--font-display)",
        }}
      >
        {loading ? (
          <><Loader2 size={14} className="animate-spin" /> Analizando…</>
        ) : (
          "Analizar requerimiento →"
        )}
      </button>
    </div>
  )
}
