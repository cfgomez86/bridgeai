"use client"

import { useEffect, useRef, useState } from "react"
import { useRouter } from "next/navigation"
import { ChevronDown } from "lucide-react"
import {
  getDashboardActivity,
  getDashboardStats,
  type DashboardActivityEvent,
  type DashboardStats,
} from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"

type EventTone = DashboardActivityEvent["tone"]

function EventIcon({ tone }: { tone: EventTone }) {
  return (
    <div style={{
      width: "28px", height: "28px", borderRadius: "7px", display: "grid", placeItems: "center", flexShrink: 0,
      background: tone === "ok" ? "var(--ok-bg)" : tone === "accent" ? "var(--accent-soft)" : tone === "warn" ? "var(--warn-bg)" : "var(--surface-2)",
      color: tone === "ok" ? "var(--ok-fg)" : tone === "accent" ? "var(--accent-strong)" : tone === "warn" ? "var(--warn-fg)" : "var(--fg-2)",
      border: (tone === "ok" || tone === "accent" || tone === "warn") ? "none" : "1px solid var(--border)",
    }}>
      {tone === "ok" && <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true"><path d="M20 6L9 17l-5-5"/></svg>}
      {tone === "accent" && <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true"><rect x="5" y="2" width="14" height="20" rx="2"/><path d="M9 7h6M9 11h6M9 15h4"/></svg>}
      {tone === "warn" && <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><line x1="12" y1="8" x2="12" y2="12"/><circle cx="12" cy="16" r="0.5" fill="currentColor"/></svg>}
      {tone === "neutral" && <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true"><path d="M21 2H3v16h5l3 3 3-3h7V2z"/></svg>}
    </div>
  )
}

function formatRelativeTime(iso: string): string {
  const utc = iso.endsWith("Z") || iso.includes("+") || iso.includes("-", 10) ? iso : iso + "Z"
  const diff = Math.floor((Date.now() - new Date(utc).getTime()) / 1000)
  if (diff < 0) return "ahora"
  if (diff < 60) return `hace ${diff}s`
  if (diff < 3600) return `hace ${Math.floor(diff / 60)}m`
  if (diff < 86400) return `hace ${Math.floor(diff / 3600)}h`
  return `hace ${Math.floor(diff / 86400)}d`
}

function formatPercent(value: number | null): string {
  if (value === null) return "—"
  return `${Math.round(value * 100)}%`
}

function formatScore(value: number | null): string {
  if (value === null) return "—"
  return value.toFixed(1)
}

function buildTicketsMeta(
  byProvider: Record<string, number>,
  jiraLabel: string,
  azureLabel: string,
  bothLabel: string,
): string {
  const hasJira = (byProvider.jira ?? 0) > 0
  const hasAzure = (byProvider.azure_devops ?? 0) > 0
  if (hasJira && hasAzure) return bothLabel
  if (hasJira) return jiraLabel
  if (hasAzure) return azureLabel
  return bothLabel
}

interface KpiCardProps {
  label: string
  value: string
  meta: string
  /** Optional secondary meta line. Rendered below the primary meta with a
   * subtle accent — for warnings or supplementary signals like UX smells. */
  secondaryMeta?: string
  loading?: boolean
  tooltip?: string
}

function InfoTooltip({ text }: { text: string }) {
  const [open, setOpen] = useState(false)
  const [alignRight, setAlignRight] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)

  // When opening, decide whether to anchor the popover from the left or the
  // right edge of the trigger so it stays inside the viewport on narrow
  // screens / right-edge cards.
  useEffect(() => {
    if (!open || !triggerRef.current) return
    const rect = triggerRef.current.getBoundingClientRect()
    const popoverWidth = Math.min(280, window.innerWidth * 0.8)
    const safeMargin = 16
    const overflowsRight = rect.left + popoverWidth > window.innerWidth - safeMargin
    setAlignRight(overflowsRight)
  }, [open])

  return (
    <span style={{ position: "relative", display: "inline-flex" }}>
      <button
        ref={triggerRef}
        type="button"
        aria-label={text}
        aria-expanded={open}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={(e) => { e.preventDefault(); setOpen(v => !v) }}
        style={{
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          width: "13px", height: "13px",
          padding: 0, margin: 0,
          border: `1px solid ${open ? "var(--fg-2)" : "var(--muted)"}`,
          borderRadius: "50%",
          background: "transparent",
          color: open ? "var(--fg-2)" : "var(--muted)",
          fontSize: "9px", fontFamily: "var(--font-display)", fontWeight: 600,
          cursor: "pointer", lineHeight: 1,
          transition: "color 120ms ease, border-color 120ms ease",
        }}
      >
        ?
      </button>
      {open ? (
        <span
          role="tooltip"
          style={{
            position: "absolute",
            top: "calc(100% + 6px)",
            ...(alignRight ? { right: 0, left: "auto" } : { left: 0, right: "auto" }),
            zIndex: 20,
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
        </span>
      ) : null}
    </span>
  )
}

function KpiCard({ label, value, meta, secondaryMeta, loading, tooltip }: KpiCardProps) {
  return (
    <div style={{
      padding: "18px",
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius-lg)",
      minWidth: 0,
    }}>
      <div style={{
        fontFamily: "var(--font-mono)", fontSize: "10px", fontWeight: 600,
        color: "var(--muted)", textTransform: "uppercase" as const,
        letterSpacing: "0.14em", marginBottom: "4px",
        display: "flex", alignItems: "center", gap: "6px",
      }}>
        <span>{label}</span>
        {tooltip ? <InfoTooltip text={tooltip} /> : null}
      </div>
      <div style={{
        fontFamily: "var(--font-display)", fontSize: "32px", fontWeight: 600,
        letterSpacing: "-0.02em", lineHeight: 1, color: "var(--fg)",
        opacity: loading ? 0.4 : 1,
      }}>
        {loading ? "—" : value}
      </div>
      <div style={{ fontFamily: "var(--font-mono)", fontSize: "12px", color: "var(--muted)", marginTop: "4px" }}>
        {meta}
      </div>
      {secondaryMeta ? (
        <div style={{
          fontFamily: "var(--font-mono)", fontSize: "11px",
          color: "var(--accent-strong)", marginTop: "2px",
        }}>
          {secondaryMeta}
        </div>
      ) : null}
    </div>
  )
}

function dimensionColor(v: number | null): string {
  if (v === null) return "var(--muted)"
  if (v >= 7) return "oklch(0.55 0.13 150)"
  if (v >= 5) return "oklch(0.65 0.16 75)"
  return "oklch(0.55 0.18 27)"
}

function DimensionBreakdownBody({
  dims,
}: {
  dims: Array<{ label: string; short: string; value: number | null }>
}) {
  // Below this width the radar + legend would crowd each other, so we stack:
  // chart on top (wider, centered), legend below as full-width rows.
  const STACK_BREAKPOINT = 520
  const ref = useRef<HTMLDivElement>(null)
  const [stacked, setStacked] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(entries => {
      for (const entry of entries) {
        setStacked(entry.contentRect.width < STACK_BREAKPOINT)
      }
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      style={{
        padding: "6px 14px 8px",
        borderTop: "1px solid var(--border)",
        display: stacked ? "flex" : "grid",
        flexDirection: stacked ? ("column" as const) : undefined,
        gridTemplateColumns: stacked ? undefined : "auto 1fr",
        gap: stacked ? "8px" : "60px",
        alignItems: stacked ? "stretch" : "center",
      }}
    >
      <div style={{
        display: "flex", justifyContent: "center", alignItems: "center",
      }}>
        <DimensionRadar dims={dims} />
      </div>
      <div style={{
        display: "flex", flexDirection: "column", gap: "4px", minWidth: 0,
      }}>
        {dims.map(d => {
          const color = dimensionColor(d.value)
          return (
            <div
              key={d.label}
              style={{
                display: "grid",
                gridTemplateColumns: "8px 1fr auto",
                alignItems: "center",
                gap: "8px",
                padding: "4px 6px",
                borderRadius: "6px",
              }}
            >
              <span style={{
                width: "8px", height: "8px", borderRadius: "999px",
                background: color,
              }} />
              <span style={{
                fontSize: "11.5px", color: "var(--fg-2)",
                overflow: "hidden", textOverflow: "ellipsis",
                whiteSpace: "nowrap" as const,
              }}>
                {d.label}
              </span>
              <span style={{
                fontSize: "12px", fontWeight: 700,
                fontFamily: "var(--font-mono)", color,
                fontVariantNumeric: "tabular-nums" as const,
              }}>
                {d.value !== null ? d.value.toFixed(1) : "—"}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function DimensionRadar({
  dims,
}: {
  dims: Array<{ label: string; short: string; value: number | null }>
}) {
  const N = dims.length
  const R = 70
  const angle = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / N
  const polar = (i: number, v: number): [number, number] => {
    const r = (v / 10) * R
    return [Math.cos(angle(i)) * r, Math.sin(angle(i)) * r]
  }

  const gridLevels = [0.2, 0.4, 0.6, 0.8, 1.0]
  const polyPoints = dims
    .map((d, i) => {
      const [x, y] = polar(i, d.value ?? 0)
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(" ")

  return (
    <div style={{
      width: 288, flexShrink: 0, position: "relative",
      padding: "0 10px", boxSizing: "content-box" as const,
    }}>
      <svg
        width={288}
        height={180}
        viewBox="-180 -100 320 200"
        style={{ overflow: "visible", display: "block" }}
        aria-hidden="true"
      >
        {/* Grid */}
        {gridLevels.map((scale, idx) => {
          const pts = dims
            .map((_, i) => {
              const [x, y] = polar(i, scale * 10)
              return `${x.toFixed(2)},${y.toFixed(2)}`
            })
            .join(" ")
          return (
            <polygon
              key={idx}
              points={pts}
              fill="none"
              stroke="var(--border)"
              strokeWidth={1}
              opacity={idx === gridLevels.length - 1 ? 1 : 0.7}
            />
          )
        })}

        {/* Axes */}
        {dims.map((_, i) => {
          const [x, y] = polar(i, 10)
          return (
            <line
              key={i}
              x1={0}
              y1={0}
              x2={x.toFixed(2)}
              y2={y.toFixed(2)}
              stroke="var(--border)"
              strokeWidth={1}
              strokeDasharray="2 3"
            />
          )
        })}

        {/* Data polygon */}
        <polygon
          points={polyPoints}
          fill="oklch(0.55 0.13 260 / 0.14)"
          stroke="var(--accent-strong)"
          strokeWidth={1.5}
          strokeLinejoin="round"
        />

        {/* Axis labels — name outside the chart (values shown only in legend).
            Long multi-word labels split onto two lines so they don't dominate
            the layout. */}
        {dims.map((d, i) => {
          const [x, y] = polar(i, 10)
          const dir = Math.hypot(x, y) || 1
          const LABEL_OFFSET = 14
          const lx = x + (x / dir) * LABEL_OFFSET
          const ly = y + (y / dir) * LABEL_OFFSET
          let anchor: "start" | "middle" | "end" = "middle"
          if (Math.abs(x) > 5) anchor = x > 0 ? "start" : "end"
          const isUpper = ly < 0
          const baseline: "auto" | "hanging" = isUpper ? "auto" : "hanging"
          const lineHeight = 10

          const spaceIdx = d.label.indexOf(" ")
          const wraps = d.label.length > 14 && spaceIdx !== -1
          const lines = wraps
            ? [d.label.slice(0, spaceIdx), d.label.slice(spaceIdx + 1)]
            : [d.label]
          // Stack so that the inner edge (closer to the axis) lines up with
          // where a single line would sit: for upper labels line 2 stays at
          // ly and line 1 goes above; for lower labels line 1 stays at ly and
          // line 2 goes below.
          const y1 = isUpper && lines.length > 1 ? ly - lineHeight : ly
          const y2 = isUpper ? ly : ly + lineHeight

          const textProps = {
            textAnchor: anchor,
            dominantBaseline: baseline,
            fontFamily: "var(--font-sans)",
            fontSize: 9,
            fontWeight: 600,
            letterSpacing: "0.02em",
            fill: "var(--fg-2)",
          } as const

          if (lines.length === 1) {
            return (
              <text key={i} x={lx.toFixed(2)} y={ly.toFixed(2)} {...textProps}>
                {d.label}
              </text>
            )
          }
          return (
            <g key={i}>
              <text x={lx.toFixed(2)} y={y1.toFixed(2)} {...textProps}>
                {lines[0]}
              </text>
              <text x={lx.toFixed(2)} y={y2.toFixed(2)} {...textProps}>
                {lines[1]}
              </text>
            </g>
          )
        })}

        {/* Solid dots at each vertex of the data polygon */}
        {dims.map((d, i) => {
          if (d.value === null) return null
          const [x, y] = polar(i, d.value)
          const color = dimensionColor(d.value)
          return (
            <circle
              key={i}
              cx={x.toFixed(2)}
              cy={y.toFixed(2)}
              r={3}
              fill={color}
              stroke="var(--surface)"
              strokeWidth={1.5}
            />
          )
        })}
      </svg>
    </div>
  )
}

export function DashboardView() {
  const { t } = useLanguage()
  const d = t.dashboard
  const router = useRouter()

  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [activity, setActivity] = useState<DashboardActivityEvent[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [showDimensions, setShowDimensions] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    async function fetchWithRetry() {
      for (let attempt = 0; attempt < 3; attempt++) {
        if (cancelled) return
        if (attempt > 0) await new Promise((r) => setTimeout(r, attempt * 800))
        try {
          const [s, a] = await Promise.all([
            getDashboardStats(),
            getDashboardActivity(10),
          ])
          if (cancelled) return
          setStats(s)
          setActivity(a ?? [])
          setLoading(false)
          return
        } catch {
          // retry
        }
      }
      if (!cancelled) setLoading(false)
    }

    fetchWithRetry()
    return () => { cancelled = true }
  }, [])

  const isCompletelyEmpty =
    !loading
    && stats !== null
    && stats.requirements_count === 0
    && stats.stories_count === 0
    && stats.tickets_count === 0
    && stats.feedback_total === 0
    && (activity?.length ?? 0) === 0

  // Tickets card meta: when there are failures show ✓/✗ chips (operational
  // signal); otherwise fall back to provider-info string.
  const ticketsMeta = stats && stats.tickets_failed_count > 0
    ? d.stats.ticketsMetaWithFailures
        .replace("{ok}", String(stats.tickets_count))
        .replace("{failed}", String(stats.tickets_failed_count))
    : stats
      ? buildTicketsMeta(stats.tickets_by_provider, d.stats.jiraOnly, d.stats.azureOnly, d.stats.jiraAzure)
      : d.stats.jiraAzure

  const windowLabel = stats?.window_days ? d.stats.last30days : d.stats.allTime

  const formatStageRate = (numerator: number, denominator: number): string | null => {
    if (denominator <= 0) return null
    const pct = Math.round((numerator / denominator) * 100)
    return String(pct)
  }

  const analysesRate = stats ? formatStageRate(stats.impact_analyses_count, stats.requirements_count) : null
  const storiesRate = stats ? formatStageRate(stats.stories_count, stats.impact_analyses_count) : null
  const avgGenTime = stats?.avg_generation_time_seconds ?? null
  const avgGenTimeStr = avgGenTime !== null ? avgGenTime.toFixed(1) : null

  const analysesMeta = analysesRate !== null
    ? d.stats.analysesMeta.replace("{n}", analysesRate)
    : windowLabel

  // Historias meta combines stage ratio + LLM latency depending on what's
  // available, falling back to the bare window label otherwise.
  const storiesMeta = (() => {
    if (storiesRate !== null && avgGenTimeStr !== null) {
      return d.stats.storiesMetaWithTime
        .replace("{n}", storiesRate)
        .replace("{time}", avgGenTimeStr)
    }
    if (storiesRate !== null) return d.stats.storiesMeta.replace("{n}", storiesRate)
    if (avgGenTimeStr !== null) return d.stats.storiesMetaTimeOnly.replace("{time}", avgGenTimeStr)
    return windowLabel
  })()

  const unnecessaryForceCount = stats?.unnecessary_force_count ?? 0
  const unnecessaryForceMeta = unnecessaryForceCount > 0
    ? d.stats.unnecessaryForceMeta.replace("{n}", String(unnecessaryForceCount))
    : null

  const approvalMeta = stats && stats.feedback_total > 0
    ? d.stats.approvalMetaWithCounts
        .replace("{up}", String(stats.feedback_thumbs_up))
        .replace("{down}", String(stats.feedback_thumbs_down))
    : d.stats.noFeedback

  const qualityOrganicMeta = stats && stats.quality_count_organic > 0
    ? d.stats.qualityMeta.replace("{n}", String(stats.quality_count_organic))
    : d.stats.qualityEmpty

  const qualityForcedMeta = (() => {
    if (!stats || stats.quality_count_forced === 0) return d.stats.qualityForcedEmpty
    const creation = stats.quality_count_creation_bypass
    const override = stats.quality_count_override
    if (creation > 0 && override > 0) {
      return d.stats.qualityForcedMeta
        .replace("{creation}", String(creation))
        .replace("{override}", String(override))
    }
    if (creation > 0) {
      return d.stats.qualityForcedMetaCreationOnly.replace("{n}", String(creation))
    }
    return d.stats.qualityForcedMetaOverrideOnly.replace("{n}", String(override))
  })()

  const conversionMeta = stats && stats.stories_count > 0
    ? d.stats.conversionMeta.replace("{n}", String(stats.stories_count))
    : d.stats.conversionEmpty

  const riskCounts = stats?.stories_by_risk ?? { LOW: 0, MEDIUM: 0, HIGH: 0 }
  const riskTotal = (riskCounts.LOW ?? 0) + (riskCounts.MEDIUM ?? 0) + (riskCounts.HIGH ?? 0)

  return (
    <div className="dashboard-content" style={{ maxWidth: "1080px" }}>
      {/* Quick-start hero */}
      <div style={{
        background: "linear-gradient(135deg, var(--accent-soft), color-mix(in oklch, var(--accent-soft) 50%, var(--surface-2)))",
        border: "1px solid color-mix(in oklch, var(--accent) 25%, var(--border))",
        borderRadius: "var(--radius-lg)",
        padding: "14px 18px",
        marginBottom: "16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: "16px",
        flexWrap: "wrap" as const,
      }}>
        <div style={{ minWidth: 0, flex: "1 1 auto" }}>
          <h3 style={{
            fontFamily: "var(--font-display)", fontSize: "15px", fontWeight: 600,
            letterSpacing: "-0.01em", margin: "0 0 2px", color: "var(--fg)",
          }}>
            {d.quickStartTitle}
          </h3>
          <p style={{ fontSize: "12.5px", color: "var(--fg-2)", margin: 0, lineHeight: 1.4 }}>
            {d.quickStartLead}
          </p>
        </div>
        <button
          onClick={() => router.push("/workflow")}
          style={{
            display: "inline-flex", alignItems: "center", height: "32px",
            padding: "0 14px", borderRadius: "var(--radius)", border: "none",
            background: "var(--accent)", color: "var(--accent-fg)",
            fontFamily: "var(--font-display)", fontSize: "12.5px", fontWeight: 600,
            cursor: "pointer", letterSpacing: "-0.01em", flexShrink: 0,
          }}
        >
          {d.startWorkflow}
        </button>
      </div>

      {/* Empty-state for new tenants */}
      {isCompletelyEmpty ? (
        <div style={{
          background: "var(--surface)",
          border: "1px dashed var(--border)",
          borderRadius: "var(--radius-lg)",
          padding: "48px 24px",
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "10px",
        }}>
          <div style={{ fontFamily: "var(--font-display)", fontSize: "16px", fontWeight: 600, color: "var(--fg)" }}>
            {d.empty.title}
          </div>
          <div style={{ fontSize: "13px", color: "var(--muted)", maxWidth: "420px", lineHeight: 1.5 }}>
            {d.empty.desc}
          </div>
          <button
            onClick={() => router.push("/workflow")}
            style={{
              marginTop: "8px",
              padding: "8px 18px",
              borderRadius: "var(--radius)",
              border: "none",
              background: "var(--accent)",
              color: "var(--accent-fg)",
              fontSize: "13px",
              fontWeight: 600,
              cursor: "pointer",
              fontFamily: "var(--font-display)",
            }}
          >
            {d.empty.cta}
          </button>
        </div>
      ) : (
        <>
          {/* Stats row 1 — funnel: requirements → analyses → stories → tickets */}
          {/* auto-fit + minmax keeps cards readable at any width: 4 cols on wide,
              wraps to 2 or 1 cols on narrower viewports without text overflow. */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "14px",
            marginBottom: "14px",
          }}>
            <KpiCard
              label={d.stats.requirements}
              value={stats ? String(stats.requirements_count) : "0"}
              meta={windowLabel}
              loading={loading}
            />
            <KpiCard
              label={d.stats.analyses}
              value={stats ? String(stats.impact_analyses_count) : "0"}
              meta={analysesMeta}
              loading={loading}
            />
            <KpiCard
              label={d.stats.stories}
              value={stats ? String(stats.stories_count) : "0"}
              meta={storiesMeta}
              loading={loading}
            />
            <KpiCard
              label={d.stats.tickets}
              value={stats ? String(stats.tickets_count) : "0"}
              meta={ticketsMeta}
              loading={loading}
            />
          </div>

          {/* Stats row 2 — approval (with thumbs chips) + quality split (organic vs forced) + conversion */}
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "14px",
            marginBottom: "24px",
          }}>
            <KpiCard
              label={d.stats.approval}
              value={stats ? formatPercent(stats.feedback_approval_rate) : "—"}
              meta={approvalMeta}
              loading={loading}
            />
            <KpiCard
              label={d.stats.qualityOrganic}
              value={stats ? formatScore(stats.quality_avg_organic) : "—"}
              meta={qualityOrganicMeta}
              secondaryMeta={unnecessaryForceMeta ?? undefined}
              loading={loading}
              tooltip={d.stats.qualityOrganicTooltip}
            />
            <KpiCard
              label={d.stats.qualityForced}
              value={stats ? formatScore(stats.quality_avg_forced) : "—"}
              meta={qualityForcedMeta}
              loading={loading}
              tooltip={d.stats.qualityForcedTooltip}
            />
            <KpiCard
              label={d.stats.conversion}
              value={stats ? formatPercent(stats.conversion_rate) : "—"}
              meta={conversionMeta}
              loading={loading}
            />
          </div>

          {/* Judge dimensions breakdown — collapsible. Only shown when there
              are organic stories (forced bucket has caps and would distort). */}
          {(stats?.quality_count_organic ?? 0) > 0 ? (() => {
            const dims: Array<{ label: string; short: string; value: number | null }> = [
              { label: d.stats.dimCompleteness,         short: d.stats.dimCompleteness,              value: stats?.quality_organic_avg_completeness ?? null },
              { label: d.stats.dimSpecificity,          short: d.stats.dimSpecificityShort,          value: stats?.quality_organic_avg_specificity ?? null },
              { label: d.stats.dimFeasibility,          short: d.stats.dimFeasibility,               value: stats?.quality_organic_avg_feasibility ?? null },
              { label: d.stats.dimRiskCoverage,         short: d.stats.dimRiskCoverageShort,         value: stats?.quality_organic_avg_risk_coverage ?? null },
              { label: d.stats.dimLanguageConsistency,  short: d.stats.dimLanguageConsistencyShort,  value: stats?.quality_organic_avg_language_consistency ?? null },
            ]
            return (
              <div style={{
                borderRadius: "var(--radius-lg)",
                border: "1px solid var(--border)",
                background: "var(--surface-2)",
                overflow: "hidden",
                marginBottom: "14px",
                minWidth: 0,
              }}>
                <button
                  type="button"
                  onClick={() => setShowDimensions(v => !v)}
                  aria-expanded={showDimensions}
                  aria-label={showDimensions ? d.stats.dimensionsHide : d.stats.dimensionsShow}
                  style={{
                    width: "100%",
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    padding: "10px 14px",
                    textAlign: "left",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    color: "var(--fg)",
                  }}
                >
                  <span style={{
                    flex: 1,
                    fontFamily: "var(--font-mono)", fontSize: "10px", fontWeight: 600,
                    color: "var(--muted)", textTransform: "uppercase" as const,
                    letterSpacing: "0.14em",
                  }}>
                    {d.stats.dimensionsTitle}
                  </span>
                  <ChevronDown
                    size={14}
                    style={{
                      flexShrink: 0,
                      color: "var(--muted)",
                      transform: showDimensions ? "rotate(180deg)" : "rotate(0deg)",
                      transition: "transform 0.15s",
                    }}
                  />
                </button>
                {showDimensions ? <DimensionBreakdownBody dims={dims} /> : null}
              </div>
            )
          })() : null}

          {/* Risk distribution — full width */}
          <div style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-lg)",
            padding: "16px 18px",
            marginBottom: "18px",
          }}>
            <div style={{
              fontFamily: "var(--font-mono)", fontSize: "10px", fontWeight: 600,
              color: "var(--muted)", textTransform: "uppercase" as const,
              letterSpacing: "0.14em", marginBottom: "10px",
            }}>
              {d.stats.riskTitle}
            </div>
            {riskTotal === 0 ? (
              <div style={{ fontSize: "13px", color: "var(--muted)" }}>
                {d.stats.riskEmpty}
              </div>
            ) : (
              <>
                <div style={{ display: "flex", gap: "24px", flexWrap: "wrap" as const, alignItems: "center" }}>
                  {[
                    { key: "LOW", label: d.stats.riskLow, color: "var(--ok-fg)", count: riskCounts.LOW ?? 0 },
                    { key: "MEDIUM", label: d.stats.riskMedium, color: "var(--warn-fg)", count: riskCounts.MEDIUM ?? 0 },
                    { key: "HIGH", label: d.stats.riskHigh, color: "var(--err-fg)", count: riskCounts.HIGH ?? 0 },
                  ].map(({ key, label, color, count }) => (
                    <div key={key} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{
                        width: "10px", height: "10px", borderRadius: "50%",
                        background: color, flexShrink: 0,
                      }} />
                      <span style={{
                        fontFamily: "var(--font-mono)", fontSize: "11px",
                        fontWeight: 600, color: "var(--muted)",
                        letterSpacing: "0.08em",
                      }}>
                        {label}
                      </span>
                      <span style={{
                        fontFamily: "var(--font-display)", fontSize: "18px",
                        fontWeight: 600, color: "var(--fg)", lineHeight: 1,
                      }}>
                        {count}
                      </span>
                    </div>
                  ))}
                </div>
                <div style={{
                  fontFamily: "var(--font-mono)", fontSize: "12px",
                  color: "var(--muted)", marginTop: "10px",
                }}>
                  {d.stats.riskMeta}
                </div>
              </>
            )}
          </div>

          {/* Activity — full width */}
          <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
              <h4 style={{ margin: 0, fontFamily: "var(--font-display)", fontSize: "13.5px", fontWeight: 600, color: "var(--fg)" }}>{d.activity.title}</h4>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "11.5px", color: "var(--muted)", marginLeft: "auto" }}>{d.activity.meta}</span>
            </div>
            <div>
              {loading && (
                <div style={{ padding: "20px 16px", color: "var(--muted)", fontSize: "13px" }}>...</div>
              )}
              {!loading && (activity?.length ?? 0) === 0 && (
                <div style={{ padding: "20px 16px", color: "var(--muted)", fontSize: "13px" }}>
                  {d.activity.empty}
                </div>
              )}
              {!loading && (activity ?? []).map((ev, i) => {
                const Wrapper: React.ElementType = ev.link ? "button" : "div"
                return (
                  <Wrapper
                    key={i}
                    onClick={ev.link ? () => router.push(ev.link!) : undefined}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "28px 1fr auto",
                      gap: "10px",
                      alignItems: "flex-start",
                      padding: "10px 16px",
                      borderTop: i === 0 ? "none" : "1px solid var(--border)",
                      width: "100%",
                      background: "transparent",
                      border: i === 0 ? "none" : undefined,
                      borderLeft: "none",
                      borderRight: "none",
                      borderBottom: "none",
                      cursor: ev.link ? "pointer" : "default",
                      textAlign: "left" as const,
                      fontFamily: "inherit",
                      color: "inherit",
                    }}
                  >
                    <EventIcon tone={ev.tone} />
                    <div>
                      <b style={{ fontSize: "13px", fontWeight: 500, display: "block", color: "var(--fg)" }}>{ev.title}</b>
                      <span style={{ fontSize: "11.5px", color: "var(--muted)", display: "flex", alignItems: "center", gap: "6px", marginTop: "2px" }}>
                        {ev.meta}
                        {ev.badge && (
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "10px", padding: "1px 5px", background: "var(--accent-soft)", color: "var(--accent-strong)", borderRadius: "4px" }}>{ev.badge}</span>
                        )}
                      </span>
                    </div>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--muted)", whiteSpace: "nowrap" as const, paddingTop: "4px" }}>
                      {formatRelativeTime(ev.time)}
                    </span>
                  </Wrapper>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
