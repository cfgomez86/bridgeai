"use client"

import { Search } from "lucide-react"
import { StepSummaryCard } from "@/components/features/StepSummaryCard"
import type { WorkflowState } from "@/hooks/useWorkflow"
import { truncate, chip } from "@/lib/workflow-ui"

interface Strings {
  step1_summary: string
  complexity: string
  lang_label: string
  intent_label: string
  coherence_judge_label: string
  parser_label: string
}

interface Props {
  state: WorkflowState
  strings: Strings
  showKeywords?: boolean
}

export function Step1SummaryCard({ state, strings: s, showKeywords = true }: Props) {
  return (
    <StepSummaryCard title={s.step1_summary} icon={<Search size={13} />}>
      <p style={{ fontSize: "12.5px", color: "var(--fg-2)", fontStyle: "italic", margin: 0 }}>
        &ldquo;{truncate(state.requirementText, 120)}&rdquo;
      </p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center" }}>
        {state.featureType && <span style={chip()}>{state.featureType}</span>}
        {state.complexity && <span style={chip()}>{s.complexity} {state.complexity}</span>}
        {state.language && <span style={chip()}>{s.lang_label} {state.language}</span>}
      </div>
      {state.intent && (
        <p style={{ fontSize: "11.5px", color: "var(--muted)", margin: 0 }}>
          {s.intent_label} <span style={{ color: "var(--fg-2)", fontWeight: 500 }}>{state.intent}</span>
        </p>
      )}
      {showKeywords && state.keywords.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "5px" }}>
          {state.keywords.map((kw) => <span key={kw} style={chip()}>{kw}</span>)}
        </div>
      )}
      {(state.coherenceModel || state.parserModel) && (
        <div style={{ display: "flex", flexDirection: "column", gap: "2px", marginTop: "2px" }}>
          {state.coherenceModel && (
            <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0, fontFamily: "var(--font-mono)" }}>
              {s.coherence_judge_label}: <span style={{ color: "var(--fg-2)" }}>{state.coherenceModel}</span>
            </p>
          )}
          {state.parserModel && (
            <p style={{ fontSize: "11px", color: "var(--muted)", margin: 0, fontFamily: "var(--font-mono)" }}>
              {s.parser_label}: <span style={{ color: "var(--fg-2)" }}>{state.parserModel}</span>
            </p>
          )}
        </div>
      )}
    </StepSummaryCard>
  )
}
