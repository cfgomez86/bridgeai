"use client"

import { useState, useEffect, useRef } from "react"
import { generateStory, getStoryDetail, type StoryDetailResponse } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { RiskBadge } from "@/components/features/RiskBadge"
import { StepSummaryCard } from "@/components/features/StepSummaryCard"
import { QualityPanel } from "@/components/features/stories/QualityPanel"
import { StoryCard } from "@/components/features/stories/StoryCard"
import { StoryFeedback } from "@/components/features/stories/StoryFeedback"
import { Loader2, Search, Zap } from "lucide-react"

const truncate = (text: string, max: number) =>
  text.length > max ? text.slice(0, max) + "…" : text

const chip = (): React.CSSProperties => ({
  display: "inline-flex", alignItems: "center",
  padding: "1px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 500,
  fontFamily: "var(--font-mono)",
  background: "var(--surface-3)", color: "var(--fg-2)",
  border: "1px solid transparent",
})

interface Step3Props {
  state: WorkflowState
  completeStep3: (storyId: string, storyTitle: string, storyPoints: number) => void
}

export function Step3Generate({ state, completeStep3 }: Step3Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [story, setStory] = useState<StoryDetailResponse | null>(null)
  const [toast, setToast] = useState<{ msg: string; tone: "ok" | "err" } | null>(null)
  const [pendingComplete, setPendingComplete] = useState<{ storyId: string; title: string; points: number } | null>(null)
  const { t } = useLanguage()
  const s = t.workflow.step3
  const triggered = useRef(false)

  function showToast(msg: string, tone: "ok" | "err") {
    setToast({ msg, tone })
    setTimeout(() => setToast(null), 3000)
  }

  useEffect(() => {
    if (triggered.current || !state.requirementId || !state.analysisId || !state.sourceConnectionId) return
    triggered.current = true
    setLoading(true)
    setError(null)
    generateStory(
      state.requirementId,
      state.analysisId,
      state.projectId,
      state.sourceConnectionId,
      state.language,
    )
      .then(genResult =>
        getStoryDetail(genResult.story_id).then(detail => {
          if (detail.source_connection_id !== state.sourceConnectionId) {
            throw new Error("La historia devuelta pertenece a otro repositorio. Reiniciá el flujo.")
          }
          setStory(detail)
          setPendingComplete({ storyId: genResult.story_id, title: detail.title, points: detail.story_points })
        })
      )
      .catch(err => setError(err instanceof Error ? err.message : "Failed to generate story"))
      .finally(() => setLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.requirementId, state.analysisId, state.sourceConnectionId])

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <StepSummaryCard title={s.step1_summary} icon={<Search size={13} />}>
        <p style={{ fontSize: "12.5px", color: "var(--fg-2)", fontStyle: "italic", margin: 0 }}>
          &ldquo;{truncate(state.requirementText, 120)}&rdquo;
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center" }}>
          {state.featureType && <span style={chip()}>{state.featureType}</span>}
          {state.complexity && <span style={chip()}>{s.complexity} {state.complexity}</span>}
          {state.language && <span style={chip()}>Lang: {state.language}</span>}
        </div>
        {state.intent && (
          <p style={{ fontSize: "11.5px", color: "var(--muted)", margin: 0 }}>
            Intent: <span style={{ color: "var(--fg-2)", fontWeight: 500 }}>{state.intent}</span>
          </p>
        )}
        {state.keywords.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
            {state.keywords.map((kw) => <span key={kw} style={chip()}>{kw}</span>)}
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
            {state.modulesImpacted.map((m) => <span key={m} style={chip()}>{m}</span>)}
          </div>
        )}
      </StepSummaryCard>

      {loading && (
        <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--muted)", fontSize: "12px", padding: "4px 0" }}>
          <Loader2 size={13} className="animate-spin" /> {s.generating}
        </div>
      )}

      {error && (
        <div style={{ padding: "10px 14px", borderRadius: "var(--radius)", background: "var(--err-bg)", color: "var(--err-fg)", fontSize: "12.5px" }}>
          {error}
        </div>
      )}

      {story && <QualityPanel storyId={story.story_id} />}

      {story && (
        <StoryCard
          key={story.story_id}
          story={story}
          onSaved={setStory}
          onToast={showToast}
        />
      )}

      {story && (
        <>
          <StoryFeedback storyId={story.story_id} onToast={showToast} />
          {pendingComplete && (
            <button
              onClick={() => completeStep3(pendingComplete.storyId, pendingComplete.title, pendingComplete.points)}
              style={{
                display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
                padding: "10px 20px", borderRadius: "var(--radius)", border: "none",
                background: "var(--accent)", color: "var(--accent-fg)",
                fontSize: "13px", fontWeight: 600, cursor: "pointer",
                fontFamily: "var(--font-display)", alignSelf: "stretch",
              }}
            >
              {s.continue_btn}
            </button>
          )}
        </>
      )}

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
    </div>
  )
}
