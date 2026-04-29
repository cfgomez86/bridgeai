"use client"

import { useState, useEffect, useRef } from "react"
import { createPortal } from "react-dom"
import { Award, Loader2, CheckCircle, XCircle, ChevronDown, Sparkles } from "lucide-react"
import { getStoryQuality, evaluateStoryQuality, type QualityMetricsResponse } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"

interface QualityPanelProps {
  storyId: string
}

function HelpTip({ text, children }: { text: string; children: React.ReactNode }) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null)
  const ref = useRef<HTMLSpanElement>(null)

  function handleEnter() {
    if (ref.current) {
      const r = ref.current.getBoundingClientRect()
      setPos({ x: r.left + r.width / 2, y: r.top - 8 })
    }
  }

  return (
    <span
      ref={ref}
      style={{ display: "inline-flex", alignItems: "center" }}
      onMouseEnter={handleEnter}
      onMouseLeave={() => setPos(null)}
    >
      <span style={{ cursor: "help", lineHeight: "inherit" }}>{children}</span>
      {pos && createPortal(
        <span style={{
          position: "fixed", left: pos.x, top: pos.y,
          transform: "translateX(-50%) translateY(-100%)",
          background: "var(--surface)", color: "var(--fg-2)",
          border: "1px solid var(--border)",
          fontSize: "11.5px", lineHeight: 1.5,
          padding: "8px 11px", borderRadius: "var(--radius)",
          whiteSpace: "normal", width: "220px",
          zIndex: 9999,
          boxShadow: "0 4px 12px oklch(0.2 0.02 260 / 0.10), 0 1px 3px oklch(0.2 0.02 260 / 0.08)",
          pointerEvents: "none",
        }}>
          {text}
        </span>,
        document.body
      )}
    </span>
  )
}

function ringColor(v: number) {
  return v >= 7 ? "oklch(0.55 0.13 150)" : v >= 5 ? "oklch(0.65 0.16 75)" : "oklch(0.55 0.18 27)"
}

// Shared neutral badge — same as ac_count / subtask_count / risk_notes_count
const neutralBadge: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", gap: 5,
  padding: "3px 9px", borderRadius: 12, fontSize: "11.5px", fontWeight: 500,
  background: "var(--surface-3)", color: "var(--fg-2)", border: "1px solid var(--border)",
}

