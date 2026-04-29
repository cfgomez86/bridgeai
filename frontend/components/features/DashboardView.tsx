"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
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
  loading?: boolean
}

function KpiCard({ label, value, meta, loading }: KpiCardProps) {
  return (
    <div style={{
      padding: "18px",
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius-lg)",
    }}>
      <div style={{
        fontFamily: "var(--font-mono)", fontSize: "10px", fontWeight: 600,
        color: "var(--muted)", textTransform: "uppercase" as const,
        letterSpacing: "0.14em", marginBottom: "4px",
      }}>
        {label}
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

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([
      getDashboardStats().catch(() => null),
      getDashboardActivity(10).catch(() => []),
    ]).then(([s, a]) => {
      if (cancelled) return
      setStats(s)
      setActivity(a ?? [])
      setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [])

  const isCompletelyEmpty =
    !loading
    && stats !== null
    && stats.requirements_count === 0
    && stats.stories_count === 0
    && stats.tickets_count === 0
    && stats.feedback_total === 0
    && (activity?.length ?? 0) === 0

  const ticketsMeta = stats
    ? buildTicketsMeta(stats.tickets_by_provider, d.stats.jiraOnly, d.stats.azureOnly, d.stats.jiraAzure)
    : d.stats.jiraAzure

  const windowLabel = stats?.window_days ? d.stats.last30days : d.stats.allTime

  const approvalMeta = stats && stats.feedback_total > 0
    ? d.stats.approvalMeta.replace("{n}", String(stats.feedback_total))
    : d.stats.noFeedback

  const qualityMeta = stats && stats.quality_evaluated_count > 0
    ? d.stats.qualityMeta.replace("{n}", String(stats.quality_evaluated_count))
    : d.stats.qualityEmpty

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
          {/* Stats row 1 */}
          <div className="grid-3col" style={{ gap: "14px", marginBottom: "14px" }}>
            <KpiCard
              label={d.stats.requirements}
              value={stats ? String(stats.requirements_count) : "0"}
              meta={windowLabel}
              loading={loading}
            />
            <KpiCard
              label={d.stats.stories}
              value={stats ? String(stats.stories_count) : "0"}
              meta={windowLabel}
              loading={loading}
            />
            <KpiCard
              label={d.stats.tickets}
              value={stats ? String(stats.tickets_count) : "0"}
              meta={ticketsMeta}
              loading={loading}
            />
          </div>

          {/* Stats row 2 — feedback approval + quality avg */}
          <div className="grid-3col" style={{ gap: "14px", marginBottom: "24px" }}>
            <KpiCard
              label={d.stats.approval}
              value={stats ? formatPercent(stats.feedback_approval_rate) : "—"}
              meta={approvalMeta}
              loading={loading}
            />
            <KpiCard
              label={d.stats.quality}
              value={stats ? formatScore(stats.quality_avg_overall) : "—"}
              meta={qualityMeta}
              loading={loading}
            />
            <KpiCard
              label={d.stats.conversion}
              value={stats ? formatPercent(stats.conversion_rate) : "—"}
              meta={conversionMeta}
              loading={loading}
            />
          </div>

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
