"use client"

interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}

export function Toggle({ checked, onChange, disabled = false }: ToggleProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      style={{
        width: "32px",
        height: "18px",
        borderRadius: "9px",
        border: "none",
        background: checked ? "var(--accent)" : "var(--surface-3)",
        cursor: disabled ? "not-allowed" : "pointer",
        position: "relative",
        transition: "background 0.15s",
        flexShrink: 0,
        padding: 0,
        opacity: disabled ? 0.5 : 1,
      }}
    >
      <span style={{
        position: "absolute",
        top: "2px",
        left: checked ? "14px" : "2px",
        width: "14px",
        height: "14px",
        borderRadius: "50%",
        background: "white",
        boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
        transition: "left 0.15s",
      }} />
    </button>
  )
}
