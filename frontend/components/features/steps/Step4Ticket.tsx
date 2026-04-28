"use client"

import { useState, useEffect } from "react"
import {
  createTicket,
  getStoryDetail,
  listConnections,
  listJiraProjects,
  listAzureProjects,
  getAzureProjectProcess,
  type CreateTicketResponse,
  type StoryDetailResponse,
  type ConnectionResponse,
  type JiraProjectResponse,
  type AzureProjectResponse,
} from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"
import type { WorkflowState } from "@/hooks/useWorkflow"
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

const SCM_PLATFORMS = new Set(["github", "gitlab", "azure_devops", "bitbucket"])

const AZURE_ITEM_TYPES: Record<string, Array<{ value: string; label: string }>> = {
  Agile: [
    { value: "User Story",          label: "User Story" },
    { value: "Bug",                  label: "Bug" },
    { value: "Task",                 label: "Task" },
  ],
  Scrum: [
    { value: "Product Backlog Item", label: "Product Backlog Item" },
    { value: "Bug",                  label: "Bug" },
    { value: "Task",                 label: "Task" },
  ],
  CMMI: [
    { value: "Requirement",          label: "Requirement" },
    { value: "Bug",                  label: "Bug" },
    { value: "Task",                 label: "Task" },
  ],
  Basic: [
    { value: "Issue",                label: "Issue" },
    { value: "Task",                 label: "Task" },
  ],
}

const AZURE_FALLBACK_ITEM_TYPES = [
  { value: "User Story",          label: "User Story (Agile)" },
  { value: "Product Backlog Item", label: "Product Backlog Item (Scrum)" },
  { value: "Issue",                label: "Issue (Basic)" },
  { value: "Requirement",          label: "Requirement (CMMI)" },
  { value: "Bug",                  label: "Bug" },
  { value: "Task",                 label: "Task" },
]

const AZURE_TEMPLATE_DEFAULTS: Record<string, string> = {
  Agile: "User Story",
  Scrum: "Product Backlog Item",
  CMMI:  "Requirement",
  Basic: "Issue",
}

interface Step4Props {
  state: WorkflowState
  setTicketProjectKey: (key: string) => void
  completeStep4: () => void
  reset: () => void
}

