"use client"

import { useEffect, useState } from "react"
import {
  getIncoherentRequirements,
  type IncoherentRequirementItem,
} from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"

const PAGE_SIZE = 20

type ReasonFilter =
  | "all"
  | "non_software_request"
  | "contradictory"
  | "unintelligible"
  | "conversational"
  | "empty_intent"

type DateRange = "all" | "day" | "week" | "month"

function formatDate(iso: string): string {
  if (!iso) return ""
  const utc = iso.endsWith("Z") || iso.includes("+") || iso.includes("-", 10) ? iso : iso + "Z"
  const date = new Date(utc)
  if (Number.isNaN(date.getTime())) return ""
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function ReasonBadge({ code }: { code: string }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: "99px",
        fontSize: "11px",
        fontWeight: 600,
        background: "var(--warn-bg)",
        color: "var(--warn-fg)",
        border: "1px solid color-mix(in oklch, var(--warn-fg) 25%, transparent)",
      }}
    >
      {code}
    </span>
  )
}

export function CoherenceReview() {
  const { t } = useLanguage()
  const c = t.coherencePage

  const [filter, setFilter] = useState<ReasonFilter>("all")
  const [dateRange, setDateRange] = useState<DateRange>("all")
  const [userFilter, setUserFilter] = useState("")
  const [items, setItems] = useState<IncoherentRequirementItem[] | null>(null)
  const [total, setTotal] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)

  useEffect(() => {
    let cancelled = false
    setItems(null)
    setError(null)
    const reason = filter === "all" ? null : filter
    const range = dateRange === "all" ? null : dateRange
    const userId = userFilter.trim() || null
    getIncoherentRequirements(PAGE_SIZE, 0, reason, range, userId)
      .then((data) => {
        if (cancelled) return
        setItems(data.items)
        setTotal(data.total)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : c.error_load)
        setItems([])
      })
    return () => {
      cancelled = true
    }
  }, [filter, dateRange, userFilter, c.error_load])

  async function loadMore() {
    if (!items) return
    setLoadingMore(true)
    const reason = filter === "all" ? null : filter
    const range = dateRange === "all" ? null : dateRange
    const userId = userFilter.trim() || null
    try {
      const next = await getIncoherentRequirements(PAGE_SIZE, items.length, reason, range, userId)
      setItems([...items, ...next.items])
      setTotal(next.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : c.error_load)
    } finally {
      setLoadingMore(false)
    }
  }

  const hasMore = items !== null && items.length < total

  const FILTERS: { key: ReasonFilter; label: string }[] = [
    { key: "all", label: c.filter_all },
    { key: "non_software_request", label: c.filter_non_software },
    { key: "contradictory", label: c.filter_contradictory },
    { key: "unintelligible", label: c.filter_unintelligible },
    { key: "conversational", label: c.filter_conversational },
    { key: "empty_intent", label: c.filter_empty_intent },
  ]

  return (
    <div className="page-content" style={{ maxWidth: "900px", display: "flex", flexDirection: "column", gap: "20px" }}>
      <div>
        <h1
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "24px",
            fontWeight: 600,
            letterSpacing: "-0.02em",
            margin: "0 0 4px",
            color: "var(--fg)",
          }}
        >
          {c.title}
        </h1>
        <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)" }}>{c.subtitle}</p>
      </div>

      {/* Filter bar - Reason */}
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
        {FILTERS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            style={{
              padding: "5px 14px",
              borderRadius: "var(--radius)",
              border: "1px solid",
              borderColor: filter === key ? "var(--accent)" : "var(--border)",
              background: filter === key ? "var(--accent-soft)" : "var(--surface)",
              color: filter === key ? "var(--accent-strong)" : "var(--fg-2)",
              fontSize: "12.5px",
              fontWeight: filter === key ? 600 : 400,
              cursor: "pointer",
              fontFamily: "var(--font-display)",
              transition: "all 0.1s",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Filter bar - Date Range */}
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
        {[
          { key: "all" as DateRange, label: c.filter_date_all },
          { key: "day" as DateRange, label: c.filter_date_day },
          { key: "week" as DateRange, label: c.filter_date_week },
          { key: "month" as DateRange, label: c.filter_date_month },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setDateRange(key)}
            style={{
              padding: "5px 14px",
              borderRadius: "var(--radius)",
              border: "1px solid",
              borderColor: dateRange === key ? "var(--accent)" : "var(--border)",
              background: dateRange === key ? "var(--accent-soft)" : "var(--surface)",
              color: dateRange === key ? "var(--accent-strong)" : "var(--fg-2)",
              fontSize: "12.5px",
              fontWeight: dateRange === key ? 600 : 400,
              cursor: "pointer",
              fontFamily: "var(--font-display)",
              transition: "all 0.1s",
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Filter bar - User */}
      <input
        type="text"
        placeholder={c.filter_user_placeholder}
        value={userFilter}
        onChange={(e) => setUserFilter(e.target.value)}
        style={{
          padding: "7px 12px",
          borderRadius: "var(--radius)",
          border: "1px solid var(--border)",
          background: "var(--surface)",
          color: "var(--fg)",
          fontSize: "13px",
          fontFamily: "var(--font-display)",
          outline: "none",
          maxWidth: "300px",
        }}
      />

      {error && (
        <div
          style={{
            padding: "12px 16px",
            borderRadius: "var(--radius)",
            background: "var(--warn-bg)",
            color: "var(--warn-fg)",
            fontSize: "13px",
            border: "1px solid color-mix(in oklch, var(--warn-fg) 25%, transparent)",
          }}
        >
          {error}
        </div>
      )}

      {items === null && !error && (
        <div style={{ color: "var(--muted)", fontSize: "13px" }}>...</div>
      )}

      {items !== null && items.length === 0 && !error && (
        <div
          style={{
            background: "var(--surface)",
            border: "1px dashed var(--border)",
            borderRadius: "var(--radius-lg)",
            padding: "48px 24px",
            textAlign: "center",
            color: "var(--muted)",
            fontSize: "13px",
          }}
        >
          {c.empty}
        </div>
      )}

      {items !== null && items.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {items.map((item) => (
            <div
              key={item.id}
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-lg)",
                padding: "16px 18px",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "12px",
                  flexWrap: "wrap",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "10px",
                      fontWeight: 600,
                      color: "var(--muted)",
                      textTransform: "uppercase",
                      letterSpacing: "0.14em",
                    }}
                  >
                    {c.reason_label}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                    {item.reason_codes.map((code) => (
                      <ReasonBadge key={code} code={code} />
                    ))}
                  </div>
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    color: "var(--muted)",
                    whiteSpace: "nowrap",
                  }}
                >
                  {formatDate(item.created_at)}
                </div>
              </div>

              <div>
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    fontWeight: 600,
                    color: "var(--muted)",
                    textTransform: "uppercase" as const,
                    letterSpacing: "0.14em",
                    marginBottom: "4px",
                  }}
                >
                  {c.requirement_label}
                </div>
                <blockquote
                  style={{
                    margin: 0,
                    padding: "10px 14px",
                    background: "var(--surface-2)",
                    borderLeft: "3px solid var(--accent)",
                    borderRadius: "var(--radius)",
                    fontSize: "13px",
                    color: "var(--fg)",
                    lineHeight: 1.55,
                    whiteSpace: "pre-wrap" as const,
                  }}
                >
                  {item.requirement_text_preview}
                </blockquote>
              </div>

              {item.warning && (
                <div>
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "10px",
                      fontWeight: 600,
                      color: "var(--muted)",
                      textTransform: "uppercase" as const,
                      letterSpacing: "0.14em",
                      marginBottom: "4px",
                    }}
                  >
                    {c.warning_label}
                  </div>
                  <p
                    style={{
                      margin: 0,
                      fontSize: "12.5px",
                      color: "var(--fg-2)",
                      lineHeight: 1.5,
                    }}
                  >
                    {item.warning}
                  </p>
                </div>
              )}

              <div
                style={{
                  display: "flex",
                  gap: "16px",
                  flexWrap: "wrap",
                  fontSize: "11.5px",
                  color: "var(--muted)",
                  fontFamily: "var(--font-mono)",
                  paddingTop: "6px",
                  borderTop: "1px solid var(--border)",
                }}
              >
                <span>
                  <strong style={{ color: "var(--fg-2)" }}>{c.user_label}:</strong>{" "}
                  {item.user_email ?? item.user_id}
                </span>
                {item.project_id && (
                  <span>
                    <strong style={{ color: "var(--fg-2)" }}>{c.project_label}:</strong>{" "}
                    {item.project_id}
                  </span>
                )}
                {item.model_used && (
                  <span>
                    <strong style={{ color: "var(--fg-2)" }}>{c.model_label}:</strong>{" "}
                    {item.model_used}
                  </span>
                )}
              </div>
            </div>
          ))}

          {hasMore && (
            <button
              onClick={loadMore}
              disabled={loadingMore}
              style={{
                marginTop: "8px",
                padding: "9px 18px",
                borderRadius: "var(--radius)",
                border: "1px solid var(--border)",
                background: "var(--surface)",
                color: "var(--fg-2)",
                fontSize: "13px",
                fontWeight: 500,
                cursor: loadingMore ? "not-allowed" : "pointer",
                fontFamily: "var(--font-display)",
                alignSelf: "center",
              }}
            >
              {loadingMore ? c.loading_more : c.load_more}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
