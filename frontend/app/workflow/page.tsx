"use client"

import { useWorkflow } from "@/hooks/useWorkflow"
import { useLanguage } from "@/lib/i18n"
import { WorkflowStepper } from "@/components/features/WorkflowStepper"
import { Step1Understand } from "@/components/features/steps/Step1Understand"
import { Step2Impact } from "@/components/features/steps/Step2Impact"
import { Step3Generate } from "@/components/features/steps/Step3Generate"
import { Step4Ticket } from "@/components/features/steps/Step4Ticket"

export default function WorkflowPage() {
  const workflow = useWorkflow()
  const { state } = workflow
  const { t } = useLanguage()
  const w = t.workflow

  return (
    <div style={{ padding: "28px 32px", maxWidth: "900px", display: "flex", flexDirection: "column", gap: "24px" }}>
      <div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
          <span style={{ fontFamily: "var(--font-mono)", color: "var(--muted)", fontSize: "12px" }}>
            REQ-NEW
          </span>
          <span style={{
            fontSize: "10.5px", fontWeight: 500, padding: "1px 7px", borderRadius: "4px",
            background: "var(--accent-soft)", color: "var(--accent-strong)", fontFamily: "var(--font-mono)",
          }}>
            {w.step_prefix} {Math.min(state.currentStep, 4)} {w.step_of} 4
          </span>
        </div>
        <h1 style={{
          fontSize: "20px", fontWeight: 700, fontFamily: "var(--font-display)",
          color: "var(--fg)", margin: 0, letterSpacing: "-0.01em",
        }}>
          {state.requirementText
            ? state.requirementText.length > 72
              ? state.requirementText.slice(0, 72) + "…"
              : state.requirementText
            : w.new_requirement}
        </h1>
        <p style={{ fontSize: "13px", color: "var(--muted)", marginTop: "4px", marginBottom: 0 }}>
          {w.subtitle}
        </p>
      </div>

      <WorkflowStepper currentStep={state.currentStep} />

      <div>
        {state.currentStep === 1 && (
          <Step1Understand
            state={state}
            setProjectId={workflow.setProjectId}
            setRequirementText={workflow.setRequirementText}
            setLanguage={workflow.setLanguage}
            completeStep1={workflow.completeStep1}
          />
        )}
        {state.currentStep === 2 && (
          <Step2Impact state={state} completeStep2={workflow.completeStep2} />
        )}
        {state.currentStep === 3 && (
          <Step3Generate state={state} completeStep3={workflow.completeStep3} />
        )}
        {state.currentStep >= 4 && (
          <Step4Ticket
            state={state}
            completeStep4={workflow.completeStep4}
            reset={workflow.reset}
          />
        )}
      </div>
    </div>
  )
}
