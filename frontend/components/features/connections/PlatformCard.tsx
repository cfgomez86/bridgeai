"use client"

import { useState, useRef, useCallback } from "react"
import { useLanguage } from "@/lib/i18n"
import {
  getOAuthAuthorizeUrl,
  deleteConnection,
  createPATConnection,
  type PlatformResponse,
  type ConnectionResponse,
} from "@/lib/api-client"
import { PlatformLogo } from "./PlatformLogos"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PlatformCardProps {
  platform: PlatformResponse
  connections: ConnectionResponse[]
  onUpdated: () => void
  onOpenHelp: (platform: string) => void
  boardsMode?: boolean
}

type TabMethod = "oauth" | "pat"

// ---------------------------------------------------------------------------
// Scopes per platform
// ---------------------------------------------------------------------------

const PLATFORM_SCOPES: Record<string, string[]> = {
  github:       ["repo", "read:user"],
  gitlab:       ["read_api", "read_repository", "read_user"],
  azure_devops: ["Code › Read", "User Profile › Read", "Work Items › Read & Write"],
  bitbucket:    ["Repositories › Read", "Account › Read"],
  jira:         ["read:jira-work", "read:jira-user"],
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PlatformCard({ platform, connections, onUpdated, onOpenHelp, boardsMode = false }: PlatformCardProps) {
  const { t, locale } = useLanguage()
  const s = t.connections

  const isGitHub    = platform.platform === "github"
  const isGitLab    = platform.platform === "gitlab"
  const isAzure     = platform.platform === "azure_devops"
  const isBitbucket = platform.platform === "bitbucket"
  const isJira      = platform.platform === "jira"
  const defaultMethod: TabMethod = isGitLab ? "pat" : "oauth"

  const [method, setMethod] = useState<TabMethod>(defaultMethod)
  const [connecting, setConnecting] = useState(false)
  const [disconnecting, setDisconnecting] = useState(false)
  const [showToken, setShowToken] = useState(false)
  const [token, setToken] = useState("")
  const [instanceUrl, setInstanceUrl] = useState("")
  const [email, setEmail] = useState("")
  const [error, setError] = useState<string | null>(null)
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const formId = `pat-form-${platform.platform}`

  const showError = useCallback((msg: string) => {
    setError(msg)
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current)
    errorTimerRef.current = setTimeout(() => setError(null), 5000)
  }, [])

  const conn = connections.find((c) => c.platform === platform.platform) ?? null
  const hasAnyActive = connections.length > 0
  const platformLabel = boardsMode ? "Azure Boards" : platform.label
  const platformDesc = boardsMode
    ? s.platform_desc.azure_boards
    : (s.platform_desc[platform.platform as keyof typeof s.platform_desc] ?? s.default_platform_desc)
  const scopes = boardsMode
    ? ["Work Items › Read & Write", "User Profile › Read"]
    : (PLATFORM_SCOPES[platform.platform] ?? [])
  const oauthDisabled       = !platform.server_configured
  const showInstanceUrl     = isGitHub || isGitLab || isAzure || isBitbucket || isJira
  const instanceUrlRequired = isAzure || isJira

  const instanceUrlLabel = isAzure
    ? (locale === "en" ? "Organization URL" : "URL de organización")
    : isJira
      ? (locale === "en" ? "Jira Site URL" : "URL del sitio Jira")
      : isBitbucket
        ? (locale === "en" ? "Instance URL (Data Center)" : "URL de instancia (Data Center)")
        : s.patPanel.instanceLabel

  const instanceUrlPlaceholder = isAzure
    ? "https://dev.azure.com/mi-org"
    : isJira
      ? "https://mi-org.atlassian.net"
      : isGitHub
        ? "https://github.acme.io"
        : isBitbucket
          ? "https://bitbucket.acme.io"
          : "https://gitlab.acme.io"

  // Status badge — only shown when connected
  const statusBg = "var(--ok-bg)"
  const statusColor = "var(--ok-fg)"
  const statusLabel = s.status.connected

  async function handleOAuthConnect() {
    setConnecting(true)
    setError(null)
    try {
      const { url } = await getOAuthAuthorizeUrl(platform.platform)
      window.location.href = url
    } catch (err) {
      showError(err instanceof Error ? err.message : s.errors.oauth)
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
      const msg = err instanceof Error ? err.message : ""
      if (!msg.includes("404") && !msg.toLowerCase().includes("not found")) {
        showError(msg || s.errors.disconnect)
        setDisconnecting(false)
        return
      }
    }
    onUpdated()
    setDisconnecting(false)
  }

  async function handlePATConnect(e: React.FormEvent) {
    e.preventDefault()
    if (!token.trim()) return
    setConnecting(true)
    setError(null)
    try {
      await createPATConnection(platform.platform, {
        token: token.trim(),
        instance_url: instanceUrl.trim() || undefined,
        email: email.trim() || undefined,
      })
      setToken("")
      setInstanceUrl("")
      setEmail("")
      onUpdated()
    } catch (err) {
      showError(err instanceof Error ? err.message : s.errors.oauth)
    } finally {
      setConnecting(false)
    }
  }

  return (
    <>
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius-lg)",
      overflow: "hidden",
    }}>
      {/* ── Header ── */}
      <div style={{ padding: "18px 18px 0", display: "flex", alignItems: "flex-start", gap: "12px" }}>
        {/* Logo */}
        <div style={{
          width: "40px",
          height: "40px",
          borderRadius: "8px",
          background: "var(--surface-2)",
          border: "1px solid var(--border)",
          display: "grid",
          placeItems: "center",
          flexShrink: 0,
          color: isGitHub ? "var(--fg)" : undefined,
        }}>
          <PlatformLogo platform={platform.platform} />
        </div>

        {/* Info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" as const }}>
            <b style={{ fontFamily: "var(--font-display)", fontSize: "15px", fontWeight: 600, color: "var(--fg)" }}>
              {platformLabel}
            </b>
            {conn && (
              <span style={{
                padding: "1px 7px",
                borderRadius: "4px",
                fontSize: "11px",
                fontWeight: 500,
                background: statusBg,
                color: statusColor,
                fontFamily: "var(--font-mono)",
              }}>
                {statusLabel}
              </span>
            )}
          </div>
          <p style={{ fontSize: "13px", color: "var(--fg-2)", margin: "4px 0 0", lineHeight: 1.4 }}>
            {platformDesc}
          </p>
        </div>

        {/* View guide button */}
        <button
          type="button"
          onClick={() => onOpenHelp(boardsMode ? "azure_boards" : platform.platform)}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "5px",
            padding: "4px 9px",
            borderRadius: "999px",
            border: "1px solid var(--border)",
            background: "var(--surface-2)",
            color: "var(--fg-2)",
            fontSize: "11px",
            cursor: "pointer",
            flexShrink: 0,
            alignSelf: "flex-start",
            fontFamily: "var(--font-sans)",
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 8v4M12 16h.01" />
          </svg>
          {s.viewGuide}
        </button>
      </div>

      {/* ── Tabs ── */}
      <div style={{ display: "flex", borderTop: "1px solid var(--border)", marginTop: "14px", background: "var(--surface-2)" }}>
        {(["oauth", "pat"] as const).map((tab) => {
          const isActive = method === tab
          const isDisabled = tab === "oauth" && oauthDisabled
          return (
            <button
              key={tab}
              type="button"
              onClick={() => !isDisabled && setMethod(tab)}
              disabled={isDisabled}
              style={{
                flex: 1,
                height: "38px",
                border: "none",
                borderBottom: isActive ? "2px solid var(--accent)" : "2px solid transparent",
                background: isActive ? "var(--surface)" : "transparent",
                color: isDisabled ? "var(--muted-2)" : isActive ? "var(--fg)" : "var(--muted)",
                fontSize: "12px",
                fontWeight: isActive ? 600 : 500,
                cursor: isDisabled ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "6px",
                opacity: isDisabled ? 0.6 : 1,
                fontFamily: "var(--font-sans)",
              }}
            >
              {tab === "oauth" ? (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
                  <path d="M20.618 5.984A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.623C17.176 19.29 21 14.59 21 9a12.02 12.02 0 00-.382-3.016z" />
                </svg>
              ) : (
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
                  <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
                </svg>
              )}
              {tab === "oauth" ? s.tabs.oauth : s.tabs.pat}
            </button>
          )
        })}
      </div>

      {/* ── Panel body ── */}
      <div style={{ padding: "14px" }}>
        {error && (
          <div style={{
            marginBottom: "12px",
            padding: "8px 10px",
            borderRadius: "var(--radius)",
            background: "var(--err-bg)",
            color: "var(--err-fg)",
            fontSize: "12px",
          }}>
            {error}
          </div>
        )}

        {/* OAuth Panel */}
        {method === "oauth" && (
          <div>

          </div>
        )}

        {/* PAT Panel */}
        {method === "pat" && !conn && (
          <form id={formId} onSubmit={handlePATConnect} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {/* Token input */}
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <label style={{ fontSize: "11.5px", fontWeight: 500, color: "var(--fg-2)" }}>
                {s.patPanel.tokenLabel}
              </label>
              <div style={{ position: "relative" }}>
                <input
                  type={showToken ? "text" : "password"}
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="Pega tu token aquí..."
                  required
                  style={{
                    width: "100%",
                    padding: "6px 32px 6px 9px",
                    borderRadius: "var(--radius)",
                    border: "1px solid var(--border)",
                    background: "var(--surface-2)",
                    color: "var(--fg)",
                    fontSize: "12.5px",
                    outline: "none",
                    fontFamily: "var(--font-mono)",
                    boxSizing: "border-box" as const,
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowToken((v) => !v)}
                  style={{
                    position: "absolute",
                    right: "6px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    padding: "3px",
                    background: "transparent",
                    border: "none",
                    color: "var(--muted)",
                    cursor: "pointer",
                  }}
                  aria-label={showToken ? "Ocultar token" : "Mostrar token"}
                >
                  {showToken ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24M1 1l22 22" />
                    </svg>
                  ) : (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {/* Instance URL */}
            {showInstanceUrl && (
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <label style={{ fontSize: "11.5px", fontWeight: 500, color: "var(--fg-2)", display: "flex", alignItems: "center", gap: "4px" }}>
                  {instanceUrlLabel}
                  {!instanceUrlRequired && (
                    <span style={{ fontSize: "10.5px", color: "var(--muted)", fontWeight: 400 }}>
                      {s.patPanel.instanceOptional}
                    </span>
                  )}
                </label>
                <input
                  type="url"
                  value={instanceUrl}
                  onChange={(e) => setInstanceUrl(e.target.value)}
                  placeholder={instanceUrlPlaceholder}
                  required={instanceUrlRequired}
                  style={{
                    width: "100%",
                    padding: "6px 9px",
                    borderRadius: "var(--radius)",
                    border: "1px solid var(--border)",
                    background: "var(--surface-2)",
                    color: "var(--fg)",
                    fontSize: "12.5px",
                    outline: "none",
                    fontFamily: "var(--font-mono)",
                    boxSizing: "border-box" as const,
                  }}
                />
              </div>
            )}

            {/* Email (Jira only) */}
            {isJira && (
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <label style={{ fontSize: "11.5px", fontWeight: 500, color: "var(--fg-2)" }}>
                  {locale === "en" ? "Atlassian Email" : "Email de Atlassian"}
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="user@example.com"
                  required
                  style={{
                    width: "100%",
                    padding: "6px 9px",
                    borderRadius: "var(--radius)",
                    border: "1px solid var(--border)",
                    background: "var(--surface-2)",
                    color: "var(--fg)",
                    fontSize: "12.5px",
                    outline: "none",
                    fontFamily: "var(--font-sans)",
                    boxSizing: "border-box" as const,
                  }}
                />
              </div>
            )}

            {/* Scopes */}
            {scopes.length > 0 && (
              <div style={{
                marginTop: "4px",
                padding: "9px 10px",
                background: "var(--surface-2)",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius)",
              }}>
                <div style={{
                  fontSize: "11px",
                  fontWeight: 500,
                  color: "var(--muted)",
                  marginBottom: "6px",
                  display: "flex",
                  alignItems: "center",
                  gap: "5px",
                }}>
                  <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
                    <rect x="3" y="11" width="18" height="11" rx="2" />
                    <path d="M7 11V7a5 5 0 0110 0v4" />
                  </svg>
                  {s.patPanel.scopesLabel}
                </div>
                <div style={{ display: "flex", flexWrap: "wrap" as const, gap: "4px" }}>
                  {scopes.map((scope) => (
                    <span key={scope} style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "10.5px",
                      fontWeight: 500,
                      padding: "2px 7px",
                      background: "var(--surface)",
                      border: "1px solid var(--border)",
                      borderRadius: "4px",
                      color: "var(--fg-2)",
                    }}>
                      {scope}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </form>
        )}

      </div>

      {/* ── Footer ── */}
      <div style={{
        padding: "12px 18px 14px",
        display: "flex",
        alignItems: "center",
        gap: "8px",
        borderTop: "1px solid var(--border)",
      }}>
        {/* OAuth connect / disconnect */}
        {method === "oauth" && !conn && !oauthDisabled && (
          <button
            type="button"
            onClick={handleOAuthConnect}
            disabled={connecting || hasAnyActive}
            title={hasAnyActive ? s.actions.one_active : undefined}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              height: "34px",
              padding: "0 14px",
              borderRadius: "var(--radius)",
              border: "none",
              background: (connecting || hasAnyActive) ? "var(--surface-3)" : "var(--accent)",
              color: (connecting || hasAnyActive) ? "var(--muted)" : "var(--accent-fg)",
              fontSize: "12.5px",
              fontWeight: 500,
              cursor: (connecting || hasAnyActive) ? "not-allowed" : "pointer",
              fontFamily: "var(--font-sans)",
            }}
          >
            {connecting ? s.actions.connecting : s.oauthPanel.connect}
          </button>
        )}

        {method === "oauth" && conn && (
          <button
            type="button"
            onClick={handleDisconnect}
            disabled={disconnecting}
            style={{
              display: "inline-flex",
              alignItems: "center",
              height: "34px",
              padding: "0 14px",
              borderRadius: "var(--radius)",
              border: "1px solid var(--err-bg)",
              background: "var(--err-bg)",
              color: "var(--err-fg)",
              fontSize: "12.5px",
              fontWeight: 500,
              cursor: disconnecting ? "not-allowed" : "pointer",
              fontFamily: "var(--font-sans)",
            }}
          >
            {disconnecting ? s.actions.disconnecting : s.oauthPanel.disconnect}
          </button>
        )}

        {/* PAT connect / disconnect */}
        {method === "pat" && !conn && (
          <button
            type="submit"
            form={formId}
            disabled={connecting || !token.trim() || (instanceUrlRequired && !instanceUrl.trim()) || (isJira && !email.trim()) || hasAnyActive}
            title={hasAnyActive ? s.actions.one_active : undefined}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              height: "34px",
              padding: "0 14px",
              borderRadius: "var(--radius)",
              border: "none",
              background: (connecting || !token.trim() || (instanceUrlRequired && !instanceUrl.trim()) || (isJira && !email.trim()) || hasAnyActive) ? "var(--surface-3)" : "var(--accent)",
              color: (connecting || !token.trim() || (instanceUrlRequired && !instanceUrl.trim()) || (isJira && !email.trim()) || hasAnyActive) ? "var(--muted)" : "var(--accent-fg)",
              fontSize: "12.5px",
              fontWeight: 500,
              cursor: (connecting || !token.trim() || (instanceUrlRequired && !instanceUrl.trim()) || (isJira && !email.trim()) || hasAnyActive) ? "not-allowed" : "pointer",
              fontFamily: "var(--font-sans)",
            }}
          >
            {connecting ? s.actions.connecting : s.patPanel.connect}
          </button>
        )}

        {method === "pat" && conn && (
          <button
            type="button"
            onClick={handleDisconnect}
            disabled={disconnecting}
            style={{
              display: "inline-flex",
              alignItems: "center",
              height: "34px",
              padding: "0 14px",
              borderRadius: "var(--radius)",
              border: "1px solid var(--err-bg)",
              background: "var(--err-bg)",
              color: "var(--err-fg)",
              fontSize: "12.5px",
              fontWeight: 500,
              cursor: disconnecting ? "not-allowed" : "pointer",
              fontFamily: "var(--font-sans)",
            }}
          >
            {disconnecting ? s.actions.disconnecting : s.oauthPanel.disconnect}
          </button>
        )}

      </div>
    </div>

    </>
  )
}
