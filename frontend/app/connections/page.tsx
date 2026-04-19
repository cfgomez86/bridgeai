"use client"

import { useState, useEffect, useCallback, useRef, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import {
  listPlatforms, listConnections,
  getOAuthAuthorizeUrl, savePlatformConfig, deletePlatformConfig, deleteConnection,
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
  const [editing, setEditing] = useState(false)
  const [clientId, setClientId] = useState(platform.client_id ?? "")
  const [clientSecret, setClientSecret] = useState("")
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { t } = useLanguage()
  const s = t.connections

  const isReady = platform.configured || platform.server_configured
  const conn = connections.find((c) => c.platform === platform.platform)

  const tone: PlatformTone = conn ? "ok" : isReady ? "warn" : "neutral"
  const statusLabel = conn ? s.status.connected : isReady ? s.status.configured : s.status.disconnected

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

  async function handleSave() {
    if (!clientId.trim() || !clientSecret.trim()) return
    setSaving(true)
    setError(null)
    try {
      await savePlatformConfig(platform.platform, clientId.trim(), clientSecret.trim())
      setEditing(false)
      setClientSecret("")
      onUpdated()
    } catch (err) {
      setError(err instanceof Error ? err.message : s.errors.save)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    setSaving(true)
    setError(null)
    try {
      await deletePlatformConfig(platform.platform)
      setEditing(false)
      setClientId("")
      setClientSecret("")
      onUpdated()
    } catch (err) {
      setError(err instanceof Error ? err.message : s.errors.delete)
    } finally {
      setSaving(false)
    }
  }

  async function handleDisconnect() {
    if (!conn) return
    setDisconnecting(true)
    setError(null)
    try {
      await deleteConnection(conn.id)
      onUpdated()
    } catch (err) {
      setError(err instanceof Error ? err.message : s.errors.disconnect)
    } finally {
      setDisconnecting(false)
    }
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

      {/* BridgeAI OAuth mode */}
      {platform.server_configured && (
        <div style={{
          border: "1px solid var(--border)", borderRadius: "var(--radius)",
          overflow: "hidden",
        }}>
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "8px 12px", background: "var(--surface-2)", gap: "10px",
          }}>
            <div>
              <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--fg)", display: "flex", alignItems: "center", gap: "6px" }}>
                {s.oauth.bridge_title}
                <span style={{
                  fontSize: "10px", padding: "1px 6px", borderRadius: "3px",
                  background: !platform.configured ? "var(--accent-soft)" : "var(--surface-3)",
                  color: !platform.configured ? "var(--accent-strong)" : "var(--muted)",
                  fontFamily: "var(--font-mono)",
                }}>
                  {!platform.configured ? s.oauth.active_tag : s.oauth.fallback_tag}
                </span>
              </div>
              <div style={{ fontSize: "11px", color: "var(--muted)", marginTop: "1px" }}>
                {s.oauth.bridge_desc}
              </div>
            </div>
            {!conn && (
              <button
                onClick={handleConnect}
                disabled={connecting || !!platform.configured}
                title={platform.configured ? t.connections.actions.connect : ""}
                style={{
                  padding: "4px 10px", borderRadius: "var(--radius)", border: "none",
                  background: platform.configured ? "var(--surface-3)" : "var(--accent)",
                  color: platform.configured ? "var(--muted)" : "var(--accent-fg)",
                  fontSize: "12px", fontWeight: 500, flexShrink: 0,
                  cursor: platform.configured ? "not-allowed" : connecting ? "not-allowed" : "pointer",
                }}
              >
                {connecting && !platform.configured ? s.actions.connecting : s.actions.connect}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Own OAuth App (BYOA) */}
      <div style={{
        border: "1px solid var(--border)", borderRadius: "var(--radius)",
        overflow: "hidden",
      }}>
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "8px 12px", background: "var(--surface-2)", gap: "10px",
        }}>
          <div>
            <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--fg)", display: "flex", alignItems: "center", gap: "6px" }}>
              {s.oauth.own_app_title}
              {platform.configured && (
                <span style={{
                  fontSize: "10px", padding: "1px 6px", borderRadius: "3px",
                  background: "var(--accent-soft)", color: "var(--accent-strong)",
                  fontFamily: "var(--font-mono)",
                }}>{s.oauth.active_tag}</span>
              )}
            </div>
            <div style={{ fontSize: "11px", color: "var(--muted)", marginTop: "1px" }}>
              {platform.configured
                ? `Client ID: ${platform.client_id?.slice(0, 8)}…`
                : s.oauth.not_configured}
            </div>
          </div>
          <div style={{ display: "flex", gap: "5px", flexShrink: 0 }}>
            {!conn && platform.configured && (
              <button
                onClick={handleConnect}
                disabled={connecting}
                style={{
                  padding: "4px 10px", borderRadius: "var(--radius)", border: "none",
                  background: "var(--accent)", color: "var(--accent-fg)",
                  fontSize: "12px", fontWeight: 500,
                  cursor: connecting ? "not-allowed" : "pointer",
                }}
              >
                {connecting ? s.actions.connecting : s.actions.connect}
              </button>
            )}
            <button
              onClick={() => setEditing((v) => !v)}
              style={{
                padding: "4px 10px", borderRadius: "var(--radius)",
                border: "1px solid var(--border)", background: "var(--surface)",
                color: "var(--fg-2)", fontSize: "12px", cursor: "pointer",
              }}
            >
              {editing ? s.actions.cancel : platform.configured ? s.actions.edit : s.actions.configure}
            </button>
          </div>
        </div>

        {/* Inline form */}
        {editing && (
          <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: "7px", borderTop: "1px solid var(--border)" }}>
            <input
              placeholder="Client ID"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              style={{
                padding: "6px 10px", borderRadius: "var(--radius)",
                border: "1px solid var(--border)", background: "var(--surface)",
                color: "var(--fg)", fontSize: "13px", outline: "none", width: "100%", boxSizing: "border-box",
              }}
            />
            <input
              type="password"
              placeholder="Client Secret"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              style={{
                padding: "6px 10px", borderRadius: "var(--radius)",
                border: "1px solid var(--border)", background: "var(--surface)",
                color: "var(--fg)", fontSize: "13px", outline: "none", width: "100%", boxSizing: "border-box",
              }}
            />
            <div style={{ display: "flex", gap: "6px" }}>
              <button
                onClick={handleSave}
                disabled={saving || !clientId.trim() || !clientSecret.trim()}
                style={{
                  padding: "5px 12px", borderRadius: "var(--radius)", border: "none",
                  background: "var(--accent)", color: "var(--accent-fg)",
                  fontSize: "12.5px", fontWeight: 500, cursor: "pointer",
                }}
              >
                {saving ? s.actions.saving : s.actions.save}
              </button>
              <button
                onClick={() => { setEditing(false); setError(null) }}
                style={{
                  padding: "5px 12px", borderRadius: "var(--radius)",
                  border: "1px solid var(--border)", background: "var(--surface)",
                  color: "var(--fg-2)", fontSize: "12.5px", cursor: "pointer",
                }}
              >
                {s.actions.cancel}
              </button>
              {platform.configured && (
                <button
                  onClick={handleDelete}
                  disabled={saving}
                  style={{
                    padding: "5px 12px", borderRadius: "var(--radius)",
                    border: "1px solid var(--border)", background: "var(--surface)",
                    color: "var(--err-fg)", fontSize: "12.5px", cursor: "pointer", marginLeft: "auto",
                  }}
                >
                  {s.actions.delete}
                </button>
              )}
            </div>
          </div>
        )}
      </div>

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
      {!conn && !isReady && (
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
  const [platforms, setPlatforms] = useState<PlatformResponse[]>([])
  const [connections, setConnections] = useState<ConnectionResponse[]>([])
  const [toast, setToast] = useState<{ msg: string; tone: "ok" | "err" } | null>(null)
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const { t } = useLanguage()
  const s = t.connections

  const refresh = useCallback(async () => {
    const [p, c] = await Promise.all([listPlatforms(), listConnections()])
    setPlatforms(p)
    setConnections(c)
  }, [])

  useEffect(() => { refresh() }, [refresh])

  useEffect(() => {
    const connected = searchParams.get("connected")
    const error = searchParams.get("error")
    if (connected) {
      setToast({ msg: `${s.toast_connected} ${PLATFORM_LABELS[connected] ?? connected}`, tone: "ok" })
      refresh()
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
  }, [searchParams, refresh, s.toast_connected, s.toast_error])

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
