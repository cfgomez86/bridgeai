import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { buttonVariants } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Zap, Database, ArrowRight, Search, GitPullRequest, Ticket } from "lucide-react"

export default function DashboardPage() {
  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-slate-500">
          Automate your requirement-to-ticket workflow with AI
        </p>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="border-indigo-200 bg-indigo-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-indigo-800">
              <Zap className="h-5 w-5" />
              Start New Story
            </CardTitle>
            <CardDescription className="text-indigo-600">
              Transform a requirement into a fully-formed user story with acceptance criteria,
              technical tasks, and story points.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              href="/workflow"
              className={cn(buttonVariants(), "bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-2")}
            >
              Launch Workflow
              <ArrowRight className="h-4 w-4" />
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5 text-slate-500" />
              Index Codebase
            </CardTitle>
            <CardDescription>
              Scan and index your source code so BridgeAI can perform accurate impact
              analysis when requirements are processed.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              href="/indexing"
              className={cn(buttonVariants({ variant: "outline" }), "flex items-center gap-2")}
            >
              Open Code Index
              <ArrowRight className="h-4 w-4" />
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Workflow explanation */}
      <div>
        <h2 className="text-xl font-semibold text-slate-800 mb-4">How it works</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 font-bold text-sm">
                  1
                </div>
                <CardTitle className="text-base">Understand</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 mb-2">
                <Search className="h-4 w-4 text-slate-400" />
              </div>
              <p className="text-sm text-slate-500">
                AI parses your requirement text to extract intent, feature type, complexity,
                and key domain terms.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 font-bold text-sm">
                  2
                </div>
                <CardTitle className="text-base">Impact</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 mb-2">
                <Database className="h-4 w-4 text-slate-400" />
              </div>
              <p className="text-sm text-slate-500">
                Cross-references your codebase index to identify affected files, modules,
                and overall risk level.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 font-bold text-sm">
                  3
                </div>
                <CardTitle className="text-base">Generate</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 mb-2">
                <GitPullRequest className="h-4 w-4 text-slate-400" />
              </div>
              <p className="text-sm text-slate-500">
                Produces a complete user story with acceptance criteria, technical tasks,
                definition of done, and story points.
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-indigo-600 font-bold text-sm">
                  4
                </div>
                <CardTitle className="text-base">Ticket</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 mb-2">
                <Ticket className="h-4 w-4 text-slate-400" />
              </div>
              <p className="text-sm text-slate-500">
                Pushes the generated story directly to Jira or Azure DevOps with a single
                click — no copy-paste needed.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
