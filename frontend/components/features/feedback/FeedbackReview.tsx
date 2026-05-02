"use client"

import { useEffect, useState } from "react"
import { getNegativeFeedback, type NegativeFeedbackItem } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"

const PAGE_SIZE = 20

type RatingFilter = "all" | "thumbs_up" | "thumbs_down"
type DateRange = "all" | "day" | "week" | "month"

function formatDate(iso: string): string {
  if (!iso) return ""
  const utc = iso.endsWith("Z") || iso.includes("+") || iso.includes("-", 10) ? iso : iso + "Z"
  const date = new Date(utc)
  if (Number.isNaN(date.getTime())) return ""
  return date.toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  })
}

function RatingBadge({ rating }: { rating: string }) {
  const isPositive = rating === "thumbs_up"
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: "4px",
      padding: "2px 8px",
      borderRadius: "99px",
      fontSize: "11px",
      fontWeight: 600,
      background: isPositive ? "var(--ok-bg, oklch(0.95 0.05 145))" : "var(--err-bg, oklch(0.95 0.05 25))",
      color: isPositive ? "var(--ok-fg, oklch(0.4 0.12 145))" : "var(--err-fg, oklch(0.45 0.15 25))",
    }}>
      {isPositive ? "👍" : "👎"}
    </span>
  )
}

export function FeedbackReview() {
  const { t } = useLanguage()
  const f = t.feedbackPage

  const [filter, setFilter] = useState<RatingFilter>("all")
  const [dateRange, setDateRange] = useState<DateRange>("all")
  const [userFilter, setUserFilter] = useState("")
  const [items, setItems] = useState<NegativeFeedbackItem[] | null>(null)
  const [total, setTotal] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)

  useEffect(() => {
    let cancelled = false
    setItems(null)
    setError(null)
    const rating = filter === "all" ? null : filter
    const range = dateRange === "all" ? null : dateRange
    const userId = userFilter.trim() || null
    getNegativeFeedback(PAGE_SIZE, 0, rating, range, userId)
      .then((data) => {
        if (cancelled) return
        setItems(data.items)
        setTotal(data.total)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(err instanceof Error ? err.message : f.error_load)
        setItems([])
      })
    return () => { cancelled = true }
  }, [filter, dateRange, userFilter, f.error_load])

  async function loadMore() {
    if (!items) return
    setLoadingMore(true)
    const rating = filter === "all" ? null : filter
    const range = dateRange === "all" ? null : dateRange
    const userId = userFilter.trim() || null
    try {
      const next = await getNegativeFeedback(PAGE_SIZE, items.length, rating, range, userId)
      setItems([...items, ...next.items])
      setTotal(next.total)
    } catch (err) {
      setError(err instanceof Error ? err.message : f.error_load)
    } finally {
      setLoadingMore(false)
    }
  }

  const hasMore = items !== null && items.length < total

  const FILTERS: { key: RatingFilter; label: string }[] = [
    { key: "all", label: f.filter_all },
    { key: "thumbs_up", label: f.filter_positive },
    { key: "thumbs_down", label: f.filter_negative },
  ]

  return (
    <div className="page-content" style={{ maxWidth: "900px", display: "flex", flexDirection: "column", gap: "20px" }}>
      <div>
        <h1 style={{
          fontFamily: "var(--font-display)", fontSize: "24px", fontWeight: 600,
          letterSpacing: "-0.02em", margin: "0 0 4px", color: "var(--fg)",
        }}>
          {f.title}
        </h1>
        <p style={{ margin: 0, fontSize: "13px", color: "var(--muted)" }}>
          {f.subtitle}
        </p>
      </div>

      {/* Filter bar - Rating */}
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
          { key: "all" as DateRange, label: f.filter_date_all },
          { key: "day" as DateRange, label: f.filter_date_day },
          { key: "week" as DateRange, label: f.filter_date_week },
          { key: "month" as DateRange, label: f.filter_date_month },
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
        placeholder={f.filter_user_placeholder}
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
        <div style={{
          padding: "12px 16px",
          borderRadius: "var(--radius)",
          background: "var(--err-bg)",
          color: "var(--err-fg)",
          fontSize: "13px",
          border: "1px solid color-mix(in oklch, var(--err-fg) 20%, transparent)",
        }}>
          {error}
        </div>
      )}

      {items === null && !error && (
        <div style={{ color: "var(--muted)", fontSize: "13px" }}>...</div>
      )}

      {items !== null && items.length === 0 && !error && (
        <div style={{
          background: "var(--surface)",
          border: "1px dashed var(--border)",
          borderRadius: "var(--radius-lg)",
          padding: "48px 24px",
          textAlign: "center",
          color: "var(--muted)",
          fontSize: "13px",
        }}>
          {f.empty}
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
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px" }}>
                <div style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "14px",
                  fontWeight: 600,
                  color: "var(--fg)",
                  letterSpacing: "-0.01em",
                  flex: 1,
                  minWidth: 0,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}>
                  {item.story_title}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", flexShrink: 0 }}>
                  <RatingBadge rating={item.rating} />
                  <div style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "11px",
                    color: "var(--muted)",
                    whiteSpace: "nowrap",
                  }}>
                    {formatDate(item.created_at)}
                  </div>
                </div>
              </div>

              {item.comment && item.comment.trim().length > 0 && (
                <>
                  <div style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "10px",
                    fontWeight: 600,
                    color: "var(--muted)",
                    textTransform: "uppercase" as const,
                    letterSpacing: "0.14em",
                  }}>
                    {f.comment_label}
                  </div>
                  <blockquote style={{
                    margin: 0,
                    padding: "10px 14px",
                    background: "var(--surface-2)",
                    borderLeft: `3px solid ${item.rating === "thumbs_up" ? "var(--ok-fg, oklch(0.55 0.14 145))" : "var(--warn-fg)"}`,
                    borderRadius: "var(--radius)",
                    fontSize: "13px",
                    color: "var(--fg)",
                    lineHeight: 1.55,
                    whiteSpace: "pre-wrap" as const,
                  }}>
                    {item.comment}
                  </blockquote>
                </>
              )}

              <div style={{ fontSize: "11.5px", color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
                {item.user_email ?? item.user_id}
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
              {loadingMore ? f.loading_more : f.load_more}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
