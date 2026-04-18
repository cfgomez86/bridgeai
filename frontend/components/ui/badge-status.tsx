type BadgeTone = "ok" | "warn" | "err" | "accent" | "neutral"

interface BadgeStatusProps {
  tone: BadgeTone
  label: string
}

const TONE_STYLES: Record<BadgeTone, { bg: string; fg: string }> = {
  ok: { bg: "var(--ok-bg)", fg: "var(--ok-fg)" },
  warn: { bg: "var(--warn-bg)", fg: "var(--warn-fg)" },
  err: { bg: "var(--err-bg)", fg: "var(--err-fg)" },
  accent: { bg: "var(--accent-soft)", fg: "var(--accent-strong)" },
  neutral: { bg: "var(--surface-3)", fg: "var(--muted)" },
}

export function BadgeStatus({ tone, label }: BadgeStatusProps) {
  const { bg, fg } = TONE_STYLES[tone]
  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: "5px",
      background: bg,
      color: fg,
      fontSize: "11px",
      fontWeight: 500,
      padding: "2px 7px 2px 5px",
      borderRadius: "3px",
      whiteSpace: "nowrap",
    }}>
      <span style={{
        width: "5px",
        height: "5px",
        borderRadius: "50%",
        background: fg,
        flexShrink: 0,
      }} />
      {label}
    </span>
  )
}
