"use client"

import { useState, useEffect, useRef } from "react"
import { createPortal } from "react-dom"
import {
  generateStory,
  getStoryDetail,
  ApiError,
  type StoryDetailResponse,
  type EntityNotFoundDetail,
  type ForceReason,
} from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { RiskBadge } from "@/components/features/RiskBadge"
import { StepSummaryCard } from "@/components/features/StepSummaryCard"
import { QualityPanel } from "@/components/features/stories/QualityPanel"
import { StoryCard } from "@/components/features/stories/StoryCard"
import { StoryFeedback } from "@/components/features/stories/StoryFeedback"
import { AlertTriangle, Loader2, Pencil, Search, ShieldOff, Wand2, Zap } from "lucide-react"

function HelpTip({ text, children }: { text: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const [anchor, setAnchor] = useState<{ x: number; y: number; alignRight: boolean } | null>(null)
  const ref = useRef<HTMLSpanElement>(null)

  function place() {
    if (!ref.current) return
    const r = ref.current.getBoundingClientRect()
    const popoverWidth = Math.min(280, window.innerWidth * 0.8)
    const safeMargin = 16
    const triggerLeft = r.left
    const overflowsRight = triggerLeft + popoverWidth > window.innerWidth - safeMargin
    setAnchor({
      x: overflowsRight ? r.right : triggerLeft,
      y: r.bottom + 6,
      alignRight: overflowsRight,
    })
  }

  function show() { place(); setOpen(true) }
  function hide() { setOpen(false) }

  return (
    <span
      ref={ref}
      style={{ display: "inline-flex", alignItems: "center" }}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
      onClick={(e) => { e.stopPropagation(); setOpen(v => { if (!v) place(); return !v }) }}
    >
      <span style={{ cursor: "pointer", lineHeight: "inherit" }}>{children}</span>
      {open && anchor && createPortal(
        <span
          role="tooltip"
          style={{
            position: "fixed",
            top: anchor.y,
            ...(anchor.alignRight
              ? { right: `calc(100vw - ${anchor.x}px)`, left: "auto" }
              : { left: anchor.x, right: "auto" }),
            zIndex: 9999,
            width: "max-content",
            maxWidth: "min(280px, 80vw)",
            padding: "10px 12px",
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius)",
            boxShadow: "var(--shadow-sm)",
            fontFamily: "var(--font-sans)",
            fontSize: "12px",
            fontWeight: 400,
            lineHeight: 1.45,
            letterSpacing: "normal",
            textTransform: "none",
            color: "var(--fg-2)",
            whiteSpace: "normal",
            pointerEvents: "none",
          }}
        >
          {text}
        </span>,
        document.body
      )}
    </span>
  )
}

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
  setGeneratorInfo: (model: string | null, calls: number) => void
  goBackToStep1: () => void
}

