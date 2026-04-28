"use client"

import { useState, useEffect } from "react"
import { ChevronDown, ChevronUp, Loader2, HelpCircle, CheckCircle, XCircle } from "lucide-react"
import { getStoryQuality, evaluateStoryQuality, type QualityMetricsResponse } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"

interface QualityPanelProps {
  storyId: string
}

function HelpTip({ text }: { text: string }) {
  const [visible, setVisible] = useState(false)
  return (
    <span
      style={{ position: "relative", display: "inline-flex", alignItems: "center", flexShrink: 0 }}
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      <HelpCircle size={11} style={{ color: "var(--muted)", cursor: "help" }} />
      {visible && (
        <span style={{
          position: "absolute", bottom: "calc(100% + 6px)", left: "50%",
          transform: "translateX(-50%)",
          background: "var(--fg)", color: "var(--bg)",
          fontSize: "11px", lineHeight: 1.45,
          padding: "7px 10px", borderRadius: "6px",
          whiteSpace: "normal", width: "230px",
          zIndex: 200, boxShadow: "0 4px 16px rgba(0,0,0,0.25)",
          pointerEvents: "none",
        }}>
          {text}
        </span>
      )}
    </span>
  )
}

function scoreColor(v: number) {
  return v >= 7 ? "var(--ok-fg)" : v >= 5 ? "#d97706" : "var(--err-fg)"
}
function scoreBg(v: number) {
  return v >= 7 ? "var(--ok-bg)" : v >= 5 ? "#fffbeb" : "var(--err-bg)"
}

