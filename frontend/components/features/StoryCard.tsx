import { FileText, CheckCircle, Code, ListChecks } from "lucide-react"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { RiskBadge } from "@/components/features/RiskBadge"

interface StoryCardProps {
  title: string
  story_description: string
  acceptance_criteria: string[]
  technical_tasks: string[]
  definition_of_done: string[]
  story_points: number
  risk_level: string
  risk_notes?: string[]
}

export function StoryCard({
  title,
  story_description,
  acceptance_criteria,
  technical_tasks,
  definition_of_done,
  story_points,
  risk_level,
  risk_notes,
}: StoryCardProps) {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-xl">{title}</CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Description */}
        <section>
          <div className="flex items-center gap-2 mb-2">
            <FileText className="h-4 w-4 text-slate-500" />
            <h4 className="font-semibold text-sm uppercase tracking-wide text-slate-500">
              Description
            </h4>
          </div>
          <p className="text-sm leading-relaxed">{story_description}</p>
        </section>

        <Separator />

        {/* Acceptance Criteria */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle className="h-4 w-4 text-slate-500" />
            <h4 className="font-semibold text-sm uppercase tracking-wide text-slate-500">
              Acceptance Criteria
            </h4>
          </div>
          <ol className="space-y-1.5 list-none pl-0">
            {acceptance_criteria.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="flex-shrink-0 inline-flex items-center justify-center h-5 w-5 rounded-full bg-slate-100 dark:bg-slate-800 text-xs font-medium">
                  {i + 1}
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ol>
        </section>

        <Separator />

        {/* Technical Tasks */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Code className="h-4 w-4 text-slate-500" />
            <h4 className="font-semibold text-sm uppercase tracking-wide text-slate-500">
              Technical Tasks
            </h4>
          </div>
          <ul className="space-y-1.5">
            {technical_tasks.map((task, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="mt-0.5 h-4 w-4 flex-shrink-0 rounded border border-slate-300 dark:border-slate-600" />
                <span>{task}</span>
              </li>
            ))}
          </ul>
        </section>

        <Separator />

        {/* Definition of Done */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <ListChecks className="h-4 w-4 text-slate-500" />
            <h4 className="font-semibold text-sm uppercase tracking-wide text-slate-500">
              Definition of Done
            </h4>
          </div>
          <ul className="space-y-1.5">
            {definition_of_done.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="mt-0.5 h-4 w-4 flex-shrink-0 rounded border border-slate-300 dark:border-slate-600" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* Risk Notes (optional) */}
        {risk_notes && risk_notes.length > 0 && (
          <>
            <Separator />
            <section>
              <h4 className="font-semibold text-sm uppercase tracking-wide text-amber-600 mb-2">
                Risk Notes
              </h4>
              <ul className="space-y-1.5">
                {risk_notes.map((note, i) => (
                  <li key={i} className="text-sm text-amber-700 dark:text-amber-400">
                    {note}
                  </li>
                ))}
              </ul>
            </section>
          </>
        )}
      </CardContent>

      <CardFooter className="gap-3 flex-wrap">
        <Badge variant="secondary">
          {story_points} {story_points === 1 ? "point" : "points"}
        </Badge>
        <RiskBadge risk={risk_level} />
      </CardFooter>
    </Card>
  )
}