export function Step3Generate({ state, completeStep3, setGeneratorInfo, goBackToStep1 }: Step3Props) {
  const [loading, setLoading] = useState(false)
  const [forcing, setForcing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [entityNotFound, setEntityNotFound] = useState<EntityNotFoundDetail | null>(null)
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

  function runGenerate(force: boolean, forceReason?: ForceReason) {
    if (!state.requirementId || !state.analysisId || !state.sourceConnectionId) return
    if (force) {
      setForcing(true)
      setEntityNotFound(null)
    } else {
      setLoading(true)
    }
    setError(null)
    generateStory(
      state.requirementId,
      state.analysisId,
      state.projectId,
      state.sourceConnectionId,
      state.language,
      force || undefined,
      force ? forceReason : undefined,
    )
      .then(genResult =>
        getStoryDetail(genResult.story_id).then(detail => {
          if (detail.source_connection_id !== state.sourceConnectionId) {
            throw new Error(s.wrong_repo_error)
          }
          setStory(detail)
          setGeneratorInfo(detail.generator_model ?? null, detail.generator_calls ?? 0)
          setPendingComplete({ storyId: genResult.story_id, title: detail.title, points: detail.story_points })
        })
      )
      .catch(err => {
        if (err instanceof ApiError && err.status === 422 && err.detail && typeof err.detail === "object") {
          const d = err.detail as Record<string, unknown>
          if (d.code === "ENTITY_NOT_FOUND") {
            setEntityNotFound({
              code: "ENTITY_NOT_FOUND",
              entity: String(d.entity ?? ""),
              message: String(d.message ?? ""),
              suggestions: Array.isArray(d.suggestions) ? d.suggestions.map(String) : [],
              hint: String(d.hint ?? ""),
            })
            return
          }
        }
        setError(err instanceof Error ? err.message : s.error_generic)
      })
      .finally(() => {
        setLoading(false)
        setForcing(false)
      })
  }

  useEffect(() => {
    if (triggered.current || !state.requirementId || !state.analysisId || !state.sourceConnectionId) return
    triggered.current = true
    runGenerate(false)
  // runGenerate closes over state, but triggered.current guarantees this fires exactly
  // once — all state values are already settled when the three IDs become available.
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
          {state.language && <span style={chip()}>{s.lang_label} {state.language}</span>}
        </div>
        {state.intent && (
          <p style={{ fontSize: "11.5px", color: "var(--muted)", margin: 0 }}>
            {s.intent_label} <span style={{ color: "var(--fg-2)", fontWeight: 500 }}>{state.intent}</span>
          </p>
        )}
        {state.keywords.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
            {state.keywords.map((kw) => <span key={kw} style={chip()}>{kw}</span>)}
          </div>
        )}
        {(state.coherenceModel || state.parserModel) && (
          <div style={{ display: "flex", flexDirection: "column", gap: "2px", marginTop: "2px" }}>
            {state.coherenceModel && (
              <p style={{ fontSize: "11px", color: "var(--fg-2)", margin: 0, fontFamily: "var(--font-mono)" }}>
                {s.coherence_judge_label}: <span style={{ color: "var(--muted)" }}>{state.coherenceModel}</span>
              </p>
            )}
            {state.parserModel && (
              <p style={{ fontSize: "11px", color: "var(--fg-2)", margin: 0, fontFamily: "var(--font-mono)" }}>
                {s.parser_label}: <span style={{ color: "var(--muted)" }}>{state.parserModel}</span>
              </p>
            )}
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

      {(loading || forcing) && (
        <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--muted)", fontSize: "12px", padding: "4px 0" }}>
          <Loader2 size={13} className="animate-spin" /> {s.generating}
        </div>
      )}

      {entityNotFound && (
        <div style={{
          padding: "14px 16px",
          borderRadius: "var(--radius-lg)",
          background: "var(--surface-2)",
          border: "1px solid var(--border)",
          display: "flex", flexDirection: "column", gap: "10px",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--fg-2)" }}>
            <AlertTriangle size={15} />
            <strong style={{ fontSize: "13px", fontFamily: "var(--font-display)" }}>
              {s.errors.entity_not_found_title}
            </strong>
          </div>

          {entityNotFound.entity && (
            <div style={{ fontSize: "12px", color: "var(--fg-2)" }}>
              {s.errors.entity_label}:{" "}
              <code style={{
                fontFamily: "var(--font-mono)", fontSize: "11.5px",
                padding: "1px 6px", borderRadius: "4px",
                background: "var(--surface-3)", color: "var(--fg)",
              }}>
                {entityNotFound.entity}
              </code>
            </div>
          )}

          <p style={{ margin: 0, fontSize: "12.5px", color: "var(--fg)" }}>
            {entityNotFound.suggestions.length > 0
              ? s.errors.entity_not_found_desc_with_suggestions
              : s.errors.entity_not_found_desc_empty}
          </p>

          {entityNotFound.suggestions.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
              {entityNotFound.suggestions.map((sug) => (
                <code key={sug} style={{
                  fontFamily: "var(--font-mono)", fontSize: "11.5px",
                  padding: "2px 8px", borderRadius: "4px",
                  background: "var(--surface-3)", color: "var(--fg)",
                  border: "1px solid var(--border)",
                }}>
                  {sug}
                </code>
              ))}
            </div>
          )}

          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginTop: "4px" }}>
            <button
              type="button"
              disabled={forcing}
              onClick={() => { setEntityNotFound(null); goBackToStep1() }}
              style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                padding: "7px 12px", borderRadius: "var(--radius)",
                border: "1px solid var(--border)",
                background: "transparent",
                color: forcing ? "var(--muted)" : "var(--fg-2)",
                fontSize: "12px", fontWeight: 500,
                fontFamily: "var(--font-display)",
                cursor: forcing ? "not-allowed" : "pointer",
              }}
            >
              <Pencil size={12} />
              {s.errors.edit_requirement_btn}
            </button>

            <HelpTip text={s.errors.force_create_hint}>
              <button
                type="button"
                disabled={forcing}
                onClick={() => runGenerate(true, "ambiguous")}
                style={{
                  display: "inline-flex", alignItems: "center", gap: "6px",
                  padding: "7px 12px", borderRadius: "var(--radius)",
                  border: "1px solid var(--border)",
                  background: "transparent",
                  color: forcing ? "var(--muted)" : "var(--fg-2)",
                  fontSize: "12px", fontWeight: 500,
                  fontFamily: "var(--font-display)",
                  cursor: forcing ? "not-allowed" : "pointer",
                }}
              >
                {forcing
                  ? <Loader2 size={12} className="animate-spin" />
                  : <Wand2 size={12} />}
                {forcing ? s.errors.creating_anyway : s.errors.force_create_btn}
              </button>
            </HelpTip>

            <HelpTip text={s.errors.intentional_new_hint}>
              <button
                type="button"
                disabled={forcing}
                onClick={() => runGenerate(true, "intentional_new")}
                style={{
                  display: "inline-flex", alignItems: "center", gap: "6px",
                  padding: "7px 12px", borderRadius: "var(--radius)",
                  border: "1px solid var(--border)",
                  background: "transparent",
                  color: forcing ? "var(--muted)" : "var(--fg-2)",
                  fontSize: "12px", fontWeight: 500,
                  fontFamily: "var(--font-display)",
                  cursor: forcing ? "not-allowed" : "pointer",
                }}
              >
                <ShieldOff size={12} />
                {s.errors.intentional_new_btn}
              </button>
            </HelpTip>
          </div>
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
