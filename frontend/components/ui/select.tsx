import * as React from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

// ─── Context ───────────────────────────────────────────────────────────────

interface SelectContextValue {
  value: string
  onValueChange: (value: string) => void
  open: boolean
  setOpen: (open: boolean) => void
}

const SelectContext = React.createContext<SelectContextValue>({
  value: "",
  onValueChange: () => {},
  open: false,
  setOpen: () => {},
})

// ─── Select root ────────────────────────────────────────────────────────────

interface SelectProps {
  value?: string
  defaultValue?: string
  onValueChange?: (value: string) => void
  children: React.ReactNode
}

function Select({ value, defaultValue = "", onValueChange, children }: SelectProps) {
  const [internalValue, setInternalValue] = React.useState(defaultValue)
  const [open, setOpen] = React.useState(false)
  const controlled = value !== undefined
  const currentValue = controlled ? value : internalValue

  function handleChange(v: string) {
    if (!controlled) setInternalValue(v)
    onValueChange?.(v)
    setOpen(false)
  }

  return (
    <SelectContext.Provider value={{ value: currentValue, onValueChange: handleChange, open, setOpen }}>
      <div className="relative">{children}</div>
    </SelectContext.Provider>
  )
}

// ─── SelectTrigger ──────────────────────────────────────────────────────────

interface SelectTriggerProps {
  id?: string
  className?: string
  children?: React.ReactNode
}

function SelectTrigger({ id, className, children }: SelectTriggerProps) {
  const { open, setOpen } = React.useContext(SelectContext)
  return (
    <button
      id={id}
      type="button"
      onClick={() => setOpen(!open)}
      className={cn(
        "flex h-10 w-full items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-2 text-sm",
        "ring-offset-white focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-2",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
    >
      {children}
      <ChevronDown className="h-4 w-4 opacity-50 shrink-0" />
    </button>
  )
}

// ─── SelectValue ────────────────────────────────────────────────────────────

interface SelectValueProps {
  placeholder?: string
  labelMap?: Record<string, string>
}

function SelectValue({ placeholder, labelMap }: SelectValueProps) {
  const { value } = React.useContext(SelectContext)
  if (!value) return <span className="text-slate-400">{placeholder}</span>
  const label = labelMap?.[value] ?? value
  return <span>{label}</span>
}

// ─── SelectContent ──────────────────────────────────────────────────────────

function SelectContent({ children }: { children: React.ReactNode }) {
  const { open } = React.useContext(SelectContext)
  if (!open) return null
  return (
    <div className="absolute z-50 mt-1 w-full rounded-md border border-slate-200 bg-white shadow-md">
      <div className="py-1">{children}</div>
    </div>
  )
}

// ─── SelectItem ─────────────────────────────────────────────────────────────

interface SelectItemProps {
  value: string
  children: React.ReactNode
  className?: string
}

function SelectItem({ value, children, className }: SelectItemProps) {
  const { value: selected, onValueChange } = React.useContext(SelectContext)
  return (
    <div
      role="option"
      aria-selected={selected === value}
      onClick={() => onValueChange(value)}
      className={cn(
        "relative flex cursor-pointer select-none items-center rounded-sm px-3 py-2 text-sm outline-none",
        "hover:bg-slate-100",
        selected === value && "bg-indigo-50 font-medium text-indigo-700",
        className
      )}
    >
      {children}
    </div>
  )
}

export { Select, SelectTrigger, SelectValue, SelectContent, SelectItem }
