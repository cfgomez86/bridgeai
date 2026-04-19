"use client"

import { useState, useEffect } from "react"
import {
  createTicket,
  checkIntegrationHealth,
  getStoryDetail,
  type CreateTicketResponse,
  type IntegrationHealthResponse,
  type StoryDetailResponse,
} from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { HealthStatus } from "@/components/features/HealthStatus"
import { RiskBadge } from "@/components/features/RiskBadge"
import { StepSummaryCard } from "@/components/features/StepSummaryCard"
import {
  Loader2, Ticket, ExternalLink, Plus, Search, Zap, GitPullRequest,
  FileText, CheckCircle, Code, ListChecks, AlertTriangle,
} from "lucide-react"

const truncate = (text: string, max: number) =>
  text.length > max ? text.slice(0, max) + "…" : text

const chip = (): React.CSSProperties => ({
  display: "inline-flex", alignItems: "center",
  padding: "1px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 500,
  fontFamily: "var(--font-mono)",
  background: "var(--surface-3)", color: "var(--fg-2)",
  border: "1px solid transparent",
})

const sectionLabel: React.CSSProperties = {
  fontSize: "10.5px", fontWeight: 600, textTransform: "uppercase",
  letterSpacing: "0.07em", color: "var(--muted)",
}

const divider: React.CSSProperties = {
  height: "1px", background: "var(--border)", margin: "2px 0",
}

const inputStyle: React.CSSProperties = {
  width: "100%", boxSizing: "border-box",
  background: "var(--surface-2)", border: "1px solid var(--border)",
  borderRadius: "var(--radius)", padding: "7px 10px",
  fontSize: "13px", color: "var(--fg)", fontFamily: "var(--font-sans)", outline: "none",
}

const labelStyle: React.CSSProperties = {
  fontSize: "12px", fontWeight: 500, color: "var(--fg-2)",
  display: "block", marginBottom: "5px",
}

const PROVIDERS: Record<string, string> = {
  jira: "Jira",
  azure_devops: "Azure DevOps",
}

interface Step4Props {
  state: WorkflowState
  completeStep4: () => void
  reset: () => void
}

