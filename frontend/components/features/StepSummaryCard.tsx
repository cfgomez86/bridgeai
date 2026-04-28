"use client"

import { useState } from "react"
import { ChevronDown, CheckCircle2 } from "lucide-react"

interface StepSummaryCardProps {
  title: string
  icon?: React.ReactNode
  children: React.ReactNode
  defaultOpen?: boolean
}

export function StepSummaryCard({ title, icon, children, defaultOpen = false }: StepSummaryCardProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div style={{
      borderRadius: "var(--radius-lg)",
      border: "1px solid var(--border)",
      background: "var(--surface-2)",
      overflow: "hidden",
      minWidth: 0,
    }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
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
        <CheckCircle2 size={14} style={{ flexShrink: 0, color: "var(--ok-fg)" }} />
        {icon && <span style={{ flexShrink: 0, color: "var(--muted)" }}>{icon}</span>}
        <span style={{ flex: 1, fontSize: "12.5px", fontWeight: 500, color: "var(--fg-2)" }}>{title}</span>
        <ChevronDown
          size={14}
          style={{
            flexShrink: 0,
            color: "var(--muted)",
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.15s",
          }}
        />
      </button>
      {open && (
        <div style={{
          padding: "4px 14px 14px",
          borderTop: "1px solid var(--border)",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
        }}>
          {children}
        </div>
      )}
    </div>
  )
}
