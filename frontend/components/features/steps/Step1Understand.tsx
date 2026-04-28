"use client"

import { useState, useEffect } from "react"
import {
  understandRequirement,
  listConnections,
  getIndexStatus,
  type ConnectionResponse,
  type IndexStatusResponse,
} from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { Loader2, Globe, CheckCircle, AlertTriangle } from "lucide-react"

const TICKET_PLATFORM_LABELS: Record<string, string> = {
  jira: "Jira Cloud",
  azure_devops: "Azure DevOps",
}

const SCM_PLATFORMS = new Set(["github", "gitlab", "azure_devops", "bitbucket"])

const LANGUAGES = [
  { code: "es", label: "Español" },
  { code: "en", label: "English" },
  { code: "ca", label: "Català" },
  { code: "fr", label: "Français" },
  { code: "de", label: "Deutsch" },
  { code: "pt", label: "Português" },
]

function timeAgo(dateStr: string, lang: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const min = Math.floor(diff / 60_000)
  const hr = Math.floor(min / 60)
  const day = Math.floor(hr / 24)
  const es = lang !== "en"
  if (min < 1) return es ? "ahora mismo" : "just now"
  if (min < 60) return es ? `hace ${min}m` : `${min}m ago`
  if (hr < 24) return es ? `hace ${hr}h` : `${hr}h ago`
  return es ? `hace ${day}d` : `${day}d ago`
}

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