export function QualityPanel({ storyId }: QualityPanelProps) {
  const [open, setOpen] = useState(true)
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
      setQuality(await evaluateStoryQuality(storyId))
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setEvaluating(false)
    }
  }

  function scoreLabel(v: number) {
    return v >= 7 ? s.score_good : v >= 5 ? s.score_ok : s.score_low
  }

  const struct = quality?.structural

  const sectionLabel: React.CSSProperties = {
    fontSize: "10px", fontWeight: 700, textTransform: "uppercase",
    letterSpacing: "0.08em", color: "var(--muted)",
  }

  return (
    <div style={{
      border: "1px solid var(--border)", borderRadius: "var(--radius)",
      background: "var(--surface)",
    }}>
      {/* Header toggle */}
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        style={{
          width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "9px 14px", background: "transparent", border: "none",
          cursor: "pointer", color: "var(--fg-2)", fontSize: "12.5px", fontWeight: 600,
        }}
      >
        <span>{s.title}</span>
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {open && (
        <div style={{ padding: "0 14px 14px", borderTop: "1px solid var(--border)" }}>
          {loading && (
            <div style={{ display: "flex", alignItems: "center", gap: "6px", padding: "10px 0", color: "var(--muted)", fontSize: "12px" }}>
              <Loader2 size={13} className="animate-spin" /> {s.loading}
            </div>
          )}

          {error && (
            <div style={{ padding: "6px 8px", borderRadius: "var(--radius)", background: "var(--err-bg)", color: "var(--err-fg)", fontSize: "12px", marginTop: "10px" }}>
              {error}
            </div>
          )}

          {struct && (
            <>
              {/* ── Structural metrics ── */}
              <div style={{ marginTop: "12px" }}>
                <div style={{ ...sectionLabel, marginBottom: "8px" }}>{s.structural_title}</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>

                  {/* Schema valid */}
                  <span style={{
                    display: "inline-flex", alignItems: "center", gap: "5px",
                    padding: "4px 10px", borderRadius: "20px", fontSize: "12px", fontWeight: 500,
                    background: struct.schema_valid ? "var(--ok-bg)" : "var(--err-bg)",
                    color: struct.schema_valid ? "var(--ok-fg)" : "var(--err-fg)",
                    border: `1px solid ${struct.schema_valid ? "var(--ok-fg)" : "var(--err-fg)"}22`,
                  }}>
                    {struct.schema_valid
                      ? <CheckCircle size={12} />
                      : <XCircle size={12} />
                    }
                    {struct.schema_valid ? s.schema_valid : s.schema_invalid}
                    <HelpTip text={s.help.schema_valid} />
                  </span>

                  {/* AC count */}
                  <span style={{
                    display: "inline-flex", alignItems: "center", gap: "5px",
                    padding: "4px 10px", borderRadius: "20px", fontSize: "12px", fontWeight: 500,
                    background: "var(--surface-3)", color: "var(--fg-2)",
                    border: "1px solid var(--border)",
                  }}>
                    <span style={{ fontWeight: 700, color: "var(--fg)" }}>{struct.ac_count}</span>
                    {s.ac_count}
                    <HelpTip text={s.help.ac_count} />
                  </span>

                  {/* Risk notes */}
                  <span style={{
                    display: "inline-flex", alignItems: "center", gap: "5px",
                    padding: "4px 10px", borderRadius: "20px", fontSize: "12px", fontWeight: 500,
                    background: "var(--surface-3)", color: "var(--fg-2)",
                    border: "1px solid var(--border)",
                  }}>
                    <span style={{ fontWeight: 700, color: "var(--fg)" }}>{struct.risk_notes_count}</span>
                    {s.risk_notes_count}
                    <HelpTip text={s.help.risk_notes_count} />
                  </span>

                  {/* Subtask count */}
                  <span style={{
                    display: "inline-flex", alignItems: "center", gap: "5px",
                    padding: "4px 10px", borderRadius: "20px", fontSize: "12px", fontWeight: 500,
                    background: "var(--surface-3)", color: "var(--fg-2)",
                    border: "1px solid var(--border)",
                  }}>
                    <span style={{ fontWeight: 700, color: "var(--fg)" }}>{struct.subtask_count}</span>
                    {s.subtask_count}
                    <HelpTip text={s.help.subtask_count} />
                  </span>

                  {/* Citation grounding */}
                  {struct.cited_paths_total > 0 ? (
                    <span style={{
                      display: "inline-flex", alignItems: "center", gap: "5px",
                      padding: "4px 10px", borderRadius: "20px", fontSize: "12px", fontWeight: 500,
                      background: struct.citation_grounding_ratio >= 0.8 ? "var(--ok-bg)" : "var(--warn-bg, #fffbeb)",
                      color: struct.citation_grounding_ratio >= 0.8 ? "var(--ok-fg)" : "#d97706",
                      border: `1px solid ${struct.citation_grounding_ratio >= 0.8 ? "var(--ok-fg)" : "#d97706"}22`,
                    }}>
                      <span style={{ fontWeight: 700 }}>
                        {struct.cited_paths_existing}/{struct.cited_paths_total}
                      </span>
                      {s.cited_paths}
                      <HelpTip text={s.help.citation_grounding} />
                    </span>
                  ) : (
                    <span style={{
                      display: "inline-flex", alignItems: "center", gap: "5px",
                      padding: "4px 10px", borderRadius: "20px", fontSize: "12px", fontWeight: 500,
                      background: "var(--surface-3)", color: "var(--muted)",
                      border: "1px solid var(--border)",
                    }}>
                      {s.no_citations}
                      <HelpTip text={s.help.citation_grounding} />
                    </span>
                  )}
                </div>
              </div>

              {/* ── AI Judge ── */}
              <div style={{ marginTop: "16px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
                  <span style={sectionLabel}>{s.judge_title}</span>
                  {!quality?.judge && (
                    <button
                      type="button"
                      disabled={evaluating}
                      onClick={handleEvaluate}
                      style={{
                        display: "flex", alignItems: "center", gap: "5px",
                        padding: "4px 10px", borderRadius: "var(--radius)",
                        border: "1px solid var(--border)",
                        background: evaluating ? "var(--surface-3)" : "var(--surface-2)",
                        color: evaluating ? "var(--muted)" : "var(--fg-2)",
                        fontSize: "11.5px", cursor: evaluating ? "not-allowed" : "pointer",
                      }}
                    >
                      {evaluating && <Loader2 size={11} className="animate-spin" />}
                      {evaluating ? s.evaluating : s.evaluate_btn}
                    </button>
                  )}
                </div>

                {quality?.judge && (() => {
                  const j = quality.judge
                  const metrics: [string, number, string][] = [
                    [s.completeness, j.completeness, s.help.completeness],
                    [s.specificity, j.specificity, s.help.specificity],
                    [s.feasibility, j.feasibility, s.help.feasibility],
                    [s.risk_coverage, j.risk_coverage, s.help.risk_coverage],
                    [s.language_consistency, j.language_consistency, s.help.language_consistency],
                  ]
                  return (
                    <div style={{ display: "flex", flexDirection: "column", gap: "1px" }}>
                      {metrics.map(([label, value, helpText]) => (
                        <div key={label} style={{
                          display: "flex", alignItems: "center", justifyContent: "space-between",
                          padding: "6px 10px", borderRadius: "var(--radius)",
                          background: "var(--surface-2)",
                        }}>
                          <span style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "12.5px", color: "var(--fg-2)" }}>
                            {label}
                            <HelpTip text={helpText} />
                          </span>
                          <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <span style={{
                              fontSize: "13px", fontWeight: 700,
                              color: scoreColor(value),
                            }}>
                              {value.toFixed(1)}
                            </span>
                            <span style={{
                              fontSize: "10.5px", fontWeight: 600,
                              padding: "1px 7px", borderRadius: "10px",
                              background: scoreBg(value),
                              color: scoreColor(value),
                            }}>
                              {scoreLabel(value)}
                            </span>
                          </span>
                        </div>
                      ))}

                      {/* Overall */}
                      <div style={{
                        display: "flex", alignItems: "center", justifyContent: "space-between",
                        padding: "8px 10px", borderRadius: "var(--radius)", marginTop: "4px",
                        background: scoreBg(j.overall),
                        border: `1px solid ${scoreColor(j.overall)}22`,
                      }}>
                        <span style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "12.5px", fontWeight: 600, color: "var(--fg)" }}>
                          {s.overall}
                          <HelpTip text={s.help.overall} />
                        </span>
                        <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span style={{ fontSize: "15px", fontWeight: 700, color: scoreColor(j.overall) }}>
                            {j.overall.toFixed(1)}<span style={{ fontSize: "11px", fontWeight: 400, color: "var(--muted)" }}>/10</span>
                          </span>
                          <span style={{
                            fontSize: "10.5px", fontWeight: 600,
                            padding: "1px 7px", borderRadius: "10px",
                            background: scoreColor(j.overall) + "22",
                            color: scoreColor(j.overall),
                          }}>
                            {scoreLabel(j.overall)}
                          </span>
                        </span>
                      </div>

                      {j.justification && (
                        <p style={{
                          fontSize: "11.5px", color: "var(--fg-2)", lineHeight: 1.55,
                          marginTop: "8px", fontStyle: "italic", padding: "0 2px",
                        }}>
                          {j.justification}
                        </p>
                      )}
                      {j.judge_model && (
                        <span style={{ fontSize: "10px", color: "var(--muted)", marginTop: "2px" }}>
                          {j.judge_model}
                        </span>
                      )}
                    </div>
                  )
                })()}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
