"use client"

import { useLanguage } from "@/lib/i18n"

interface WorkflowStepperProps {
  currentStep: 1 | 2 | 3 | 4
}

export function WorkflowStepper({ currentStep }: WorkflowStepperProps) {
  const { t } = useLanguage()
  const s = t.workflow.stepper

  const STEPS = [
    { id: 1 as const, ...s.steps.requirement },
    { id: 2 as const, ...s.steps.impact },
    { id: 3 as const, ...s.steps.story },
    { id: 4 as const, ...s.steps.ticket },
  ]

  return (
    <>
    {/* Desktop stepper — hidden on mobile */}
    <div
      className="grid-stepper-4"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)",
        overflow: "hidden",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      {STEPS.map((step, i) => {
        const done   = step.id < currentStep
        const active = step.id === currentStep

        return (
          <div
            key={step.id}
            style={{
              padding: "14px 18px",
              borderRight: i < 3 ? "1px solid var(--border)" : undefined,
              background: active ? "var(--surface-2)" : "var(--surface)",
              position: "relative",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "5px" }}>
              <span style={{
                width: "22px",
                height: "22px",
                borderRadius: "50%",
                display: "grid",
                placeItems: "center",
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                fontWeight: 600,
                flexShrink: 0,
                background: active ? "var(--accent)" : done ? "var(--ok-fg)" : "var(--surface-3)",
                color: done || active ? "#fff" : "var(--muted)",
              }}>
                {done ? "✓" : step.id}
              </span>
              <span style={{
                fontFamily: "var(--font-display)",
                fontWeight: 600,
                fontSize: "13.5px",
                color: "var(--fg)",
              }}>
                {step.label}
              </span>
              {active && (
                <span style={{
                  marginLeft: "auto",
                  fontSize: "10.5px",
                  fontWeight: 500,
                  padding: "1px 7px",
                  borderRadius: "4px",
                  background: "var(--accent-soft)",
                  color: "var(--accent-strong)",
                  fontFamily: "var(--font-mono)",
                }}>
                  {s.current}
                </span>
              )}
            </div>
            <div style={{ fontSize: "11.5px", color: "var(--muted)" }}>{step.hint}</div>
            {active && (
              <div style={{
                position: "absolute",
                left: 0,
                bottom: 0,
                right: 0,
                height: "2px",
                background: "var(--accent)",
              }} />
            )}
          </div>
        )
      })}
    </div>

    {/* Mobile compact stepper — hidden on desktop */}
    <div className="stepper-mobile-compact">
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <span style={{
          width: "26px",
          height: "26px",
          borderRadius: "50%",
          background: "var(--accent)",
          color: "#fff",
          display: "grid",
          placeItems: "center",
          fontFamily: "var(--font-mono)",
          fontSize: "12px",
          fontWeight: 700,
          flexShrink: 0,
        }}>
          {Math.min(currentStep, STEPS.length)}
        </span>
        <div>
          <div style={{ fontFamily: "var(--font-display)", fontWeight: 600, fontSize: "14px", color: "var(--fg)" }}>
            {STEPS[Math.min(currentStep, STEPS.length) - 1]?.label}
          </div>
          <div style={{ fontFamily: "var(--font-mono)", fontSize: "11px", color: "var(--muted)", marginTop: "1px" }}>
            {s.current} · {Math.min(currentStep, STEPS.length)}/{STEPS.length}
          </div>
        </div>
      </div>
      <div style={{ display: "flex", gap: "5px", alignItems: "center" }}>
        {STEPS.map((step) => (
          <div key={step.id} style={{
            width: step.id === currentStep ? "16px" : "6px",
            height: "6px",
            borderRadius: "3px",
            background: step.id < currentStep ? "var(--ok-fg)" : step.id === currentStep ? "var(--accent)" : "var(--border-strong)",
            transition: "width 0.2s ease, background 0.2s ease",
            flexShrink: 0,
          }} />
        ))}
      </div>
    </div>
    </>
  )
}
