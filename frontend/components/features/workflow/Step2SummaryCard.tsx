"use client"

import { Zap } from "lucide-react"
import { StepSummaryCard } from "@/components/features/StepSummaryCard"
import { RiskBadge } from "@/components/features/RiskBadge"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { chip } from "@/lib/workflow-ui"

interface Strings {
  step2_summary: string
  files: string
}

interface Props {
  state: WorkflowState
  strings: Strings
}

export function Step2SummaryCard({ state, strings: s }: Props) {
  return (
    <StepSummaryCard title={s.step2_summary} icon={<Zap size={13} />}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "16px", alignItems: "center" }}>
        {state.filesImpacted !== null && (
          <span style={{ fontSize: "12.5px", color: "var(--muted)" }}>
            {s.files} <span style={{ color: "var(--fg)", fontWeight: 600 }}>{state.filesImpacted}</span>
          </span>
        )}
        {state.riskLevel && <RiskBadge risk={state.riskLevel} />}
      </div>
      {state.modulesImpacted.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
          {state.modulesImpacted.map((m) => <span key={m} style={chip()}>{m}</span>)}
        </div>
      )}
    </StepSummaryCard>
  )
}