const labelStyle: React.CSSProperties = {
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

const divider: React.CSSProperties = { height: "1px", background: "var(--border)" }

function StatusRow({
  label, ok, detail, loading,
}: {
  label: string
  ok: boolean
  detail?: string
  loading?: boolean
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "10px", minHeight: "22px" }}>
      {loading ? (
        <Loader2 size={13} style={{ color: "var(--muted)", flexShrink: 0 }} className="animate-spin" />
      ) : ok ? (
        <CheckCircle size={13} style={{ color: "var(--ok-fg, #22c55e)", flexShrink: 0 }} />
      ) : (
        <AlertTriangle size={13} style={{ color: "var(--warn-fg, #f59e0b)", flexShrink: 0 }} />
      )}
      <span style={{ fontSize: "12px", fontWeight: 500, color: "var(--fg-2)", flex: 1 }}>
        {label}
      </span>
      {!loading && detail && (
        <span style={{ fontSize: "11.5px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
          {detail}
        </span>
      )}
    </div>
  )
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
  const [ticketConn, setTicketConn] = useState<ConnectionResponse | null>(null)
  const [scmConn, setScmConn] = useState<ConnectionResponse | null>(null)
  const [indexStatus, setIndexStatus] = useState<IndexStatusResponse | null>(null)
  const [configLoading, setConfigLoading] = useState(true)
  const { t } = useLanguage()
  const s = t.workflow.step1

  useEffect(() => {
    function loadConfig() {
      setConfigLoading(true)
      Promise.all([listConnections(), getIndexStatus()])
        .then(([conns, idx]) => {
          const ticket =
            conns.find((c) => c.platform === "jira") ??
            conns.find((c) => c.platform === "azure_devops" && Boolean(c.boards_project))
          const scm = state.sourceConnectionId
            ? conns.find((c) => c.id === state.sourceConnectionId)
            : conns.find((c) => c.is_active && SCM_PLATFORMS.has(c.platform))
          setTicketConn(ticket ?? null)
          setScmConn(scm ?? null)
          setIndexStatus(idx)
          // Auto-derive project ID from the connected repo so the user doesn't need to type it
          if (scm?.repo_full_name) setProjectId(scm.repo_full_name)
          else if (scm?.display_name) setProjectId(scm.display_name)
        })
        .catch(() => {})
        .finally(() => setConfigLoading(false))
    }

    loadConfig()
    window.addEventListener("focus", loadConfig)
    return () => window.removeEventListener("focus", loadConfig)
  }, [state.sourceConnectionId, state.repoFullName])

  const hasRepo = Boolean(scmConn ?? state.sourceConnectionId)
  const isIndexed = (indexStatus?.total_files ?? 0) > 0
  const hasSite = ticketConn?.platform === "azure_devops"
    ? Boolean(ticketConn.boards_project)
    : Boolean(ticketConn?.repo_full_name)
  const isReady = Boolean(ticketConn) && hasSite && hasRepo && isIndexed
  const isValid = state.requirementText.trim().length >= 10 && isReady

  async function handleSubmit() {
    if (!isValid || !state.sourceConnectionId) return
    setLoading(true)
    setError(null)
    try {
      const result = await understandRequirement(
        state.requirementText,
        state.projectId,
        state.sourceConnectionId,
        state.language,
      )
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

  // Build detail strings — same muted color regardless of ok/not-ok state
  const ticketDetail = !ticketConn
    ? s.ticket_provider_not_configured
    : !hasSite
      ? s.ticket_site_not_selected
      : ticketConn.platform === "azure_devops"
        ? [ticketConn.display_name, ticketConn.boards_project, "Azure DevOps"].filter(Boolean).join(" · ")
        : [ticketConn.display_name, TICKET_PLATFORM_LABELS[ticketConn.platform] ?? ticketConn.platform].filter(Boolean).join(" · ")

  const repoDetail = scmConn?.repo_full_name
    ? `${scmConn.repo_full_name}${scmConn.default_branch ? ` · ${scmConn.default_branch}` : ""}`
    : scmConn?.display_name ?? s.not_configured

  const indexDetail = isIndexed && indexStatus
    ? `${indexStatus.total_files} ${s.files_indexed}${indexStatus.last_indexed_at ? ` · ${timeAgo(indexStatus.last_indexed_at, state.language)}` : ""}`
    : s.not_indexed

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>

      {/* Setup status card */}
      <div style={{
        background: "var(--surface)",
        border: `1px solid ${isReady ? "var(--border)" : "color-mix(in oklch, var(--warn-fg, #f59e0b) 30%, var(--border))"}`,
        borderRadius: "var(--radius-lg)", padding: "14px 16px",
        display: "flex", flexDirection: "column", gap: "10px",
      }}>
        <p style={{
          fontSize: "10.5px", fontWeight: 600, textTransform: "uppercase",
          letterSpacing: "0.07em", color: "var(--muted)", margin: 0,
        }}>
          {s.config_title}
        </p>

        <StatusRow
          label={s.ticket_provider_label}
          ok={Boolean(ticketConn) && hasSite}
          detail={ticketDetail}
          loading={configLoading}
        />

        <div style={divider} />

        <StatusRow
          label={s.repo_label}
          ok={hasRepo}
          detail={repoDetail}
          loading={configLoading}
        />

        <div style={divider} />

        <StatusRow
          label={s.index_label}
          ok={isIndexed}
          detail={indexDetail}
          loading={configLoading}
        />

        {!configLoading && !isReady && (
          <p style={{
            fontSize: "11.5px", color: "var(--muted)",
            margin: "2px 0 0", borderTop: "1px solid var(--border)", paddingTop: "8px",
          }}>
            {s.blocked_hint}
          </p>
        )}
      </div>

      {/* Main form */}
      <div style={card}>
        <div>
          <h2 style={{ fontSize: "15px", fontWeight: 600, fontFamily: "var(--font-display)", margin: "0 0 4px", color: "var(--fg)" }}>
            {s.title}
          </h2>
          <p style={{ fontSize: "12.5px", color: "var(--muted)", margin: 0 }}>
            {s.description}
          </p>
        </div>

        {/* Story language */}
        <div>
          <label htmlFor="story-language" style={{ ...labelStyle, display: "flex", alignItems: "center", gap: "6px" }}>
            <Globe size={13} style={{ color: "var(--muted)" }} />
            {s.story_language}
          </label>
          <select
            id="story-language"
            value={state.language}
            onChange={(e) => setLanguage(e.target.value)}
            style={{
              ...inputStyle,
              cursor: "pointer",
              appearance: "auto",
            }}
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.code} value={lang.code}>
                {lang.label}
              </option>
            ))}
          </select>
        </div>

        {/* Requirement text */}
        <div>
          <label style={labelStyle} htmlFor="requirement-text">{s.requirement_label}</label>
          <textarea
            id="requirement-text"
            value={state.requirementText}
            onChange={(e) => setRequirementText(e.target.value)}
            rows={6}
            placeholder={s.placeholder}
            style={{ ...inputStyle, resize: "none", lineHeight: 1.6 }}
          />
          {state.requirementText.length > 0 && state.requirementText.trim().length < 10 && (
            <p style={{ fontSize: "11.5px", color: "var(--err-fg)", marginTop: "4px" }}>
              {s.min_chars}
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
            <><Loader2 size={14} className="animate-spin" /> {s.analyzing}</>
          ) : (
            s.analyze_btn
          )}
        </button>
      </div>
    </div>
  )
}