export function Step4Ticket({ state, completeStep4, reset }: Step4Props) {
  const [provider, setProvider] = useState<string>("jira")
  const [projectKey, setProjectKey] = useState("SCRUM")
  const [issueType, setIssueType] = useState("Story")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ticket, setTicket] = useState<CreateTicketResponse | null>(null)
  const [health, setHealth] = useState<IntegrationHealthResponse | null>(null)
  const [story, setStory] = useState<StoryDetailResponse | null>(null)
  const { t } = useLanguage()
  const s = t.workflow.step4

  useEffect(() => {
    checkIntegrationHealth().then(setHealth).catch(() => {})
  }, [])

  useEffect(() => {
    if (state.storyId) {
      getStoryDetail(state.storyId).then(setStory).catch(() => {})
    }
  }, [state.storyId])

  async function handleCreate() {
    if (!state.storyId) return
    setLoading(true)
    setError(null)
    try {
      const result = await createTicket(state.storyId, provider, projectKey, issueType)
      setTicket(result)
      completeStep4()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create ticket")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <StepSummaryCard title={s.step1_summary} icon={<Search size={13} />}>
        <p style={{ fontSize: "12.5px", color: "var(--fg-2)", fontStyle: "italic", margin: 0 }}>
          &ldquo;{truncate(state.requirementText, 120)}&rdquo;
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
          {state.featureType && <span style={chip()}>{state.featureType}</span>}
          {state.complexity && <span style={chip()}>{s.complexity} {state.complexity}</span>}
          {state.language && <span style={chip()}>Lang: {state.language}</span>}
        </div>
        {state.intent && (
          <p style={{ fontSize: "11.5px", color: "var(--muted)", margin: 0 }}>
            Intent: <span style={{ color: "var(--fg-2)", fontWeight: 500 }}>{state.intent}</span>
          </p>
        )}
      </StepSummaryCard>

      <StepSummaryCard title={s.step2_summary} icon={<Zap size={13} />}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "16px", alignItems: "center" }}>
          {state.filesImpacted !== null && (
            <span style={{ fontSize: "12.5px", color: "var(--muted)" }}>
              {s.files} <span style={{ color: "var(--fg)", fontWeight: 600 }}>{state.filesImpacted}</span>
            </span>
          )}
          {state.riskLevel && <RiskBadge risk={state.riskLevel} />}
        </div>
        {state.modulesImpacted.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
            {state.modulesImpacted.map((m) => <span key={m} style={chip()}>{m}</span>)}
          </div>
        )}
      </StepSummaryCard>

      <StepSummaryCard title={s.step3_summary} icon={<GitPullRequest size={13} />} defaultOpen={true}>
        {!story ? (
          <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12.5px", color: "var(--muted)", padding: "8px 0" }}>
            <Loader2 size={14} className="animate-spin" />
            {s.loading_story}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div>
              <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--fg)", margin: "0 0 6px", fontFamily: "var(--font-display)" }}>
                {story.title}
              </p>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ ...chip(), background: "var(--accent-soft)", color: "var(--accent-strong)" }}>
                  {story.story_points} {story.story_points === 1 ? s.point : s.points}
                </span>
                <RiskBadge risk={story.risk_level} />
              </div>
            </div>

            <div style={divider} />

            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "5px" }}>
                <FileText size={11} style={{ color: "var(--muted)" }} />
                <span style={sectionLabel}>{s.description_label}</span>
              </div>
              <p style={{ fontSize: "12px", lineHeight: 1.6, color: "var(--fg-2)", margin: 0 }}>
                {story.story_description}
              </p>
            </div>

            <div style={divider} />

            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                <CheckCircle size={11} style={{ color: "var(--muted)" }} />
                <span style={sectionLabel}>{s.acceptance_criteria}</span>
              </div>
              <ol style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "5px" }}>
                {story.acceptance_criteria.map((item, i) => (
                  <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: "7px", fontSize: "12px" }}>
                    <span style={{
                      flexShrink: 0, display: "inline-flex", alignItems: "center", justifyContent: "center",
                      width: "16px", height: "16px", borderRadius: "50%",
                      background: "var(--surface-3)", color: "var(--fg-2)",
                      fontSize: "9px", fontWeight: 600, fontFamily: "var(--font-mono)",
                    }}>{i + 1}</span>
                    <span style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>{item}</span>
                  </li>
                ))}
              </ol>
            </div>

            <div style={divider} />

            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                <Code size={11} style={{ color: "var(--muted)" }} />
                <span style={sectionLabel}>{s.technical_tasks}</span>
              </div>
              <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "5px" }}>
                {story.technical_tasks.map((task, i) => (
                  <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: "7px", fontSize: "12px" }}>
                    <span style={{ flexShrink: 0, marginTop: "3px", width: "12px", height: "12px", borderRadius: "3px", border: "1px solid var(--border)" }} />
                    <span style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>{task}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div style={divider} />

            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                <ListChecks size={11} style={{ color: "var(--muted)" }} />
                <span style={sectionLabel}>{s.definition_of_done}</span>
              </div>
              <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "5px" }}>
                {story.definition_of_done.map((item, i) => (
                  <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: "7px", fontSize: "12px" }}>
                    <span style={{ flexShrink: 0, marginTop: "3px", width: "12px", height: "12px", borderRadius: "3px", border: "1px solid var(--border)" }} />
                    <span style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {story.risk_notes && story.risk_notes.length > 0 && (
              <>
                <div style={divider} />
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                    <AlertTriangle size={11} style={{ color: "var(--warn-fg)" }} />
                    <span style={sectionLabel}>{s.risk_notes}</span>
                  </div>
                  <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "5px" }}>
                    {story.risk_notes.map((note, i) => (
                      <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: "7px", fontSize: "12px" }}>
                        <span style={{ flexShrink: 0, marginTop: "5px", width: "5px", height: "5px", borderRadius: "50%", background: "var(--warn-fg)" }} />
                        <span style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>{note}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </div>
        )}
      </StepSummaryCard>

      {/* Integration health */}
      {health && (
        <div style={{
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: "var(--radius-lg)", padding: "14px 16px",
        }}>
          <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--fg-2)", margin: "0 0 10px", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            {s.integration_status}
          </p>
          <HealthStatus jira={health.jira} azureDevops={health.azure_devops} />
        </div>
      )}

      {/* Ticket creation */}
      <div style={{
        background: "var(--surface)", border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-sm)",
        padding: "20px 22px", display: "flex", flexDirection: "column", gap: "16px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Ticket size={15} style={{ color: "var(--accent)" }} />
          <h2 style={{ fontSize: "15px", fontWeight: 600, fontFamily: "var(--font-display)", margin: 0, color: "var(--fg)" }}>
            {s.ticket_title}
          </h2>
        </div>
        <p style={{ fontSize: "12.5px", color: "var(--muted)", margin: 0 }}>
          {s.ticket_description}
        </p>

        {error && (
          <div style={{ padding: "10px 14px", borderRadius: "var(--radius)", background: "var(--err-bg)", color: "var(--err-fg)", fontSize: "12.5px" }}>
            {error}
          </div>
        )}

        {ticket ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ padding: "12px 16px", borderRadius: "var(--radius)", background: "var(--ok-bg)", border: "1px solid color-mix(in oklch, var(--ok-fg) 20%, transparent)" }}>
              <p style={{ fontSize: "13px", fontWeight: 600, color: "var(--ok-fg)", margin: "0 0 6px" }}>
                {s.ticket_success}
              </p>
              <p style={{ fontSize: "12.5px", color: "var(--ok-fg)", margin: "0 0 3px" }}>
                ID: <span style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{ticket.ticket_id}</span>
              </p>
              <p style={{ fontSize: "12.5px", color: "var(--ok-fg)", margin: "0 0 8px" }}>
                {s.provider_label} <span style={{ fontWeight: 500, textTransform: "capitalize" }}>{ticket.provider}</span>
              </p>
              {ticket.url && (
                <a
                  href={ticket.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ display: "inline-flex", alignItems: "center", gap: "5px", fontSize: "12.5px", color: "var(--accent)", fontWeight: 500, textDecoration: "underline", textUnderlineOffset: "2px" }}
                >
                  {s.open_in} {ticket.provider}
                  <ExternalLink size={12} />
                </a>
              )}
            </div>
            <button
              onClick={reset}
              style={{
                display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
                padding: "9px 18px", borderRadius: "var(--radius)", border: "none",
                background: "var(--accent)", color: "var(--accent-fg)",
                fontSize: "13px", fontWeight: 600, cursor: "pointer",
                fontFamily: "var(--font-display)",
              }}
            >
              <Plus size={14} />
              {s.new_story}
            </button>
          </div>
        ) : (
          <>
            {/* Provider select */}
            <div>
              <label style={labelStyle}>{s.provider_select}</label>
              <div style={{ display: "flex", gap: "8px" }}>
                {Object.entries(PROVIDERS).map(([val, label]) => (
                  <button
                    key={val}
                    type="button"
                    onClick={() => setProvider(val)}
                    style={{
                      flex: 1, padding: "7px 12px", borderRadius: "var(--radius)",
                      border: "1px solid",
                      fontSize: "12.5px", fontWeight: 500, cursor: "pointer",
                      transition: "all .12s",
                      background: provider === val ? "var(--accent)" : "var(--surface)",
                      borderColor: provider === val ? "transparent" : "var(--border)",
                      color: provider === val ? "var(--accent-fg)" : "var(--fg-2)",
                      fontFamily: "var(--font-display)",
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label style={labelStyle} htmlFor="project-key">Project Key</label>
              <input
                id="project-key"
                style={inputStyle}
                value={projectKey}
                onChange={(e) => setProjectKey(e.target.value)}
                placeholder="SCRUM"
              />
            </div>

            <div>
              <label style={labelStyle} htmlFor="issue-type">Issue Type</label>
              <input
                id="issue-type"
                style={inputStyle}
                value={issueType}
                onChange={(e) => setIssueType(e.target.value)}
                placeholder="Story"
              />
            </div>

            <button
              onClick={handleCreate}
              disabled={loading || !state.storyId || !projectKey.trim()}
              style={{
                display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
                padding: "9px 18px", borderRadius: "var(--radius)", border: "none",
                background: loading || !state.storyId || !projectKey.trim() ? "var(--surface-3)" : "var(--accent)",
                color: loading || !state.storyId || !projectKey.trim() ? "var(--muted)" : "var(--accent-fg)",
                fontSize: "13px", fontWeight: 600,
                cursor: loading || !state.storyId || !projectKey.trim() ? "not-allowed" : "pointer",
                fontFamily: "var(--font-display)",
              }}
            >
              {loading
                ? <><Loader2 size={14} className="animate-spin" /> {s.creating}</>
                : <><Ticket size={14} /> {s.create_btn}</>
              }
            </button>
          </>
        )}
      </div>
    </div>
  )
}
