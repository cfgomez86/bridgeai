"use client"

import Link from "next/link"
import { useLanguage } from "@/lib/i18n"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Zap, Database, ArrowRight, Search, GitPullRequest, Ticket } from "lucide-react"

export function DashboardView() {
  const { t } = useLanguage()
  const d = t.dashboard

  const steps = [
    { num: "1", icon: <Search className="h-4 w-4 text-slate-400" />, ...d.steps.understand },
    { num: "2", icon: <Database className="h-4 w-4 text-slate-400" />, ...d.steps.impact },
    { num: "3", icon: <GitPullRequest className="h-4 w-4 text-slate-400" />, ...d.steps.generate },
    { num: "4", icon: <Ticket className="h-4 w-4 text-slate-400" />, ...d.steps.ticket },
  ]

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-3xl font-bold" style={{ color: "var(--fg)" }}>{d.title}</h1>
        <p className="mt-1" style={{ color: "var(--muted)" }}>{d.subtitle}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card style={{ borderColor: "var(--accent-soft)", background: "var(--accent-soft)" }}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2" style={{ color: "var(--accent-strong)" }}>
              <Zap className="h-5 w-5" />
              {d.start_story.title}
            </CardTitle>
            <CardDescription style={{ color: "var(--accent)" }}>
              {d.start_story.description}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              href="/workflow"
              className={cn(buttonVariants(), "flex items-center gap-2")}
              style={{ background: "var(--accent)", color: "var(--accent-fg)" }}
            >
              {d.start_story.btn}
              <ArrowRight className="h-4 w-4" />
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2" style={{ color: "var(--fg)" }}>
              <Database className="h-5 w-5" style={{ color: "var(--muted)" }} />
              {d.index_code.title}
            </CardTitle>
            <CardDescription style={{ color: "var(--muted)" }}>
              {d.index_code.description}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              href="/indexing"
              className={cn(buttonVariants({ variant: "outline" }), "flex items-center gap-2")}
            >
              {d.index_code.btn}
              <ArrowRight className="h-4 w-4" />
            </Link>
          </CardContent>
        </Card>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4" style={{ color: "var(--fg)" }}>
          {d.how_it_works}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {steps.map(({ num, icon, title, description }) => (
            <Card key={num}>
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <div
                    className="flex h-8 w-8 items-center justify-center rounded-full font-bold text-sm"
                    style={{ background: "var(--accent-soft)", color: "var(--accent-strong)" }}
                  >
                    {num}
                  </div>
                  <CardTitle className="text-base" style={{ color: "var(--fg)" }}>{title}</CardTitle>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2 mb-2">{icon}</div>
                <p className="text-sm" style={{ color: "var(--muted)" }}>{description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
