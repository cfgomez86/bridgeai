import { Check } from "lucide-react"
import { cn } from "@/lib/utils"

interface WorkflowStepperProps {
  currentStep: 1 | 2 | 3 | 4
}

const steps = [
  { id: 1, label: "Requirement" },
  { id: 2, label: "Impact" },
  { id: 3, label: "Story" },
  { id: 4, label: "Ticket" },
]

export function WorkflowStepper({ currentStep }: WorkflowStepperProps) {
  return (
    <div className="flex items-center w-full">
      {steps.map((step, index) => {
        const isDone = step.id < currentStep
        const isActive = step.id === currentStep
        const isPending = step.id > currentStep
        const isLast = index === steps.length - 1

        return (
          <div key={step.id} className="flex items-center flex-1 last:flex-none">
            {/* Step circle + label */}
            <div className="flex flex-col items-center gap-1.5">
              <div
                className={cn(
                  "flex h-9 w-9 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors",
                  isDone &&
                    "border-indigo-600 bg-indigo-600 text-white",
                  isActive &&
                    "border-indigo-600 bg-white text-indigo-600 dark:bg-slate-900",
                  isPending &&
                    "border-slate-300 bg-white text-slate-400 dark:border-slate-600 dark:bg-slate-900"
                )}
              >
                {isDone ? <Check className="h-4 w-4" /> : step.id}
              </div>
              <span
                className={cn(
                  "text-xs font-medium whitespace-nowrap",
                  isActive && "text-indigo-600",
                  isDone && "text-slate-700 dark:text-slate-300",
                  isPending && "text-slate-400"
                )}
              >
                {step.label}
              </span>
            </div>

            {/* Connector line */}
            {!isLast && (
              <div
                className={cn(
                  "flex-1 h-0.5 mx-2 mb-5 transition-colors",
                  isDone ? "bg-indigo-600" : "bg-slate-200 dark:bg-slate-700"
                )}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}
