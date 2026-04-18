interface RiskBadgeProps {
  risk: string
}

export function RiskBadge({ risk }: RiskBadgeProps) {
  const upper = risk?.toUpperCase() ?? ""

  const styles: React.CSSProperties =
    upper === "LOW"
      ? { background: "var(--ok-bg)", color: "var(--ok-fg)", border: "1px solid color-mix(in oklch, var(--ok-fg) 20%, transparent)" }
      : upper === "MEDIUM"
      ? { background: "var(--warn-bg)", color: "var(--warn-fg)", border: "1px solid color-mix(in oklch, var(--warn-fg) 20%, transparent)" }
      : upper === "HIGH"
      ? { background: "var(--err-bg)", color: "var(--err-fg)", border: "1px solid color-mix(in oklch, var(--err-fg) 20%, transparent)" }
      : { background: "var(--surface-3)", color: "var(--fg-2)", border: "1px solid transparent" }

  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "1px 8px", borderRadius: "4px",
      fontSize: "11px", fontWeight: 600,
      fontFamily: "var(--font-mono)",
      ...styles,
    }}>
      {upper || (risk ?? "UNKNOWN")}
    </span>
  )
}
