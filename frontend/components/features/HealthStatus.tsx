type ServiceStatus = "healthy" | "not_configured" | "unhealthy"

function dotColor(status: ServiceStatus | undefined): string {
  if (status === "healthy") return "var(--ok-fg)"
  if (status === "not_configured") return "var(--warn-fg)"
  if (status === "unhealthy") return "var(--err-fg)"
  return "var(--muted)"
}

function statusLabel(status: ServiceStatus | undefined): string {
  if (status === "healthy") return "Healthy"
  if (status === "not_configured") return "Not configured"
  if (status === "unhealthy") return "Unhealthy"
  return "Unknown"
}

interface HealthStatusProps {
  jira?: ServiceStatus
  azureDevops?: ServiceStatus
}

export function HealthStatus({ jira, azureDevops }: HealthStatusProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {[
        { label: "Jira", status: jira },
        { label: "Azure DevOps", status: azureDevops },
      ].map(({ label, status }) => (
        <div key={label} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "12.5px" }}>
          <span style={{
            display: "inline-block", width: "8px", height: "8px",
            borderRadius: "50%", flexShrink: 0,
            background: dotColor(status),
          }} />
          <span style={{ fontWeight: 500, color: "var(--fg)" }}>{label}</span>
          <span style={{ color: "var(--muted)" }}>{statusLabel(status)}</span>
        </div>
      ))}
    </div>
  )
}
