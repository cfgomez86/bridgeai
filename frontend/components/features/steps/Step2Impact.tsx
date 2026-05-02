"use client"

import { useState } from "react"
import type { CSSProperties } from "react"
import { analyzeImpact } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { StepSummaryCard } from "@/components/features/StepSummaryCard"
import { RiskBadge } from "@/components/features/RiskBadge"
import { Loader2, Zap, Search } from "lucide-react"
import { truncate } from "@/lib/workflow-ui"

const chip = (text: string, accent?: boolean): CSSProperties => ({
  display: "inline-flex", alignItems: "center",
  padding: "1px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 500,
  fontFamily: "var(--font-mono)",
  background: accent ? "var(--accent-soft)" : "var(--surface-3)",
  color: accent ? "var(--accent-strong)" : "var(--fg-2)",
  border: "1px solid transparent",
})

interface Step2Props {
  state: WorkflowState
  completeStep2: (data: {
    analysisId: string
    filesImpacted: number
    modulesImpacted: string[]
    riskLevel: string
  }) => void
}

export function Step2Impact({ state, completeStep2 }: Step2Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { t } = useLanguage()
  const s = t.workflow.step2

  async function handleAnalyze() {
    if (!state.sourceConnectionId) {
      setError(s.no_active_repo)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const result = await analyzeImpact(
        state.requirementText,
        state.projectId,
        state.sourceConnectionId,
      )
      completeStep2({
        analysisId: result.analysis_id,
        filesImpacted: result.files_impacted,
        modulesImpacted: result.modules_impacted,
        riskLevel: result.risk_level,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : s.error_generic)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
      <StepSummaryCard title={s.step1_summary} icon={<Search size={13} />}>
        <p style={{ fontSize: "12.5px", color: "var(--fg-2)", fontStyle: "italic", margin: 0 }}>
          &ldquo;{truncate(state.requirementText, 140)}&rdquo;
        </p>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center" }}>
          {state.intent && (
            <span style={{ fontSize: "11.5px", color: "var(--muted)" }}>
              {s.intent_label} <span style={{ color: "var(--fg-2)", fontWeight: 500 }}>{state.intent}</span>
            </span>
          )}
          {state.featureType && <span style={chip(state.featureType, true)}>{state.featureType}</span>}
          {state.complexity && (
            <span style={chip(`${s.complexity} ${state.complexity}`)}>
              {s.complexity} {state.complexity}
            </span>
          )}
        </div>
        {state.keywords.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
            {state.keywords.map((kw) => <span key={kw} style={chip(kw)}>{kw}</span>)}
          </div>
        )}
        {(state.coherenceModel || state.parserModel) && (
          <div style={{ display: "flex", flexDirection: "column", gap: "2px", marginTop: "2px" }}>
            {state.coherenceModel && (
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0, fontFamily: "var(--font-mono)" }}>
                {s.coherence_judge_label}: <span style={{ color: "var(--fg-2)" }}>{state.coherenceModel}</span>
              </p>
            )}
            {state.parserModel && (
              <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0, fontFamily: "var(--font-mono)" }}>
                {s.parser_label}: <span style={{ color: "var(--fg-2)" }}>{state.parserModel}</span>
              </p>
            )}
          </div>
        )}
      </StepSummaryCard>

      {/* Main card */}
      <div style={{
        background: "var(--surface)", border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-sm)",
        padding: "20px 22px", display: "flex", flexDirection: "column", gap: "16px",
      }}>
        <div>
          <h2 style={{ fontSize: "15px", fontWeight: 600, fontFamily: "var(--font-display)", margin: "0 0 4px", color: "var(--fg)" }}>
            {s.title}
          </h2>
          <p style={{ fontSize: "12.5px", color: "var(--muted)", margin: 0 }}>
            {s.description}
          </p>
        </div>

        {error && (
          <div style={{ padding: "10px 14px", borderRadius: "var(--radius)", background: "var(--err-bg)", color: "var(--err-fg)", fontSize: "12.5px" }}>
            {error}
          </div>
        )}

        {state.filesImpacted !== null && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ display: "flex", gap: "24px" }}>
              <div>
                <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: "3px" }}>
                  {s.files}
                </div>
                <div style={{ fontSize: "22px", fontWeight: 700, fontFamily: "var(--font-display)", color: "var(--fg)" }}>
                  {state.filesImpacted}
                </div>
              </div>
              {state.riskLevel && (
                <div>
                  <div style={{ fontSize: "11px", color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: "6px" }}>
                    {s.risk}
                  </div>
                  <RiskBadge risk={state.riskLevel} />
                </div>
              )}
            </div>
            {state.modulesImpacted.length > 0 && (
              <div>
                <div style={{ fontSize: "11.5px", color: "var(--muted)", marginBottom: "6px" }}>{s.affected_modules}</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
                  {state.modulesImpacted.map((m) => <span key={m} style={chip(m)}>{m}</span>)}
                </div>
              </div>
            )}
          </div>
        )}

        <button
          onClick={handleAnalyze}
          disabled={loading}
          style={{
            display: "flex", alignItems: "center", justifyContent: "center", gap: "8px",
            padding: "9px 18px", borderRadius: "var(--radius)", border: "none",
            background: loading ? "var(--surface-3)" : "var(--accent)",
            color: loading ? "var(--muted)" : "var(--accent-fg)",
            fontSize: "13px", fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
            fontFamily: "var(--font-display)",
          }}
        >
          {loading
            ? <><Loader2 size={14} className="animate-spin" /> {s.analyzing}</>
            : <><Zap size={14} /> {state.filesImpacted !== null ? s.re_analyze : s.analyze_btn} →</>
          }
        </button>
      </div>
    </div>
  )
}
