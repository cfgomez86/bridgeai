"use client"

import React, { useState, useEffect, useCallback, useRef, Suspense } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { useUser } from "@auth0/nextjs-auth0/client"
import {
  listPlatforms, listConnections,
  type PlatformResponse, type ConnectionResponse,
} from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"
import { ConnectionCard } from "@/components/features/connections/ConnectionCard"
import { PatHelpDrawer } from "@/components/features/connections/PatHelpDrawer"
import { PlatformCard } from "@/components/features/connections/PlatformCard"

const PLATFORM_LABELS: Record<string, string> = {
  github: "GitHub",
  gitlab: "GitLab",
  azure_devops: "Azure Repos",
  bitbucket: "Bitbucket",
}

const SCM_PLATFORMS = new Set(["github", "gitlab", "azure_devops", "bitbucket"])

// Shown immediately on paint — server_configured updates after the API responds
const STATIC_PLATFORMS: PlatformResponse[] = [
  { platform: "github",       label: "GitHub",       server_configured: false },
  { platform: "gitlab",       label: "GitLab",       server_configured: false },
  { platform: "azure_devops", label: "Azure Repos",  server_configured: false },
  { platform: "bitbucket",    label: "Bitbucket",    server_configured: false },
]

const SECTION_LABEL_STYLE: React.CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  color: "var(--fg-2)",
  margin: 0,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  fontFamily: "var(--font-mono)",
}

function ConnectionsContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const { user, isLoading } = useUser()
  const isLoaded = !isLoading
  const isSignedIn = !!user
  const [platforms, setPlatforms] = useState<PlatformResponse[]>(STATIC_PLATFORMS)
  const [connections, setConnections] = useState<ConnectionResponse[]>([])
  const [toast, setToast] = useState<{ msg: string; tone: "ok" | "err" } | null>(null)
  const [activeSection, setActiveSection] = useState("repositorios")
  const [helpPlatform, setHelpPlatform] = useState<string | null>(null)
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const refreshingRef = useRef(false)
  const { t } = useLanguage()
  const s = t.connections

  const refresh = useCallback(async () => {
    if (refreshingRef.current) return
    refreshingRef.current = true
    try {
      const [p, c] = await Promise.all([listPlatforms(), listConnections()])
      setPlatforms(p)
      setConnections(c)
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load connections"
      console.error("[Connections] Error loading platforms/connections:", err)
      setToast({ msg: `Error al cargar: ${message}`, tone: "err" })
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
      toastTimerRef.current = setTimeout(() => setToast(null), 5000)
    } finally {
      refreshingRef.current = false
    }
  }, [])

  useEffect(() => { if (isLoaded && isSignedIn) refresh() }, [refresh, isLoaded, isSignedIn])

  useEffect(() => {
    const connected = searchParams.get("connected")
    const error = searchParams.get("error")
    if (!connected && !error) return

    router.replace("/connections", { scroll: false })

    if (connected) {
      if (!SCM_PLATFORMS.has(connected)) setActiveSection("herramientas")
      if (isLoaded && isSignedIn) refresh()
    } else if (error) {
      setToast({ msg: `${s.toast_error} ${PLATFORM_LABELS[error] ?? error}`, tone: "err" })
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
      toastTimerRef.current = setTimeout(() => setToast(null), 6000)
    }
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    }
  }, [searchParams, router, refresh, isLoaded, isSignedIn, s.toast_connected, s.toast_error])

  const NAV_ITEMS = [
    { id: "repositorios", label: s.sections.repositories },
    { id: "herramientas", label: s.sections.management_tools },
  ]

  return (
    <>
      {/* Toast — fixed position, independent of layout */}
      {toast && (
        <div style={{
          position: "fixed",
          top: "64px",
          right: "16px",
          zIndex: 50,
          background: toast.tone === "ok" ? "var(--ok-bg)" : "var(--err-bg)",
          color: toast.tone === "ok" ? "var(--ok-fg)" : "var(--err-fg)",
          padding: "10px 16px",
          borderRadius: "var(--radius)",
          border: `1px solid ${toast.tone === "ok" ? "var(--ok-fg)" : "var(--err-fg)"}`,
          fontSize: "13px",
          fontWeight: 500,
          boxShadow: "var(--shadow-sm)",
          maxWidth: "320px",
        }}>
          {toast.msg}
        </div>
      )}

      <div className="grid-connections-layout">
        {/* Left nav — hidden on mobile */}
        <nav className="desktop-side-nav" style={{
          background: "var(--surface)",
          borderRight: "1px solid var(--border)",
          padding: "16px 8px",
          position: "sticky",
          top: "48px",
          height: "calc(100vh - 48px)",
          overflow: "auto",
        }}>
          {NAV_ITEMS.map((item) => {
            const isActive = item.id === activeSection
            return (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                style={{
                  display: "block",
                  width: "100%",
                  textAlign: "left",
                  padding: "6px 10px",
                  borderRadius: "5px",
                  border: "none",
                  background: isActive ? "var(--accent-soft)" : "transparent",
                  color: isActive ? "var(--accent-strong)" : "var(--fg-2)",
                  fontSize: "13px",
                  fontWeight: isActive ? 500 : 400,
                  cursor: "pointer",
                  marginBottom: "1px",
                }}
              >
                {item.label}
              </button>
            )
          })}
        </nav>

        {/* Content column */}
        <div style={{ minWidth: 0 }}>
          {/* Mobile tabs — shown only on mobile */}
          <div className="mobile-nav-tabs">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                className={item.id === activeSection ? "tab-active" : undefined}
              >
                {item.label}
              </button>
            ))}
          </div>

          {/* Main content */}
          <div className="page-content" style={{ maxWidth: "900px", display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Header */}
          <div>
            <h1 style={{
              fontSize: "24px",
              fontWeight: 600,
              fontFamily: "var(--font-display)",
              color: "var(--fg)",
              margin: 0,
              letterSpacing: "-0.02em",
            }}>
              {activeSection === "repositorios" ? s.title : NAV_ITEMS.find((n) => n.id === activeSection)?.label}
            </h1>
            <p style={{ fontSize: "13.5px", color: "var(--muted)", marginTop: "4px", marginBottom: 0, maxWidth: "640px" }}>
              {s.description}
            </p>
          </div>

          {activeSection === "repositorios" && (
            <>
              {/* Connected SCM accounts */}
              {connections.filter((c) => SCM_PLATFORMS.has(c.platform)).length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                  <h2 style={SECTION_LABEL_STYLE}>
                    {s.connected_accounts}
                  </h2>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {connections.filter((c) => SCM_PLATFORMS.has(c.platform)).map((c) => (
                      <ConnectionCard key={c.id} connection={c} onUpdated={refresh} />
                    ))}
                  </div>
                </div>
              )}

              {/* SCM platform cards */}
              <div className="grid-2col" style={{ gap: "14px" }}>
                {platforms.filter((p) => SCM_PLATFORMS.has(p.platform)).map((p) => (
                  <PlatformCard
                    key={p.platform}
                    platform={p}
                    connections={connections.filter((c) => SCM_PLATFORMS.has(c.platform))}
                    onUpdated={refresh}
                    onOpenHelp={setHelpPlatform}
                  />
                ))}
              </div>
            </>
          )}

          {activeSection === "herramientas" && (() => {
            const jiraConns = connections.filter((c) => !SCM_PLATFORMS.has(c.platform))
            const azureConn = connections.find((c) => c.platform === "azure_devops") ?? null
            const hasJira = jiraConns.length > 0
            // Azure Boards counts as a configured management tool only when boards_project is set
            const azureBoardsConns = connections.filter((c) => c.platform === "azure_devops" && c.boards_project)
            // Jira takes priority: if Jira is connected, hide Azure Boards from connected accounts
            const showAzureBoardsAccount = !!azureConn && !hasJira
            const mgmtAccounts = [
              ...(showAzureBoardsAccount ? [{ conn: azureConn, boards: true }] : []),
              ...jiraConns.map((c) => ({ conn: c, boards: false })),
            ]

            return (
              <>
                {/* Connected management tool accounts — at most ONE shown */}
                {mgmtAccounts.length > 0 && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                    <h2 style={SECTION_LABEL_STYLE}>{s.connected_accounts}</h2>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                      {mgmtAccounts.map(({ conn, boards }) => (
                        <ConnectionCard
                          key={boards ? `boards-${conn.id}` : conn.id}
                          connection={conn}
                          onUpdated={refresh}
                          boardsMode={boards}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Management tool platform cards */}
                <div className="grid-2col" style={{ gap: "14px" }}>
                  {/* Azure Boards — disabled when Jira is already connected */}
                  {platforms.filter((p) => p.platform === "azure_devops").map((p) => (
                    <PlatformCard
                      key="azure_boards"
                      platform={p}
                      connections={[...(azureConn ? [azureConn] : []), ...jiraConns]}
                      onUpdated={refresh}
                      onOpenHelp={setHelpPlatform}
                      boardsMode
                    />
                  ))}
                  {/* Jira — disabled when Azure Boards is configured (boards_project set) */}
                  {platforms.filter((p) => !SCM_PLATFORMS.has(p.platform)).map((p) => (
                    <PlatformCard
                      key={p.platform}
                      platform={p}
                      connections={[...jiraConns, ...azureBoardsConns]}
                      onUpdated={refresh}
                      onOpenHelp={setHelpPlatform}
                    />
                  ))}
                </div>
              </>
            )
          })()}
          </div>
        </div>
      </div>

      <PatHelpDrawer
        platform={helpPlatform}
        onClose={() => setHelpPlatform(null)}
      />
    </>
  )
}

export default function ConnectionsPage() {
  return (
    <Suspense>
      <ConnectionsContent />
    </Suspense>
  )
}
