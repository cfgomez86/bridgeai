"use client"

import { useState, useEffect } from "react"
import { getSystemQuality, type SystemQualityResponse } from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"

export function SystemQualityBadge() {
  const [data, setData] = useState<SystemQualityResponse | null>(null)
  const [showTooltip, setShowTooltip] = useState(false)
  const { t } = useLanguage()
  const s = t.stories.system_quality

  useEffect(() => {
    getSystemQuality()
      .then(res => {
        if (res.status === "ok") setData(res)
      })
      .catch(() => {/* silent */})
  }, [])

  if (!data || data.status !== "ok" || !data.data) return null

  const rawRecall = data.data.overall_recall
  const recall = typeof rawRecall === "number" ? rawRecall : null
  const pct = recall !== null ? Math.round(recall * 100) : null

  const datasetSize = data.data.dataset_size
  const timestamp = data.data.timestamp

  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <button
        type="button"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onClick={() => setShowTooltip(v => !v)}
        style={{
          display: "inline-flex", alignItems: "center", gap: "5px",
          padding: "3px 10px", borderRadius: "12px",
          border: "1px solid var(--border)", background: "var(--surface-2)",
          color: "var(--fg-2)", fontSize: "11.5px", cursor: "pointer",
          fontWeight: 500,
        }}
      >
        {pct !== null
          ? s.precision_label.replace("{pct}", String(pct))
          : s.evaluated_label}
      </button>

      {showTooltip && (
        <div style={{
          position: "absolute", top: "calc(100% + 6px)", left: 0, zIndex: 10,
          background: "var(--surface)", border: "1px solid var(--border)",
          borderRadius: "var(--radius)", padding: "10px 14px", boxShadow: "var(--shadow-sm)",
          minWidth: "200px", fontSize: "12px", color: "var(--fg-2)",
        }}>
          {datasetSize !== undefined && (
            <div>{s.dataset_size}: <strong>{String(datasetSize)}</strong></div>
          )}
          {typeof timestamp === "string" && (
            <div style={{ marginTop: "4px" }}>
              {s.evaluated_at}: <strong>{new Date(timestamp).toLocaleDateString()}</strong>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
