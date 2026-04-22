"use client"

import { useState, useEffect, useCallback, useRef, Suspense } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { useAuth } from "@clerk/nextjs"
import {
  listPlatforms, listConnections,
  getOAuthAuthorizeUrl, deleteConnection,
  type PlatformResponse, type ConnectionResponse,
} from "@/lib/api-client"
import { useLanguage } from "@/lib/i18n"
import { BadgeStatus } from "@/components/ui/badge-status"
import { ConnectionCard } from "@/components/features/connections/ConnectionCard"

const PLATFORM_LABELS: Record<string, string> = {
  github: "GitHub",
  gitlab: "GitLab",
  azure_devops: "Azure DevOps",
  bitbucket: "Bitbucket",
}

const PLATFORM_ICONS: Record<string, string> = {
  github: "GH",
  gitlab: "GL",
  azure_devops: "AZ",
  bitbucket: "BB",
}

type PlatformTone = "ok" | "warn" | "neutral"

function PlatformCardDesign({
  platform,
  connections,
  onUpdated,
}: {
  platform: PlatformResponse
  connections: ConnectionResponse[]
  onUpdated: () => void
}) {
  const [connecting, setConnecting] = useState(false)
  const [disconnecting, setDisconnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { t } = useLanguage()
  const s = t.connections

  const conn = connections.find((c) => c.platform === platform.platform)
  const tone: PlatformTone = conn ? "ok" : platform.server_configured ? "warn" : "neutral"
  const statusLabel = conn ? s.status.connected : platform.server_configured ? s.status.configured : s.status.disconnected

  async function handleConnect() {
    setConnecting(true)
    setError(null)
    try {
      const { url } = await getOAuthAuthorizeUrl(platform.platform)
      window.location.href = url
    } catch (err) {
      setError(err instanceof Error ? err.message : s.errors.oauth)
      setConnecting(false)
    }
  }

  async function handleDisconnect() {
    if (!conn) return
    setDisconnecting(true)
    setError(null)
    try {
      await deleteConnection(conn.id)
    } catch (err) {
      // 404 means already deleted — desired state achieved, not an error
      const msg = err instanceof Error ? err.message : ""
      if (!msg.includes("404") && !msg.toLowerCase().includes("not found")) {
        setError(msg || s.errors.disconnect)
        setDisconnecting(false)
        return
      }
    }
    onUpdated()
    setDisconnecting(false)
  }

  const platformDesc = s.platform_desc[platform.platform as keyof typeof s.platform_desc] ?? s.default_platform_desc

  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius-lg)",
      padding: "16px",
      boxShadow: "var(--shadow-sm)",
      display: "flex",
      flexDirection: "column",
      gap: "12px",
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
        <div style={{
          width: "40px",
          height: "40px",
          borderRadius: "8px",
          background: "var(--surface-2)",
          border: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "11px",
          fontWeight: 700,
          color: "var(--fg-2)",
          fontFamily: "var(--font-mono)",
          flexShrink: 0,
        }}>
          {PLATFORM_ICONS[platform.platform] ?? "??"}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "2px" }}>
            <span style={{ fontSize: "14px", fontWeight: 600, fontFamily: "var(--font-display)", color: "var(--fg)" }}>
              {platform.label}
            </span>
            <BadgeStatus tone={tone} label={statusLabel} />
          </div>
          <p style={{ fontSize: "12px", color: "var(--muted)", margin: 0, lineHeight: 1.4 }}>
            {platformDesc}
          </p>
        </div>
      </div>

      {error && (
        <div style={{ padding: "8px 10px", borderRadius: "var(--radius)", background: "var(--err-bg)", color: "var(--err-fg)", fontSize: "12px" }}>
          {error}
        </div>
      )}

      {/* BridgeAI OAuth */}
      {platform.server_configured && !conn && (
        <button
          onClick={handleConnect}
          disabled={connecting}
          style={{
            padding: "5px 12px", borderRadius: "var(--radius)", border: "none",
            background: "var(--accent)", color: "var(--accent-fg)",
            fontSize: "12.5px", fontWeight: 500, alignSelf: "flex-start",
            cursor: connecting ? "not-allowed" : "pointer",
          }}
        >
          {connecting ? s.actions.connecting : s.actions.connect}
        </button>
      )}

      {/* Disconnect (if active connection) */}
      {conn && (
        <button
          onClick={handleDisconnect}
          disabled={disconnecting}
          style={{
            padding: "5px 12px", borderRadius: "var(--radius)",
            border: "1px solid var(--err-bg)", background: "var(--err-bg)",
            color: "var(--err-fg)", fontSize: "12.5px", fontWeight: 500,
            cursor: disconnecting ? "not-allowed" : "pointer", alignSelf: "flex-start",
          }}
        >
          {disconnecting ? s.actions.disconnecting : s.actions.disconnect}
        </button>
      )}

      {/* Connect (no connection, not ready) */}
      {!conn && !platform.server_configured && (
        <button
          disabled
          style={{
            padding: "5px 12px", borderRadius: "var(--radius)", border: "none",
            background: "var(--surface-3)", color: "var(--muted)",
            fontSize: "12.5px", fontWeight: 500, cursor: "not-allowed",
          }}
        >
          {s.actions.connect_first}
        </button>
      )}
    </div>
  )
}

function ConnectionsContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const { isLoaded, isSignedIn } = useAuth()
  const [platforms, setPlatforms] = useState<PlatformResponse[]>([])
  const [connections, setConnections] = useState<ConnectionResponse[]>([])
  const [toast, setToast] = useState<{ msg: string; tone: "ok" | "err" } | null>(null)
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

    // Clear params from URL immediately so StrictMode double-mount doesn't re-process them
    router.replace("/connections", { scroll: false })

    if (connected) {
      setToast({ msg: `${s.toast_connected} ${PLATFORM_LABELS[connected] ?? connected}`, tone: "ok" })
      // Only refresh now if Clerk is already loaded — otherwise the isLoaded/isSignedIn
      // effect will fire refresh() once Clerk finishes initializing after the OAuth redirect.
      if (isLoaded && isSignedIn) refresh()
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
      toastTimerRef.current = setTimeout(() => setToast(null), 5000)
    } else if (error) {
      setToast({ msg: `${s.toast_error} ${PLATFORM_LABELS[error] ?? error}`, tone: "err" })
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
      toastTimerRef.current = setTimeout(() => setToast(null), 6000)
    }
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    }
  }, [searchParams, router, refresh, isLoaded, isSignedIn, s.toast_connected, s.toast_error])

  return (
    <div style={{ padding: "28px 32px", maxWidth: "1100px", display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Toast */}
      {toast && (
        <div style={{
          position: "fixed",
          top: "16px",
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

      {/* Header */}
      <div>
        <h1 style={{
          fontSize: "20px",
          fontWeight: 700,
          fontFamily: "var(--font-display)",
          color: "var(--fg)",
          margin: 0,
          letterSpacing: "-0.01em",
        }}>{s.title}</h1>
        <p style={{ fontSize: "13px", color: "var(--muted)", marginTop: "4px", marginBottom: 0 }}>
          {s.description}
        </p>
      </div>

      {/* Connected accounts */}
      {connections.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <h2 style={{ fontSize: "13px", fontWeight: 600, color: "var(--fg-2)", margin: 0, textTransform: "uppercase", letterSpacing: "0.06em" }}>
            {s.connected_accounts}
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {connections.map((c) => (
              <ConnectionCard key={c.id} connection={c} onUpdated={refresh} />
            ))}
          </div>
        </div>
      )}

      {/* Platform cards grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
        {platforms.map((p) => (
          <PlatformCardDesign key={p.platform} platform={p} connections={connections} onUpdated={refresh} />
        ))}
        {/* Placeholder for future platforms */}
        {["bitbucket"].filter(id => !platforms.find(p => p.platform === id)).map((id) => {
          const desc = s.platform_desc[id as keyof typeof s.platform_desc] ?? s.default_platform_desc
          return (
            <div key={id} style={{
              background: "var(--surface)",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-lg)",
              padding: "16px",
              opacity: 0.6,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div style={{
                  width: "40px", height: "40px", borderRadius: "8px",
                  background: "var(--surface-2)", border: "1px solid var(--border)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "11px", fontWeight: 700, color: "var(--muted)", fontFamily: "var(--font-mono)",
                }}>
                  {PLATFORM_ICONS[id] ?? "??"}
                </div>
                <div>
                  <div style={{ fontSize: "14px", fontWeight: 600, color: "var(--fg-2)", fontFamily: "var(--font-display)" }}>
                    {PLATFORM_LABELS[id]}
                  </div>
                  <div style={{ fontSize: "12px", color: "var(--muted)", marginTop: "2px" }}>
                    {desc}
                  </div>
                </div>
              </div>
              <div style={{ marginTop: "12px" }}>
                <button disabled style={{
                  padding: "5px 12px",
                  borderRadius: "var(--radius)",
                  border: "1px solid var(--border)",
                  background: "var(--surface-3)",
                  color: "var(--muted)",
                  fontSize: "12.5px",
                  cursor: "not-allowed",
                }}>
                  {s.coming_soon}
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function ConnectionsPage() {
  return (
    <Suspense>
      <ConnectionsContent />
    </Suspense>
  )
}
