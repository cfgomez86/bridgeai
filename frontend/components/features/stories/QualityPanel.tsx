"use client"

import { useState, useEffect } from "react"
import { ChevronDown, ChevronUp, Loader2 } from "lucide-react"
import { getStoryQuality, evaluateStoryQuality, type QualityMetricsResponse } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"

interface QualityPanelProps {
  storyId: string
}

function CitationBadge({ ratio }: { ratio: number }) {
  const pct = Math.round(ratio * 100)
  const color = pct >= 80 ? "var(--ok-fg)" : pct >= 50 ? "var(--warn-fg)" : "var(--err-fg)"
  const bg = pct >= 80 ? "var(--ok-bg)" : pct >= 50 ? "var(--warn-bg, #fffbeb)" : "var(--err-bg)"
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", padding: "1px 8px",
      borderRadius: "4px", fontSize: "11px", fontWeight: 600,
      background: bg, color,
    }}>
      {pct}%
    </span>
  )
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = (value / 10) * 100
  const color = value >= 7 ? "var(--ok-fg)" : value >= 5 ? "var(--warn-fg)" : "var(--err-fg)"
  return (
    <div style={{ marginBottom: "6px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "2px" }}>
        <span style={{ fontSize: "11.5px", color: "var(--fg-2)" }}>{label}</span>
        <span style={{ fontSize: "11.5px", fontWeight: 600, color }}>{value.toFixed(1)}/10</span>
      </div>
      <div style={{ height: "4px", background: "var(--border)", borderRadius: "2px" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: "2px" }} />
      </div>
    </div>
  )
}

export function QualityPanel({ storyId }: QualityPanelProps) {
  const [open, setOpen] = useState(false)
  const [quality, setQuality] = useState<QualityMetricsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { t } = useLanguage()
  const s = t.stories.quality

  useEffect(() => {
    if (!open || quality) return
    setLoading(true)
    getStoryQuality(storyId)
      .then(setQuality)
      .catch(err => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false))
  }, [open, storyId, quality])

  async function handleEvaluate() {
    setEvaluating(true)
    setError(null)
    try {
      const result = await evaluateStoryQuality(storyId)
      setQuality(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setEvaluating(false)
    }
  }

  const struct = quality?.structural

  return (
    <div style={{
      border: "1px solid var(--border)", borderRadius: "var(--radius)",
      background: "var(--surface)", marginTop: "8px",
    }}>
      {/* Toggle header */}
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        style={{
          width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "8px 12px", background: "transparent", border: "none",
          cursor: "pointer", color: "var(--fg-2)", fontSize: "12.5px", fontWeight: 500,
        }}
      >
        <span>{s.title}</span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {open && (
        <div style={{ padding: "0 12px 12px", borderTop: "1px solid var(--border)" }}>
          {loading && (
            <div style={{ display: "flex", alignItems: "center", gap: "6px", padding: "8px 0", color: "var(--muted)", fontSize: "12px" }}>
              <Loader2 size={13} className="animate-spin" /> {s.loading}
            </div>
          )}

          {error && (
            <div style={{ padding: "6px 8px", borderRadius: "var(--radius)", background: "var(--err-bg)", color: "var(--err-fg)", fontSize: "12px", marginTop: "8px" }}>
              {error}
            </div>
          )}

          {struct && (
            <>
              {/* Structural section */}
              <div style={{ marginTop: "10px" }}>
                <div style={{ fontSize: "10.5px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--muted)", marginBottom: "8px" }}>
                  {s.structural_title}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  <span style={{
                    display: "inline-flex", alignItems: "center", padding: "2px 8px",
                    borderRadius: "4px", fontSize: "11px", fontWeight: 600,
                    background: struct.schema_valid ? "var(--ok-bg)" : "var(--err-bg)",
                    color: struct.schema_valid ? "var(--ok-fg)" : "var(--err-fg)",
                  }}>
                    {struct.schema_valid ? s.schema_valid : s.schema_invalid}
                  </span>
                  <span style={{ display: "inline-flex", alignItems: "center", padding: "2px 8px", borderRadius: "4px", fontSize: "11px", background: "var(--surface-3)", color: "var(--fg-2)" }}>
                    {s.ac_count}: {struct.ac_count}
                  </span>
                  <span style={{ display: "inline-flex", alignItems: "center", padding: "2px 8px", borderRadius: "4px", fontSize: "11px", background: "var(--surface-3)", color: "var(--fg-2)" }}>
                    {s.subtask_count}: {struct.subtask_count}
                  </span>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: "4px", padding: "2px 8px", borderRadius: "4px", fontSize: "11px", background: "var(--surface-3)", color: "var(--fg-2)" }}>
                    {s.citation_grounding}: <CitationBadge ratio={struct.citation_grounding_ratio} />
                  </span>
                </div>
              </div>

              {/* AI Judge section */}
              <div style={{ marginTop: "14px" }}>
                <div style={{ fontSize: "10.5px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--muted)", marginBottom: "8px" }}>
                  {s.judge_title}
                </div>
                {quality?.judge ? (
                  <div>
                    <ScoreBar label={s.completeness} value={quality.judge.completeness} />
                    <ScoreBar label={s.specificity} value={quality.judge.specificity} />
                    <ScoreBar label={s.feasibility} value={quality.judge.feasibility} />
                    <ScoreBar label={s.risk_coverage} value={quality.judge.risk_coverage} />
                    <ScoreBar label={s.language_consistency} value={quality.judge.language_consistency} />
                    <div style={{ marginTop: "6px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--fg)" }}>{s.overall}: {quality.judge.overall.toFixed(1)}/10</span>
                      {quality.judge.judge_model && (
                        <span style={{ fontSize: "10.5px", color: "var(--muted)" }}>{quality.judge.judge_model}</span>
                      )}
                    </div>
                    {quality.judge.justification && (
                      <p style={{ fontSize: "11.5px", color: "var(--fg-2)", lineHeight: 1.5, marginTop: "8px", fontStyle: "italic" }}>
                        {quality.judge.justification}
                      </p>
                    )}
                  </div>
                ) : (
                  <button
                    type="button"
                    disabled={evaluating}
                    onClick={handleEvaluate}
                    style={{
                      display: "flex", alignItems: "center", gap: "6px",
                      padding: "6px 12px", borderRadius: "var(--radius)",
                      border: "1px solid var(--border)",
                      background: evaluating ? "var(--surface-3)" : "var(--surface-2)",
                      color: evaluating ? "var(--muted)" : "var(--fg-2)",
                      fontSize: "12px", cursor: evaluating ? "not-allowed" : "pointer",
                    }}
                  >
                    {evaluating && <Loader2 size={12} className="animate-spin" />}
                    {evaluating ? s.evaluating : s.evaluate_btn}
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
