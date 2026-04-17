import { cn } from "@/lib/utils"

type ServiceStatus = "healthy" | "not_configured" | "unhealthy"

interface HealthDotProps {
  status: ServiceStatus | undefined
}

function HealthDot({ status }: HealthDotProps) {
  return (
    <span
      className={cn(
        "inline-block h-2.5 w-2.5 rounded-full",
        status === "healthy" && "bg-green-500",
        status === "not_configured" && "bg-yellow-400",
        status === "unhealthy" && "bg-red-500",
        status === undefined && "bg-slate-400"
      )}
    />
  )
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
    <div className="flex flex-col gap-2 text-sm">
      <div className="flex items-center gap-2">
        <HealthDot status={jira} />
        <span className="font-medium">Jira</span>
        <span className="text-slate-500 dark:text-slate-400">{statusLabel(jira)}</span>
      </div>
      <div className="flex items-center gap-2">
        <HealthDot status={azureDevops} />
        <span className="font-medium">Azure DevOps</span>
        <span className="text-slate-500 dark:text-slate-400">{statusLabel(azureDevops)}</span>
      </div>
    </div>
  )
}
