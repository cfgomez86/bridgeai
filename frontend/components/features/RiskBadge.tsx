import { Badge } from "@/components/ui/badge"

interface RiskBadgeProps {
  risk: string
  className?: string
}

export function RiskBadge({ risk, className }: RiskBadgeProps) {
  const upper = risk?.toUpperCase() ?? ""

  if (upper === "LOW") {
    return (
      <Badge variant="success" className={className}>
        LOW
      </Badge>
    )
  }
  if (upper === "MEDIUM") {
    return (
      <Badge variant="warning" className={className}>
        MEDIUM
      </Badge>
    )
  }
  if (upper === "HIGH") {
    return (
      <Badge variant="destructive" className={className}>
        HIGH
      </Badge>
    )
  }

  return (
    <Badge variant="secondary" className={className}>
      {risk ?? "UNKNOWN"}
    </Badge>
  )
}
