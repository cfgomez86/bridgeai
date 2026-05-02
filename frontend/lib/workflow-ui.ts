import type { CSSProperties } from "react"

export const truncate = (text: string, max: number) =>
  text.length > max ? text.slice(0, max) + "…" : text

export const chip = (): CSSProperties => ({
  display: "inline-flex", alignItems: "center",
  padding: "1px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 500,
  fontFamily: "var(--font-mono)",
  background: "var(--surface-3)", color: "var(--fg-2)",
  border: "1px solid transparent",
})
