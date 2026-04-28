"use client"

import { useState } from "react"
import { generateStory, getStoryDetail, type StoryDetailResponse } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { RiskBadge } from "@/components/features/RiskBadge"
import { StepSummaryCard } from "@/components/features/StepSummaryCard"
import { EditStoryModal } from "@/components/features/stories/EditStoryModal"
import { QualityPanel } from "@/components/features/stories/QualityPanel"
import { StoryFeedback } from "@/components/features/stories/StoryFeedback"
import { Loader2, GitPullRequest, CheckCircle, Code, ListChecks, FileText, Search, Zap, AlertTriangle, Pencil, Lock } from "lucide-react"

const truncate = (text: string, max: number) =>
  text.length > max ? text.slice(0, max) + "…" : text

const chip = (text: string): React.CSSProperties => ({
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

interface Step3Props {
  state: WorkflowState
  completeStep3: (storyId: string, storyTitle: string, storyPoints: number) => void
}

export function Step3Generate({ state, completeStep3 }: Step3Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [story, setStory] = useState<StoryDetailResponse | null>(null)
  const [editOpen, setEditOpen] = useState(false)
  const [toast, setToast] = useState<{ msg: string; tone: "ok" | "err" } | null>(null)
  const { t } = useLanguage()
  const s = t.workflow.step3

  function showToast(msg: string, tone: "ok" | "err") {
    setToast({ msg, tone })
    setTimeout(() => setToast(null), 3000)
  }

  async function handleGenerate() {
    if (!state.requirementId || !state.analysisId) return
    if (!state.sourceConnectionId) {
      setError("Selecciona un repositorio activo antes de generar.")
      return
    }
    setLoading(true)
    setError(null)
    try {
      const genResult = await generateStory(
        state.requirementId,
        state.analysisId,
        state.projectId,
        state.sourceConnectionId,
        state.language,
      )
      const detail = await getStoryDetail(genResult.story_id)
      if (detail.source_connection_id !== state.sourceConnectionId) {
        // El backend devolvió una historia de otra conexión — abortar.
        throw new Error(
          "La historia devuelta pertenece a otro repositorio. Reiniciá el flujo.",
        )
      }
      setStory(detail)
      completeStep3(genResult.story_id, detail.title, detail.story_points)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate story")
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
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center" }}>
          {state.featureType && <span style={chip(state.featureType)}>{state.featureType}</span>}
          {state.complexity && <span style={chip(`${s.complexity} ${state.complexity}`)}>{s.complexity} {state.complexity}</span>}
          {state.language && <span style={chip(state.language)}>Lang: {state.language}</span>}
        </div>
        {state.intent && (
          <p style={{ fontSize: "11.5px", color: "var(--muted)", margin: 0 }}>
            Intent: <span style={{ color: "var(--fg-2)", fontWeight: 500 }}>{state.intent}</span>
          </p>
        )}
        {state.keywords.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
            {state.keywords.map((kw) => <span key={kw} style={chip(kw)}>{kw}</span>)}
          </div>
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
            {state.modulesImpacted.map((m) => <span key={m} style={chip(m)}>{m}</span>)}
          </div>
        )}
      </StepSummaryCard>

      {/* Main card */}
      <div style={{
        background: "var(--surface)", border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-sm)",
        padding: "20px 22px", display: "flex", flexDirection: "column", gap: "16px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <GitPullRequest size={15} style={{ color: "var(--accent)" }} />
          <h2 style={{ fontSize: "15px", fontWeight: 600, fontFamily: "var(--font-display)", margin: 0, color: "var(--fg)" }}>
            {s.title}
          </h2>
        </div>
        <p style={{ fontSize: "12.5px", color: "var(--muted)", margin: 0 }}>
          {s.description}
        </p>

        {error && (
          <div style={{ padding: "10px 14px", borderRadius: "var(--radius)", background: "var(--err-bg)", color: "var(--err-fg)", fontSize: "12.5px" }}>
            {error}
          </div>
        )}

        {story && (
          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            <div>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px", marginBottom: "6px" }}>
                <h3 style={{ fontSize: "14px", fontWeight: 600, color: "var(--fg)", margin: 0, fontFamily: "var(--font-display)", flex: 1 }}>
                  {story.title}
                </h3>
                {story.is_locked ? (
                  <span style={{
                    display: "inline-flex", alignItems: "center", gap: "4px",
                    padding: "2px 8px", borderRadius: "12px", fontSize: "11px", fontWeight: 600,
                    background: "var(--surface-3)", color: "var(--muted)",
                    flexShrink: 0,
                  }}>
                    <Lock size={10} /> {t.stories.locked_badge}
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => setEditOpen(true)}
                    style={{
                      display: "flex", alignItems: "center", gap: "4px",
                      padding: "4px 10px", borderRadius: "var(--radius)",
                      border: "1px solid var(--border)", background: "var(--surface-2)",
                      color: "var(--fg-2)", fontSize: "12px", cursor: "pointer",
                      flexShrink: 0,
                    }}
                  >
                    <Pencil size={11} /> {t.stories.edit_btn}
                  </button>
                )}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ ...chip("pts"), background: "var(--accent-soft)", color: "var(--accent-strong)" }}>
                  {story.story_points} {story.story_points === 1 ? s.point : s.points}
                </span>
                <RiskBadge risk={story.risk_level} />
              </div>
            </div>

            <div style={divider} />

            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "6px" }}>
                <FileText size={12} style={{ color: "var(--muted)" }} />
                <span style={sectionLabel}>{s.description_label}</span>
              </div>
              <p style={{ fontSize: "12.5px", lineHeight: 1.65, color: "var(--fg-2)", margin: 0, overflowWrap: "break-word" }}>
                {story.story_description}
              </p>
            </div>

            <div style={divider} />

            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
                <CheckCircle size={12} style={{ color: "var(--muted)" }} />
                <span style={sectionLabel}>{s.acceptance_criteria}</span>
              </div>
              <ol style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "6px" }}>
                {story.acceptance_criteria.map((item, i) => (
                  <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: "8px", fontSize: "12.5px" }}>
                    <span style={{
                      flexShrink: 0, display: "inline-flex", alignItems: "center", justifyContent: "center",
                      width: "18px", height: "18px", borderRadius: "50%",
                      background: "var(--surface-3)", color: "var(--fg-2)",
                      fontSize: "10px", fontWeight: 600, fontFamily: "var(--font-mono)",
                    }}>
                      {i + 1}
                    </span>
                    <span style={{ color: "var(--fg-2)", lineHeight: 1.5, overflowWrap: "break-word", flex: 1, minWidth: 0 }}>{item}</span>
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
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
                    <Code size={12} style={{ color: "var(--muted)" }} />
                    <span style={sectionLabel}>{labels[cat]}</span>
                  </div>
                  <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "10px" }}>
                    {tasks.map((sub, i) => (
                      <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: "8px", fontSize: "12.5px" }}>
                        <span style={{
                          flexShrink: 0, marginTop: "3px", width: "14px", height: "14px",
                          borderRadius: "3px", border: "1px solid var(--border)",
                        }} />
                        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: "4px" }}>
                          <span style={{ color: "var(--fg)", fontWeight: 500, lineHeight: 1.4, overflowWrap: "break-word" }}>
                            {sub.title}
                          </span>
                          {sub.description && (
                            <span style={{
                              color: "var(--muted)", fontSize: "12px", lineHeight: 1.6,
                              whiteSpace: "pre-wrap", overflowWrap: "break-word",
                            }}>
                              {sub.description}
                            </span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })}

            <div style={divider} />

            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
                <ListChecks size={12} style={{ color: "var(--muted)" }} />
                <span style={sectionLabel}>{s.definition_of_done}</span>
              </div>
              <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "6px" }}>
                {story.definition_of_done.map((item, i) => (
                  <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: "8px", fontSize: "12.5px" }}>
                    <span style={{
                      flexShrink: 0, marginTop: "3px", width: "14px", height: "14px",
                      borderRadius: "3px", border: "1px solid var(--border)",
                    }} />
                    <span style={{ color: "var(--fg-2)", lineHeight: 1.5, overflowWrap: "break-word", flex: 1, minWidth: 0 }}>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {story.risk_notes && story.risk_notes.length > 0 && (
              <>
                <div style={divider} />
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
                    <AlertTriangle size={12} style={{ color: "var(--warn-fg)" }} />
                    <span style={sectionLabel}>{s.risk_notes}</span>
                  </div>
                  <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "6px" }}>
                    {story.risk_notes.map((note, i) => (
                      <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: "8px", fontSize: "12.5px" }}>
                        <span style={{
                          flexShrink: 0, marginTop: "6px", width: "6px", height: "6px",
                          borderRadius: "50%", background: "var(--warn-fg)",
                        }} />
                        <span style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>{note}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </div>
        )}

        {!story && (
          <button
            onClick={handleGenerate}
            disabled={loading || !state.requirementId || !state.analysisId}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
              padding: "9px 18px", borderRadius: "var(--radius)", border: "none",
              background: loading || !state.requirementId || !state.analysisId ? "var(--surface-3)" : "var(--accent)",
              color: loading || !state.requirementId || !state.analysisId ? "var(--muted)" : "var(--accent-fg)",
              fontSize: "13px", fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
              fontFamily: "var(--font-display)",
            }}
          >
            {loading
              ? <><Loader2 size={14} className="animate-spin" /> {s.generating}</>
              : s.generate_btn
            }
          </button>
        )}

        {story && (
          <button
            onClick={handleGenerate}
            disabled={loading}
            style={{
              display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
              padding: "7px 14px", borderRadius: "var(--radius)", border: "1px solid var(--border)",
              background: "var(--surface-2)", color: "var(--fg-2)",
              fontSize: "12px", fontWeight: 500, cursor: loading ? "not-allowed" : "pointer",
              fontFamily: "var(--font-display)", alignSelf: "flex-start",
            }}
          >
            {loading ? <><Loader2 size={13} className="animate-spin" /> {s.regenerating}</> : s.regenerate_btn}
          </button>
        )}
      </div>

      {/* Quality Panel and Feedback — shown after story is generated */}
      {story && (
        <>
          <QualityPanel storyId={story.story_id} />
          <StoryFeedback storyId={story.story_id} onToast={showToast} />
        </>
      )}

      {/* Toast notification */}
      {toast && (
        <div style={{
          position: "fixed", top: "64px", right: "16px", zIndex: 50,
          background: toast.tone === "ok" ? "var(--ok-bg)" : "var(--err-bg)",
          color: toast.tone === "ok" ? "var(--ok-fg)" : "var(--err-fg)",
          padding: "10px 16px", borderRadius: "var(--radius)",
          border: `1px solid ${toast.tone === "ok" ? "var(--ok-fg)" : "var(--err-fg)"}`,
          fontSize: "13px", fontWeight: 500, boxShadow: "var(--shadow-sm)", maxWidth: "320px",
        }}>
          {toast.msg}
        </div>
      )}

      {/* Edit Modal */}
      {story && editOpen && (
        <EditStoryModal
          story={story}
          isOpen={editOpen}
          onClose={() => setEditOpen(false)}
          onSaved={updated => {
            setStory(updated)
            showToast(t.stories.edit_saved, "ok")
          }}
        />
      )}
    </div>
  )
}