export function Step4Ticket({ state, setTicketProjectKey, completeStep4, reset }: Step4Props) {
  const [provider, setProvider] = useState<string>("jira")
  const [issueType, setIssueType] = useState("Story")
  const [createSubtasks, setCreateSubtasks] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ticket, setTicket] = useState<CreateTicketResponse | null>(null)
  const [story, setStory] = useState<StoryDetailResponse | null>(null)
  const [ticketConn, setTicketConn] = useState<ConnectionResponse | null>(null)
  const [projects, setProjects] = useState<JiraProjectResponse[]>([])
  const [azureProjects, setAzureProjects] = useState<AzureProjectResponse[]>([])
  const [azureProcessTemplate, setAzureProcessTemplate] = useState("")
  const [projectsLoading, setProjectsLoading] = useState(false)
  const { t } = useLanguage()
  const s = t.workflow.step4

  const azureItemTypes = azureProcessTemplate
    ? (AZURE_ITEM_TYPES[azureProcessTemplate] ?? AZURE_FALLBACK_ITEM_TYPES)
    : AZURE_FALLBACK_ITEM_TYPES

  useEffect(() => {
    if (provider !== "azure_devops") { setIssueType("Story"); return }
    setIssueType(AZURE_TEMPLATE_DEFAULTS[azureProcessTemplate] ?? "User Story")
  }, [provider, azureProcessTemplate])

  // Fetch process template whenever the selected Azure project changes
  useEffect(() => {
    if (provider !== "azure_devops" || !ticketConn || !state.ticketProjectKey) {
      setAzureProcessTemplate("")
      return
    }
    getAzureProjectProcess(ticketConn.id, state.ticketProjectKey)
      .then(setAzureProcessTemplate)
      .catch(() => setAzureProcessTemplate(""))
  }, [provider, ticketConn, state.ticketProjectKey])

  useEffect(() => {
    listConnections().then((conns) => {
      const conn =
        conns.find((c) => c.platform === "jira") ??
        conns.find((c) => c.platform === "azure_devops" && Boolean(c.boards_project))
      setTicketConn(conn ?? null)
      if (conn) setProvider(conn.platform)
      if (conn?.platform === "jira") {
        setProjectsLoading(true)
        listJiraProjects(conn.id)
          .then(setProjects)
          .catch(() => {})
          .finally(() => setProjectsLoading(false))
      }
      if (conn?.platform === "azure_devops") {
        if (conn.boards_project) {
          const projectName = conn.boards_project.split("/").pop() ?? conn.boards_project
          setTicketProjectKey(projectName)
        }
        setProjectsLoading(true)
        listAzureProjects(conn.id)
          .then(setAzureProjects)
          .catch(() => {})
          .finally(() => setProjectsLoading(false))
      }
    }).catch(() => {})
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
      const result = await createTicket(state.storyId, provider, state.ticketProjectKey, issueType, createSubtasks)
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

            {(["frontend", "backend", "configuration"] as const).map((cat) => {
              const tasks = story.subtasks?.[cat] ?? []
              if (tasks.length === 0) return null
              const labels = { frontend: s.subtasks_frontend, backend: s.subtasks_backend, configuration: s.subtasks_configuration }
              return (
                <div key={cat}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                    <Code size={11} style={{ color: "var(--muted)" }} />
                    <span style={sectionLabel}>{labels[cat]}</span>
                  </div>
                  <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "5px" }}>
                    {tasks.map((task, i) => (
                      <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: "7px", fontSize: "12px" }}>
                        <span style={{ flexShrink: 0, marginTop: "3px", width: "12px", height: "12px", borderRadius: "3px", border: "1px solid var(--border)" }} />
                        <span style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>{task}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })}

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
            {ticket.subtask_urls && ticket.subtask_urls.length > 0 && (
              <div style={{ padding: "10px 14px", borderRadius: "var(--radius)", background: "var(--surface-2, var(--surface))", border: "1px solid var(--border)" }}>
                <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--fg-2)", margin: "0 0 6px", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {s.subtasks_created} ({ticket.subtask_urls.length})
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
                  {ticket.subtask_urls.map((url, i) => {
                    const id = url.split("/").pop()
                    const title = ticket.subtask_titles?.[i]
                    return (
                      <a
                        key={i}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ display: "block", fontSize: "12px", color: "var(--accent)", textDecoration: "none", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
                      >
                        <span style={{ fontFamily: "var(--font-mono)", fontWeight: 600 }}>{id}</span>
                        {title && <span style={{ fontFamily: "var(--font-sans)", fontWeight: 400, color: "var(--fg-2)", textDecoration: "none", marginLeft: "8px" }}>{title}</span>}
                      </a>
                    )
                  })}
                </div>
              </div>
            )}
            {ticket.failed_subtasks && ticket.failed_subtasks.length > 0 && (
              <div style={{ padding: "10px 14px", borderRadius: "var(--radius)", background: "var(--warn-bg, var(--err-bg))", border: "1px solid color-mix(in oklch, var(--warn-fg, var(--err-fg)) 20%, transparent)" }}>
                <p style={{ fontSize: "12px", fontWeight: 600, color: "var(--warn-fg, var(--err-fg))", margin: "0 0 4px", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  {s.subtasks_failed} ({ticket.failed_subtasks.length})
                </p>
                <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                  {ticket.failed_subtasks.map((task, i) => (
                    <p key={i} style={{ fontSize: "12px", color: "var(--warn-fg, var(--err-fg))", margin: 0, fontFamily: "var(--font-mono)" }}>{task}</p>
                  ))}
                </div>
              </div>
            )}
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
            <div>
              <label style={labelStyle} htmlFor="project-key">
                {s.project_key_label}
                <span style={{ color: "var(--err-fg)", marginLeft: "3px" }}>*</span>
              </label>
              {provider === "azure_devops" && azureProjects.length > 0 ? (
                <select
                  id="project-key"
                  style={{ ...inputStyle, cursor: "pointer" }}
                  value={state.ticketProjectKey}
                  onChange={(e) => setTicketProjectKey(e.target.value)}
                >
                  <option value="">{s.project_key_hint}</option>
                  {azureProjects.map((p) => (
                    <option key={p.full_name} value={p.name}>{p.name}</option>
                  ))}
                </select>
              ) : provider === "jira" && projects.length > 0 ? (
                <select
                  id="project-key"
                  style={{ ...inputStyle, cursor: "pointer" }}
                  value={state.ticketProjectKey}
                  onChange={(e) => setTicketProjectKey(e.target.value)}
                >
                  <option value="">{s.project_key_hint}</option>
                  {projects.map((p) => (
                    <option key={p.key} value={p.key}>
                      {p.name} ({p.key})
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  id="project-key"
                  style={{
                    ...inputStyle,
                    borderColor: state.ticketProjectKey.trim() ? "var(--border)" : "color-mix(in oklch, var(--err-fg) 50%, var(--border))",
                  }}
                  value={state.ticketProjectKey}
                  onChange={(e) => setTicketProjectKey(e.target.value.toUpperCase())}
                  placeholder={projectsLoading ? s.project_key_loading : "SCRUM"}
                  disabled={projectsLoading}
                />
              )}
            </div>

            <div>
              <label style={labelStyle} htmlFor="issue-type">
                {s.issue_type_label}
                {provider === "azure_devops" && azureProcessTemplate && (
                  <span style={{ fontSize: "11px", fontWeight: 400, color: "var(--muted)", marginLeft: "6px", fontFamily: "var(--font-mono)" }}>
                    {azureProcessTemplate}
                  </span>
                )}
              </label>
              <select
                id="issue-type"
                style={{ ...inputStyle, cursor: "pointer" }}
                value={issueType}
                onChange={(e) => setIssueType(e.target.value)}
              >
                {provider === "azure_devops"
                  ? azureItemTypes.map((t) => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))
                  : (
                    <>
                      <option value="Story">Story</option>
                      <option value="Bug">Bug</option>
                    </>
                  )
                }
              </select>
            </div>

            <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", userSelect: "none" }}>
              <input
                type="checkbox"
                checked={createSubtasks}
                onChange={(e) => setCreateSubtasks(e.target.checked)}
                style={{ width: "14px", height: "14px", accentColor: "var(--accent)", cursor: "pointer" }}
              />
              <span style={{ fontSize: "12.5px", color: "var(--fg-2)" }}>{s.create_subtasks_label}</span>
            </label>

            <button
              onClick={handleCreate}
              disabled={loading || !state.storyId || !state.ticketProjectKey.trim()}
              style={{
                display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
                padding: "9px 18px", borderRadius: "var(--radius)", border: "none",
                background: loading || !state.storyId || !state.ticketProjectKey.trim() ? "var(--surface-3)" : "var(--accent)",
                color: loading || !state.storyId || !state.ticketProjectKey.trim() ? "var(--muted)" : "var(--accent-fg)",
                fontSize: "13px", fontWeight: 600,
                cursor: loading || !state.storyId || !state.ticketProjectKey.trim() ? "not-allowed" : "pointer",
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