export function QualityPanel({ storyId }: QualityPanelProps) {
  const [open, setOpen] = useState(true)
  const [quality, setQuality] = useState<QualityMetricsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [evaluated, setEvaluated] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { t } = useLanguage()
  const s = t.stories.quality

  // Auto-load structural metrics on mount
  useEffect(() => {
    setLoading(true)
    getStoryQuality(storyId)
      .then(data => {
        setQuality(data)
        if (data.judge) setEvaluated(true)
      })
      .catch(err => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false))
  }, [storyId])

  async function handleEvaluate() {
    setEvaluating(true)
    setError(null)
    try {
      const result = await evaluateStoryQuality(storyId)
      setQuality(result)
      setEvaluated(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setEvaluating(false)
    }
  }

  function scoreLabel(v: number) {
    return v >= 7 ? s.score_good : v >= 5 ? s.score_ok : s.score_low
  }

  const judge = quality?.judge
  const struct = quality?.structural

  const radius = 32
  const circ = 2 * Math.PI * radius
  const overall = judge?.overall ?? 0
  const dash = circ * (overall / 10)

  const sectionLabelStyle: React.CSSProperties = {
    fontSize: "10px", fontWeight: 700, textTransform: "uppercase",
    letterSpacing: "0.10em", color: "var(--muted)", marginBottom: 8,
  }

  const evidence = judge?.evidence ?? null
  const metrics: [string, number, string, string | null, string][] = judge ? [
    [s.completeness,         judge.completeness,         s.help.completeness,         evidence?.completeness ?? null,         "completeness"],
    [s.specificity,          judge.specificity,          s.help.specificity,          evidence?.specificity ?? null,          "specificity"],
    [s.feasibility,          judge.feasibility,          s.help.feasibility,          evidence?.feasibility ?? null,          "feasibility"],
    [s.risk_coverage,        judge.risk_coverage,        s.help.risk_coverage,        evidence?.risk_coverage ?? null,        "risk_coverage"],
    [s.language_consistency, judge.language_consistency, s.help.language_consistency, evidence?.language_consistency ?? null, "language_consistency"],
  ] : []

  const dispersion = judge?.dispersion ?? null
  const samplesUsed = judge?.samples_used ?? null
  const dispersionUnstable = dispersion != null && dispersion >= 1.0

  return (
    <div style={{
      borderRadius: "var(--radius-lg)", border: "1px solid var(--border)",
      background: "var(--surface-2)", minWidth: 0,
    }}>
      {/* ── Header: título (toggle) + botón evaluar a la derecha ── */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "10px 14px",
      }}>
        <Award size={14} style={{ flexShrink: 0, color: "var(--accent-strong)" }} />
        <span style={{ flex: 1, fontSize: "12.5px", fontWeight: 500, color: "var(--fg-2)" }}>
          {s.title}
        </span>

        {/* Botón juzgador IA — solo aparece una vez, antes del chevron */}
        {!evaluated && !loading && !evaluating && quality && (
          <button
            type="button"
            onClick={handleEvaluate}
            style={{
              display: "inline-flex", alignItems: "center", gap: 5,
              padding: "4px 10px", borderRadius: 6,
              border: "1px solid var(--border)", background: "var(--surface-2)",
              color: "var(--fg-2)", fontSize: "11.5px", fontWeight: 500,
              cursor: "pointer", flexShrink: 0,
            }}
          >
            <Sparkles size={11} style={{ color: "var(--accent-strong)" }} />
            {s.evaluate_btn}
          </button>
        )}

        {evaluating && (
          <div style={{ display: "inline-flex", alignItems: "center", gap: 5, color: "var(--muted)", fontSize: "11.5px", flexShrink: 0 }}>
            <Loader2 size={11} className="animate-spin" /> {s.loading}
          </div>
        )}

        <button
          type="button"
          onClick={() => setOpen(v => !v)}
          style={{ background: "none", border: "none", cursor: "pointer", padding: 0, display: "inline-flex", flexShrink: 0 }}
        >
          <ChevronDown
            size={14}
            style={{
              color: "var(--muted)",
              transform: open ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 0.15s",
            }}
          />
        </button>
      </div>

      {open && (
        <div style={{
          padding: "4px 14px 14px", borderTop: "1px solid var(--border)",
          display: "flex", flexDirection: "column", gap: 14,
        }}>

          {loading && (
            <div style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--muted)", fontSize: "12px" }}>
              <Loader2 size={13} className="animate-spin" /> {s.loading}
            </div>
          )}

          {error && (
            <div style={{
              padding: "6px 8px", borderRadius: "var(--radius)",
              background: "var(--err-bg)", color: "var(--err-fg)", fontSize: "12px",
            }}>
              {error}
            </div>
          )}

          {/* ── Score ring + justification ── */}
          {judge && (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: 16, alignItems: "center" }}>
                {/* Ring */}
                <div style={{ position: "relative", width: 84, height: 84, flexShrink: 0 }}>
                  <svg width="84" height="84" viewBox="0 0 84 84" style={{ transform: "rotate(-90deg)" }}>
                    <circle cx="42" cy="42" r={radius} fill="none" stroke="var(--surface-3)" strokeWidth="6" />
                    <circle
                      cx="42" cy="42" r={radius} fill="none"
                      stroke={ringColor(overall)} strokeWidth="6" strokeLinecap="round"
                      strokeDasharray={`${dash} ${circ}`}
                    />
                  </svg>
                  <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", lineHeight: 1 }}>
                      <span style={{
                        fontFamily: "var(--font-display)", fontSize: "22px", fontWeight: 700,
                        color: ringColor(overall),
                      }}>
                        {overall.toFixed(1)}
                      </span>
                      <span style={{
                        fontSize: "9px", color: "var(--muted)", marginTop: 2,
                        fontFamily: "var(--font-mono)", letterSpacing: "0.05em",
                      }}>
                        /10
                      </span>
                    </div>
                  </div>
                </div>

                {/* Label + justification */}
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
                    <span style={{
                      fontSize: "15px", fontWeight: 600,
                      fontFamily: "var(--font-display)", color: "var(--fg)",
                    }}>
                      {scoreLabel(overall)}
                    </span>
                    {judge.judge_model && (
                      <span style={{ fontSize: "11px", color: "var(--muted)" }}>· {judge.judge_model}</span>
                    )}
                    {dispersion != null && samplesUsed != null && samplesUsed > 1 && (
                      <HelpTip text={s.help.dispersion}>
                        <span style={{
                          fontSize: "11px",
                          color: dispersionUnstable ? "var(--warn-fg)" : "var(--muted)",
                          fontFamily: "var(--font-mono)",
                          cursor: "help",
                        }}>
                          · ±{dispersion.toFixed(2)} ({samplesUsed} {s.dispersion_label})
                          {dispersionUnstable ? ` — ${s.dispersion_unstable}` : ""}
                        </span>
                      </HelpTip>
                    )}
                  </div>
                  {judge.justification && (
                    <p style={{ margin: 0, fontSize: "12px", color: "var(--fg-2)", lineHeight: 1.5 }}>
                      {judge.justification}
                    </p>
                  )}
                </div>
              </div>

              {/* Divider */}
              <div style={{ height: 1, background: "var(--border)" }} />

              {/* ── Per-dimension pills ── */}
              <div>
                <div style={sectionLabelStyle}>{s.per_dimension}</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {metrics.map(([label, v, helpText, cite]) => {
                    const tipText = cite
                      ? `${helpText} — ${s.evidence_label}: "${cite}"`
                      : helpText
                    return (
                      <div
                        key={label}
                        style={{
                          display: "flex", alignItems: "center", gap: 12,
                          padding: "6px 10px", borderRadius: 6,
                          background: "var(--surface-2)", border: "1px solid var(--border)",
                        }}
                      >
                        <HelpTip text={tipText}>
                          <span style={{
                            fontSize: "11.5px",
                            color: "var(--fg-2)",
                            textDecoration: cite ? "underline dotted" : "none",
                            textDecorationColor: "var(--muted)",
                            textUnderlineOffset: 3,
                          }}>{label}</span>
                        </HelpTip>
                        <span style={{
                          fontSize: "12px", fontWeight: 700,
                          color: ringColor(v), fontFamily: "var(--font-mono)",
                        }}>
                          {v.toFixed(1)}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            </>
          )}

          {/* ── Structural ── */}
          {struct && (
            <>
              {judge && <div style={{ height: 1, background: "var(--border)" }} />}

              <div>
                <div style={sectionLabelStyle}>{s.structural_title}</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>

                  {/* Esquema válido — neutral cuando válido, rojo cuando inválido */}
                  <span style={struct.schema_valid ? neutralBadge : {
                    ...neutralBadge,
                    background: "var(--err-bg)", color: "var(--err-fg)", border: "1px solid transparent",
                  }}>
                    {struct.schema_valid ? <CheckCircle size={11} /> : <XCircle size={11} />}
                    <HelpTip text={s.help.schema_valid}>
                      {struct.schema_valid ? s.schema_valid : s.schema_invalid}
                    </HelpTip>
                  </span>

                  <span style={neutralBadge}>
                    <span style={{ fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--fg)" }}>
                      {struct.ac_count}
                    </span>
                    <HelpTip text={s.help.ac_count}>{s.ac_count}</HelpTip>
                  </span>

                  <span style={neutralBadge}>
                    <span style={{ fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--fg)" }}>
                      {struct.subtask_count}
                    </span>
                    <HelpTip text={s.help.subtask_count}>{s.subtask_count}</HelpTip>
                  </span>

                  <span style={neutralBadge}>
                    <span style={{ fontWeight: 700, fontFamily: "var(--font-mono)", color: "var(--fg)" }}>
                      {struct.risk_notes_count}
                    </span>
                    <HelpTip text={s.help.risk_notes_count}>{s.risk_notes_count}</HelpTip>
                  </span>

                  {/* Archivos en repo — neutral cuando está bien, warn cuando grounding bajo */}
                  {struct.cited_paths_total > 0 ? (
                    <span style={struct.citation_grounding_ratio >= 0.8 ? neutralBadge : {
                      ...neutralBadge,
                      background: "var(--warn-bg)", color: "var(--warn-fg)", border: "1px solid transparent",
                    }}>
                      <span style={{ fontWeight: 700, fontFamily: "var(--font-mono)" }}>
                        {struct.cited_paths_existing}/{struct.cited_paths_total}
                      </span>
                      <HelpTip text={s.help.citation_grounding}>{s.cited_paths}</HelpTip>
                    </span>
                  ) : (
                    <span style={neutralBadge}>
                      <HelpTip text={s.help.citation_grounding}>{s.no_citations}</HelpTip>
                    </span>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
