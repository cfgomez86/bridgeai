"use client"

import { useState } from "react"
import { ChevronDown, CheckCircle2 } from "lucide-react"

interface StepSummaryCardProps {
  title: string
  icon?: React.ReactNode
  children: React.ReactNode
  defaultOpen?: boolean
}

export function StepSummaryCard({ title, icon, children, defaultOpen = false }: StepSummaryCardProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2.5 px-4 py-3 text-left hover:bg-slate-100 transition-colors"
      >
        <CheckCircle2 className="h-4 w-4 flex-shrink-0 text-indigo-500" />
        {icon && <span className="flex-shrink-0 text-slate-400">{icon}</span>}
        <span className="flex-1 text-sm font-medium text-slate-700">{title}</span>
        <ChevronDown
          className={`h-4 w-4 flex-shrink-0 text-slate-400 transition-transform duration-200 ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-slate-200 space-y-3">
          {children}
        </div>
      )}
    </div>
  )
}
