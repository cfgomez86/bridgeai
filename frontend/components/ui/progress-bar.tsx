interface ProgressBarProps {
  value: number
  tone?: "ok" | "warn" | "neutral"
}

export function ProgressBar({ value, tone }: ProgressBarProps) {
  const fill =
    tone === "ok" ? "var(--ok-fg)" :
    tone === "warn" ? "var(--warn-fg)" :
    "var(--accent)"
  return (
    <div style={{ height: "4px", background: "var(--surface-3)", borderRadius: "2px", overflow: "hidden", flex: 1 }}>
      <div style={{ height: "100%", width: `${Math.min(100, Math.max(0, value))}%`, background: fill, borderRadius: "2px" }} />
    </div>
  )
}
