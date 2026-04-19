"use client"

import { useState } from "react"
import { generateStory, getStoryDetail, type StoryDetailResponse } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { RiskBadge } from "@/components/features/RiskBadge"
import { StepSummaryCard } from "@/components/features/StepSummaryCard"
import { Loader2, GitPullRequest, CheckCircle, Code, ListChecks, FileText, Search, Zap, AlertTriangle } from "lucide-react"

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
  const { t } = useLanguage()
  const s = t.workflow.step3

  async function handleGenerate() {
    if (!state.requirementId || !state.analysisId) return
    setLoading(true)
    setError(null)
    try {
      const genResult = await generateStory(
        state.requirementId,
        state.analysisId,
        state.projectId,
        state.language
      )
      const detail = await getStoryDetail(genResult.story_id)
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
              <h3 style={{ fontSize: "14px", fontWeight: 600, color: "var(--fg)", margin: "0 0 6px", fontFamily: "var(--font-display)" }}>
                {story.title}
              </h3>
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
              <p style={{ fontSize: "12.5px", lineHeight: 1.65, color: "var(--fg-2)", margin: 0 }}>
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
                    <span style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>{item}</span>
                  </li>
                ))}
              </ol>
            </div>

            <div style={divider} />

            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "8px" }}>
                <Code size={12} style={{ color: "var(--muted)" }} />
                <span style={sectionLabel}>{s.technical_tasks}</span>
              </div>
              <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "6px" }}>
                {story.technical_tasks.map((task, i) => (
                  <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: "8px", fontSize: "12.5px" }}>
                    <span style={{
                      flexShrink: 0, marginTop: "3px", width: "14px", height: "14px",
                      borderRadius: "3px", border: "1px solid var(--border)",
                    }} />
                    <span style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>{task}</span>
                  </li>
                ))}
              </ul>
            </div>

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
                    <span style={{ color: "var(--fg-2)", lineHeight: 1.5 }}>{item}</span>
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
    </div>
  )
}
