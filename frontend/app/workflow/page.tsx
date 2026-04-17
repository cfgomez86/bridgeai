"use client"

import { useWorkflow } from "@/hooks/useWorkflow"
import { WorkflowStepper } from "@/components/features/WorkflowStepper"
import { Step1Understand } from "@/components/features/steps/Step1Understand"
import { Step2Impact } from "@/components/features/steps/Step2Impact"
import { Step3Generate } from "@/components/features/steps/Step3Generate"
import { Step4Ticket } from "@/components/features/steps/Step4Ticket"

export default function WorkflowPage() {
  const workflow = useWorkflow()
  const { state } = workflow

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900">New Story</h1>
        <p className="mt-1 text-slate-500">
          Follow the steps to turn a requirement into a ready-to-create ticket
        </p>
      </div>

      {/* Stepper */}
      <WorkflowStepper currentStep={state.currentStep} />

      {/* Step content */}
      <div className="mt-6">
        {state.currentStep === 1 && (
          <Step1Understand
            state={state}
            setProjectId={workflow.setProjectId}
            setRequirementText={workflow.setRequirementText}
            completeStep1={workflow.completeStep1}
          />
        )}
        {state.currentStep === 2 && (
          <Step2Impact
            state={state}
            completeStep2={workflow.completeStep2}
          />
        )}
        {state.currentStep === 3 && (
          <Step3Generate
            state={state}
            completeStep3={workflow.completeStep3}
          />
        )}
        {state.currentStep === 4 && (
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
