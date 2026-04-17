import * as React from "react"
import { cn } from "@/lib/utils"

interface SeparatorProps extends React.HTMLAttributes<HTMLHRElement> {
  orientation?: "horizontal" | "vertical"
}

const Separator = React.forwardRef<HTMLHRElement, SeparatorProps>(
  ({ className, orientation = "horizontal", ...props }, ref) => (
    <hr
      ref={ref}
      className={cn(
        "shrink-0 border-slate-200 dark:border-slate-700",
        orientation === "horizontal" ? "border-t w-full my-1" : "border-l h-full mx-1",
        className
      )}
      {...props}
    />
  )
)
Separator.displayName = "Separator"

export { Separator }
