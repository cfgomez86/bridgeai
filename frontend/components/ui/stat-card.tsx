interface StatCardProps {
  label: string
  value: string
  delta: string
  tone?: "ok" | "warn" | ""
}

export function StatCard({ label, value, delta, tone = "" }: StatCardProps) {
  const deltaColor =
    tone === "ok" ? "var(--ok-fg)" :
    tone === "warn" ? "var(--warn-fg)" :
    "var(--muted)"

  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius-lg)",
      padding: "16px 18px",
      boxShadow: "var(--shadow-sm)",
    }}>
      <div style={{
        fontSize: "10px",
        fontWeight: 600,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: "var(--muted)",
        fontFamily: "var(--font-mono)",
        marginBottom: "6px",
      }}>
        {label}
      </div>
      <div style={{
        fontSize: "24px",
        fontWeight: 700,
        fontFamily: "var(--font-display)",
        color: "var(--fg)",
        lineHeight: 1.1,
        marginBottom: "4px",
        letterSpacing: "-0.02em",
      }}>
        {value}
      </div>
      <div style={{
        fontSize: "11px",
        fontFamily: "var(--font-mono)",
        color: deltaColor,
      }}>
        {delta}
      </div>
    </div>
  )
}
